# VRRP_TRACK — Phase F 副次 DB 書込スキャンノート

調査日: 2026-05-19
対象テーブル: VRRP_TRACK / VRRP6_TRACK (CONFIG_DB)
ソース: sonic-net/SONiC doc/vrrp/VRRP_Adaptation_HLD.md, sonic-net/sonic-utilities config/main.py

## 結論

VRRP_TRACK / VRRP6_TRACK テーブルへの SET/DEL は CONFIG_DB 以外の DB への副次書込を発生させない。

## 根拠

HLD L481-492 (Uplink interface tracking セクション):
- zebra がカーネルの netlink イベントでインタフェース Up/Down を検出
- FRR vrrpd が CONFIG_DB.VRRP_TRACK を直接読み込み、メモリ内で追跡設定を保持
- zebra からのインタフェース状態変化通知を受け priority を再計算
- priority の変化は VRRP Advertisement パケットの priority フィールドに反映されるのみ
- CONFIG_DB, APPL_DB, STATE_DB, ASIC_DB, COUNTERS_DB, FLEX_COUNTER_DB への書込は一切発生しない

## 親テーブルとの対比

VRRP / VRRP6 テーブルへの SET は以下の副次書込を起点とする（vrrp-side-effects.md 参照）:
1. macvlanmgrd → Linux カーネル macvlan デバイス操作 + vtysh 経由 FRR vrrpd 設定
2. vrrpsyncd → APPL_DB.VRRP_TABLE (Master 昇格/降格)
3. vrrporch (intforch) → ASIC_DB.SAI_OBJECT_TYPE_ROUTER_INTERFACE (仮想 RIF)

VRRP_TRACK はこのチェーンのいずれにも参加しない。FRR vrrpd が CONFIG_DB から直接購読する唯一のテーブルであり、orchagent / swss 側には伝搬しない。

## STATE_DB

STATE_DB への VRRP_TRACK 関連エントリは存在しない。VRRP インスタンスの Master/Backup 状態は
APPL_DB.VRRP_TABLE の有無と macvlan デバイスの protodown 状態で管理されており、VRRP_TRACK に
よる priority 変化は間接的にフェイルオーバーを引き起こすが、STATE_DB 書込はない。
