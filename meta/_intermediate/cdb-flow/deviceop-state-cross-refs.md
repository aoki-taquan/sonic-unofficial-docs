# deviceop-state — 暗黙参照テーブル (Phase C) 調査メモ

## 調査対象

- slug: `deviceop-state`
- テーブル: `DEVICE_NEIGHBOR`
- 追加 phase: cross-refs (Phase C)

## 参照テーブル一覧

### DEVICE_NEIGHBOR_METADATA (CONFIG_DB)

- **pfcwd** (`pfcwd/main.py:98-104`): `get_server_facing_ports()` で `candidates[port]['name']` をキーとして `DEVICE_NEIGHBOR_METADATA` の `type` フィールドを照合。`type == 'server'` のポートのみサーバー向けポートとして扱う。
- **bgpcfgd** (`managers_bgp.py:220-224`): `check_neig_meta` 有効時、`data['name']`（= DEVICE_NEIGHBOR の `name` フィールド値）が `DEVICE_NEIGHBOR_METADATA` に存在しない場合 `return False` で延期。

### VLAN_MEMBER (CONFIG_DB)

- **pfcwd** (`pfcwd/main.py:106-107`): `get_server_facing_ports()` でサーバー向けポードが 0 件の場合、`VLAN_MEMBER` をフォールバックとして使用。

### PORT (CONFIG_DB)

- **pfcwd** (`pfcwd/main.py:111-119`): `get_bp_ports()` で `PORT` テーブルを全読み、`role='Int'` かつ `admin_status='up'` のポートをバックプレーンポートとして `active_ports` に追加。

### DEVICE_METADATA|localhost (CONFIG_DB)

- **pfcwd** (`pfcwd/main.py:408-419`): `start_default` が `default_pfcwd_status` フィールドを読み、`'enable'` でない場合は即 return（DEVICE_NEIGHBOR を読んでも PFC WD を設定しない）。

## Evidence ファイル

- `sonic-utilities` `pfcwd/main.py:97-119,405-424`
- `sonic-buildimage` `src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:118-154,219-224`
