# PORTCHANNEL テーブル — プラットフォーム差 (Phase H)

調査日: 2026-05-15
調査対象:
- sonic-swss/orchagent/portsorch.cpp
- sonic-swss/orchagent/orch.h (PLATFORM_SUBSTRING 定数群)
- sonic-swss/cfgmgr/teammgr.cpp
- sonic-sairedis/vslib/SwitchStateBase.cpp

---

## 検出したプラットフォーム差

### 1. Mellanox — distribution-only モード非対応

**検出箇所**: `portsorch.cpp:6361-6382`

```cpp
/* enable collection first, distribution-only mode
 * is not supported on Mellanox platform
 */
if (setCollectionOnLagMember(port, true) &&
    setDistributionOnLagMember(port, true))
{ ... }

/* disable distribution first, distribution-only mode
 * is not supported on Mellanox platform
 */
if (setDistributionOnLagMember(port, false) &&
    setCollectionOnLagMember(port, false))
{ ... }
```

- **LAG メンバを enabled/disabled に切り替える際の操作順がプラットフォーム依存**
- Mellanox は `distribution-only mode`（ingress collection=false、egress distribution=true の中間状態）を SAI レベルでサポートしない
- そのため：
  - **enable 時**: collection を先に有効化 → distribution を有効化（中間状態を回避）
  - **disable 時**: distribution を先に無効化 → collection を無効化（中間状態を回避）
- 非 Mellanox ASIC ではこの順序制約は存在しないが、コードは全プラットフォームで同じ実装を使用する（安全側）

### 2. VoQ (Virtual on Queue) スイッチ — SAI_LAG_ATTR_SYSTEM_PORT_AGGREGATE_ID 追加属性

**検出箇所**: `portsorch.cpp:7962-7991`

```cpp
if (gMySwitchType == "voq")
{
    if (switch_id < 0)
    {
        // Local PortChannel. Allocate unique lag id from central CHASSIS_APP_DB
        switch_id = gVoqMySwitchId;
        system_lag_alias = gMyHostName + "|" + gMyAsicName + "|" + lag_alias;

        if (gMultiAsicVoq)
        {
            // Allocate unique lag id
            spa_id = m_lagIdAllocator->lagIdAdd(system_lag_alias, 0);
        }
    }

    sai_attribute_t attr;
    attr.id = SAI_LAG_ATTR_SYSTEM_PORT_AGGREGATE_ID;
    attr.value.u32 = spa_id;
    lag_attrs.push_back(attr);
}
```

- VoQ スイッチ (`gMySwitchType == "voq"`) では `create_lag()` に `SAI_LAG_ATTR_SYSTEM_PORT_AGGREGATE_ID` を追加で渡す
- 通常スイッチでは `create_lag()` に属性を渡さない（0 属性で呼び出し）
- VoQ の multi-ASIC 構成 (`gMultiAsicVoq`) では CHASSIS_APP_DB の `LagIdAllocator` でシャーシ全体でユニークな LAG ID を払い出す
- LAG 名も `<hostname>|<asic>|PortChannelXXXX` 形式に変換されシャーシ全体で識別可能になる

### 3. SAI_LAG_ATTR_TPID — HW 対応依存

**検出箇所**: `portsorch.cpp:8267-8293`, `teammgr.cpp:538-547`

```cpp
bool PortsOrch::setLagTpid(sai_object_id_t id, sai_uint16_t tpid)
{
    attr.id = SAI_LAG_ATTR_TPID;
    attr.value.u16 = (uint16_t)tpid;

    status = sai_lag_api->set_lag_attribute(id, &attr);
    if (status != SAI_STATUS_SUCCESS)
    {
        SWSS_LOG_ERROR("Failed to set TPID 0x%x to LAG pid:%" PRIx64 ", rv:%d",
                attr.value.u16, id, status);
    }
}
```

- `SAI_LAG_ATTR_TPID` 属性の SET に capability チェックを行わず直接実行する
- HW が Q-in-Q (0x9100/0x9200/0x88a8) の TPID をサポートしない ASIC では `SAI_STATUS_NOT_SUPPORTED` / `SAI_STATUS_NOT_IMPLEMENTED` が返り SWSS_LOG_ERROR が出力される
- VS (Virtual Switch) SAI は `SAI_LAG_ATTR_TPID` の SET を支援しないため VS 環境でのテストでは TPID 設定は常にエラーまたは NO-OP
- 802.1Q (0x8100) のみ対応 ASIC では YANG `tpid_type` に含まれる非 0x8100 値を設定しても SAI エラーになる

### 4. Nvidia/Mellanox — isMlnxPlatform() による trim 統計処理

**検出箇所**: `portsorch.cpp:858-863`, `orch.h:42`

```cpp
if (isMlnxPlatform() && \
    isPortStatSupported(SAI_PORT_STAT_TRIM_PACKETS) && \
    isPortStatSupported(SAI_PORT_STAT_TX_TRIM_PACKETS) && \
    !isPortStatSupported(SAI_PORT_STAT_DROPPED_TRIM_PACKETS))
{
    portStatPlugins += "," + nvdaPortTrimSha;
}
```

- LAG テーブル直接の制御ではないが、Mellanox プラットフォームでは追加の Lua 統計プラグインが登録される
- これは LAG インタフェースを含む全ポートカウンタ収集に影響する可能性がある

### 5. プラットフォーム識別子一覧 (orch.h)

orchagent は `platform` 環境変数の部分文字列でベンダーを識別する。PORTCHANNEL 関連の分岐で参照される定義:

| 定数 | 値 | LAG 関連の影響 |
|------|----|---------------|
| `MLNX_PLATFORM_SUBSTRING` | `"mellanox"` | distribution-only モード非対応（コメント明記）|
| `BRCM_PLATFORM_SUBSTRING` | `"broadcom"` | TPID/VoQ 対応程度がシリーズ依存 |
| `BRCM_DNX_PLATFORM_SUBSTRING` | `"broadcom-dnx"` | 同上 |
| `BFN_PLATFORM_SUBSTRING` | `"barefoot"` | — |
| `VS_PLATFORM_SUBSTRING` | `"vs"` | SAI_LAG_ATTR_TPID SET が NO-OP/エラー |
| `NPS_PLATFORM_SUBSTRING` | `"nephos"` | — |
| `CISCO_8000_PLATFORM_SUBSTRING` | `"cisco-8000"` | — |
| `XS_PLATFORM_SUBSTRING` | `"xsight"` | — |
| `CLX_PLATFORM_SUBSTRING` | `"clounix"` | — |
| `MRVL_PRST_PLATFORM_SUBSTRING` | `"marvell-prestera"` | — |
| `MRVL_TL_PLATFORM_SUBSTRING` | `"marvell-teralynx"` | — |

---

## 結論

| 差の性質 | 対象プラットフォーム | 影響 |
|---------|---------|------|
| distribution-only モード非対応 | Mellanox | LAG メンバ enable/disable の操作順が逆転。コメントで明記。誤順序では SAI エラーの可能性 |
| `SAI_LAG_ATTR_SYSTEM_PORT_AGGREGATE_ID` | VoQ スイッチのみ | `create_lag()` 追加属性・シャーシ全体でユニーク ID 管理が必要 |
| `SAI_LAG_ATTR_TPID` サポート | ASIC 依存 (VS は NO-OP) | Q-in-Q TPID 非対応 ASIC・VS 環境では SAI エラー |
| 統計プラグイン追加 | Mellanox のみ | trim 統計が追加登録。LAG を含むポートカウンタ収集に波及 |
