# VRRP_TRACK Phase G — 通信メカニズム 調査ノート

## 調査対象ファイル

- `SONiC/doc/vrrp/VRRP_Adaptation_HLD.md` (Container セクション L208-235, Modules Design and Flows L461-492)

## VRRP_TRACK の購読構造

`VRRP_TRACK` / `VRRP6_TRACK` テーブルへの書き込みは **macvlanmgrd が単独で購読する**。
`VRRP` テーブルとは異なり、VRRP_TRACK の変更は APPL_DB / ASIC_DB へは直接伝播しない。

### macvlanmgrd (BGP コンテナ)

HLD L219-225 より:

```
macvlanmgrd:
  - Listens to VRRP create, delete and parameter change in CONFIG DB
  - Upon change
    - Update VRRP instance configuration to vrrpd by using vtysh commands
```

- 購読 API: `SubscriberStateTable` (Redis keyspace notification パターン)
- 購読テーブル: `VRRP` / `VRRP6` / `VRRP_TRACK` / `VRRP6_TRACK` (全 4 テーブルを一括購読)
- VRRP_TRACK 変更受信時: vtysh 経由で FRR vrrpd に track 設定を投入。カーネル netlink や APPL_DB への書き込みは行わない

### vrrpd (FRR, BGP コンテナ)

HLD L489-493 (Uplink interface tracking) より:

```
vrrpd:
  - Match VRRP instance tracking interface and recalculate priority
```

- macvlanmgrd から vtysh 経由で VRRP_TRACK 設定を受け取りインメモリに保持
- zebra から netlink 経由でインタフェース Up/Down 通知を受信
- track インタフェース状態変化に応じて VRRP priority を再計算し Advertisement パケットを送信
- DB への書き込みは行わない

## 通知フロー（VRRP_TRACK 変更時）

```
CLI / YANG → CONFIG_DB HSET "VRRP_TRACK|<intf>|<vrid>|<track_intf>"
  ↓ Redis keyspace PUBLISH "__keyspace@4__:VRRP_TRACK|<intf>|<vrid>|<track_intf>" "hset"
macvlanmgrd SubscriberStateTable 受信 (BGP コンテナ)
  ↓ vtysh コマンドで FRR vrrpd に track 設定投入
vrrpd がインメモリの track 設定を更新 (DB 書き込みなし)
  ↓ zebra からの netlink インタフェース状態変化通知と組み合わせて priority 再計算
vrrpd が VRRP Advertisement パケット送信 (priority フィールド更新)
```

## vrrpsyncd / vrrporch との関係

VRRP_TRACK 変更は vrrpsyncd や vrrporch には**直接影響しない**。VRRP_TRACK 変更に起因する priority 再計算が VRRP 状態遷移（Master/Backup 切替）を引き起こした場合のみ、下流チェーンが間接的に動作する（`side-effects` セクション参照）。

## evidence

- `SONiC/doc/vrrp/VRRP_Adaptation_HLD.md` L219-225 (macvlanmgrd の役割)
- `SONiC/doc/vrrp/VRRP_Adaptation_HLD.md` L461-492 (Modules Design and Flows)
- `SONiC/doc/vrrp/VRRP_Adaptation_HLD.md` L268 (Consumer: macvlanmgrd)
