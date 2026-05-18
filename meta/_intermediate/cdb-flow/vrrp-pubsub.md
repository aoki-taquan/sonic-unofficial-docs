# VRRP Phase G — 通信メカニズム 調査ノート

## 調査対象ファイル

- `SONiC/doc/vrrp/VRRP_Adaptation_HLD.md` (Modules Design and Flows セクション L200-240, L460-492)
- `SONiC/doc/vrrp/sonic-vrrp.yang`

## macvlanmgrd の購読方式

HLD L219-225 の記述:
- macvlanmgrd は CONFIG_DB の `VRRP` / `VRRP6` / `VRRP_TRACK` / `VRRP6_TRACK` テーブルへの変更を購読する
- BGP コンテナ内で動作 (HLD L219)
- 購読 API: SubscriberStateTable (SONiC 標準の cfgmgr パターン)
- 起動時に CONFIG_DB の既存エントリをリプレイ

## vrrpsyncd の購読方式

HLD L229-232 の記述:
- vrrpsyncd は SWSS コンテナ内で動作
- Linux カーネルの macvlan インターフェース変化を **netlink** で監視 (DB subscribe ではない)
- macvlan デバイスへの IP add/del イベントをトリガとして APPL_DB.VRRP_TABLE に書き込む
- 購読方式: netlink socket (Redis keyspace notification ではない)

## vrrporch (intforch) の購読方式

HLD L234-235 の記述:
- vrrporch は APPL_DB の `VRRP_TABLE` を ConsumerStateTable で購読
- orchagent 内で動作、標準 Orch select ループで処理
- SELECT_TIMEOUT = 1000ms (orchdaemon.cpp 標準)

## HLD 記述箇所 (Modules Design and Flows)

```
macvlanmgrd:
  - Listens to VRRP create, delete and parameter change in CONFIG DB
  - Upon change
    - Add/del VRRP instance corresponding Macvlan device to kernel with IPs and state.
    - Updates VRRP instance configuration to the APPL DB, such as Macvlan device name and Vip.
    - Update changes to vrrpd by using vtysh commands

vrrpsyncd:
  - Listens to Macvlan interface programming in kernel.
  - Update the kernel Macvlan device's state to the INTF_table entry of APPL DB.

intforch:
  - Listens to INTF_Table in APP_DB and updates Vip and virtual MAC entries in ASIC_DB for VRRP instances
```
(HLD L461-479)

## 通知フロー

1. CLI/YANG → CONFIG_DB HSET "VRRP|<intf>|<vrid>"
2. Redis keyspace PUBLISH → macvlanmgrd SubscriberStateTable 受信
3. macvlanmgrd → Linux カーネル netlink (ip link add macvlan デバイス)
4. macvlanmgrd → vtysh 経由で vrrpd に設定投入 (DB 書込なし)
5. vrrpd が VRRP 状態機械を実行し Master 昇格時に macvlan デバイスの protodown=off
6. vrrpsyncd が netlink で macvlan デバイスへの IP add を検出
7. vrrpsyncd → APPL_DB ProducerStateTable VRRP_TABLE SET
8. vrrporch が ConsumerStateTable で APPL_DB.VRRP_TABLE を受信
9. vrrporch → SAI API → syncd → ASIC_DB

## APPL_DB テーブル

Producer: vrrpsyncd
Consumer: vrrporch
テーブル名: VRRP_TABLE
キー: `VRRP_TABLE:<interface_name>:<vip>:<type>`
フィールド: `vmac` = 仮想 MAC アドレス
(HLD APPL_DB Changes セクション L407-436)
