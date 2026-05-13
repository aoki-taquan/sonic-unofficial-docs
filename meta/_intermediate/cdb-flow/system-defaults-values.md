# SYSTEM_DEFAULTS — 値依存挙動調査メモ

## ソース

- `sonic-system-defaults.yang` (sonic-buildimage@9ea932ec)
- `files/build_templates/init_cfg.json.j2` — `mux_tunnel_egress_acl` エントリ
- `sonic-swss/orchagent/muxorch.cpp` — `tunnel_qos_remap` 参照
- `sonic-buildimage/src/sonic-config-engine/config_samples.py`

## enum 値

### `status` (admin_mode typedef)

- `enabled`: 機能を有効化
- `disabled`: 機能を無効化

## 代表的な `<name>` とその意味

| name | enabled 時の効果 |
|------|----------------|
| `tunnel_qos_remap` | IPinIP トンネルデカプセル時の QoS リマップを有効化 (muxorch 参照) |
| `synchronous_mode` | orchagent が SAI 操作を同期実行。P4RT 連携時に必要 |
| `dhcp_server` | SONiC 組み込み DHCP サーバを有効化 (init_cfg で `disabled` デフォルト) |
| `mux_tunnel_egress_acl` | Dual-ToR mux ACL 適用 (Mellanox: `enabled` / その他: `disabled`) |

## 値依存挙動

| フィールド | 値 | 挙動 |
|-----------|-----|-----|
| `status` | `enabled` | 対応機能が起動時に有効化される |
| `status` | `disabled` | 対応機能が無効化。同等: エントリを DEL した場合もデフォルト disabled として扱う |
| エントリ不在 | - | `config_samples.py` が空 dict を補完。各機能は不在を disabled として扱う |
| `tunnel_qos_remap` | `enabled` → 起動後に `disabled` 変更 | muxorch は起動時のみ参照のためサービス再起動まで変更は無効 |
