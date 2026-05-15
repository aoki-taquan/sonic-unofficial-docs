# AAA — プラットフォーム差調査

Task F Phase H: `AAA` テーブル適用時のプラットフォーム/構成差を `hostcfgd` (`sonic-host-services`) と `sonic-buildimage` の AAA 関連アセットから精読した結果。

## 結論

**プラットフォーム差なし**。AAA は host 単位で適用され、ASIC 種別・multi-asic / chassis 構成・ベンダー固有 PAM モジュールに依存しない。

## 根拠

### 1. hostcfgd は host CONFIG_DB のみを購読する

`scripts/hostcfgd` の main クラスで:

- 行 2166–2167: `self.config_db = ConfigDBConnector()` を引数なしで生成 → host namespace の CONFIG_DB に接続
- 行 2185: `self.aaacfg = AaaCfg(self.config_db)` で host CONFIG_DB を渡す
- 行 2182: `self.is_multi_npu = device_info.is_multi_npu()` を取得しているが、**`AaaCfg` には渡されず、AAA 経路では参照されない**

`AaaCfg.__init__` (354–398) は `CfgDb` 1 個を保持するだけで、`asic0..N` namespace への接続や iteration を一切しない。

### 2. AaaCfg は host 上のグローバルファイルだけを書き換える

`AaaCfg.modify_conf_file()` (`hostcfgd:641–`) が更新するのはすべて host root filesystem のグローバル設定:

- `/etc/pam.d/common-auth-sonic` (テンプレ `common-auth-sonic.j2`)
- `/etc/pam.d/sshd`, `/etc/pam.d/login` 系
- `/etc/nsswitch.conf` および `/etc/tacplus_nss.conf` (テンプレ `tacplus_nss.conf.j2`)
- `nslcd` (LDAP) 設定

これらはコンテナごと・ASIC ごとではなく **host 1 か所**。multi-asic chassis でも line card host の `hostcfgd` が同じファイルを書く。

### 3. テンプレートにプラットフォーム分岐なし

`data/templates/common-auth-sonic.j2` および `data/templates/tacplus_nss.conf.j2` を `platform|asic|chassis|namespace|vendor` で grep しても 0 ヒット。条件分岐は `AAA.authentication.login` 文字列・`failthrough` / `debug` / `trace` ブール・サーバリストのみ。

### 4. image_config / build_templates に AAA 固有のプラットフォーム上書きなし

`sonic-buildimage/files/image_config/` に `aaa` / `pam` / `tacacs` / `radius` / `ldap` / `nss` ディレクトリは存在しない（`ls files/image_config | grep -iE 'aaa|tacacs|radius|ldap|pam|nss'` が 0 ヒット）。プラットフォーム別 PAM モジュールの差し替え機構はビルド時にも実行時にもない。

`files/build_templates/tacacs-config.service` / `tacacs-config.timer` も `platform|asic|chassis|namespace|vendor` 0 ヒット。

### 5. multi-asic / VOQ chassis 構成での扱い

`is_multi_npu()` が true でも AAA テーブルは host CONFIG_DB のみに置かれ、`asicN` namespace の CONFIG_DB には AAA / TACPLUS_SERVER / RADIUS / LDAP_SERVER が存在しない（YANG モジュール `sonic-system-aaa` も host scope）。VOQ chassis の line card / supervisor 双方で各 host が独立に同じ AAA 設定を持ち、`hostcfgd` が各 host で PAM を再生成する。chassis 全体での集中適用機構はない（オペレータが各 line card に同一設定を流す運用が前提）。

### 6. ベンダー固有 PAM モジュールの注入なし

`pam_tacplus.so` / `pam_radius_auth.so` / `pam_ldap.so` / `pam_unix.so` は Debian / community SONiC の標準パッケージ。ベンダー版 SONiC （NVIDIA / Edgecore / Cisco / AsterNOS 等）は本リポジトリのスコープ外であり、community master にはベンダー固有 PAM の hook ポイントが存在しない。

## まとめ

AAA 経路は SAI を経由せず、ASIC SDK にも依存しない host-only な「Linux PAM / NSS 設定ファイル再生成」処理。よって `T0 / T1 / VOQ chassis / multi-asic` 等の物理構成や ASIC ベンダーに関わらず動作・適用範囲は同一。
