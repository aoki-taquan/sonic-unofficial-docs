# RADIUS_SERVER — Phase B 書込み順依存スキャンノート

対象テーブル: `RADIUS_SERVER`
Consumer: `hostcfgd` / `AaaCfg` (`sonic-host-services/scripts/hostcfgd`)
スキャン範囲: load(), radius_server_update(), modify_conf_file(), handle_radius_source_intf_ip_chg() 全行精読

---

## 検出した順序依存・タイミング依存

### 1. load() フェーズ — 全テーブル一括読込みと PAM 一括生成

- `hostcfgd.load()` 内で `load_independent_config()` を先に呼ぶ（`hostcfgd:2230`）。
- `load_independent_config()` → `AaaCfg.load(aaa, tacacs_global, tacacs_server, radius_global, radius_server, ldap_global, ldap_server)` が呼ばれ、**全サーバ一括**で `radius_servers` を構築し `modify_conf_file()` を 1 回だけ実行する（`hostcfgd:399-416`）。
- **順序依存**: load フェーズ時点で `RADIUS_SERVER` エントリが CONFIG_DB に存在しない場合、PAM ファイルは空のサーバリストで生成される。後から `RADIUS_SERVER` を追加した場合は `radius_server_update()` コールバックで追加反映される（順序は緩和）。
- evidence: `hostcfgd:2215-2232`, `hostcfgd:399-416`

### 2. RADIUS|global が先行必須 — server merge のベース

- `modify_conf_file()` は `radius_global_default` をベースに各サーバエントリをマージする（`hostcfgd:670-700`）。
- `RADIUS|global` が CONFIG_DB に存在しない場合、`radius_global_default` のハードコードデフォルト（`auth_port=1812`, `auth_type=pap`, `timeout=5`, `retransmit=3`, `priority=0`）が代替される。
- **順序依存（推奨）**: `RADIUS_SERVER` を書く前に `RADIUS|global` を設定することで、グローバル設定（`nas_ip`, `nas_id`, `src_ip`）が各サーバに正しく継承される。逆順の場合、load 後のコールバックで最終的に正しい状態に収束するが、中間的に NAS-IP が誤設定の PAM ファイルが生成される。
- evidence: `hostcfgd:670-695`, `hostcfgd:354-416`

### 3. AAA.authentication.login = "radius" との連動 — PAM 反映の前提条件

- `modify_conf_file()` 内で `radsrvs_conf` リスト（RADIUS サーバ設定行）が空の場合、`aaastatsd` サービスが stop される（`hostcfgd:839-844`）。
- `AAA|authentication.login` に `radius` が含まれない場合、PAM の `common-auth-sonic` ファイルに radius 行が追加されない（NSS radius プラグインが無効）。
- **順序依存（必須）**: `RADIUS_SERVER` エントリがあっても `AAA|authentication.login` に `radius` が含まれなければ実際のログイン認証には使用されない。`RADIUS_SERVER` → `RADIUS|global` → `AAA` の順で書き込むことで中間不整合期間（RADIUS サーバがあるが AAA が未設定の状態）を短縮できる。
- evidence: `hostcfgd:825-844`, `hostcfgd:354-416`

### 4. src_intf 設定時 — MGMT_INTERFACE / INTERFACE が先行必須

- `modify_conf_file()` 内で `server['src_intf']` が設定されている場合、`get_interface_ip(server['src_intf'], addr)` で IP アドレスを取得する（`hostcfgd:686-695`）。
- `get_interface_ip()` は CONFIG_DB から `MGMT_INTERFACE` / `INTERFACE` / `VLAN_INTERFACE` 等を参照する。
- **順序依存**: `src_intf` を設定する場合、対応するインターフェース設定が CONFIG_DB に先行していなければ `src_ip` が空になり PAM ファイルに `source_ip` 行が生成されない。後から `MGMT_INTERFACE` 変更が届くと `mgmt_intf_handler()` → `modify_conf_file()` で自動更新される（緩和あり）。
- evidence: `hostcfgd:670-695`, `hostcfgd:2484-2490`

### 5. DEVICE_METADATA.hostname が先行必須 — nas_id 自動補完

- `RADIUS|global` に `nas_id` が未設定の場合、`get_hostname()` でホスト名を取得し NAS-Identifier に設定する（`hostcfgd:676-679`）。
- load フェーズでは `devmetacfg.load()` → `aaacfg.hostname_update()` の順が保証されている（`hostcfgd:2273-2275`）。
- **順序依存（load 内は自動保証）**: runtime 中に `RADIUS_SERVER` エントリを追加する場合、`DEVICE_METADATA|localhost.hostname` が CONFIG_DB に存在していること。未設定なら `nas_id` が空になる。
- evidence: `hostcfgd:2273-2275`, `hostcfgd:574-581`

### 6. PAM 設定書込み順 — priority 降順ソート後に全サーバ逐次書き込み

- `modify_conf_file()` は `radius_servers` を `priority` 降順（`reverse=True`）でソートしてから PAM 設定ファイルを生成する（`hostcfgd:702-714`）。
- 各サーバに対して `RADIUS_PAM_AUTH_CONF_DIR + ip + "_" + auth_port + ".conf"` ファイルを個別に書き込む（Jinja2 テンプレート展開）。
- **書込み順（内部）**: priority 降順 → 各サーバの pam_radius_auth.conf 生成 → NSS 設定生成 → aaastatsd 起動/停止。この順序はコードで固定されており変更不可。
- **副作用**: `auth_port` 変更時に旧ファイル（`<ip>_<old_port>.conf`）は自動削除されない。追加された新ポートのファイルと旧ポートのファイルが共存する。
- evidence: `hostcfgd:700-844`

### 7. DEL 操作 — data={} で即時削除・設定再生成

- `radius_server_update()` で `data == {}` の場合、`radius_servers` からエントリを削除して `modify_conf_file()` を呼ぶ（`hostcfgd:536`）。
- 削除操作は待機なし・即時実行。対応する pam_radius_auth.conf ファイルは再生成で除外されるが、ファイル削除は行わない（残留リスクなし—新しい `radsrvs_conf` に含まれなくなるだけ）。
- **順序依存なし**（DEL は後処理不要）。
- evidence: `hostcfgd:533-546`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 強度 | 緩和策 |
|---|----------|------|------|--------|
| 1 | RADIUS_SERVER は load() 時点で全件一括反映 | load フェーズ先行 | 強 | runtime コールバックで後追い反映 |
| 2 | RADIUS\|global → RADIUS_SERVER（server merge ベース） | 推奨先行 | 中 | ハードコードデフォルトでフォールバック |
| 3 | RADIUS_SERVER → RADIUS\|global → AAA（login=radius） | 推奨先行 | 中 | runtime subscribe で後追い自動更新 |
| 4 | MGMT_INTERFACE / INTERFACE → RADIUS_SERVER src_intf | 推奨先行 | 中 | mgmt_intf_handler で後追い自動更新 |
| 5 | DEVICE_METADATA.hostname → RADIUS_SERVER（nas_id 補完） | load 内は自動保証 | 低 | runtime 追加時は hostname 設定済みであること |
| 6 | 内部: priority 降順ソート → PAM 書き込み → NSS → aaastatsd | コード固定順 | 内部 | 変更不可 |
| 7 | DEL は即時（待機なし） | 順序依存なし | — | — |
