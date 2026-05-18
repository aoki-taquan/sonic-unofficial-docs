# LLDP — Phase G 通信メカニズム調査ノート

対象テーブル: `LLDP|GLOBAL`, `LLDP_PORT|<ifname>`
Consumer: `lldpmgrd` (`sonic-buildimage/dockers/docker-lldp/lldpmgrd`)
スキャン範囲: lldpmgrd 全行精読（2026-05-18）

---

## 購読テーブル一覧

lldpmgrd:298-311 の Select() 登録:

1. `APPL_DB APP_PORT_TABLE` → SubscriberStateTable
   - PortInitDone / PortConfigDone + oper_status イベントを購読
2. `CONFIG_DB CFG_MGMT_INTERFACE_TABLE_NAME` → SubscriberStateTable
   - 管理 IP 変化を購読
3. `CONFIG_DB CFG_DEVICE_METADATA_TABLE_NAME` → SubscriberStateTable
   - hostname / chassis_hostname 変化を購読

**LLDP / LLDP_PORT テーブルは登録されていない。**

## LLDP / LLDP_PORT が購読されない設計理由

lldpmgrd のコメント（lldpmgrd:1-14）:
> TODO: Also listen for changes in DEVICE_NEIGHBOR and PORT tables in
>       Config DB and update LLDP config upon changes.

LLDP|GLOBAL / LLDP_PORT の購読は TODO のまま実装されていない。

## lldp-syncd の追加購読

`lldp-syncd` (`python3 -m lldp_syncd`) は lldpd Unix ソケットをポーリングし、
ネイバー情報を `APPL_DB LLDP_ENTRY_TABLE|<ifname>` に書き込む。
これは LLDP_PORT の書き込みイベントとは独立した別経路。

## swsscommon.Select の動作

SELECT_TIMEOUT_MS = 10000 ms（10秒）
→ イベントなし時は 10 秒ごとに process_pending_cmds() を実行

## 結論

- LLDP|GLOBAL / LLDP_PORT は dead field（購読なし）
- lldpmgrd は PORT oper_status→lldpcli の変換のみ
- Redis pub/sub メカニズムは swsscommon.SubscriberStateTable のみ使用
