# RADIUS_SERVER — 設定生成順序・PAM 順序調査 (Phase B)

生成日: 2026-05-16
ソース: `sonic-net/sonic-host-services/scripts/hostcfgd`

## 調査対象

`hostcfgd` の `modify_conf_file()` メソッドにおける RADIUS_SERVER 設定生成順序と PAM スタック内サーバ順序。

## 設定ファイル生成ステップ順序

L.667–851 の実装を追跡した結果、以下の順序で処理が実行される。

### ステップ 1: グローバル設定マージ (L.667–668)

```python
radius_global = self.radius_global_default.copy()
radius_global.update(self.radius_global)
```

`RADIUS|global` テーブルの値で `radius_global_default` を上書き。グローバル優先度の基底はデフォルト (priority=0, auth_port=1812 等)。

### ステップ 2: NAS 情報自動補完 (L.671–678)

```python
if 'nas_ip' not in radius_global:
    nas_ip = self.get_interface_ip("eth0")
    ...
if 'nas_id' not in radius_global:
    nas_id = self.get_hostname()
    ...
```

`nas_ip`/`nas_id` が未設定の場合は eth0 IP / ホスト名で自動補完。後続の各サーバエントリに継承される。

### ステップ 3: サーバエントリ構築 (L.681–702)

```python
for addr in self.radius_servers:
    server = radius_global.copy()
    server['ip'] = addr
    server.update(self.radius_servers[addr])
    # src_intf 処理 (L.687-700)
    radsrvs_conf.append(server)
```

各 RADIUS_SERVER エントリに対し、グローバル設定をコピーしてサーバ固有設定で上書き。`src_intf` がある場合は IP 解決処理を実行 (L.687–700)。

### ステップ 4: priority 降順ソート (L.703)

```python
radsrvs_conf = sorted(radsrvs_conf, key=lambda t: int(t['priority']), reverse=True)
```

**これが PAM 順序の決定要因**。priority 値が大きいサーバが `radsrvs_conf` の先頭に来る。

### ステップ 5: common-auth-sonic 生成 (L.722–723)

```python
if 'radius' in authentication['login']:
    pam_conf = template.render(..., servers=radsrvs_conf)
```

`AAA.authentication.login` に `radius` が含まれる場合のみ実行。`radsrvs_conf` (priority 降順) がそのまま PAM テンプレートに渡される。

### ステップ 6: NSS radius 設定生成 (L.821)

```python
nss_radius_conf = template.render(..., servers=radsrvs_conf)
```

`/etc/radius_nss.conf` も同じ `radsrvs_conf` 順序で生成。

### ステップ 7: per-server pam_radius_auth.conf 生成 (L.826–837)

```python
for srv in radsrvs_conf:
    pam_radius_auth_file = RADIUS_PAM_AUTH_CONF_DIR + srv['ip'] + "_" + srv['auth_port'] + ".conf"
    ...
```

`radsrvs_conf` の priority 降順でファイルが生成される。ファイル名は `<ip>_<auth_port>.conf`。

### ステップ 8: aaastatsd 制御 (L.839–844)

```python
if ('radius' in authentication['login']) and ('statistics' in radius_global) and radius_global['statistics']:
    cmd = ['service', 'aaastatsd', 'start']
else:
    cmd = ['service', 'aaastatsd', 'stop']
```

RADIUS 有効 + `statistics=true` の場合にのみ統計サービスを起動。

## PAM スタック内サーバ順序

| 順序決定要因 | 詳細 | evidence |
|---|---|---|
| `priority` 降順 | `sorted(..., reverse=True)` — 最大値のサーバが最初に試行される | `hostcfgd` L.703 |
| 同 priority の場合 | Python `sorted()` は安定ソート → `self.radius_servers` dict イテレーション順（登録順）が維持される | Python sort stability |
| `priority` 未設定時 | `radius_global_default['priority'] = 0` で補完 → YANG 範囲外 (1..64) の 0 が最低優先度として使われる | `hostcfgd` L.375 |
| YAML range との乖離 | YANG は `range "1..64"` だが hostcfgd は 0 を許容し降順末尾に配置する | YANG/hostcfgd discrepancy |

## 生成されるファイル一覧と順序

| ファイル | 生成ステップ | サーバ順序 |
|---|---|---|
| `/etc/pam.d/common-auth-sonic` | ステップ 5 | priority 降順 |
| `/etc/radius_nss.conf` | ステップ 6 | priority 降順 |
| `/etc/pam_radius_auth.d/<ip>_<port>.conf` | ステップ 7 (per-server) | priority 降順でファイル生成 |

## 副作用・注意点

- **auth_port 変更時の残留ファイル**: ステップ 7 で旧ポートのファイル (`<ip>_<old_port>.conf`) は削除されない。PAM が古いファイルを参照し続ける可能性がある。
- **部分更新なし**: RADIUS_SERVER の任意フィールド変更でも全ステップが再実行される（全サーバの設定ファイルが再生成）。
- **PAM 反映タイミング**: 次回ログインから有効。既存 SSH セッションには影響しない。
