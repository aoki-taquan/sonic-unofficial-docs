# TACPLUS / TACPLUS_SERVER — Phase A コード由来暗黙デフォルト調査

ソース精読: `sonic-host-services/scripts/hostcfgd`、`sonic-utilities/config/aaa.py`、`sonic-buildimage/src/sonic-yang-models/yang-models/sonic-system-tacacs.yang`、`sonic-host-services/data/templates/tacplus_nss.conf.j2`、`sonic-host-services/data/templates/common-auth-sonic.j2`

---

## 1. ハードコードデフォルト（hostcfgd モジュール定数）

| 定数 | 値 | 参照 field | 証跡 |
|------|----|-----------|------|
| `TACPLUS_SERVER_PASSKEY_DEFAULT` | `""` (空文字) | `passkey` | hostcfgd L87 |
| `TACPLUS_SERVER_TIMEOUT_DEFAULT` | `"5"` | `timeout` | hostcfgd L88 |
| `TACPLUS_SERVER_AUTH_TYPE_DEFAULT` | `"pap"` | `auth_type` | hostcfgd L89 |

`tacplus_global_default` dict (L366-370) でこれら 3 値が常に初期化され、`TACPLUS|global` の取得値で上書きされる。`TACPLUS|global` が空でも `timeout=5`、`auth_type=pap`、`passkey=""` は補完される。

## 2. CLI 書き込み時デフォルト（aaa.py `tacacs add`）

`config tacacs add <addr>` コマンドは以下を**無条件**に CONFIG_DB へ書き込む:

| フィールド | CLI default値 | コード |
|-----------|-------------|--------|
| `tcp_port` | `49` | `default=49` (click.option) |
| `priority` | `1` | `default=1` (click.option) |

`auth_type`、`timeout`、`passkey`、`vrf` は CLI オプションが渡された時のみ書き込まれる（None チェック）。つまり:
- `tcp_port` と `priority` は YANG default だけでなく CLI が明示的に DB へ書き込む
- `auth_type`、`timeout`、`passkey` は省略時に DB に書かれず、hostcfgd の `tacplus_global_default` でランタイム補完される

## 3. ランタイム global→per-server 継承（modify_conf_file）

```python
# hostcfgd L648-663
tacplus_global = self.tacplus_global_default.copy()   # {auth_type:pap, timeout:5, passkey:""}
tacplus_global.update(self.tacplus_global)             # TACPLUS|global で上書き

for addr in self.tacplus_servers:
    server = tacplus_global.copy()                     # global 値を per-server ベースにコピー
    server['ip'] = addr
    server.update(self.tacplus_servers[addr])          # per-server 値で上書き
```

**継承ルール**: `TACPLUS|global` の `auth_type`/`timeout`/`passkey` は全サーバーに fallback。per-server で上書き可。

## 4. YANG default と実装 discrepancy

### 4-A: `key_encrypt` — YANG定義済みだが hostcfgd で未参照 (dead field)

YANG: `key_encrypt_type` → `default false`。しかし hostcfgd の `modify_conf_file()` および全テンプレートに `key_encrypt` の参照ゼロ。passkey は CONFIG_DB から平文でそのまま展開される。`key_encrypt=true` を設定しても暗号化・復号処理は行われず、passkey が暗号化されたまま pam_tacplus に渡される (= 認証失敗)。**デッドフィールド**。

### 4-B: `src_intf` vs `src_ip` — YANG定義と実装の乖離

YANG: `TACPLUS|global.src_intf` (union leafref)。しかし hostcfgd L653-656:
```python
if 'src_ip' in tacplus_global:    # src_ip を参照
    src_ip = tacplus_global['src_ip']
else:
    src_ip = None
```
`src_intf` を読み取る処理がない（RADIUS には `get_interface_ip(server['src_intf'])` が実装されている）。`TACPLUS|global.src_intf` を設定しても PAM / NSS 設定に `source_ip=...` は挿入されない。`src_ip` はどの書き込み経路でも CONFIG_DB に書き込まれないため、TACPLUS の `source_ip` 機能は実質的に動作しない。**YANG-実装 discrepancy + dead consumer**。

### 4-C: `priority` — YANG `default 1` だが CLI が常に書き込む

CLI が `priority` を常に `1` として書き込むため YANG default は実質 passthrough。hostcfgd は `int(t['priority'])` で降順ソートするため、`priority` が DB に存在しない場合は `KeyError` → `ValueError` でソートが失敗する。CLI 経由では常に存在するが、直接 DB 操作時は注意。

## 5. passkey 空文字デフォルトの silent drop

`TACPLUS_SERVER_PASSKEY_DEFAULT = ""` → テンプレートで `secret=` (空) として pam_tacplus に渡される。pam_tacplus は空 secret を許容するが、サーバー側が shared secret を要求する構成では認証失敗になる。ユーザーに通知される仕組みなし (silent)。

## 6. `aaa.authentication.login` 依存（経路依存 dead consumer）

`TACPLUS_SERVER` エントリが存在しても `AAA|authentication.login` に `tacacs+` が含まれない場合、hostcfgd は PAM に TACACS+ 行を生成しない（L755: `if 'tacacs+' in authentication['login'] and servers_conf`）。NSS の nsswitch.conf からも除外される（L779）。設定があっても認証には無効。

## 7. `tacacs_global_update` key ≠ 'global' 時の silent drop

```python
def tacacs_global_update(self, key, data, modify_conf=True):
    if key == 'global':          # 'global' 以外は何もしない
        self.tacplus_global = data
```
`TACPLUS` テーブルで key が `global` 以外のエントリは silently 無視される。

## 8. 書き込み順依存

`load()` 呼び出し時 `modify_conf=False` で全エントリをロードした後に `modify_conf_file()` を呼ぶ設計だが、`__init__` 後の即時イベント (SET 操作) は `modify_conf=True` で個別に `modify_conf_file()` を呼ぶ。複数フィールドを別々の SET で書き込む場合、中間状態で設定ファイルが再生成される可能性がある（パーシャル設定の瞬間的適用）。

## 9. migrate_tacplus の上書き条件

`db_migrator.migrate_tacplus()` は `global_old` が空のとき限定で `TACPLUS|global` を新規書き込みする。既存エントリがある場合は何もしない（上書きなし）。

---

## まとめ: フィールド別デフォルト一覧

| テーブル | フィールド | YANGデフォルト | hostcfgdデフォルト | CLIデフォルト | 備考 |
|---------|-----------|--------------|------------------|-------------|------|
| TACPLUS_SERVER | priority | 1 | 継承なし※ | 1 (常時書込) | DB未存在時ソート失敗 |
| TACPLUS_SERVER | tcp_port | 49 | 継承なし | 49 (常時書込) | |
| TACPLUS_SERVER | timeout | 5 | global fallback 5 | 未設定時書かず | |
| TACPLUS_SERVER | auth_type | pap | global fallback pap | 未設定時書かず | |
| TACPLUS_SERVER | key_encrypt | false | **未参照(dead)** | 未実装 | discrepancy |
| TACPLUS_SERVER | passkey | - | global fallback "" | 未設定時書かず | 空でsilent動作 |
| TACPLUS_SERVER | vrf | - | 継承なし | 未設定時書かず | |
| TACPLUS\|global | auth_type | pap | pap | 未設定時書かず | |
| TACPLUS\|global | timeout | 5 | 5 | 未設定時書かず | |
| TACPLUS\|global | key_encrypt | false | **未参照(dead)** | 未実装 | discrepancy |
| TACPLUS\|global | passkey | - | "" (空文字) | 未設定時書かず | |
| TACPLUS\|global | src_intf | - | **src_ipを参照、src_intf無視** | 未実装 | YANG-impl discrepancy |
