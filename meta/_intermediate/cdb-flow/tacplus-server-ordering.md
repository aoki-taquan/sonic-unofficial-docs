# TACPLUS_SERVER — Phase B 書込み順依存スキャンノート

対象テーブル: `TACPLUS_SERVER` / `TACPLUS|global`
Consumer: `hostcfgd` / `AaaCfg` (`sonic-host-services/scripts/hostcfgd`)
スキャン範囲: `load()`, `tacacs_global_update()`, `tacacs_server_update()`, `modify_conf_file()` 全行精読

---

## 検出した順序依存・タイミング依存

### 1. load フェーズの読み込み順序と modify_conf_file() 呼び出し

`AaaCfg.load()` (hostcfgd:399-417) は以下の順序でテーブルを取り込む:

1. `AAA` → `aaa_update(..., modify_conf=False)`
2. `TACPLUS|global` → `tacacs_global_update(..., modify_conf=False)`
3. `TACPLUS_SERVER` 各エントリ → `tacacs_server_update(..., modify_conf=False)`
4. `RADIUS|global` / `RADIUS_SERVER` / `LDAP|global` / `LDAP_SERVER`
5. `modify_conf_file()` を 1 回のみ呼び出す

load フェーズ内では `modify_conf=False` により中間 PAM 再生成は起きない。`load_independent_config()` から呼ばれるため `wait_till_system_init_done()` より**前**に実行される（systemctl 完了前適用）。

evidence: `hostcfgd:399-417`, `hostcfgd:2221-2230`

### 2. modify_conf_file() での PAM 設定生成順序

`modify_conf_file()` (hostcfgd:641-816) の TACACS+ 関連処理の実行順:

1. `tacplus_global_default`（`timeout="5"`, `auth_type="pap"`, `passkey=""`）をコピー
2. `TACPLUS|global` 実値で上書き
3. `TACPLUS_SERVER` 各エントリに `tacplus_global.copy()` をベース + per-server 値で上書き
4. `servers_conf` を `priority` 降順ソート (`reverse=True`): `sorted(..., key=lambda t: int(t['priority']), reverse=True)` — 大きい priority が PAM の先頭（evidence: hostcfgd:665）
5. Jinja2 テンプレート (`common-auth-sonic.j2`) で展開 → `.tmp` に書き込み → `os.rename()` でアトミック置換
6. `/etc/pam.d/sshd` / `/etc/pam.d/login` の `@include common-auth` を `common-auth-sonic` に書き換え
7. `nsswitch.conf` の `passwd` 行を更新（`tacacs+` 有効時は `tacplus` を先頭に挿入; 他メソッド時は削除）
8. `/etc/tacplus_nss.conf` を `tacplus_nss.conf.j2` から生成（認可・アカウンティング設定含む）
9. `audisp-tacplus` に SIGHUP 送信（アカウンティングリロード）

evidence: `hostcfgd:641-816`

### 3. TACPLUS_SERVER 先書き推奨

runtime 中に `AAA|authentication.login = "tacacs+"` を先書きし、`TACPLUS_SERVER` を後追いすると:

- AAA 書き込み時点で `servers_conf = []` → `common-auth-sonic` は TACACS+ なし（実質 `local`）
- `TACPLUS_SERVER` 追加後に `tacacs_server_update()` → `modify_conf_file()` で正しい設定に更新

その間 TACACS+ 認証は機能しない（silent 中間不整合）。

推奨順序: `TACPLUS|global` → `TACPLUS_SERVER` エントリ群 → `AAA|authentication.login`

evidence: `hostcfgd:641-665`, `hostcfgd:473-481`

### 4. TACPLUS|global.passkey 先行必須（YANG + db_migrator）

2 種類の先行必須制約が存在する:

**YANG バリデーション**: `sonic-system-aaa.yang` の must 制約により、`AAA|authentication.login` に `tacacs+` を含む場合、`TACPLUS|global.passkey` が存在しなければ CLI 書き込みが reject される。

**db_migrator**: `migrate_aaa()` (db_migrator.py:869-900) は `TACPLUS|global.passkey` が空の場合、既存の `AAA|authorization` エントリを**削除**する。事後に passkey を設定しても自動復元されない（手動 `config aaa authorization login tacacs+` が必要）。

evidence: `sonic-system-aaa.yang:must`, `db_migrator.py:869-900`

### 5. priority 欠如による設定生成中断リスク

`sorted(..., key=lambda t: int(t['priority']))` は `priority` キーが存在しない場合 `KeyError`、整数変換不可の値は `ValueError` を発生させ設定ファイル生成が中断する。

- CLI (`config tacacs add`) は常に `priority=1` を書き込む（aaa.py:267）
- 直接 DB 操作（`sonic-db-cli CONFIG_DB HSET`）時は `priority` フィールドの明示的設定が必須

evidence: `hostcfgd:665`, `sonic-utilities/config/aaa.py:267`

### 6. AAA.authentication.login に tacacs+ 未含有時のサイレントスキップ

`modify_conf_file()` 内の `if 'tacacs+' in authentication['login'] and servers_conf:` (hostcfgd:755):

- `TACPLUS_SERVER` にエントリが存在しても `AAA|authentication.login` に `tacacs+` がなければ nsswitch.conf に `tacplus` は挿入されない
- PAM テンプレートも `servers` が空として展開される
- この動作はサイレント（エラーログなし）

evidence: `hostcfgd:755-761`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | load フェーズ: AAA → TACPLUS → TACPLUS_SERVER → ... → modify_conf_file() | 1 回まとめ生成（中間状態なし） | silent fallback（不在フィールドは定数デフォルト） |
| 2 | TACPLUS_SERVER エントリ先書き → AAA 書き込み | 推奨（中間不整合最小化） | runtime は subscribe 後追いで自動更新 |
| 3 | TACPLUS\|global.passkey 設定 → AAA authentication.login=tacacs+ | **先行必須**（YANG reject） | passkey を先に CLI で設定してから AAA 変更 |
| 4 | TACPLUS\|global.passkey 存在 → db_migrator による AAA authorization 保持 | **先行必須**（passkey 未設定で migration が走ると authorization 削除） | upgrade 前に passkey 設定済みであること |
| 5 | priority フィールド存在 + 整数変換可能 → PAM 生成成功 | **前提条件**（KeyError / ValueError で生成中断） | CLI 使用時は自動付与; 直接 DB 操作時は明示設定 |
| 6 | AAA.authentication.login に tacacs+ を含む → TACACS+ が PAM / NSS に反映 | 機能前提（silent skip） | login フィールドに tacacs+ を追加してから効果確認 |
