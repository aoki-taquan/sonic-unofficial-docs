# VRRP — Phase F 副次 DB 書込スキャンノート

調査日: 2026-05-18
対象テーブル: VRRP / VRRP6 / VRRP_TRACK / VRRP6_TRACK (CONFIG_DB)
ソース: sonic-net/SONiC doc/vrrp/VRRP_Adaptation_HLD.md

## 書込みチェーン概要

CONFIG_DB.VRRP / VRRP6 → macvlanmgrd が以下を実行:
1. Linux カーネルに macvlan デバイスを作成 (ip link add)
2. APPL_DB には macvlanmgrd が直接書き込まない（VIP/VMAC 情報の APPL_DB 書き込みは vrrpsyncd が担当）
3. vtysh 経由で FRR vrrpd に設定を投入

HLD L219-226, L461-466 より:
- macvlanmgrd: CONFIG_DB → Linux kernel macvlan device + vtysh (vrrpd 設定)
- vrrpsyncd: Linux kernel macvlan interface state → APPL_DB.VRRP_TABLE (Master 状態の VIP/VMAC エントリ)
- intforch (vrrporch): APPL_DB.VRRP_TABLE → ASIC_DB (仮想 RIF, VIP ネクストホップ)

## 詳細

### macvlanmgrd の副次書込

CONFIG_DB.VRRP SET 時:
- Linux カーネル: `ip link add Vrrp4-<intf>-<vrid> link <intf> addrgenmode random type macvlan mode bridge` を実行
- Linux カーネル: macvlan デバイスに仮想 MAC アドレスを設定 (`ip link set ... address 00:00:5e:00:01:<vrid>`)
- Linux カーネル: macvlan デバイスに VIP を付与 (`ip addr add <vip> dev Vrrp4-<intf>-<vrid>`)
- FRR: vtysh コマンドで vrrpd に VRRP インスタンス設定を投入

### vrrpsyncd の副次書込

Linux macvlan interface の IP 追加イベント (Master 状態での protodown off 後):
- APPL_DB.VRRP_TABLE SET: key = `VRRP_TABLE:<intf_name>|<vip>/32` (IPv4) または `<vip>/128` (IPv6), field = `vmac:<virtual_mac>`

Linux macvlan interface の IP 削除イベント:
- APPL_DB.VRRP_TABLE DEL: 対応エントリを削除

### intforch / vrrporch の副次書込

APPL_DB.VRRP_TABLE SET 時:
- ASIC_DB: `ASIC_STATE:SAI_OBJECT_TYPE_ROUTER_INTERFACE:<oid>` に仮想 RIF を作成 (SAI_ROUTER_INTERFACE_ATTR_IS_VIRTUAL=true)
- ASIC_DB: VIP ルートエントリ / ネクストホップエントリを追加

### STATE_DB への書込

HLD に STATE_DB への明示的な書込み記述なし。
VRRP 設定の状態は macvlan デバイスの protodown 状態と APPL_DB.VRRP_TABLE の有無で管理。

### VRRP_TRACK の副次書込

VRRP_TRACK への SET/DEL は CONFIG_DB から直接読まれる FRR vrrpd のメモリに反映されるだけで、
他 DB への書込は発生しない。priority の変化は VRRP Advertisement パケットのフィールド更新のみ。
