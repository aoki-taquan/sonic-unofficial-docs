# macsec-port — 暗黙参照テーブル調査 (Phase C)

調査対象: `sonic-swss/cfgmgr/macsecmgr.cpp`、`sonic-swss/orchagent/macsecorch.cpp`

## 調査方針

`PORT|<ifname>` の `macsec` フィールドを処理するのは主に 2 コンポーネント:
1. `macsecmgrd` (MACsecMgr) — CONFIG_DB `PORT` を直接購読
2. `MACsecOrch` — APPL_DB `MACSEC_PORT_TABLE` 等を購読して SAI に反映

本ブロックでは Direction A 入力 (`PORT.macsec` フィールドそのもの) 以外の **暗黙的な参照先** を列挙する。

## macsecmgrd (CFG→wpa_supplicant パス)

### STATE_DB — PORT_TABLE

`isPortStateOk()` が `STATE_PORT_TABLE_NAME` ("PORT_TABLE") から以下を読み出す:
- `state == "ok"` — portmgrd が書き込むポート設定完了フラグ
- `netdev_oper_status == "up"` — Linux netdev が UP 状態であること

どちらか一方でも未達の場合は `task_need_retry`。

証跡: `cfgmgr/macsecmgr.cpp:614-631`

### CONFIG_DB — MACSEC_PROFILE

`m_profiles` メモリキャッシュは `loadProfile()` が `MACSEC_PROFILE` SET イベントを受信した際に構築される。
`enableMACsec()` は `m_profiles.find(profile_name)` でキャッシュを参照し、未ロードなら `task_need_retry`。

証跡: `cfgmgr/macsecmgr.cpp:488-495`

### m_macsec_ports — インメモリ状態テーブル

ポートごとの MACsec セッション状態 (`profile_name`, `sock`, `wpa_supplicant_pid`) をメモリで保持。
Redis テーブルではないが、`enableMACsec()` / `disableMACsec()` / `removeProfile()` がすべてこのマップを参照する。

## MACsecOrch (APPL→SAI パス)

### APPL_DB — MACSEC_PORT/SC/SA テーブル群

`MACsecOrch` は以下を購読:
- `APP_MACSEC_PORT_TABLE_NAME` (SET/DEL)
- `APP_MACSEC_EGRESS_SC_TABLE_NAME` / `APP_MACSEC_INGRESS_SC_TABLE_NAME` (SET/DEL)
- `APP_MACSEC_EGRESS_SA_TABLE_NAME` / `APP_MACSEC_INGRESS_SA_TABLE_NAME` (SET/DEL)

`PORT` macsec フィールドの変化は最終的に `macsecmgrd` 経由で `MACSEC_PORT_TABLE` に書き込まれ、`MACsecOrch` がそれを処理する。

証跡: `orchagent/macsecorch.cpp:872-890`

### STATE_DB — MACSEC_{PORT,SC,SA} テーブル群

`MACsecOrch` は SAI 処理完了後に以下に書き戻す:
- `STATE_MACSEC_PORT_TABLE_NAME`
- `STATE_MACSEC_EGRESS_SC_TABLE_NAME` / `STATE_MACSEC_INGRESS_SC_TABLE_NAME`
- `STATE_MACSEC_EGRESS_SA_TABLE_NAME` / `STATE_MACSEC_INGRESS_SA_TABLE_NAME`

証跡: `orchagent/macsecorch.cpp:633-637`

### COUNTERS_DB / GB_COUNTERS_DB

`MACsecOrch` は SA 作成後に `COUNTERS_MACSEC_NAME_MAP`、`COUNTERS_MACSEC_SA_ATTR_GROUP`、`COUNTERS_MACSEC_SA_GROUP`、`COUNTERS_MACSEC_FLOW_GROUP` を登録してカウンタ収集を有効化する。

証跡: `orchagent/macsecorch.cpp:639-667`

## 参照方向サマリ

| 参照先 DB / テーブル | 参照方向 | 条件 | evidence |
|---------------------|---------|------|----------|
| STATE_DB `PORT_TABLE` | 読み出し (ゲート) | PORT ready チェック — 必須 | `macsecmgr.cpp:614-631` |
| CONFIG_DB `MACSEC_PROFILE` | 読み出し (キャッシュ経由) | プロファイル存在チェック — 必須 | `macsecmgr.cpp:488-495` |
| APPL_DB `MACSEC_PORT_TABLE` | 書き込み (macsecmgrd) → 読み出し (MACsecOrch) | PORT.macsec SET 後 | `macsecmgr.cpp:_, macsecorch.cpp:872` |
| STATE_DB `STATE_MACSEC_PORT_TABLE` | 書き戻し (MACsecOrch) | SAI MACsec Port 作成後 | `macsecorch.cpp:633` |
| COUNTERS_DB `COUNTERS_MACSEC_NAME_MAP` 等 | 書き込み (MACsecOrch) | MACsec SA 有効化後 | `macsecorch.cpp:639-667` |
