# PORTCHANNEL_MEMBER — Phase H: プラットフォーム差

## 調査対象ソース

- `sonic-net/sonic-swss`
  - `orchagent/portsorch.cpp` — `PortsOrch::doLagMemberTask()` (L6260–6395)、`voqSyncAddLagMember()` (L11179–11205)、`setCollectionOnLagMember()` / `setDistributionOnLagMember()` (L8296–8354)
  - `cfgmgr/teammgr.cpp` — `TeamMgr::doLagMemberTask()` / `addLagMember()` (L730–870)
- `sonic-net/sonic-buildimage`
  - `src/sonic-py-common/sonic_py_common/multi_asic.py` — `is_port_channel_internal()` / `get_back_end_interface_set()` (L401–447)

## 差異 1: VOQ Chassis — CHASSIS_APP_LAG_MEMBER_TABLE 経由処理

`portsorch.cpp:L6297-6315`

VOQ chassis 環境 (`gMySwitchType == "voq"` かつ `isChassisDbInUse()` が true) では、PortsOrch が `CHASSIS_APP_LAG_MEMBER_TABLE` を追加で購読する。

| 条件 | 挙動 |
|------|------|
| `gMySwitchType != "voq"` (通常) | CONFIG_DB → APP_DB `APP_LAG_MEMBER_TABLE` のみ処理 |
| `gMySwitchType == "voq"` (VOQ chassis) | `CHASSIS_APP_LAG_MEMBER_TABLE` も購読。ローカル LAG メンバ追加時に `voqSyncAddLagMember()` が `CHASSIS_APP_DB` にも書き込み |
| `switch_id == gVoqMySwitchId` (自 switch の LAG) | CHASSIS_APP_DB 由来の自 switch の LAG メンバ追加はスキップ（二重処理防止） |
| `port_switch_id != lag_switch_id` (switch_id ミスマッチ) | `SWSS_LOG_ERROR: "System lag switch id mismatch..."` → エントリ消去 |

- VOQ chassis 環境で LAG メンバを追加する際、`voqSyncAddLagMember()` が自 switch の LAG のみ `CHASSIS_APP_DB:CHASSIS_APP_LAG_MEMBER_TABLE` に `status` フィールド付きで同期する (`portsorch.cpp:L11179-11195`)。
- PORTCHANNEL_MEMBER の key-only 制約は CONFIG_DB 側のみ。APP_DB / CHASSIS_APP_DB の LAG_MEMBER_TABLE は `status` フィールドを持つ。

## 差異 2: Mellanox プラットフォーム — distribution-only モード非サポート

`portsorch.cpp:L6361-6382` のコメント明記

LAG メンバの `status` フィールド (`enabled` / `disabled`) は APP_DB `APP_LAG_MEMBER_TABLE` 経由で orchagent に渡され、`setCollectionOnLagMember()` / `setDistributionOnLagMember()` で `SAI_LAG_MEMBER_ATTR_INGRESS_DISABLE` / `SAI_LAG_MEMBER_ATTR_EGRESS_DISABLE` に変換される。

| プラットフォーム | enabled 時の順序 | disabled 時の順序 | 制約理由 |
|---|---|---|---|
| Mellanox | collection 有効化 → distribution 有効化 | distribution 無効化 → collection 無効化 | distribution-only モード（collection=false, distribution=true）が非サポート |
| Broadcom / その他 | 同上（同一コードパス） | 同上 | 制約なし（コメントは Mellanox 固有と明記）|

> **補足**: `status=enabled` で collection を先に有効化するのは、distribution-only 状態（EGRESS のみ有効）を経由しないようにするため。`status=disabled` で distribution を先に無効化するのも同様の理由。このシーケンスは Mellanox SAI の制限に由来し、orchagent のコードで共通パスとして実装されている。

## 差異 3: Multi-ASIC — バックエンド LAG の内部判定

`multi_asic.py:L401-447`

マルチ ASIC 環境では `is_port_channel_internal()` が PORTCHANNEL_MEMBER を参照して LAG の internal / external を判定する。

| 条件 | 挙動 |
|------|------|
| `is_multi_asic() == False` (シングル ASIC) | `is_port_channel_internal()` は常に `False` を返す |
| LAG のメンバポートが internal role | LAG 自体が internal (backend) LAG と判定 |
| LAG のメンバポートが external role | LAG は external (frontend) LAG |
| LAG にメンバなし | `False` を返す（メンバが空の場合は判定不能）|

- `get_back_end_interface_set()` が backend LAG 一覧を生成する際も PORTCHANNEL_MEMBER を走査し、メンバポートが internal role のものを backend LAG として分類する。
- backend LAG は show コマンドのフィルタリング・BGP / VLAN 設定の適用範囲制御などに使用される。
- **混在配置禁止**: 「backend と frontend のメンバを混在させた LAG は誤設定」とコメントで明記されている (`multi_asic.py:L439-441`)。

## 差異 4: VOQ Chassis — LAG エイリアス命名規則

`portsorch.cpp:L7960-7972`

| 環境 | LAG の system alias 形式 |
|------|--------------------------|
| 非 VOQ | `PortChannel0001`（設定名そのまま） |
| VOQ chassis (local LAG) | `<hostname>|<asic_name>|PortChannel0001` |
| VOQ chassis (remote LAG) | リモート switch の system alias 形式 |

VOQ chassis では system_lag_alias が `hostname|asic|lag` 形式となり、これが CHASSIS_APP_DB のキーとして使われる。CONFIG_DB 側の PORTCHANNEL_MEMBER key は従来通り `PORTCHANNEL_MEMBER|PortChannel0001|Ethernet0` であり変更なし。

## スキャン証跡

- `portsorch.cpp:L6260-6395` 全行読了（VOQ chassis 分岐・Mellanox collection/distribution コメント確認）
- `portsorch.cpp:L11179-11205` `voqSyncAddLagMember` / `voqSyncDelLagMember` 確認
- `portsorch.cpp:L8296-8354` `setCollectionOnLagMember` / `setDistributionOnLagMember` 確認
- `teammgr.cpp:L730-870` `addLagMember` / admin_status 処理確認（プラットフォーム固有分岐なし）
- `multi_asic.py:L401-447` `is_port_channel_internal` / `get_back_end_interface_set` 確認
- MCLAG / iccpd 関連コードは sonic-swss リポジトリ内に PORTCHANNEL_MEMBER 固有の分岐なし（MCLAG は iccpd が独立プロセスで CONFIG_DB を直接操作する設計）
- Broadcom 固有の LAG member 処理: collection/distribution の順序制約は Mellanox と同一コードパスを使用（Broadcom 向け特殊分岐なし）
