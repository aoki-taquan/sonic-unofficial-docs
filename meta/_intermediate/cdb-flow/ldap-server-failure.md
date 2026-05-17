# LDAP_SERVER — 失敗挙動調査 (Phase D)

生成日: 2026-05-17
ソース: `sonic-net/sonic-host-services/scripts/hostcfgd`

## 調査対象

`hostcfgd` の LDAP 関連ハンドラ (`ldap_global_update`, `ldap_server_update`, `modify_conf_file`, `handle_nslcd_service`, `is_ldap_config_complete`) における失敗・エラー処理。

## 失敗ケース一覧

### 1. is_ldap_config_complete() が False → nslcd stop + mask

`is_ldap_config_complete()` は以下の全条件を AND 評価する（L.437-442）:

```python
def is_ldap_config_complete(self):
    if self.ldap_global == {}:
        return False
    return self.ldap_global.get('bind_dn', "") and \
           self.ldap_global.get('base_dn', "") and \
           self.ldap_global.get('bind_password', "") and \
           'ldap' in self.authentication.get('login', "") and \
           self.ldap_servers
```

いずれかが欠けると `handle_nslcd_service(False)` が呼ばれ、nslcd が stop + mask される（L.247-251）。

**トリガー条件**:
- `LDAP|global` 未設定または `bind_dn`/`base_dn`/`bind_password` いずれかが空
- `AAA|authentication.login` に `ldap` が含まれない
- `LDAP_SERVER` エントリが 0 件

**挙動**: `systemctl stop nslcd && systemctl mask nslcd` が実行される。LDAP 認証が完全に無効化される。

### 2. priority フィールド不正値 → ValueError で modify_conf_file() 中断

`modify_conf_file()` は `ldapsrvs_conf = sorted(..., key=lambda t: int(t['priority']), reverse=True)` を実行する（L.713）。`priority` フィールドに整数変換不可能な文字列が含まれる場合、`int()` が `ValueError` を送出し `modify_conf_file()` 全体が中断される。nslcd.conf/ldap.conf は更新されず前回生成済みファイルが残る。例外はキャッチされない（unhandled）。

CLI (`config ldap add`) は常に有効な数値 priority を書き込むため通常経路では発生しないが、`sonic-db-cli` 等での直接書き込み時に注意が必要。

### 3. generate_file_from_template 失敗 → LOG_ERR のみ・前回設定残留

`nslcd.conf` および `ldap.conf` の生成は `generate_file_from_template()` で行われる（L.855, L.863）。この関数は例外を内部でキャッチし `LOG_ERR: 'Failed generate_file_from_template error={e}'` をsyslog に出力して **復帰** する（L.214-216）。

```python
def generate_file_from_template(template_j2, file_conf_output, permission, kwargs):
    try:
        ...
        os.rename(file_conf_output + ".tmp", file_conf_output)
    except Exception as e:
        log_msg = f'Failed generate_file_from_template error={e}'
        syslog.syslog(syslog.LOG_ERR, log_msg)
```

**結果**: 設定ファイル (`/etc/nslcd.conf`, `/etc/ldap/ldap.conf`) は更新されず前回の内容のまま残る。その後 `handle_nslcd_service(True)` が呼ばれ nslcd が **前回の設定で restart** される。メモリ上の状態（`self.ldap_servers`）と nslcd の実行設定が乖離する。

### 4. pam_conf 生成失敗 → 例外非キャッチ・PAM 設定残留

`modify_conf_file()` は PAM 設定ファイル (`/etc/pam.d/common-auth-sonic`) を直接 `open/write/rename` で生成する（L.728-731）。`generate_file_from_template()` と異なり例外キャッチなし。Jinja2 テンプレートエラー・ファイルシステム権限不足・ディスクフルで例外が上位に伝播し、`ldap_server_update()` / `ldap_global_update()` のコールスタック全体が中断される。

### 5. ldap_server_update data=={} で存在しない key を削除 → silent skip

```python
def ldap_server_update(self, key, data, modify_conf=True):
    if data == {}:
        if key in self.ldap_servers:
            del self.ldap_servers[key]
    ...
```

`data == {}` かつ `key` が `self.ldap_servers` に存在しない場合は何もしない（silent skip）。その後 `modify_conf_file()` と `handle_nslcd_service()` は通常通り実行される。

## 失敗マトリクス

| 失敗ケース | トリガー | 検出方法 | 自動復旧 | evidence |
|---|---|---|---|---|
| `is_ldap_config_complete()` == False | bind_dn/base_dn/bind_password 欠如、AAA login 不一致、LDAP_SERVER 空 | syslog LOG_DEBUG "nslcd: deactivating" | LDAP 設定追加後の次の更新イベントで自動復旧 | `hostcfgd` L.437-442, L.247-251 |
| priority 不正値 ValueError | `int(t['priority'])` 変換失敗 | syslog 出力なし（unhandled exception） | なし（手動で正しい priority に修正が必要） | `hostcfgd` L.713 |
| generate_file_from_template 失敗 | FS 権限不足・ディスクフル・テンプレートエラー | syslog LOG_ERR "Failed generate_file_from_template" | なし（前回設定で nslcd 再起動） | `hostcfgd` L.200-216 |
| pam_conf 生成 unhandled exception | FS エラー・Jinja2 エラー | 例外スタックトレース（syslog 未保証） | なし | `hostcfgd` L.716-731 |
| 存在しない key の DEL | data=={} + key 未存在 | なし（silent skip） | 不要（副作用なし） | `hostcfgd` L.554-558 |
