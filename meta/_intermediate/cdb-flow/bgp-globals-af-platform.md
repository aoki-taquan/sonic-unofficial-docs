# BGP_GLOBALS_AF — プラットフォーム差調査

Task F Phase H: `BGP_GLOBALS_AF` テーブル適用時のプラットフォーム/構成差を `bgpcfgd/` (`sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/`) と `frrcfgd.py` (`sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`) から精読した結果。

## 結論

**プラットフォーム差なし**。`BGP_GLOBALS_AF` の適用経路は FRR (`bgpd`) を最終 sink とする制御プレーン経路であり、ASIC 種別・hwsku・multi-asic / VOQ chassis 構成・ベンダー固有モジュールに依存しない。

## 根拠

### 1. ハンドラを保持するのは `frrcfgd` 一本

`BGP_GLOBALS_AF` を購読するのは `frrcfgd.BGPConfigDaemon.bgp_af_handler` (L3918 付近) のみで、`sonic-bgpcfgd/bgpcfgd/` 配下の Python モジュールには `BGP_GLOBALS_AF` の購読・参照が存在しない (`grep -rn 'BGP_GLOBALS_AF' src/sonic-bgpcfgd/bgpcfgd/` が 0 ヒット)。`bgpcfgd` 系は j2 テンプレートベースの BGP セッション生成、`frrcfgd` 系は YANG / generic config 経由の FRR vtysh 反映、という分業のため、AF 単位の global 設定は完全に `frrcfgd` 側に閉じている。

### 2. `frrcfgd.py` 全体にプラットフォーム分岐なし

`frrcfgd.py` を `platform` / `hwsku` / `asic_type` のいずれの語でも grep しても 0 ヒット。`DEVICE_METADATA` 参照は `bgp_asn` と `docker_routing_config_mode` の 2 キーのみ (L2162-2168) で、`platform` / `hwsku` / `asic_type` / `sub_role` / `switch_type` 等の構成判別キーには触れていない。

### 3. `bgp_af_handler` の出力は FRR vtysh コマンド文字列

`bgp_af_handler` は CONFIG_DB の `<vrf>|<af>` キーを受け取り、`address-family <afi> <safi>` 配下の `maximum-paths` / `distance bgp` / `bgp dampening` / `import vrf` / `autort` / `advertise-all-vni` / `advertise-svi-ip` 等を vtysh に発行する。出力先は常に同一プロセス内 (`bgpd` コンテナ) の FRR であり、SAI / ASIC SDK / platform driver には到達しない。よってハードウェア能力差 (TCAM 容量、ECMP 上限、L3VNI ハードウェア対応等) は本テーブル適用挙動には現れない。

### 4. multi-asic / VOQ chassis 構成での扱い

multi-asic / VOQ chassis では `bgpd` が `asicN` namespace ごとに分離されているが、各 namespace の `frrcfgd` は同一コードで動作し、自身の CONFIG_DB の `BGP_GLOBALS_AF` を独立に処理する。`frrcfgd.py` 自身は multi-asic を意識する分岐を持たず、`ConfigDBConnector` の namespace は外部 (docker / supervisord) から渡される。コードパスは namespace 数に関わらず単一実装。

### 5. ECMP 上限の表現上の注意

`max_ebgp_paths` / `max_ibgp_paths` は uint16 1..256 を YANG が許容する。実際に SAI / ASIC に降りるのは BGP 経路選択後の FIB であり、ASIC が ECMP group 当たり 64 / 128 / 256 何 path まで保持できるかは別経路 (`SWITCH` / `BUFFER_*` / ASIC capability) の問題。`BGP_GLOBALS_AF` の値自体は制御プレーン上の multipath 計算上限であり、ハードウェア能力との突き合わせは本テーブル外。

### 6. ベンダー固有モジュールの注入なし

community master の `frrcfgd` / `bgp_af_handler` にはベンダー固有 hook ポイントが存在しない。ベンダー版 SONiC は本リポジトリのスコープ外。

## まとめ

`BGP_GLOBALS_AF` は FRR vtysh を最終 sink とする純制御プレーンテーブル。`frrcfgd.bgp_af_handler` には `platform` / `hwsku` / `asic_type` / `switch_type` のいずれを参照する分岐もなく、multi-asic / VOQ chassis 構成でも namespace 単位で同一コードが走る。よって T0 / T1 / VOQ chassis / multi-asic 等の物理構成や ASIC ベンダーに関わらず適用挙動は同一。
