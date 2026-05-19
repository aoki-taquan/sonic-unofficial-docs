# VRRP_TRACK — Phase F 副次 DB 書込スキャンノート

調査日: 2026-05-19
対象テーブル: VRRP_TRACK / VRRP6_TRACK (CONFIG_DB)
ソース: sonic-net/SONiC doc/vrrp/VRRP_Adaptation_HLD.md; sonic-utilities/config/main.py

## 結論

VRRP_TRACK / VRRP6_TRACK への SET / DEL は **他の DB（APPL_DB / STATE_DB / ASIC_DB）へ直接書き込まない**。
変更は CONFIG_DB から直接読み込む FRR `vrrpd` のインメモリ track 設定に反映されるのみ。

## 書込みチェーン（間接波及）

VRRP_TRACK.priority_increment 変化
  → FRR vrrpd が priority を再計算
  → VRRP Advertisement パケットの priority フィールドが更新される（DB 書き込みなし）
  → priority 変化によって VRRP 状態遷移（Master↔Backup）が発生する場合:
      ↓ （vrrpsyncd 経由・VRRP_TRACK の直接結果ではない）
      APPL_DB.VRRP_TABLE SET/DEL （Master 状態のインタフェースのみ）
      ↓ （vrrporch 経由）
      ASIC_DB: 仮想 RIF / VIP ルートエントリ追加・削除

## SET 時の副次書込

なし。CONFIG_DB.VRRP_TRACK は FRR vrrpd が直接読む（SubscriberStateTable または起動時読み込み）。
DB 外側のカーネル / FRR 内部状態が変化するが、DB への副次書き込みは発生しない。

## DEL 時の副次書込

なし。同上。priority 再計算のみ。

## 波及チェーン詳細

HLD L228-232, L481-492 より:
- macvlanmgrd: CONFIG_DB.VRRP を購読。MACVLAN デバイス作成と vtysh 投入を担当（VRRP_TRACK は対象外）
- vrrpsyncd: Linux macvlan インタフェースの IP 変化 → APPL_DB.VRRP_TABLE SET/DEL（VRRP インスタンスの Master 状態が変わった場合のみ）
- VRRP_TRACK は FRR vrrpd の priority 計算パラメータとしてのみ機能する

## 注記

`vrrp-side-effects.md`（VRRP テーブル側）に詳細なチェーン説明がある。
VRRP_TRACK はそのチェーンに間接的に寄与するが、自身では DB 書き込みを発生させない。
