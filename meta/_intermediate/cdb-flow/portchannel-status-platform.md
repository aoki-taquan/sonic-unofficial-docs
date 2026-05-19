# Phase H: APPL_DB LAG_TABLE (portchannel-status) プラットフォーム差調査

## 調査日

2026-05-19

## 調査対象ファイル

- `sonic-swss/orchagent/portsorch.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/orch.h`
- `sonic-swss/teamsyncd/teamsync.cpp` (同上)
- `sonic-swss/cfgmgr/teammgr.cpp` (同上)

## 検出したプラットフォーム差

### 1. Mellanox — LAG_MEMBER の collection/distribution 操作順が異なる

**検出箇所**: `portsorch.cpp:6361-6382`

LAG メンバーの enabled/disabled 状態を切り替えるとき、orchagent は `SAI_LAG_MEMBER_ATTR_INGRESS_DISABLE` (collection) と `SAI_LAG_MEMBER_ATTR_EGRESS_DISABLE` (distribution) の 2 属性を SET する。

Mellanox SAI は「collection=false かつ distribution=true」の **distribution-only 中間状態**をサポートしないため、操作順がプラットフォーム依存になっている:

- **enabled → enabled 状態**: collection を先に `true` にしてから distribution を `true` にする (distribution-only 中間状態を経由しない)
- **enabled → disabled 状態**: distribution を先に `false` にしてから collection を `false` にする (同様に中間状態を回避)

```cpp
// portsorch.cpp:6361-6382
/* enable collection first, distribution-only mode
 * is not supported on Mellanox platform
 */
if (setCollectionOnLagMember(port, true) &&
    setDistributionOnLagMember(port, true)) { ... }

/* disable distribution first, distribution-only mode
 * is not supported on Mellanox platform
 */
if (setDistributionOnLagMember(port, false) &&
    setCollectionOnLagMember(port, false)) { ... }
```

**APPL_DB への影響**: `LAG_TABLE` 本体には影響しないが、LAG_MEMBER の status フィールドがこのプラットフォーム固有の操作順でSAIに反映される。collection/distribution の中間状態エラーで SAI が失敗した場合、orchagent は `it++` で再試行する (`portsorch.cpp:6370-6372, 6382-6384`)。

### 2. VoQ スイッチ — `create_lag()` に追加属性

**検出箇所**: `portsorch.cpp:7962-7991`

通常スイッチでは `sai_lag_api->create_lag()` を属性 0 個で呼び出すが、VoQ スイッチ (`gMySwitchType == "voq"`) では `SAI_LAG_ATTR_SYSTEM_PORT_AGGREGATE_ID` 属性を追加する。

```cpp
// portsorch.cpp:7962-7991
if (gMySwitchType == "voq")
{
    sai_attribute_t attr;
    attr.id = SAI_LAG_ATTR_SYSTEM_PORT_AGGREGATE_ID;
    attr.value.u32 = spa_id;
    lag_attrs.push_back(attr);
}
sai_lag_api->create_lag(&lag_id, gSwitchId, lag_attrs.size(), lag_attrs.data());
```

Multi-ASIC VoQ 構成では CHASSIS_APP_DB の `LagIdAllocator` (`m_lagIdAllocator`) でシャーシ全体でユニークな LAG ID を払い出し、LAG 名も `<hostname>|<asic>|PortChannelXXXX` 形式に変換する。通常スイッチと VoQ スイッチで `create_lag()` の属性セットが異なる。

**APPL_DB LAG_TABLE への波及**: VoQ モードでは `addLag()` が CHASSIS_APP_DB の `CHASSIS_APP_LAG_TABLE_NAME` にも書き込む (`voqSyncAddLag(lag)`, `portsorch.cpp:8039`)。

### 3. `SAI_LAG_ATTR_TPID` — ASIC 対応依存

**検出箇所**: `portsorch.cpp:8267-8291`

`setLagTpid()` は SAI capability チェックなしに `SAI_LAG_ATTR_TPID` を直接 SET する:

```cpp
attr.id = SAI_LAG_ATTR_TPID;
attr.value.u16 = (uint16_t)tpid;
status = sai_lag_api->set_lag_attribute(id, &attr);
```

`SAI_LAG_ATTR_TPID` に非対応の ASIC では `SAI_STATUS_NOT_SUPPORTED` が返り `SWSS_LOG_ERROR` が出力される。VS (Virtual Switch) SAI は `SAI_LAG_ATTR_TPID` の SET をサポートしないため、VS 環境での TPID 設定は常にエラーになる。

**APPL_DB への影響**: APPL_DB の `tpid` フィールドへの書き込み (teammgrd 側) はプラットフォームに依らず行われる。SAI でのエラーは orchagent 内でのみ発生し、APPL_DB のエントリは書き込まれたまま残る。

## プラットフォーム識別定数 (orch.h)

| 定数 | 値 | LAG 関連の影響 |
|------|----|---------------|
| `MLNX_PLATFORM_SUBSTRING` | `"mellanox"` | distribution-only モード非対応のコメント明記 (直接 if 分岐なし、操作順で対応) |
| `VS_PLATFORM_SUBSTRING` | `"vs"` | `SAI_LAG_ATTR_TPID` SET が NO-OP / エラー |

## プラットフォーム無依存部分

- **teamsyncd**: カーネル RTM_NEWLINK 駆動のため、プラットフォーム差なし。`admin_status` / `oper_status` / `mtu` の書き込みはすべての環境で同一
- **teammgrd**: CONFIG_DB → APPL_DB の転写はプラットフォーム差なし
- **STATE_DB LAG_TABLE**: `state: ok` 書き込みはプラットフォーム差なし

## 証跡

- `portsorch.cpp:6361-6382`: Mellanox distribution-only 非対応のコメントと collection/distribution 操作順
- `portsorch.cpp:7962-7991`: VoQ スイッチの `SAI_LAG_ATTR_SYSTEM_PORT_AGGREGATE_ID` 追加
- `portsorch.cpp:8267-8291`: `setLagTpid()` 実装 — capability チェックなし
- `portsorch.cpp:8039`: VoQ モードの `voqSyncAddLag()` 呼び出し (CHASSIS_APP_DB への書き込み)
