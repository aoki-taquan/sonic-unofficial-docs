# TACPLUS_SERVER テーブル 暗黙参照スキャン (Phase C)

`docs/reference/config-db/tacplus-server.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソースは `sonic-net/sonic-host-services/scripts/hostcfgd`。`TACPLUS_SERVER` / `TACPLUS` テーブル変更時に `hostcfgd` (`AaaCfg`) が間接的に読み出す関連 CONFIG_DB テーブルを列挙する。

## スキャン手順

```
grep -n "TACPLUS\|tacacs\|tacplus" \
    .cache/sonic-sources/sonic-host-services/scripts/hostcfgd | \
    grep -i "subscribe\|init_data\|load_independent"

grep -n "modify_conf_file\|authentication\|login" \
    .cache/sonic-sources/sonic-host-services/scripts/hostcfgd | head -60
```

`hostcfgd` の `load_independent_config()` (L2221-2230) で `AaaCfg.load()` に渡される 7 テーブル、`modify_conf_file()` 内で参照される `authentication['login']` の値、および `register_callbacks()` (L2456-2509) で `TACPLUS_SERVER` に間接影響する subscribe を抽出。

## 検出された暗黙参照テーブル

### 起動時一括ロード (load_independent_config — hostcfgd:2221-2230)

`AaaCfg.load(aaa, tacacs_global, tacacs_server, radius_global, radius_server, ldap_global, ldap_server)` に 7 テーブルが渡される。`TACPLUS_SERVER` はその一員だが、**PAM/NSS テンプレ再生成は全 7 テーブルの dict 結合後に `modify_conf_file()` が一括実行**する。つまり `AAA` の値が `TACPLUS_SERVER` の効果を決定する。

| テーブル | 参照タイミング | 用途 | evidence |
|---|---|---|---|
| `AAA` | load + subscribe | `authentication['login']` の値が `'tacacs+'` を含む場合のみ TACACS+ 行を PAM/NSS に出力。TACPLUS_SERVER の設定全体の有効化を制御 | hostcfgd:2223,2470,755 |
| `TACPLUS` | load + subscribe | TACACS+ global (`passkey` / `auth_type` / `timeout` / `src_ip`) を per-server dict にマージして `tacplus_global_default` の上書き元 | hostcfgd:2224,2471,648-649 |

> `TACPLUS_SERVER` が存在しても `AAA|authentication.login` に `tacacs+` が含まれない場合、`modify_conf_file()` 内の `if 'tacacs+' in authentication['login'] and servers_conf:` (hostcfgd:755) が偽となり、PAM 設定と `nsswitch.conf` の tacplus 行が**生成されない** (silent skip)。

### `AAA|authentication.login` の PAM 連動制御

`modify_conf_file()` (hostcfgd:640-830) 内でテンプレートレンダリング時に `authentication['login']` の内容に応じて分岐する:

| 条件 | 効果 | evidence |
|---|---|---|
| `'tacacs+'` in `authentication['login']` かつ `servers_conf` 非空 | `/etc/pam.d/common-auth-sonic` を TACACS+ chain で生成 + `nsswitch.conf` に `tacplus` を prepend | hostcfgd:725,755-761 |
| `'tacacs+'` なし | PAM から TACACS+ 行を除去 + `nsswitch.conf` の `tacplus` を削除 | hostcfgd:779-781 |
| `'radius'` in `authentication['login']` | PAM を RADIUS chain で生成 (TACACS+ より優先: `if radius` が `else` ブランチで上書き) | hostcfgd:723,763-770 |
| `'ldap'` in `authentication['login']` | PAM を LDAP chain で生成 | hostcfgd:721,771-778 |

### PAM 設定ファイル連動 (ファイル間接参照)

`modify_conf_file()` が書き換えるファイルのうち、TACACS+ 有効時に影響するもの:

| ファイル | 書き換え内容 | evidence |
|---|---|---|
| `/etc/pam.d/common-auth-sonic` | Jinja2 テンプレ `common-auth-sonic.j2` を展開。TACACS+ chain を含む | hostcfgd:715,725,728-731 |
| `/etc/nsswitch.conf` | `passwd` 行に `tacplus` を prepend または削除 | hostcfgd:757-761,779 |
| `/etc/tacplus_nss.conf` | `tacplus_nss.conf.j2` テンプレを展開。認証/認可/accounting の設定と server list を含む | hostcfgd:805-815 |
| `/etc/pam.d/sshd` | `common-auth-sonic` include に書き換え (TACACS+ 有効時) | hostcfgd:748 |
| `/etc/pam.d/login` | 同上 | hostcfgd:749 |

### `AAA|authorization` / `AAA|accounting` の連動

`TACPLUS_SERVER` の設定は `AAA|authorization.login` / `AAA|accounting.login` の値にも間接依存する。`tacplus_nss.conf.j2` に `tacacs_authorization` / `tacacs_accounting` フラグとして渡される。

| テーブル.フィールド | 用途 | evidence |
|---|---|---|
| `AAA|authorization.login` | `'tacacs+'` を含む場合 `tacacs_authorization_conf="on"` を NSS テンプレに渡す | hostcfgd:784-785 |
| `AAA|accounting.login` | `'tacacs+'` を含む場合 `tacacs_accounting_conf="on"` を NSS テンプレに渡す | hostcfgd:789-790 |

### 範囲外 (誤解されやすい隣接テーブル)

- `RADIUS` / `RADIUS_SERVER`: 同 `modify_conf_file()` 内で処理されるが `TACPLUS_SERVER` の設定とは独立したブランチ。`authentication['login']` が `'radius'` の場合は TACACS+ chain が上書きされるため相互排他的な関係。
- `LDAP` / `LDAP_SERVER`: 同様に独立ブランチ。
- `DEVICE_METADATA` / インタフェーステーブル: RADIUS の `nas_ip` / `src_intf` 解決のみに使用。TACACS+ 経路には現れない (`src_intf` は dead code — Phase A 参照)。

## まとめ — `tacplus-server.md` Phase C 記載対象

| カテゴリ | テーブル / フィールド |
|---|---|
| 有効化制御 (PAM/NSS への反映を制御) | `AAA|authentication.login` (`'tacacs+'` 要否) |
| global 設定マージ元 | `TACPLUS|global` (`passkey` / `auth_type` / `timeout` / `src_ip`) |
| 認可・accounting フラグ | `AAA|authorization.login` / `AAA|accounting.login` |

## 検証コマンド

```bash
grep -n "subscribe\|init_data\['\(AAA\|TACPLUS\)" \
    .cache/sonic-sources/sonic-host-services/scripts/hostcfgd

grep -n "tacacs+\|modify_conf_file\|servers_conf\|authentication\[.login" \
    .cache/sonic-sources/sonic-host-services/scripts/hostcfgd | head -40
```

このスキャン結果から派生して `docs/reference/config-db/tacplus-server.md` の `<!-- cross-refs -->` ブロックを生成する。
