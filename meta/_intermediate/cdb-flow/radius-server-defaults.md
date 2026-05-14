# RADIUS_SERVER コード由来デフォルト調査 (Phase A)

## ソース

- `sonic-host-services/scripts/hostcfgd` (hostcfgd)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-system-radius.yang`
- `sonic-utilities/config/aaa.py`

## フィールド別デフォルト・暗黙挙動一覧

### `auth_port`
- **YANG default**: 1812 (明示)
- **CLI default**: `default=1812` (aaa.py L.514)
- **hostcfgd fallback**: `RADIUS_SERVER_AUTH_PORT_DEFAULT = "1812"` (L.92) → `radius_global_default['auth_port']` で補完
- **PAM template**: `[{{ server.ip }}]:{{ server.auth_port }}` — 常に出力される。欠落時は空文字列になる
- **注意**: hostcfgd は `auth_port` を文字列として格納するが YANG は `inet:port-number`(uint16)。型変換なし

### `priority`
- **YANG default**: なし (range 1..64 のみ)
- **CLI default**: `default=1` (aaa.py L.515) — CLI 経由なら必ず 1 が書き込まれる
- **hostcfgd fallback**: `radius_global_default['priority'] = 0` (L.375) — YANG に存在しない値 0 がデフォルト
- **YANG-実装 discrepancy**: YANG は `range "1..64"` だが hostcfgd の `radius_global_default` は `priority: 0` を持つ。直接 CONFIG_DB 書き込みで priority 未設定時に hostcfgd は 0 を使って `sorted(..., key=lambda t: int(t['priority']))` に渡す → YANG 制約違反の値が runtime で使われる
- **ソート**: `radsrvs_conf = sorted(radsrvs_conf, key=lambda t: int(t['priority']), reverse=True)` (L.703) — priority 降順でサーバを並べる。0 は最低優先度になる

### `auth_type`
- **YANG default**: `pap`
- **CLI default**: None (未指定時は未書き込み)
- **hostcfgd fallback**: `RADIUS_SERVER_AUTH_TYPE_DEFAULT = "pap"` (L.96) → `radius_global_default['auth_type']` で補完
- **経路依存**: CLI で `-a` 未指定なら CONFIG_DB に `auth_type` キーなし → hostcfgd が global_default の `pap` を server に継承

### `timeout`
- **YANG default**: 5 (uint16, range 1..60)
- **CLI default**: なし (IntRange(1,60)、未指定なら未書き込み)
- **hostcfgd fallback**: `RADIUS_SERVER_TIMEOUT_DEFAULT = "5"` (L.95) → `radius_global_default['timeout']` で補完
- **注意**: CLI の `--retransmit` の `IntRange(1, 10)` は YANG の `range "0..10"` と不一致 (CLI は 0 を許可しない)

### `retransmit`
- **YANG default**: 3 (uint8, range 0..10)
- **CLI default**: なし (IntRange(1,10)、未指定なら未書き込み)
- **hostcfgd fallback**: `RADIUS_SERVER_RETRANSMIT_DEFAULT = "3"` (L.94)
- **YANG-CLI discrepancy**: YANG は `range "0..10"` だが CLI は `IntRange(1, 10)` — CLI では 0 を設定不能

### `passkey`
- **YANG default**: なし
- **hostcfgd fallback**: `RADIUS_SERVER_PASSKEY_DEFAULT = ""` (L.93) — 空文字列でフォールバック
- **PAM template に空文字列が展開される**: `pam_radius_auth.conf.j2` で `{{ server.passkey }}` が空文字列になる → pam_radius_auth が認証失敗する可能性
- **silent behavior**: passkey 未設定でも pam_radius_auth.conf は生成される (認証は失敗)

### `skip_msg_auth`
- **YANG**: 存在しない (YANG-実装 discrepancy / dead field from YANG perspective)
- **hostcfgd**: `RADIUS_SERVER_SKIP_MSG_AUTH = False` (L.98) → `radius_global_default['skip_msg_auth']` (L.381)
- **radius_server_update での変換**: `is_true(self.radius_servers[key]['skip_msg_auth'])` (L.542) で bool に変換
- **CLI**: `config radius add` に `--skip-msg-auth` オプションなし → CLI から設定不可能
- **dead consumer**: YANG 未定義、CLI 未実装だが hostcfgd が参照。CONFIG_DB 直接書き込みのみで設定可能

### `vrf`
- **YANG**: `pattern "mgmt|default"` — 2値のみ
- **CLI**: `--use-mgmt-vrf` フラグで `vrf = "mgmt"` を書き込む。`default` は書き込まれない (未設定 = default VRF 扱い)
- **hostcfgd**: `if server.vrf` で真の時のみ PAM 設定に `vrf=<vrf>` を追記
- **暗黙デフォルト**: `vrf` 未設定 → PAM に vrf 行なし → OS デフォルト VRF で接続

### `src_intf`
- **YANG**: union leafref (PORT, PORTCHANNEL, VLAN, LOOPBACK, MGMT_PORT)
- **CLI**: `--source-interface` 任意。有効インタフェース名検証あり (ADHOC_VALIDATION 時)
- **hostcfgd 優先規則**: `src_intf` が設定されていると `src_ip` を上書き (無視)。`src_intf` の IP 解決に失敗すると `src_ip` が削除される (L.697-700)
- **書き込み順依存**: `src_intf` の IP が未解決状態で hostcfgd 起動 → pam_radius_auth.conf の src_ip 行が省略される。後でインタフェース IP が設定されると `handle_radius_source_intf_ip_chg` で再生成

## NAS デフォルト補完 (global derived)

- `nas_ip` が radius_global に未設定の場合: `get_interface_ip("eth0")` で管理インタフェース IP を自動補完 (L.671-674)
- `nas_id` が radius_global に未設定の場合: `get_hostname()` でホスト名を自動補完 (L.675-678)
- これらは RADIUS_SERVER の各エントリに `radius_global` のコピーを通じて継承される

## サーバ上限

- `max-elements 8` (YANG L.118) / `RADIUS_MAXSERVERS = 8` (aaa.py L.11) — 一致

## pam_radius_auth.conf ファイル名規則

- `RADIUS_PAM_AUTH_CONF_DIR + srv['ip'] + "_" + srv['auth_port'] + ".conf"` (L.829)
- 例: `/etc/pam_radius_auth.d/192.168.1.1_1812.conf`
- `auth_port` が変更されると古いファイルは残留する (dead file) — 自動削除なし

## is_true() のスコープ

- `statistics` (radius_global): is_true() で変換 (L.531)
- `skip_msg_auth` (radius_server): is_true() で変換 (L.542)
- `yes/1` は is_true() では False になる (`True/true` のみ True) — YANG boolean は `true/false` 受け入れるが is_true() はさらに制限的
