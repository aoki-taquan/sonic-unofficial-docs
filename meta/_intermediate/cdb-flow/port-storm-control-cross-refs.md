# PORT_STORM_CONTROL — Phase C 暗黙参照 中間ファイル

生成日: 2026-05-16

## スキャン対象

`sonic-swss/orchagent/policerorch.cpp` — `handlePortStormControlTable()` および `doTask()`

## 抽出した暗黙参照

### PORT テーブルへの依存

| 参照箇所 | コード | 参照の性質 |
|---------|--------|-----------|
| `policerorch.cpp:14` | `extern PortsOrch* gPortsOrch;` | `PortsOrch` グローバルポインタを外部宣言。PORT テーブルを管理する orch への直接依存 |
| `policerorch.cpp:138` | `gPortsOrch->getPort(interface_name, port)` | `PORT_STORM_CONTROL` key の `<ifname>` 部分を `PortsOrch::getPort()` で PORT テーブルから暗黙 lookup。存在しない場合 `task_success` で silent drop |
| `policerorch.cpp:379` | `gPortsOrch->allPortsReady()` | 全 PORT エントリ初期化完了まで `doTask()` を早期リターン。PORT テーブルの初期化状態に暗黙依存 |
| `policerorch.cpp:278,291` | `sai_port_api->set_port_attribute(port.m_port_id, ...)` | `getPort()` で取得した `port.m_port_id` を SAI 呼び出しに使用。PORT テーブル由来の SAI OID への暗黙依存 |
| `policerorch.cpp:132` | `strncmp(interface_name.c_str(), ETHERNET_PREFIX, ...)` | `ETHERNET_PREFIX = "Ethernet"` との prefix 比較。CONFIG_DB の PORT テーブルに登録されるインタフェース名規則を暗黙前提とする |

### PortsOrch (PORT) 経由 SAI oid 参照

`handlePortStormControlTable()` は PORT エントリの SAI object id (`port.m_port_id`) を
`PortsOrch::getPort()` 経由で取得し、storm control policer を SAI_PORT_ATTR_*_STORM_CONTROL_POLICER_ID
属性としてアタッチする。CONFIG_DB の `PORT_STORM_CONTROL` テーブルには SAI oid は格納されず、
`PortsOrch` のメモリ内キャッシュを介した暗黙参照となる。

## 結論

| 参照先テーブル | 参照の性質 | 明示的 lookup か |
|--------------|-----------|----------------|
| `PORT` | `PortsOrch::getPort()` による SAI oid 取得 + `allPortsReady()` による初期化ガード | 暗黙 (CONFIG_DB を直接読まず、PortsOrch キャッシュ経由) |
