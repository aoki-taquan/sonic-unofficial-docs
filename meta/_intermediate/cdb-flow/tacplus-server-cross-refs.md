# TACPLUS_SERVER 暗黙参照スキャン (Phase C)

`docs/reference/config-db/tacplus-server.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソースは `sonic-net/sonic-host-services/scripts/hostcfgd`、`sonic-utilities/scripts/db_migrator.py`、
`sonic-buildimage/src/sonic-yang-models/yang-models/sonic-system-aaa.yang`。

## スキャン手順

```
grep -nE 'subscribe\(|init_data\[|AaaCfg\.load|tacplus_global|tacplus_servers|modify_conf_file' \
    .cache/sonic-sources/sonic-host-services/scripts/hostcfgd

grep -nE 'TACPLUS|tacplus|AAA|authorization' \
    .cache/sonic-sources/sonic-utilities/scripts/db_migrator.py

grep -nE 'tacacs|TACPLUS' \
    .cache/sonic-sources/sonic-buildimage/src/sonic-yang-models/yang-models/sonic-system-aaa.yang
```

## 検出された暗黙参照テーブル

### 共依存 — 同一 `AaaCfg.load()` 一括ロード (hostcfgd:2221-2230)

`load_independent_config()` は `init_data` から 7 テーブルを読み出して `AaaCfg.load()` に一括渡し、
最後に `modify_conf_file()` を 1 回だけ呼ぶ。`TACPLUS_SERVER` が変化すると `modify_conf_file()` が
これら全テーブルの in-memory コピーを結合して PAM/NSS を再生成する。

| テーブル | 役割 | evidence |
|---|---|---|
| `AAA` | `authentication.login` に `tacacs+` が含まれる場合のみ PAM 行・nsswitch.conf への TACACS+ エントリ生成を行う制御テーブル | hostcfgd:2223, L755 |
| `TACPLUS` | `auth_type`/`timeout`/`passkey`/`src_ip` の global デフォルトを提供。per-server 値の継承元 | hostcfgd:2224, L648-665 |
| `RADIUS` / `RADIUS_SERVER` | `modify_conf_file()` 内で NSS 設定 (nsswitch.conf の `passwd` 行) を tacplus/radius の排他制御で決定するために同時参照される | hostcfgd:2226-2227, L757-783 |
| `LDAP` / `LDAP_SERVER` | 同上。LDAP 有効時は nsswitch の `group`/`shadow` 行も書き換え。TACACS+ との排他は `elif` チェーンで制御 | hostcfgd:2228-2229, L770-783 |

### YANG 制約による依存 (sonic-system-aaa.yang:50-52)

`AAA_LIST[type="authentication"].login` に `tacacs+` を設定するためには
`/sonic-system-tacacs/TACPLUS/global/passkey` が存在することを YANG `must` 文が要求する。
すなわち `TACPLUS|global.passkey` が未設定の状態では `AAA|authentication.login = "tacacs+"` を
CLI から書き込むこと自体が YANG バリデーションで reject される。

```yang
must 'not(./type = "authentication" and contains(./login, "tacacs+")
      and not(/tacacs:sonic-system-tacacs/tacacs:TACPLUS/tacacs:global/tacacs:passkey))' {
    error-message "Authentication with 'tacacs+' is not allowed when passkey not exists.";
}
```

evidence: `sonic-system-aaa.yang` L50-52

### db_migrator — マイグレーション時の相互依存 (db_migrator.py:856-903)

`migrate_aaa()` は `TACPLUS|global.passkey` の有無を確認してから `AAA|authorization` を設定する。

| 条件 | 動作 |
|---|---|
| `TACPLUS\|global.passkey` が存在し非空 | `AAA\|authorization` を migration ソースの値で設定 |
| `TACPLUS\|global.passkey` が空または欠如 | `AAA\|authorization` エントリを DB から削除してコマンド認可を無効化 |

evidence: `db_migrator.py:890-903`

### NSS 設定排他制御 (hostcfgd:754-783)

`modify_conf_file()` の nsswitch.conf 編集ロジックは tacplus / radius / ldap を排他 elif で制御する。
`AAA|authentication.login` に複数プロトコルが列挙された場合でも、nsswitch.conf の `passwd` 行追加は
最初にマッチしたプロトコル (tacacs+ → radius → ldap の優先順) のみ。

| 優先順 | 条件 | nsswitch.conf passwd 行 |
|--------|------|-------------------------|
| 1 | `tacacs+ in login AND servers_conf` | `tacplus files` / `tacplus compat` |
| 2 | `radius in login` | `files radius` / `compat radius` |
| 3 | `ldap in login` | `files ldap` / `compat ldap` |
| 4 | none | tacplus / radius / ldap 行を全削除 |

evidence: `hostcfgd:755-783`

## まとめ — `tacplus-server.md` Phase C 記載対象

| カテゴリ | テーブル / モジュール |
|---|---|
| 共依存 (load 一括) | `AAA` / `TACPLUS` / `RADIUS` / `RADIUS_SERVER` / `LDAP` / `LDAP_SERVER` |
| YANG 制約 | `sonic-system-aaa` の `must` 文が `TACPLUS\|global.passkey` を外部参照 |
| db_migrator | `migrate_aaa()` が `TACPLUS\|global.passkey` を参照して `AAA\|authorization` を条件付き削除 |
| nsswitch.conf 排他制御 | `AAA\|authentication.login` の値で tacplus/radius/ldap の nsswitch エントリが排他切替 |
