# SSH SFTP サブシステム — プラットフォーム差調査

Task F Phase H: `SSH_SFTP` (非存在テーブル) / `SSH_SERVER` テーブル処理の `SshServer` クラス (`sonic-host-services/scripts/hostcfgd`) と YANG モジュール (`sonic-ssh-server.yang`) を中心に、プラットフォーム・構成依存差を精読した結果。

## 結論

**プラットフォーム差なし**。`SshServer` クラスと SFTP サブシステムの扱いは、ASIC 種別・multi-asic / chassis 構成・ベンダー固有差分に一切依存しない。

## 根拠

### 1. SshServer クラスにプラットフォーム条件分岐なし

`class SshServer` (`hostcfgd:1045-1161`) を `platform|multi_asic|is_multi_npu|chassis|asic[0-9]|namespace|vendor` で grep すると **0 ヒット**。

- `__init__()` は `self.policies = {}` のみ
- `set_policies()` は `SSH_CONFIG_NAMES` 辞書に基づき固定ファイルパス (`/etc/ssh/sshd_config`) を書き換えるのみ
- `Subsystem sftp` 行は `SSH_CONFIG_NAMES` に存在しないため処理対象外 (機種非依存)

### 2. hostcfgd は host 単一インスタンス

`hostcfgd` main クラス (行 2166-2167) は `ConfigDBConnector()` を引数なしで生成 → **host namespace の CONFIG_DB のみ**に接続。`self.is_multi_npu = device_info.is_multi_npu()` (行 2182) は取得されるが、`SshServer` 経路では参照されず SSH/SFTP 処理に影響しない。

multi-asic / VOQ chassis でも:

- `SSH_SERVER` テーブルは host CONFIG_DB のみに存在し、`asicN` namespace の CONFIG_DB には存在しない
- `hostcfgd` は host namespace で 1 インスタンスのみ起動し、`/etc/ssh/sshd_config` を host root filesystem 上で 1 か所更新する

### 3. YANG モデルにプラットフォーム分岐なし

`sonic-buildimage/src/sonic-yang-models/yang-models/sonic-ssh-server.yang` を `platform|asic|chassis|namespace|vendor|multi` で grep すると **namespace 宣言の "github.com/sonic-net/sonic-ssh-server" のみ**にヒット (0 件の機種分岐)。YANG 拡張 deviation や augment によるプラットフォーム別スキーマ差異も存在しない。

### 4. SFTP バイナリは OS パッケージ提供で固定

`/usr/lib/openssh/sftp-server` は `openssh-server` Debian パッケージが提供する。sshd_config テンプレートへの `Subsystem sftp` 行の組み込みもパッケージ標準であり、ベンダー/プラットフォーム固有のカスタマイズは community SONiC master に存在しない。

`sonic-buildimage/files/image_config/` に SSH 固有のプラットフォーム別オーバーレイは存在しない (`find files/image_config -iname "*ssh*"` 0 ヒット)。

### 5. PAM 経由の max_sessions 処理にも機種非依存

`PamLimitsCfg.update_config_file()` (`hostcfgd:1421-1479`) は `SSH_SERVER|POLICIES.max_sessions` を `/etc/security/limits.conf` に書き込むが、PAM limits はカーネル共通機能であり ASIC 依存なし。

## まとめ

SSH SFTP サブシステムは SAI を経由せず、ASIC SDK・platform plugin・multi-asic 分岐のいずれにも依存しない。`T0 / T1 / VOQ chassis / SmartSwitch` 等の物理構成を問わず挙動・適用範囲は同一。
