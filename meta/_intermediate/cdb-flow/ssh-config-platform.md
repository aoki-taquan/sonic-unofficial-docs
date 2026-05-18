# SSH_SERVER — プラットフォーム差調査

Task F Phase H: `SSH_SERVER` テーブル適用時のプラットフォーム/構成差を `hostcfgd` (`sonic-host-services`) と関連テンプレートから精読した結果。

## 結論

**プラットフォーム差なし**。SSH_SERVER は host 単位で適用され、ASIC 種別・multi-asic / chassis 構成に依存しない。

## 根拠

### 1. hostcfgd は host CONFIG_DB のみを購読する

`scripts/hostcfgd` の `HostconfigDaemon`:

- `self.config_db = ConfigDBConnector()` を引数なしで生成 → host namespace の CONFIG_DB に接続
- `self.sshscfg = SshServer()` / `self.pamLimitsCfg = PamLimitsCfg(self.config_db)` で host CONFIG_DB のみを扱う
- `is_multi_npu()` を取得 (hostcfgd:L2182) しているが、`SshServer` / `PamLimitsCfg` には渡されず SSH 経路では参照されない

### 2. SshServer は host ファイルシステムのグローバル設定のみを書き換える

`SshServer.set_policies()` が更新するのは:

- `/etc/ssh/sshd_config` (SSH_CONFG = `/etc/ssh/sshd_config`)
- 一時ファイル `sshd_tmp` → rename でアトミック置換

`PamLimitsCfg.render_conf_file()` が更新するのは:

- `/etc/pam.d/pam-limits-conf`
- `/etc/security/limits.conf`

これらは host root filesystem の単一グローバル設定ファイルで、コンテナ別・ASIC 別ではない。

### 3. limits.conf.j2 / pam_limits.j2 にプラットフォーム分岐なし

`render_conf_file()` は `hwsku` / `type` を Jinja2 テンプレートへ渡すが、実際のテンプレート (`data/templates/limits.conf.j2` / `data/templates/pam_limits.j2`) はこれらの変数を**一切参照しない**。`limits.conf.j2` が条件参照するのは `max_sessions` のみ (`{% if max_sessions and max_sessions | int > 0 %}`):

```jinja2
{% if max_sessions and max_sessions | int > 0 -%}
* - maxsyslogins {{ max_sessions }}
{% endif -%}
```

`platform|hwsku|type|asic|chassis|namespace|vendor` による分岐は 0 ヒット。

### 4. sshd_config 書き換えに ASIC / ハードウェア依存なし

`SshServer.set_policies()` は `SSH_CONFIG_NAMES` 静的マッピング（`ciphers` → `Ciphers`、`ports` → `Port` 等）を使って sshd_config を直接書き換える。SAI / SDK / ASIC capability クエリは一切ない。暗号スイート (`ciphers` / `kex_algorithms` / `macs`) は YANG enumeration で制限されるが、これはプラットフォームに依存せず community YANG モデルで固定されている。

### 5. multi-asic / VOQ chassis での扱い

`is_multi_npu()` が true でも `SSH_SERVER` テーブルは host CONFIG_DB にのみ存在する。各 `asicN` namespace の CONFIG_DB には `SSH_SERVER` エントリが置かれない (YANG scope: host)。chassis 全体で共有される host-level 設定であり、line card / supervisor 各 host で独立した `hostcfgd` が同一処理を実行する。

## まとめ

SSH_SERVER 経路は SAI を経由せず ASIC SDK にも依存しない host-only な「Linux sshd / PAM 設定ファイル再生成」処理。よって `T0 / T1 / VOQ chassis / multi-asic` 等の物理構成や ASIC ベンダーに関わらず動作・適用範囲は同一。唯一のプラットフォーム依存候補であった `hwsku` / `type` は Jinja2 テンプレートに未参照のため実質無効。
