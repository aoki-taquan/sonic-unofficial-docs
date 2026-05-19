# vrrp-platform — 調査ノート

## 調査対象

`CONFIG_DB VRRP` / `VRRP6` テーブル処理のプラットフォーム差異 (Phase H)

## 主要な差異

### 1. `SAI_ROUTER_INTERFACE_ATTR_IS_VIRTUAL` — ベンダー SAI 対応差

VRRP 仮想 RIF を作成する際、`SAI_ROUTER_INTERFACE_ATTR_IS_VIRTUAL` 属性を使用する。
一部ベンダーの SAI 実装はこの属性をサポートしない。

根拠:
- VRRP_Adaptation_HLD.md L520: "Considering that some particular vendor SAI implementations may not support this attribute. Use sai_query_attribute_capability to judge if ASIC platform support SAI_ROUTER_INTERFACE_ATTR_IS_VIRTUAL attribute. if not support, the attribute will not added when createvirtual interface with sai interface."

挙動:
- 属性が未サポートの場合: `IS_VIRTUAL` 属性を付けずに通常 RIF として作成。ASIC リソース効率は落ちるが機能は維持される。
- 属性がサポートされる場合: 仮想 RIF を最適化して作成（neighbor エントリを持てない READ-ONLY RIF）。

### 2. COPP トラップ（VRRP/VRRPv6）— プラットフォーム共通

VRRP コントロールパケット受信は `SAI_HOSTIF_TRAP_TYPE_VRRP` / `SAI_HOSTIF_TRAP_TYPE_VRRPV6` トラップで処理される（copporch.cpp:73,78）。
これはベンダー共通の SAI ホストインターフェーストラップで、プラットフォーム固有分岐はない。

### 3. Multi-ASIC / VOQ / DPU — 非対応・未実装

VRRP_Adaptation_HLD.md には multi-asic / VOQ / DPU に関する記述がない。
VRRP は Linux macvlan デバイスと FRR vrrpd を介して動作するため、主要な処理が Linux ネットワークスタック上で行われる。
`macvlanmgrd` は BGP コンテナ内で動作し、namespace を跨ぐ multi-asic 処理には対応していない。

sonic-utilities のソースでも multi-asic 対応コード（`is_multi_npu()` 等）の VRRP CLI への適用は確認されない。

## 結論

- **ベンダー SAI 差**: `SAI_ROUTER_INTERFACE_ATTR_IS_VIRTUAL` の対応有無が仮想 RIF 作成方法に影響
- **Multi-ASIC / VOQ / DPU**: HLD で未定義。VRRP は Linux スタック上の機能であり、ASIC 種別・マルチ ASIC 構成への依存は最小
