# SSH_SERVER base — プラットフォーム差調査

Task F Phase H: `SSH_SERVER|POLICIES` テーブルを処理する `SshServer` クラスおよび `PamLimitsCfg` クラス (`sonic-host-services/scripts/hostcfgd`) と YANG モジュール (`sonic-ssh-server.yang`) を対象に、プラットフォーム・構成依存差を精読した結果。

## 結論

**プラットフォーム差なし**。`SSH_SERVER|POLICIES` の処理は、ASIC 種別・multi-asic / chassis 構成・ベンダー固有差分に一切依存しない。

## 根拠

### 1. SshServer / PamLimitsCfg クラスにプラットフォーム条件分岐なし

`class SshServer` (`hostcfgd:1045-1161`) および `class PamLimitsCfg` (`hostcfgd:1418-1490`) を `platform|multi_asic|is_multi_npu|chassis|asic[0-9]|namespace|vendor` で grep すると **0 ヒット**。

- `set_policies()` は `SSH_CONFIG_NAMES` 辞書に基づき固定パス `/etc/ssh/sshd_config` を書き換えるのみ
- `update_config_file()` は固定パス `/etc/security/limits.conf` / `/etc/pam.d/pam-limits-conf` を書き換えるのみ
- いずれの経路にも ASIC 種別・プラットフォーム識別子・SAI API 呼び出しは存在しない

### 2. hostcfgd は host 単一インスタンス

`hostcfgd` main クラス (行 2166-2167) は `ConfigDBConnector()` を引数なしで生成し **host namespace の CONFIG_DB のみ**に接続。`self.is_multi_npu = device_info.is_multi_npu()` (行 2182) は取得されるが、`SshServer` / `PamLimitsCfg` 経路では参照されず SSH 処理に影響しない。

multi-asic / VOQ chassis でも:

- `SSH_SERVER` テーブルは host CONFIG_DB のみに存在し、`asicN` namespace の CONFIG_DB には存在しない
- `hostcfgd` は host namespace で 1 インスタンスのみ起動し、`/etc/ssh/sshd_config` を host root filesystem 上で 1 か所更新する

### 3. YANG モデルにプラットフォーム分岐なし

`sonic-buildimage/src/sonic-yang-models/yang-models/sonic-ssh-server.yang` を `platform|asic|chassis|namespace|vendor|multi` で grep すると **namespace 宣言の `http://github.com/sonic-net/sonic-ssh-server` のみ**にヒット (機種分岐 0 件)。YANG deviation / augment によるプラットフォーム別スキーマ差異も存在しない。

### 4. sshd は OS パッケージ提供で固定

sshd は `openssh-server` Debian パッケージが提供する標準バイナリ。`sonic-buildimage/files/image_config/` に SSH 固有のプラットフォーム別オーバーレイは存在しない (`find files/image_config -iname "*ssh*"` 0 ヒット)。community SONiC master 全機種で同一バイナリ・同一設定パスが使用される。

### 5. PAM 経由の max_sessions 処理にも機種非依存

`PamLimitsCfg.update_config_file()` は `SSH_SERVER|POLICIES.max_sessions` を `/etc/security/limits.conf` に書き込むが、PAM limits はカーネル共通機能であり ASIC 依存なし。SmartSwitch DPU 上でも hostcfgd は別インスタンスとして起動するが、`SSH_SERVER` テーブルが存在する場合は同一コードパスで処理される。

## まとめ

SSH base 設定 (`SSH_SERVER|POLICIES`) は SAI を経由せず、ASIC SDK・platform plugin・multi-asic 分岐のいずれにも依存しない。`T0 / T1 / VOQ chassis / SmartSwitch` 等の物理構成を問わず挙動・適用範囲は同一。
