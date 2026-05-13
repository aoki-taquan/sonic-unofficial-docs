# 値依存挙動分析: MGMT_VRF_CONFIG

## Phase 1: YANG フィールド全列挙

- `mgmtVrfEnabled` (boolean): default `false`

## Phase 2: per-value explicit grep

- `hostcfgd`: `enabled = data.get('mgmtVrfEnabled', '')` — "true"/"false" 文字列で比較
- `vrfmgr.cpp`: mgmtVrfEnabled=false → op を DEL_COMMAND に上書き
- `hostcfgd tests`: `mgmtVrfEnabled: "true"` / `"false"` で挙動確認

## Phase 3: 専用ファイル確認

- `sonic-host-services/scripts/hostcfgd`: `update_mgmt_vrf()` — chrony stop → interfaces-config restart → chrony start の順で再起動
- `sonic-swss/cfgmgr/vrfmgr.cpp`: mgmt VRF netdev (table ID 6000) を作成/削除
- `sonic-ntp.yang`: `must` — `vrf = 'mgmt'` のとき `mgmtVrfEnabled = 'true'` が必要

## Phase 5: 値依存挙動マトリクス

| フィールド | 値 | 挙動 |
|-----------|-----|------|
| `mgmtVrfEnabled` | `true` | Linux カーネルに `mgmt` VRF (table ID 6000) を作成。eth0 を mgmt VRF に所属。chrony/NTP/SNMP を mgmt VRF で動作 |
| `mgmtVrfEnabled` | `false` (default) | mgmt VRF を削除 (または作成しない)。eth0 はデフォルト VRF のまま |
| `mgmtVrfEnabled` | `false` → `true` 変更 | vrfmgr が VRF netdev 作成 + hostcfgd が `systemctl stop chrony` → `restart interfaces-config` → `start chrony` を実行 |
| `mgmtVrfEnabled` | `true` → `false` 変更 | vrfmgr が VRF netdev 削除 + 上記サービス再起動シーケンス |

enum なし (boolean)。NTP `vrf=mgmt` は本フィールドが `true` の場合のみ YANG バリデーション通過。
