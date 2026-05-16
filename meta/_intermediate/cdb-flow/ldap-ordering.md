# LDAP_SERVER — Phase B 書込み順依存スキャンノート

対象テーブル: `LDAP_SERVER`, `LDAP`
Consumer: `hostcfgd` / `AaaCfg` (`sonic-host-services/scripts/hostcfgd`)
スキャン範囲: `load()`, `ldap_global_update()`, `ldap_server_update()`, `is_ldap_config_complete()`, `modify_conf_file()`, `register_callbacks()` 全行精読

---

## 検出した順序依存・タイミング依存

### 1. LDAP|global 必須フィールド先行 — nslcd 起動ガード

- `is_ldap_config_complete()` (hostcfgd:437-442) は以下の全条件を満たす場合のみ `True` を返す:
  1. `self.ldap_global` が空 dict でない（`LDAP|global` が DB に存在）
  2. `ldap_global.get('bind_dn', "")` が空でない
  3. `ldap_global.get('base_dn', "")` が空でない
  4. `ldap_global.get('bind_password', "")` が空でない
  5. `'ldap' in self.authentication.get('login', "")`（AAA テーブルの login に ldap を含む）
  6. `self.ldap_servers` が空でない（LDAP_SERVER エントリが 1 件以上存在）
- **順序依存（先行必須）**: `AAA|authentication.login = "ldap"` を CONFIG_DB に書く前に、`LDAP|global`（`bind_dn` / `base_dn` / `bind_password` の 3 フィールド全て）と `LDAP_SERVER` エントリを揃えなければ `handle_nslcd_service(False)` が呼ばれ nslcd が停止・mask される。
- **自動復旧**: 後から不足していた設定が追加されると `ldap_global_update()` / `ldap_server_update()` / `aaa_update()` が `is_ldap_config_complete()` を再評価し、条件を満たした時点で `handle_nslcd_service(True)` が呼ばれ nslcd が起動する。
- evidence: `hostcfgd:437-442`, `hostcfgd:241-250`, `hostcfgd:553-564`

### 2. LDAP_SERVER → LDAP|global → AAA の推奨書き込み順序

- `AaaCfg.load()` (hostcfgd:399-417): 初期化時は `ldap_global_conf` を先に処理してから `ldap_conf`（LDAP_SERVER）を処理し、最後に `modify_conf_file()` を 1 回だけ呼ぶ。中間状態での `nslcd.conf` 生成は発生しない。
- runtime 中の個別イベント処理: `ldap_global_handler()` → `ldap_global_update()` → `modify_conf_file()` + `handle_nslcd_service()` / `ldap_server_handler()` → `ldap_server_update()` → `modify_conf_file()` + `handle_nslcd_service()` がそれぞれ独立して動作する。
- **順序依存（推奨）**: runtime での設定変更は `LDAP_SERVER` エントリ追加 → `LDAP|global` 設定 → `AAA|authentication.login = "ldap"` の順に書くことで、各ステップの `is_ldap_config_complete()` 評価が `False` → `False` → `True` と推移し、nslcd の不正起動を避けられる。
- 逆順（`AAA` 先書き）の場合: 各中間状態で `handle_nslcd_service(False)` が繰り返し呼ばれる可能性があるが、全条件が揃った時点で自動復旧する。
- evidence: `hostcfgd:399-417`, `hostcfgd:2331-2343`, `hostcfgd:2475-2476`

### 3. priority ソート — LDAP_SERVER 複数エントリの順序不定リスク

- `modify_conf_file()` 内 (hostcfgd:706-713): `ldapsrvs_conf` は `sorted(..., key=lambda t: int(t['priority']), reverse=True)` で降順ソートされる。priority 値が大きいサーバが nslcd の URI リストで先頭になる。
- **順序依存（priority 重複）**: 複数の `LDAP_SERVER` エントリが同一 priority 値を持つ場合、Python の `sorted()` は安定ソートのためメモリ上の挿入順（＝ CONFIG_DB からの取得順）が保持されるが、この取得順は Redis の `HGETALL` 結果に依存し、**書き込み順序は保証されない**。
- YANG スキーマには priority 重複チェックがなく CLI 上でも重複は許可される。フェイルオーバ順序が重要な環境では priority 値の一意性を運用ルールで担保する必要がある。
- evidence: `hostcfgd:706-713`

### 4. LDAP|global mergeWith — グローバル設定がサーバ設定を上書きする

- `modify_conf_file()` 内 (hostcfgd:709-711): 各 LDAP_SERVER エントリに対して `server = ldap_global.copy()` してから `server.update(self.ldap_servers[addr])` する。
- これにより `LDAP|global` のフィールド（`bind_dn`, `base_dn`, `bind_password`, `port`, `version`, `bind_timeout`, `timeout`）が **server エントリのベース値**として使われ、サーバ固有フィールド（`priority`）で上書きされる。
- **順序依存（設計上の先行前提）**: `LDAP|global` が CONFIG_DB に存在しない状態で `LDAP_SERVER` エントリのみが存在すると、`ldap_global = self.ldap_global_default.copy()` (空 dict) が使われ、`LdapCfg` のクラス属性 fallback が適用される。`LDAP|global` の書き込みが `LDAP_SERVER` より後になった場合でも `ldap_global_update()` → `modify_conf_file()` で設定ファイルが再生成されるが、その間の nslcd 設定は不完全（`base_dn` = `LdapCfg.BASE` の example.com 値など）になる。
- evidence: `hostcfgd:650-651`, `hostcfgd:706-713`, `ldap.py:8-18`

### 5. load() フェーズでの処理順序 — LDAP は AAA バッチ内で最後に処理

- `AaaCfg.load()` 内の処理順序: AAA → TACPLUS → TACPLUS_SERVER → RADIUS → RADIUS_SERVER → **LDAP(global)** → **LDAP_SERVER** → `modify_conf_file()`
- `hostcfgd.load_independent_config()` は `wait_till_system_init_done()` より**前**に呼ばれるため、LDAP を含む AAA 設定はシステム初期化完了前に CONFIG_DB から読み込まれる。
- **順序依存なし（load フェーズ内）**: load フェーズでは全テーブルを一括バッチ読み込みし `modify_conf_file()` は最後の 1 回だけ呼ばれるため、中間状態での設定ファイル生成は発生しない。
- evidence: `hostcfgd:399-417`, `hostcfgd:2221-2230`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `LDAP\|global`（bind_dn / base_dn / bind_password）+ `LDAP_SERVER` エントリ → `AAA` `login=ldap` | **先行必須**（欠如時 nslcd 停止） | 後から設定追加で自動復旧（ldap_global_update / aaa_update が再評価） |
| 2 | `LDAP_SERVER` → `LDAP\|global` → `AAA` の順で書き込む | 推奨（中間 nslcd 停止回避） | 逆順でも最終的に自動復旧するが nslcd 停止期間が生じる |
| 3 | `LDAP_SERVER` の priority 重複 → フェイルオーバ順序不定 | 運用上の注意 | priority 値の一意性を運用ルールで担保 |
| 4 | `LDAP\|global` 未設定時の LDAP_SERVER 単体 → LdapCfg fallback 値（example.com 等）が使われる | 設計上の前提 | LDAP_SERVER 追加前に LDAP\|global を設定済みにする |
| 5 | load フェーズ内は AAA バッチで一括処理 → 中間状態なし | 自動保証 | 対策不要（load フェーズ内） |
