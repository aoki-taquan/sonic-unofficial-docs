# MGMT_VRF_CONFIG テーブル — 通信メカニズム (Phase G) 解析メモ

対象: `CONFIG_DB` の `MGMT_VRF_CONFIG` テーブル。  
ソース: `sonic-swss/cfgmgr/vrfmgr.cpp`, `sonic-swss/cfgmgr/vrfmgrd.cpp`, `sonic-host-services/scripts/hostcfgd`

## 1. 購読者と API 種別

`MGMT_VRF_CONFIG` を購読するコンポーネントは **2 つ**。

### 1-1. vrfmgrd (swss コンテナ) — `Orch` フレームワーク + `ConsumerStateTable`

`vrfmgrd.cpp` は `DBConnector` + `Orch` ベースの C++ ループで動く。

```cpp
// sonic-swss/cfgmgr/vrfmgrd.cpp:29-34
vector<string> cfg_vrf_tables = {
    CFG_VRF_TABLE_NAME,
    CFG_VNET_TABLE_NAME,
    CFG_VXLAN_EVPN_NVO_TABLE_NAME,
    CFG_MGMT_VRF_CONFIG_TABLE_NAME   // ← MGMT_VRF_CONFIG
};
DBConnector cfgDb("CONFIG_DB", 0);
DBConnector appDb("APPL_DB", 0);
DBConnector stateDb("STATE_DB", 0);
VrfMgr vrfmgr(&cfgDb, &appDb, &stateDb, cfg_vrf_tables);
```

- `Orch(cfgDb, tableNames)` コンストラクタが内部で各テーブル名に対して `ConsumerStateTable` (swss の Producer/Consumer チャネル) を生成し `Select` セレクタに登録する。
- `ConsumerStateTable` は Redis の `SUBSCRIBE <TABLE>_KEY_SPACE_NOTIFICATION` (swss 独自プロトコル: `LPUSH`/`RPOP` による双方向チャネル) ではなく、**swss ProducerStateTable** が `XADD` した Redis Stream をコンシュームする方式。
- CONFIG_DB の場合 sonic-cfggen / config CLI が `HSET CONFIG_DB:<TABLE>:<KEY> field value` を直接発行し、swss の `SubscriberStateTable` が keyspace 通知 (`__keyspace@<dbId>__:CFG_MGMT_VRF_CONFIG_TABLE_NAME|*`) を受けてイベントを生成する。
- `select(&sel, SELECT_TIMEOUT=1000ms)` のタイムアウトごとに `vrfmgr.doTask()` を呼び出してキュー残タスクを消化する。

```cpp
// vrfmgrd.cpp:49-83
swss::Select s;
for (Orch *o : cfgOrchList) { s.addSelectables(o->getSelectables()); }
while (true) {
    ret = s.select(&sel, SELECT_TIMEOUT);
    if (ret == Select::TIMEOUT) {
        vrfmgr.doTask();  // ← タイムアウト時にも pending タスクを処理
        ...
        continue;
    }
    auto *c = (Executor *)sel;
    c->execute();  // ← テーブル変化時はここで doTask() が呼ばれる
}
```

### 1-2. hostcfgd (host-services) — `ConfigDBConnector.subscribe()` (keyspace 通知)

`hostcfgd` は Python の `swsscommon.ConfigDBConnector` を使い、keyspace 通知ベースで購読する。

```python
# sonic-host-services/scripts/hostcfgd:2495-2497
# Handle MGMT_VRF_CONFIG changes
self.config_db.subscribe(swsscommon.CFG_MGMT_VRF_CONFIG_TABLE_NAME,
                         make_callback(self.mgmt_vrf_handler))
# ...
self.config_db.listen(init_data_handler=self.load)   # hostcfgd:2528
```

- `ConfigDBConnector.listen()` が内部で Redis の keyspace 通知 (`PSUBSCRIBE __keyspace@<dbId>__:MGMT_VRF_CONFIG|*`) を購読。
- テーブルに変化があると `mgmt_vrf_handler(key, op, data)` が呼ばれる。
- `op` は `data is None` のとき `"DEL"`、それ以外 `"SET"` (HGETALL 結果有無で判定)。

## 2. キー単位ディスパッチ

`make_callback()` ラッパが `(table, key, data)` → `(key, op, data)` に変換する。

```python
# hostcfgd:2454-2466 (共通パターン)
def make_callback(func):
    def callback(table, key, data):
        op = "DEL" if data is None else "SET"
        return func(key, op, data)
    return callback
```

`mgmt_vrf_handler` の実装:

```python
# hostcfgd:2352-2353
def mgmt_vrf_handler(self, key, op, data):
    self.mgmtifacecfg.update_mgmt_vrf(data)
```

`update_mgmt_vrf()` 内でフィールド `mgmtVrfEnabled` を取り出し、変化がある場合のみ処理する。

```python
# hostcfgd:1645-1693
def update_mgmt_vrf(self, data):
    enabled = data.get('mgmtVrfEnabled', '')
    if not enabled or enabled == self.mgmt_vrf_enabled:
        return    # 変化なし / 空文字 → サイレントドロップ
    run_cmd(['systemctl', 'stop', 'chrony'], ...)
    run_cmd(['systemctl', 'restart', 'interfaces-config'], ...)  # ifupdown2 経由で eth0 を mgmt netns へ
    run_cmd(['systemctl', 'start', 'chrony'], ...)
    self.mgmt_vrf_enabled = enabled
    if enabled == 'true':
        # eth0 の default route (metric 202) を削除
        run_cmd(["ip", "-4", "route", "del", "default", "dev", "eth0", "metric", "202"], ...)
```

## 3. vrfmgr.cpp 側の SET/DEL ブランチと kernel netns 制御

`vrfmgrd` の `VrfMgr::doTask()` は `MGMT_VRF_CONFIG` テーブルの変化を受け取ると以下の処理をする。

| op | 条件 | kernel 操作 | APPL_DB 操作 |
|----|------|------------|-------------|
| `SET` (実効) | `mgmtVrfEnabled == "true"` かつ `in_band_mgmt_enabled == "true"` | `setLink("mgmt")` — 内部マップに table_id=6000 を登録 (ip link add は **hostcfgd** 経由) | `APP_VRF_TABLE_NAME` に `set("mgmt", fields)` |
| `SET` → `DEL` 変換 | `mgmtVrfEnabled != "true"` または `in_band_mgmt_enabled != "true"` | DEL 処理へフォールスルー | - |
| `DEL` | STATE_VRF_OBJECT_TABLE に mgmt が存在する間 | 待機 (`it++; continue`) | - |
| `DEL` (実効) | STATE_VRF_OBJECT_TABLE から mgmt が消えた後 | `delLink("mgmt")` — 内部マップから削除 (ip link del は hostcfgd 経由) | `APP_VRF_TABLE_NAME` に `del("mgmt")` |

```cpp
// vrfmgr.cpp:176-183  setLink("mgmt") の特殊処理
if (vrfName == MGMT_VRF) {
    // Mgmt VRF is initialised as part of hostcfgd,
    // just return the reserved table_id for mgmt VRF from here.
    uint32_t table_id = MGMT_VRF_TABLE_ID;   // 6000 (ハードコード)
    m_vrfTableMap.emplace(vrfName, table_id);
    return true;
}
// vrfmgr.cpp:148-153  delLink("mgmt") の特殊処理
if (vrfName == MGMT_VRF) {
    recycleTable(m_vrfTableMap[vrfName]);
    m_vrfTableMap.erase(vrfName);
    return true;   // ip link del は実行しない
}
```

### kernel netns 制御の実態

- `vrfmgr.cpp` 自体は `ip link add/del mgmt` を実行しない。
- **ifupdown2** (`interfaces-config` サービス) が `/etc/network/interfaces` テンプレートを再生成し、`ifupdown2` が `ip vrf exec mgmt ...` でカーネル VRF netns (`mgmt` VRF デバイス, table 6000) を作成する。
- `hostcfgd` の `systemctl restart interfaces-config` がそのトリガー。
- eth0 は `interfaces-config` 再起動後に mgmt VRF デバイスへ enslaved され、ルーティングテーブル 6000 を使うようになる。

## 4. 起動時スナップショット

`hostcfgd` は `listen()` の前に `load()` を呼び、`MGMT_VRF_CONFIG` の現在値を取得して `MgmtIfaceCfg.load()` に渡す。

```python
# hostcfgd:2249, 2268
mgmt_vrf = init_data.get(swsscommon.CFG_MGMT_VRF_CONFIG_TABLE_NAME, {})
self.mgmtifacecfg.load(mgmt_ifc, mgmt_vrf)
```

```python
# hostcfgd:1615-1624
def load(self, mgmt_iface={}, mgmt_vrf={}):
    self.mgmt_vrf_enabled = mgmt_vrf.get('mgmtVrfEnabled', '')
```

起動時は interfaces-config 再起動を行わず、`self.mgmt_vrf_enabled` にキャッシュするのみ。通知ループで受けた差分のみ適用する。

## 5. まとめ

| 側面 | 詳細 |
|------|------|
| 購読 API (vrfmgrd) | `Orch` + `ConsumerStateTable` / Select ループ (C++, 1s タイムアウト) |
| 購読 API (hostcfgd) | `ConfigDBConnector.subscribe()` → keyspace 通知 PSUBSCRIBE (Python) |
| kernel netns 制御 | `interfaces-config` (ifupdown2) restart 経由 — vrfmgr は直接 ip link を叩かない |
| ifupdown | `systemctl restart interfaces-config` で eth0 を mgmt VRF table 6000 へ enslave |
| channel 種別 | CONFIG_DB: HSET → keyspace 通知。APPL_DB: ProducerStateTable (`APP_VRF_TABLE_NAME`) |
