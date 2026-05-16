# VXLAN_FDB_TABLE — Phase A: Implicit Defaults & Code-derived Behaviors

## テーブル位置

`VXLAN_FDB_TABLE` は **APP_DB** に存在するテーブルである（CONFIG_DB ではない）。
`fdbsyncd` が Linux カーネル netlink イベント（RTM_NEWNEIGH / RTM_DELNEIGH）から EVPN 学習 MAC を検知し、`APP_VXLAN_FDB_TABLE_NAME = "VXLAN_FDB_TABLE"` として APP_DB に書き込む。
`orchagent` の `FdbOrch` が `APP_VXLAN_FDB_TABLE` を購読し、SAI FDB エントリを生成する。

コード根拠: `sonic-swss/fdbsyncd/fdbsync.cpp`, `sonic-swss/orchagent/fdborch.cpp`, `sonic-swss-common/common/schema.h:87`

---

## キー構造

```text
VXLAN_FDB_TABLE|<VlanName>:<MAC>
```

例: `VXLAN_FDB_TABLE|Vlan200:00:02:00:00:47:e2`

`fdbsync.cpp:823-825`:
```cpp
key+= vlan_id;   // "VlanXXX"
key+= ":";
key+= macStr;    // "xx:xx:xx:xx:xx:xx"
```

---

## フィールド一覧

| フィールド | 型 | 書き込み元 | 説明 |
|-----------|-----|----------|------|
| `remote_vtep` | IPv4 アドレス文字列 | fdbsyncd | リモート VTEP の IP アドレス |
| `type` | string (`dynamic`\|`static`) | fdbsyncd | FDB エントリ種別 |
| `vni` | string (数値) | fdbsyncd | VxLAN Network Identifier |

---

## コード由来の暗黙デフォルト

### 1. `type` フィールド — netlink state から決定

**根拠**: `fdbsync.cpp:794-802` (onMsgNbr 関数)
```cpp
int state = rtnl_neigh_get_state(neigh);
if (state & NUD_NOARP)
{
    /* This is a static route */
    type = "static";
}
else
{
    type = "dynamic";
}
```

カーネル netlink の `NUD_NOARP` フラグが立っている場合は `"static"`、それ以外はすべて `"dynamic"` となる。EVPN 経由で学習されるリモート MAC は通常 `NUD_NOARP` なし（ARP タイムアウトで消える動的エントリ）のため `"dynamic"` がデフォルト的に使われる。

**分類**: ハードコード決定（netlink state に基づく）

---

### 2. `type` フィールドの fdborch 側デフォルト

**根拠**: `fdborch.cpp:769-770`
```cpp
string type = "dynamic";
```

`FdbOrch::doTask()` で `APP_VXLAN_FDB_TABLE_NAME` からエントリを受け取る際、`type` フィールドが存在しない場合のデフォルトは `"dynamic"` に初期化される。

**根拠**: `fdborch.cpp:829-830`
```cpp
/* FDB type is either dynamic or static */
assert(type == "dynamic" || type == "dynamic_local" || type == "static" );
```

許容値は `"dynamic"` / `"dynamic_local"` / `"static"` の 3 値。`"dynamic_local"` は MCLAG 専用で VXLAN_FDB_TABLE では出現しない。

**分類**: ローカル変数初期化デフォルト（フィールド省略時のフォールバック）

---

### 3. `vni` フィールド — 省略・不正値時 = 0

**根拠**: `fdborch.cpp:773, 816-825`
```cpp
unsigned int vni = 0;
...
if (fvField(i) == "vni")
{
    try {
        vni = (unsigned int) stoi(fvValue(i));
    } catch(exception &e) {
        SWSS_LOG_INFO("Invalid VNI in remote MAC %s", fvValue(i).c_str());
        vni = 0;
        break;
    }
}
```

`vni` フィールドが省略または数値変換不可能な場合 `0` に初期化される。

**分類**: ローカル変数初期化デフォルト（フィールド省略または変換エラー時）

---

### 4. `remote_vtep` フィールド — 不正値時はエントリ破棄

**根拠**: `fdborch.cpp:795-808`
```cpp
if (fvField(i) == "remote_vtep")
{
    remote_ip = fvValue(i);
    try {
        IpAddress valid_ip = IpAddress(remote_ip);
        (void)valid_ip;
    } catch(exception &e) {
        SWSS_LOG_NOTICE("Invalid IP address in remote MAC %s", remote_ip.c_str());
        remote_ip = "";
        break;
    }
}
```

**根拠**: `fdborch.cpp:838-841`
```cpp
if(!remote_ip.length())
{
    it = consumer.m_toSync.erase(it);
    continue;
}
```

`remote_vtep` が不正 IP または省略の場合 `remote_ip = ""` となり、DIP トンネルサポートモード (`isDipTunnelsSupported() == true`) では即座にエントリを破棄する（silent drop）。

**分類**: バリデーション失敗 → silent drop

---

### 5. `FDB_ORIGIN_VXLAN_ADVERTIZED` — origin ハードコード

**根拠**: `fdborch.cpp:719-722`
```cpp
if(table_name == APP_VXLAN_FDB_TABLE_NAME)
{
    origin = FDB_ORIGIN_VXLAN_ADVERTIZED;
}
```

`APP_VXLAN_FDB_TABLE_NAME` から来るエントリは常に `FDB_ORIGIN_VXLAN_ADVERTIZED` として扱われる。SAI FDB エントリ作成時のメタデータとして使用され、ローカル学習 MAC との区別に使用される。

**分類**: ハードコード（テーブル名判定による自動設定）

---

### 6. fdbsyncd における `esi` フィールド — 書き込み元なし

**根拠**: `fdbsync.cpp:658-664`（macAddVxlan 関数）
```cpp
FieldValueTuple rv("remote_vtep", svtep);
FieldValueTuple t("type", type);
FieldValueTuple v("vni", svni);
fvVector.push_back(rv);
fvVector.push_back(t);
fvVector.push_back(v);
```

`fdbsyncd` は `remote_vtep`・`type`・`vni` の 3 フィールドのみを書き込む。`esi` フィールドは `fdborch.cpp:771-814` で読み出し変数として定義されるが、`fdbsyncd` はこれを書かない（空文字列のまま）。

`fdborch.cpp:771`:
```cpp
string esi = "";
```

**分類**: 書き込み元依存 — `esi` はネットリンク経由の `fdbsyncd` ではなく EVPN BGP 経路からの別経路で設定される可能性があるが、`fdbsyncd` コードパスでは常に空文字列。

---

### 7. warm-restart 中のキャッシュ挙動

**根拠**: `fdbsync.cpp:669-673`
```cpp
if (m_AppRestartAssist->isWarmStartInProgress())
{
    m_AppRestartAssist->insertToMap(APP_VXLAN_FDB_TABLE_NAME, key, fvVector, false);
    return;
}
```

warm-restart 中は `m_fdbTable.set()` の代わりに `insertToMap()` でキャッシュに蓄積される。warm-restart 完了後に一括フラッシュされる。この間は APP_DB への即時書き込みが行われない。

**分類**: warm-restart 時の遅延書き込み

---

### 8. delete_key 判定 — NUD_INCOMPLETE / NUD_FAILED

**根拠**: `fdbsync.cpp:787-792`
```cpp
int state = rtnl_neigh_get_state(neigh);
if ((nlmsg_type == RTM_DELNEIGH) || (state == NUD_INCOMPLETE) ||
    (state == NUD_FAILED))
{
    delete_key = true;
}
```

`RTM_DELNEIGH` メッセージのほか、`NUD_INCOMPLETE`（ARP 解決中）または `NUD_FAILED`（ARP 失敗）の state の場合も `macDelVxlan()` が呼ばれエントリが削除される。EVPN MAC が消えた場合の主トリガー。

**分類**: netlink state ハードコード（削除トリガー）

---

## 要約テーブル

| フィールド | 省略/条件 | 実挙動 | 分類 | 根拠 |
|-----------|---------|--------|------|------|
| `type` | NUD_NOARP なし | `"dynamic"` を書き込む | netlink state ハードコード | `fdbsync.cpp:794-802` |
| `type` | NUD_NOARP あり | `"static"` を書き込む | netlink state ハードコード | `fdbsync.cpp:794-798` |
| `type` | fdborch 側でフィールド省略 | `"dynamic"` デフォルト | ローカル変数初期化 | `fdborch.cpp:770` |
| `vni` | 省略または数値変換失敗 | `0` デフォルト | ローカル変数初期化 | `fdborch.cpp:773, 820-824` |
| `remote_vtep` | 不正 IP または省略 | `""` → silent drop (DIP モード) | バリデーション失敗 → silent drop | `fdborch.cpp:795-841` |
| `esi` | fdbsyncd 経由 | 常に空文字列 (書き込まれない) | 書き込み元依存 | `fdbsync.cpp:658-664` |
| origin | テーブル名判定 | `FDB_ORIGIN_VXLAN_ADVERTIZED` ハードコード | ハードコード | `fdborch.cpp:719-722` |
| warm-restart 中 | isWarmStartInProgress() == true | APP_DB 直書きせずキャッシュ蓄積 | warm-restart 遅延書き込み | `fdbsync.cpp:669-673` |
