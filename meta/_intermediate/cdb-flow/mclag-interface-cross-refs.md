# MCLAG_INTERFACE 暗黙参照マップ調査 (Phase C)

調査日: 2026-05-19  
調査対象: CONFIG_DB `MCLAG_INTERFACE` テーブルの暗黙参照関係

## 調査ソース

- `sonic-swss/orchagent/mlagorch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/fdborch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/mlagorch.h` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/mclagsyncd/mclaglink.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss-common/common/schema.h` (ref: 158de8d3463ff4b841653f6d57190bb142b80d9c)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-mclag.yang` (ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)
- `sonic-utilities/config/mclag.py` (ref: a3e5b4c9fb7a95e213d08f8761e6c94f02a18b41)

## MCLAG_INTERFACE → 参照先テーブル

| 参照先テーブル / DB | 参照箇所 | 参照種別 | 補足 |
|---|---|---|---|
| `PORTCHANNEL` (CONFIG_DB) | `sonic-mclag.yang:115-116` | YANG leafref 必須 | `if_name` フィールドが `/sonic-portchannel/PORTCHANNEL/PORTCHANNEL_LIST/name` へ leafref。PortChannel が未存在の場合 YANG バリデーション拒否 |
| `MCLAG_DOMAIN` (CONFIG_DB) | `sonic-mclag.yang:108-109` | YANG leafref 必須 | `domain_id` フィールドが `MCLAG_DOMAIN_LIST/domain_id` へ leafref。MCLAG_DOMAIN エントリ未存在時に YANG バリデーション拒否 |
| `PortsOrch` (orchagent 内部) | `mlagorch.cpp:49-52` | 間接依存 | `gPortsOrch->allPortsReady()` 完了前は `doTask()` が即 return。PortsOrch 完了後に初めてエントリ処理開始 |

## MCLAG_INTERFACE ← 参照元（他テーブル/モジュールから参照される）

| 参照元 | 参照方法 | 用途 | evidence |
|---|---|---|---|
| `FdbOrch` (orchagent) | `gMlagOrch->isMlagInterface(port.m_alias)` | MCLAG メンバーポートが oper-down になっても FDB フラッシュをスキップ | `fdborch.cpp:1209-1212` |
| `FdbOrch` (orchagent) | `gMlagOrch->isMlagInterface(port.m_alias)` | MCLAG 広告 FDB 削除時にポート down 状態確認。ローカル MAC 削除の `origin` を `FDB_ORIGIN_LEARN` に書き換え | `fdborch.cpp:1665-1670` |
| `mclagsyncd` | `addDomainCfgDependentSelectables()` で `SubscriberStateTable` 追加 | MCLAG_DOMAIN 初回 SET 後に MCLAG_INTERFACE 変更イベントを購読し、iccpd へメンバー名を IPC 送信 | `mclaglink.cpp:918,938-941` |
| `config mclag member add/del` (CLI) | `config/mclag.py:283-293` | CLI が MCLAG_DOMAIN 存在を事前チェックしてから MCLAG_INTERFACE を SET。`if_type="PortChannel"` を固定書込み | `config/mclag.py:283-293` |

## STATE_DB / APPL_DB への副次書込み（MCLAG_INTERFACE 起因）

mclagsyncd が MCLAG_INTERFACE の SET/DEL を iccpd に通知した後、iccpd → mclagsyncd IPC を経由して以下の STATE_DB / APPL_DB が書き換わる。

| 書込み先テーブル | DB | キー | フィールド | evidence |
|---|---|---|---|---|
| `MCLAG_LOCAL_INTF_TABLE` | STATE_DB | `<if_name>` | `port_isolate_peer_link` (true/false) | `mclaglink.cpp:1512-1533` |
| `MCLAG_REMOTE_INTF_TABLE` | STATE_DB | `<domain_id>\|<if_name>` | `oper_status` 等 | `mclaglink.cpp:1538-1633` |
| `ISOLATION_GROUP_TABLE` | APPL_DB | `MCLAG_ISO_GRP` | `TYPE`, `PORTS`, `MEMBERS`, `DESCRIPTION` | `mclaglink.cpp:239,277,1811` |

> **注意**: これらの STATE_DB / APPL_DB 書込みは MCLAG_DOMAIN の ICCP セッション状態に依存するため、MCLAG_INTERFACE SET 後に即座に反映されるとは限らない。iccpd の ICCP ネゴシエーション完了後に反映される。

## MlagOrch 内部状態との整合

`MlagOrch` は `m_mlagIntfs` (std::set) でメンバー PortChannel 名を保持する。
`addMlagInterface()` / `delMlagInterface()` で更新し、`SUBJECT_TYPE_MLAG_INTF_CHANGE` を observer に broadcast。
`FdbOrch` は `Observer` インターフェース経由でこの通知を受信するのではなく、`gMlagOrch->isMlagInterface()` を直接ポーリング呼び出しで確認する（`fdborch.cpp:1209, 1666`）。

## 結論（Phase C 範囲）

1. MCLAG_INTERFACE は YANG の leafref 制約で `PORTCHANNEL` と `MCLAG_DOMAIN` への参照が必須。
2. FdbOrch が MCLAG メンバーポート一覧を `isMlagInterface()` 経由で暗黙的に参照し、FDB フラッシュ制御に使用する。
3. mclagsyncd が MCLAG_INTERFACE を iccpd に転送した後、STATE_DB の `MCLAG_LOCAL_INTF_TABLE` / `MCLAG_REMOTE_INTF_TABLE` と APPL_DB の `ISOLATION_GROUP_TABLE` が副次的に書き換わる（Phase F 相当だが、Phase C で参照関係として記録）。
