# SERIAL_CONSOLE / SSH_SERVER — プラットフォーム差調査

Task F Phase H: `SERIAL_CONSOLE` / `SSH_SERVER` テーブル適用時のプラットフォーム/構成差を `hostcfgd` (`sonic-host-services`) と `sonic-buildimage` の関連アセットから精読した結果。

## 結論

**プラットフォーム差なし**。SERIAL_CONSOLE / SSH_SERVER は host 単位で適用される host-only 設定であり、ASIC 種別・multi-asic / chassis 構成・ベンダー固有モジュールに依存しない。

## 根拠

### 1. hostcfgd は host CONFIG_DB のみを購読する

`scripts/hostcfgd` の main クラスで:

- 行 2182: `self.is_multi_npu = device_info.is_multi_npu()` を取得するが、**`SshServer` / `SerialConsoleCfg` には渡されず、SSH/シリアル経路では参照されない**
- `SshServer.__init__` (行 1045-1047) は `self.policies = {}` のみを保持し、asicN namespace への接続や iteration を一切しない
- `SerialConsoleCfg.__init__` (行 2013+) も同様に host scope の `ConfigDBConnector()` のみを使用

### 2. 適用対象はすべて host root filesystem のグローバルファイル

`SshServer.set_policies()` が更新するのはすべて host root filesystem 上のファイル:

- `/etc/ssh/sshd_config` — SSH デーモン設定 (ホスト共通)
- `/etc/security/limits.conf` / `/etc/security/limits.d/` — PAM limits (ホスト共通)

`SerialConsoleCfg.update_serial_console_cfg()` が再生成するのも:

- `tmout-env.sh.j2` → `/etc/profile.d/tmout-env.sh` (ホスト共通)
- `sysrq-sysctl.conf.j2` → `/etc/sysctl.d/` エントリ (ホスト共通)

これらはコンテナごと・ASIC ごとではなく **host 1 か所** のみ。

### 3. テンプレートにプラットフォーム分岐なし

`tmout-env.sh.j2` および `sysrq-sysctl.conf.j2` を `platform|asic|chassis|namespace|vendor` で grep しても 0 ヒット。

`tmout-env.sh.j2` の分岐は `SERIAL_CONSOLE.POLICIES.inactivity_timeout` 値のみ。`sysrq-sysctl.conf.j2` の分岐は `SERIAL_CONSOLE.POLICIES.sysrq_capabilities == 'enabled'` のみ。

### 4. image_config に SSH / シリアルコンソール向けプラットフォーム上書きなし

`sonic-buildimage/files/image_config/` の `cli_sessions/` ディレクトリはプラットフォーム非依存のテンプレートのみを保持する。`platform|asic|chassis|namespace|vendor` での grep で 0 ヒット。SSH 設定のプラットフォーム別差し替え機構はビルド時にも実行時にもない。

### 5. multi-asic / VOQ chassis 構成での扱い

`is_multi_npu()` が true でも `SSH_SERVER` / `SERIAL_CONSOLE` テーブルは host CONFIG_DB のみに置かれ、`asicN` namespace の CONFIG_DB には存在しない。VOQ chassis の各 host (supervisor / line card) で独立した `hostcfgd` が同 SSH / シリアル設定を管理する。chassis 全体での集中適用機構はない。

## まとめ

SERIAL_CONSOLE / SSH_SERVER 経路は SAI を経由せず、ASIC SDK にも依存しない host-only な「Linux sshd_config / PAM / sysctl 設定ファイル再生成」処理。よって `T0 / T1 / VOQ chassis / multi-asic` 等の物理構成や ASIC ベンダーに関わらず動作・適用範囲は同一。
