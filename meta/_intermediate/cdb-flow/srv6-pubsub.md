# SRv6 テーブル群 — 通信メカニズム (Phase G) 解析メモ

対象テーブル:
- CONFIG_DB: `SRV6_MY_SIDS` / `SRV6_MY_LOCATORS`
- APP_DB: `SRV6_SID_LIST_TABLE` / `SRV6_MY_SID_TABLE` / `PIC_CONTEXT_TABLE`

---

## 1. 全体データフロー

```
CONFIG_DB (SRV6_MY_SIDS / SRV6_MY_LOCATORS)
  → bgpcfgd (SRv6Mgr) — keyspace 通知受信
    → FRR zebra/bgpd (vtysh cfg_mgr.push_list() 経由)
      → fpmsyncd (routesync) — FPM/netlink 受信
        → APP_DB (SRV6_SID_LIST_TABLE / SRV6_MY_SID_TABLE / PIC_CONTEXT_TABLE) — ProducerStateTable 書き込み
          → Srv6Orch — ConsumerStateTable (TableConnector) で購読
            → SAI / ASIC
```

---

## 2. CONFIG_DB → bgpcfgd (SRv6Mgr)

### 購読 API

`bgpcfgd/managers_srv6.py` の `SRv6Mgr` クラスは `Manager` 基底クラスを継承し、
`directory.subscribe()` + keyspace 通知パターンで CONFIG_DB 変更を受信する。

```python
# bgpcfgd/managers_srv6.py:62-68
if not self.directory.path_exist(self.db_name, "SRV6_MY_LOCATORS", locator_name):
    if (self.db_name, "SRV6_MY_LOCATORS", locator_name) not in self.deps:
        self.deps.add((self.db_name, "SRV6_MY_LOCATORS", locator_name))
        self.directory.subscribe(
            [(self.db_name, "SRV6_MY_LOCATORS", locator_name)],
            self.on_deps_change
        )
```

- `SRV6_MY_SIDS`: ロケータ名の依存解決後に `sids_set_handler()` が呼ばれる
- `SRV6_MY_LOCATORS`: `locators_set_handler()` が呼ばれ、ロケータ情報をキャッシュ

### bgpcfgd → FRR への伝達

`cfg_mgr.push_list()` で vtysh コマンドリストを FRR bgpd に送信する。

```python
# bgpcfgd/managers_srv6.py:41-50 (locators_set_handler)
cmd_list = ["segment-routing", "srv6"]
cmd_list += ['locators', 'locator {}'.format(locator_name), ...]
self.cfg_mgr.push_list(cmd_list)

# bgpcfgd/managers_srv6.py:88-95 (sids_set_handler)
cmd_list = ['segment-routing', 'srv6', 'static-sids']
cmd_list.append(sid_cmd)
self.cfg_mgr.push_list(cmd_list)
```

- channel 名: bgpcfgd 内部での vtysh CLI ディスパッチ（Redis channel ではない）
- FRR bgpd/zebra が SID/ロケータ情報を受信し、経路制御に反映する

---

## 3. FRR → APP_DB (fpmsyncd/routesync)

### ProducerStateTable 書き込み

`fpmsyncd/routesync.cpp` の `RouteSync` クラスが FPM (Forwarding Plane Manager) インタフェース
経由で FRR (zebra) からのネットリンクメッセージを受信し、APP_DB に書き込む。

```cpp
// fpmsyncd/routesync.cpp:163-164
m_srv6MySidTable(pipeline, APP_SRV6_MY_SID_TABLE_NAME, true),
m_srv6SidListTable(pipeline, APP_SRV6_SID_LIST_TABLE_NAME, true),
// fpmsyncd/routesync.cpp:159
m_pic_context_groupTable(pipeline, APP_PIC_CONTEXT_TABLE_NAME, true),
```

| APP_DB テーブル | 書き込みメソッド | 行番号 (routesync.cpp) |
|----------------|-----------------|----------------------|
| `SRV6_SID_LIST_TABLE` | `m_srv6SidListTable.set()` / `.del()` | 1389, 1424 |
| `SRV6_MY_SID_TABLE` | `m_srv6MySidTable.set()` / `.del()` | 1562, 1667 |
| `PIC_CONTEXT_TABLE` | `m_pic_context_groupTable.set()` / `.del()` | 3389, 3441 |

- `RedisPipeline` 経由でバッチ書き込みを行い、パイプラインフラッシュ間隔は `gFlushTimeout` で制御
- FPM インタフェース: `fpmsyncd/fpmlink.cpp` が TCP ソケット (FPM プロトコル: デフォルト port 2620) で zebra と通信
- ZMQ: route テーブルは `m_zmqClient` (ZMQ) 経由のオプションパスあり。SRv6 テーブルは pipeline 直接書き込み

---

## 4. APP_DB → Srv6Orch (ConsumerStateTable)

### TableConnector による購読

`orchagent/orchdaemon.cpp:312-324` で以下の通り `TableConnector` を用いて購読を設定し、
`Orch(tables)` コンストラクタに渡す。内部で `ConsumerStateTable` として動作する。

```cpp
// orchdaemon.cpp:312-324
TableConnector srv6_sid_list_table(m_applDb, APP_SRV6_SID_LIST_TABLE_NAME);
TableConnector srv6_my_sid_table(m_applDb, APP_SRV6_MY_SID_TABLE_NAME);
TableConnector pic_context_table(m_applDb, APP_PIC_CONTEXT_TABLE_NAME);
TableConnector srv6_my_sid_cfg_table(m_configDb, CFG_SRV6_MY_SID_TABLE_NAME);

vector<TableConnector> srv6_tables = {
    srv6_sid_list_table,
    srv6_my_sid_table,
    pic_context_table,
    srv6_my_sid_cfg_table
};
gSrv6Orch = new Srv6Orch(m_configDb, m_applDb, srv6_tables, ...);
```

- `Orch(tables)` が各 TableConnector を `ConsumerStateTable` + `Executor` に変換
- `Srv6Orch::doTask(Consumer &consumer)` がディスパッチャ役を担い、テーブル名で分岐 (`srv6orch.cpp:2352-2386`)

### doTask ディスパッチ

```cpp
// srv6orch.cpp:2352-2386
void Srv6Orch::doTask(Consumer &consumer) {
    if (table_name == APP_SRV6_SID_LIST_TABLE_NAME)
        status = doTaskSidTable(t);
    else if (table_name == APP_SRV6_MY_SID_TABLE_NAME)
        doTaskMySidTable(t);
    else if (table_name == APP_PIC_CONTEXT_TABLE_NAME)
        status = doTaskPicContextTable(t);
    else if (table_name == CFG_SRV6_MY_SID_TABLE_NAME)
        doTaskCfgMySidTable(t);
}
```

### タイマートリガー

`Srv6Orch::doTask(SelectableTimer &timer)` (`srv6orch.cpp:286`) で定期的なリトライキュー
処理を実行する。`PIC_CONTEXT_TABLE` 参照カウント待ちのエントリはここで再試行される。

---

## 5. Srv6Orch 内部の書き戻し ProducerStateTable

`srv6orch.h:238-240` の member は書き込み用 (`ProducerStateTable`):

```cpp
ProducerStateTable m_sidTable;    // APP_SRV6_SID_LIST_TABLE 書き込み専用
ProducerStateTable m_mysidTable;  // APP_SRV6_MY_SID_TABLE 書き込み専用
ProducerStateTable m_piccontextTable; // APP_PIC_CONTEXT_TABLE 書き込み専用
```

これらは SAI 処理後の状態反映または他コンポーネントへの通知用であり、
購読（Consumer）側は `Orch(tables)` 経由の別チャネルで行われる（二重登録ではない）。

---

## 6. channel 名まとめ

| 経路 | 通信手段 | channel / テーブル |
|------|---------|-------------------|
| CONFIG_DB → bgpcfgd | Redis keyspace notification (`PSUBSCRIBE __keyspace@4__:SRV6_MY_SIDS|*`) | CONFIG_DB dbId=4 |
| CONFIG_DB → bgpcfgd | Redis keyspace notification (`PSUBSCRIBE __keyspace@4__:SRV6_MY_LOCATORS|*`) | CONFIG_DB dbId=4 |
| bgpcfgd → FRR | vtysh TCP ソケット (cfg_mgr.push_list) | 非 Redis |
| FRR zebra → fpmsyncd | FPM TCP ソケット (port 2620, netlink エンコード) | 非 Redis |
| fpmsyncd → APP_DB | `ProducerStateTable` + `RedisPipeline` | `SRV6_SID_LIST_TABLE`, `SRV6_MY_SID_TABLE`, `PIC_CONTEXT_TABLE` |
| APP_DB → Srv6Orch | `ConsumerStateTable` (TableConnector 経由) | 同上 3 テーブル + `CFG_SRV6_MY_SIDS` |
| Srv6Orch → SAI | C++ SAI API 呼び出し | 非 Redis |

---

## 7. NotificationProducer / SubscriberStateTable の非使用確認

- `SRV6_MY_SIDS` / `SRV6_MY_LOCATORS` に対して `SubscriberStateTable` を直接使う箇所は orchagent 内になし
- `NotificationProducer` で SRv6 関連通知を出す箇所はソース内になし
- SRv6 は CONFIG_DB → bgpcfgd → FRR → fpmsyncd → APP_DB の **非同期パイプライン** で動作し、
  STATE_DB への書き戻しは `Srv6Orch` が直接行わない（SAI/ASIC 層で完結）

---

## 8. 参考コード箇所

| ファイル | 行番号 | 内容 |
|---------|--------|------|
| `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_srv6.py` | 14-133 | SRv6Mgr クラス全体 |
| `sonic-swss/fpmsyncd/routesync.cpp` | 155-164 | RouteSync コンストラクタ (ProducerStateTable 初期化) |
| `sonic-swss/fpmsyncd/routesync.cpp` | 1389,1424,1562,1667,3389,3441 | 各テーブルへの set/del |
| `sonic-swss/orchagent/orchdaemon.cpp` | 312-324 | TableConnector + Srv6Orch 初期化 |
| `sonic-swss/orchagent/srv6orch.cpp` | 98-140 | Srv6Orch コンストラクタ |
| `sonic-swss/orchagent/srv6orch.cpp` | 2352-2386 | doTask(Consumer&) ディスパッチャ |
| `sonic-swss/orchagent/srv6orch.h` | 238-242 | ProducerStateTable メンバ (書き込み用) |
| `sonic-swss-common/common/schema.h` | 168-170,398-399 | テーブル名定数 |
