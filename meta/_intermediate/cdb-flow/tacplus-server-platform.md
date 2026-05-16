# TACPLUS_SERVER — プラットフォーム差調査 (Phase H)

Task F Phase H: `TACPLUS_SERVER` / `TACPLUS` テーブル適用時のプラットフォーム/構成差を `hostcfgd` (`sonic-host-services`) と `sonic-buildimage` の関連アセットから精読した結果。

## 結論

**ASIC 種別・ARM/x86 差・SmartSwitch 固有コードはなし**。ただし以下の注記事項あり:

1. **multi-asic**: TACACS+ 設定は host CONFIG_DB のみ。asicN namespace には TACPLUS_SERVER が存在しない。
2. **SmartSwitch (DPU)**: 特別処理なし。各 DPU が host として独立に hostcfgd を動作させる。
3. **ARM/x86**: アーキテクチャ固有の PAM モジュール分岐なし。
4. **管理 VRF (mgmt)**: `pam_tacplus.so` に `vrf=mgmt` パラメータとして渡すことで VRF binding を実現。VRF 有効/無効は `MGMT_VRF_CONFIG` テーブルで管理されるが、TACACS+ handler はそれを直接参照せず、`TACPLUS_SERVER.vrf` / `TACPLUS|global.src_ip` のフィールドをテンプレートに展開するのみ。

## 根拠

### 1. hostcfgd は host CONFIG_DB のみを購読

`scripts/hostcfgd` の `AaaCfg.__init__` (L354–398) は `ConfigDBConnector` を host namespace で 1 個生成するのみ。
`asic0..N` namespace への接続・iteration はない。`is_multi_npu()` を `main()` (L2182) で取得しているが、`AaaCfg` には渡されず TACACS+ 経路では参照されない。

### 2. multi-asic / VOQ chassis での挙動

multi-asic (pizza box) および VOQ chassis line card では:
- TACPLUS_SERVER は host CONFIG_DB (`namespace=""`) にのみ存在する。asicN CONFIG_DB には配置されない。
- 各 host (line card / supervisor) が独立に `hostcfgd` を起動し、それぞれの `/etc/pam.d/common-auth-sonic` と `/etc/tacplus_nss.conf` を生成する。
- chassis 全体に同一設定を配布する集中機構はない。オペレータが各 line card 宛に同じ `config tacacs add ...` を実行する運用前提。

### 3. SmartSwitch (DPU) での挙動

sonic-host-services の hostcfgd は SmartSwitch subtype を参照しない。DPU は独立した SONiC インスタンスを持ち、NPU 側 supervisor の TACACS+ 設定と DPU 側の TACACS+ 設定は連動しない。DPU 向け hostcfgd も同じ `AaaCfg` コードパスで動作する。`DEVICE_METADATA.localhost.subtype` の値は `AaaCfg` の処理で参照されない（`PamLimitCfg` の `type` / `hwsku` 参照とは別処理）。

### 4. ARM / x86 差なし

テンプレート (`common-auth-sonic.j2`, `tacplus_nss.conf.j2`) に `platform|asic|arch|vendor` の条件分岐なし。`pam_tacplus.so` / `libnss_tacplus.so` は community SONiC の Debian パッケージとしてアーキテクチャ共通で提供される。

### 5. PAM 設定とアーキテクチャ

`common-auth-sonic.j2` の条件分岐は `auth['login']` 文字列 (`local`, `tacacs+`, `radius`, `ldap` の組み合わせ) および `failthrough` / `debug` / `trace` ブール値のみ。物理ハードウェア・ASICベンダー・CPU アーキテクチャには依存しない。

### 6. 管理 VRF binding の仕組み

`TACPLUS_SERVER.vrf` フィールドに `mgmt` を設定すると、`common-auth-sonic.j2` の `{% if server.vrf %} vrf={{ server.vrf }} {% endif %}` により PAM 行に `vrf=mgmt` が挿入される。`pam_tacplus` モジュールが Linux の mgmt VRF (`ip vrf exec mgmt`) を使って TACACS+ サーバに接続する。
管理 VRF 自体の有効/無効は `MGMT_VRF_CONFIG.mgmtVrfEnabled` で制御されるが、`AaaCfg` はこの値を読まず、`vrf` フィールドをそのままテンプレートに渡す。管理 VRF が無効な状態で `vrf=mgmt` を設定すると、`pam_tacplus` は mgmt VRF ルーティングテーブルを参照しアクセス不能となり認証失敗する。

### 7. minigraph 由来の TACPLUS_SERVER

`minigraph.py` (L2668) は MetadataDeclaration から `tacacs_servers` IP リストを読み取り、
`TACPLUS_SERVER = { ip: {'priority': '1', 'tcp_port': '49'} }` として CONFIG_DB に投入する。chassis 構成では `parse_chassis_meta()` が同様に TACACS サーバ一覧を生成する。プラットフォーム型 (`type`) による TACACS_SERVER 生成の分岐はない。

## まとめ

TACPLUS_SERVER / TACPLUS テーブルの hostcfgd 処理は host-only な「Linux PAM / NSS 設定ファイル再生成」。ASIC 種別・multi-asic / chassis 構成・SmartSwitch / DPU・CPU アーキテクチャ (ARM/x86) に関わらず動作・適用範囲は同一。唯一注意すべき点は `vrf=mgmt` 設定と `MGMT_VRF_CONFIG.mgmtVrfEnabled` の整合性であり、VRF 未有効化状態での `vrf=mgmt` 指定は silent な認証失敗を引き起こす。

## スキャン証跡

- `sonic-host-services/scripts/hostcfgd`: `AaaCfg.__init__` L354–398, `modify_conf_file()` L640–816
- `sonic-host-services/data/templates/common-auth-sonic.j2`: 条件分岐は `auth['login']` 文字列のみ
- `sonic-host-services/data/templates/tacplus_nss.conf.j2`: `platform|asic|arch` 分岐なし
- `sonic-buildimage/src/sonic-config-engine/minigraph.py`: L2668, `parse_chassis_meta()` L1435-1471
