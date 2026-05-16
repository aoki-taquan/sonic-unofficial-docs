# AAA — Phase B 書込み順依存スキャンノート

対象テーブル: `AAA`
Consumer: `hostcfgd` / `AaaCfg` (`sonic-host-services/scripts/hostcfgd`)
スキャン範囲: load(), aaa_update(), modify_conf_file(), ldap_global_update(), register_callbacks() 全行精読

---

## 検出した順序依存・タイミング依存

### 1. load_independent_config() — AAA は systemctl 完了前に適用される（他テーブルと異なる先行処理）

- `hostcfgd.load()` (hostcfgd:2232) は `load_independent_config()` を先に呼び、その後 `wait_till_system_init_done()` でシステム初期化完了待ちに入る。
- `load_independent_config()` の中で `self.aaacfg.load(aaa, tacacs_global, tacacs_server, radius_global, radius_server, ldap_global, ldap_server)` が呼ばれる (hostcfgd:2230)。
- `AaaCfg.load()` は **AAA / TACPLUS / TACPLUS_SERVER / RADIUS / RADIUS_SERVER / LDAP / LDAP_SERVER** を一括で読み込み、最後に `modify_conf_file()` を 1 回だけ呼ぶ (hostcfgd:399-416)。
- **順序依存**: `AAA` テーブルを CONFIG_DB に書く場合、`TACPLUS` / `RADIUS` / `LDAP` / `LDAP_SERVER` が**同時に** CONFIG_DB に存在しなくても `load()` は実行されるが、不在フィールドはデフォルト値で代替される（silent fallback）。
- 逆に CONFIG_DB 書き込みが `load()` 呼び出し**後**に行われた場合は `subscribe()` コールバック経由で個別ハンドラが動作する（依存 #2）。
- evidence: `hostcfgd:2215-2232`

### 2. `modify_conf_file()` の一括呼び出し — 個別更新は毎回 PAM 再生成を引き起こす

- runtime 中の `aaa_update()` / `ldap_global_update()` / `ldap_server_update()` / `tacacs_global_update()` / `radius_global_update()` / `radius_server_update()` はそれぞれ最後に `modify_conf_file()` を呼ぶ (hostcfgd:432, 552, 564, 475, 530, 545)。
- `modify_conf_file()` は PAM 設定 / NSS 設定 / NSLCD 設定 / RADIUS 設定を**全部まとめて再生成**する。
- これは **中間状態で PAM ファイルが書き換わる** ことを意味する。
- **順序依存**: `AAA|authentication.login = "tacacs+,local"` を先に書き込み、`TACPLUS_SERVER` エントリを後から追加する場合、`AAA` 書き込み時点で `servers_conf` は空になり、`common-auth-sonic` は TACACS+ サーバなしの状態で生成される（実質 `local` 相当）。`TACPLUS_SERVER` 追加後に再度 `modify_conf_file()` が呼ばれて正しい設定になる。
- **推奨**: `TACPLUS_SERVER` / `RADIUS_SERVER` / `LDAP_SERVER` / `LDAP` を先に書いてから `AAA` を書く順序にすることで中間不整合期間を最小化できる。
- evidence: `hostcfgd:641-870`

### 3. LDAP early return — LDAP global 設定が先行必須

- `is_ldap_config_complete()` (hostcfgd:437-442): `ldap_global` が空 (`{}`) の場合は即 `False` を返し、`nslcd` は起動しない。
- `ldap_global.get('bind_dn')` / `ldap_global.get('base_dn')` / `ldap_global.get('bind_password')` のいずれかが空文字でも `False`。
- `LDAP_SERVER` エントリが存在しない場合も `False`（`and self.ldap_servers` チェック）。
- `authentication.login` に `ldap` が含まれない場合も `False`。
- **順序依存**: `AAA|authentication.login = "ldap"` を書く前に `LDAP|global` (`bind_dn`, `base_dn`, `bind_password`) と `LDAP_SERVER` エントリを揃えておかないと、`aaa_update()` 呼び出し時点で `handle_nslcd_service(False)` が呼ばれ、nslcd が停止 / mask される。後から LDAP global 設定を追加しても `ldap_global_update()` が `handle_nslcd_service()` を呼ぶため最終的に復旧するが、期間中は LDAP 認証が機能しない。
- evidence: `hostcfgd:434-442`, `hostcfgd:241-250`

### 4. TACPLUS passkey と authorization の条件依存（db_migrator）

- `db_migrator.migrate_aaa()` (db_migrator.py:869-900): `AAA|authorization` の migration は `TACPLUS|global.passkey` が存在かつ空でない場合のみ実行される。passkey がない場合は既存の `AAA|authorization` エントリを**削除**する。
- **順序依存（migration 時）**: DB upgrade 時に `TACPLUS|global.passkey` が設定されていない状態で migration が走ると、`AAA|authorization` が削除される。事後に passkey を設定しても `AAA|authorization` は自動復元されない（手動で `config aaa authorization login tacacs+` が必要）。
- **順序依存（運用時）**: YANG must 制約 (`sonic-system-aaa.yang`) により、`AAA|authentication.login` に `tacacs+` を含む場合、`TACPLUS|global.passkey` が存在しなければ YANG バリデーションエラーになる。CLI 経由の書き込みは事前に YANG レベルで reject される。
- evidence: `db_migrator.py:869-900`, `sonic-system-aaa.yang:must`

### 5. DEL 操作の影響 — エントリ消去時のデフォルト回帰

- `aaa_update()` で `data == {}` (DEL) の場合、`self.authentication` / `self.authorization` / `self.accounting` は更新されない（既存の状態を保持）。
- ただし `modify_conf_file()` は `authentication_default.copy()` に `self.authentication` を `update()` するため、DEL されたエントリに対応する key が `default` dict に存在しない限り、直前の値が維持される。
- `AAA|authentication` を DEL した後に `modify_conf_file()` が呼ばれると、`authentication_default = {'login': 'local'}` が使われ `local` 認証に回帰する。
- **順序依存なし**（DEL は即時フォールバック、待機ループなし）。
- evidence: `hostcfgd:419-435`, `hostcfgd:641-645`, `hostcfgd:357-366`

### 6. RADIUS src_intf 解決 — MGMT_INTERFACE / INTERFACE が先行必須

- `modify_conf_file()` 内で `server['src_intf']` が設定されている場合、`get_interface_ip(server['src_intf'], addr)` で IP アドレスを取得する (hostcfgd:686-695)。
- `get_interface_ip()` は CONFIG_DB から `MGMT_INTERFACE` / `INTERFACE` / `VLAN_INTERFACE` 等を参照する。
- **順序依存**: `RADIUS_SERVER` エントリに `src_intf` を設定する場合、対応するインターフェース設定 (`MGMT_INTERFACE|eth0|...` 等) が CONFIG_DB に存在していなければ `src_ip` が空になり、RADIUS サーバへの送信元 IP が設定されない。後から `MGMT_INTERFACE` 変更が届くと `mgmt_intf_handler()` → `modify_conf_file()` で自動更新される。
- evidence: `hostcfgd:670-695`, `hostcfgd:2484-2490`

### 7. hostname 依存 — DEVICE_METADATA が先行必須（RADIUS nas_id）

- `modify_conf_file()` 内で `nas_id` が未設定の場合 `get_hostname()` を呼ぶ (hostcfgd:676-679)。
- `hostname_update()` は `load()` 内で `devmetacfg.load()` 後に `self.aaacfg.hostname_update(self.devmetacfg.hostname)` として呼ばれる (hostcfgd:2273-2275)。
- **順序依存**: `DEVICE_METADATA|localhost.hostname` が設定されていない状態で RADIUS 設定を `load()` すると `nas_id` が空になる。`load()` 内では `devmetacfg.load()` → `aaacfg.hostname_update()` の順で呼ばれるため、**load フェーズ内では自動的に正しい順序が保たれる**。ただし runtime 中に `RADIUS_SERVER` エントリを追加する場合は `DEVICE_METADATA.hostname` が既に DB に存在していること。
- evidence: `hostcfgd:2273-2275`, `hostcfgd:574-581`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | AAA は load_independent_config() で systemctl 完了前に適用 | 強制先行（他テーブルより早い） | silent fallback（不在フィールドはデフォルト値使用） |
| 2 | TACPLUS_SERVER / RADIUS_SERVER / LDAP_SERVER を先書き → AAA 書き込み | 推奨（中間状態最小化） | runtime は subscribe で後追い自動更新 |
| 3 | LDAP|global (bind_dn/base_dn/bind_password) + LDAP_SERVER → AAA login=ldap | 先行必須（欠如時 nslcd 停止） | LDAP 設定追加後 ldap_global_update が自動復旧 |
| 4 | TACPLUS|global.passkey → AAA authorization / migration | 先行必須（YANG reject + migrator 削除） | 手動 CLI 再設定 |
| 5 | AAA DEL → デフォルト回帰 | 即時（待機ループなし） | authentication_default で local 回帰 |
| 6 | MGMT_INTERFACE / INTERFACE → RADIUS_SERVER src_intf | 推奨先行 | 後追い mgmt_intf_handler で自動更新 |
| 7 | DEVICE_METADATA.hostname → RADIUS nas_id | load フェーズ内は自動保証 | runtime 追加時は hostname 設定済みであること |
