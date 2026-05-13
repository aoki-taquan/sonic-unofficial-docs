# SYSLOG_SERVER — 値依存挙動調査メモ

## ソース

- `sonic-syslog.yang` (sonic-buildimage@9ea932ec)
- `sonic-host-services/scripts/hostcfgd` (RSyslogCfg)

## enum 値

### `vrf` (vrf-device typedef + leafref)

- `default`: デフォルト VRF を経由してリモート syslog に転送
- `mgmt`: 管理 VRF 経由。`MGMT_VRF_CONFIG.mgmtVrfEnabled = true` 必須 (YANG must 制約)
- VRF 名 (leafref): DATA_PLANE VRF テーブルの任意の VRF 名

### `filter` (syslog-filter-type typedef)

- `include`: 正規表現 `filter_regex` にマッチしたログのみ転送
- `exclude`: 正規表現 `filter_regex` にマッチしたログを除外して転送

### `protocol` (rsyslog-protocol typedef)

- `tcp`: TCP でリモートサーバに転送（信頼性あり、再送機能あり）
- `udp`: UDP で転送（デフォルト相当、低オーバーヘッド）

### `severity` (rsyslog-severity typedef)

- `none` / `debug` / `info` / `notice` / `warn` / `error` / `crit`

## 値依存挙動

| フィールド | 値 | 挙動 |
|-----------|-----|-----|
| `vrf` | `mgmt` | `MGMT_VRF_CONFIG.mgmtVrfEnabled != true` なら YANG must 制約違反で拒否 |
| `vrf` | `default` | デフォルト VRF 経由で転送 |
| `filter` | `include` | `filter_regex` にマッチするメッセージのみ転送 |
| `filter` | `exclude` | `filter_regex` にマッチするメッセージを除外 |
| `filter_regex` | 未設定 + `filter` 設定あり | テンプレート展開時に正規表現が空になり全ログが対象 |
| `source` | `server_address` と異なる IP family | YANG must 制約違反で書き込み拒否 |
| `protocol` | `tcp` | rsyslog が TCP omfwd で転送。接続失敗時キュー蓄積 |
| `protocol` | `udp` | rsyslog が UDP omfwd で転送。パケットロスあり |
