# macsec-profile — Phase H: プラットフォーム差異

> 調査日: 2026-05-16  
> ソース: `sonic-swss/orchagent/macsecorch.cpp`

## 1. Gearbox PHY 搭載ポート vs. NPU ネイティブポート

`MACsecOrch` はポートに Gearbox PHY が接続されているかどうかで SAI オブジェクトの操作対象を動的に切り替える。

### 1.1 バックエンド選択ロジック

```cpp
// macsecorch.cpp:359-378, 405-417
const auto *phy = get_gearbox_phy();
bool force_npu = true;
if (phy)
    force_npu = !phy->macsec_supported;

if (!force_npu && port->m_line_side_id != SAI_NULL_OBJECT_ID)
    m_port_id = port->m_line_side_id;   // PHY 側 line port を使用
else
    m_port_id = port->m_port_id;        // NPU ポートへフォールバック
```

| 条件 | Port ID | Switch ID | カウンタグループ |
|------|---------|-----------|----------------|
| `phy && phy->macsec_supported == true` | `port.m_line_side_id` | PHY の switch ID | `m_gb_macsec_*` |
| PHY なし / `macsec_supported == false` | `port.m_port_id` | `gSwitchId` (グローバル) | `m_macsec_*` |

PHY が接続されていても `macsec_supported == false` の場合は NPU にフォールバックし、`SWSS_LOG_NOTICE("backend=NPU (phy marked unsupported)")` を出力する。

### 1.2 カウンタ管理の分岐

```cpp
// macsecorch.cpp:2536-2566
FlexCounterManager& MACsecOrch::MACsecSaStatManager(MACsecOrchContext &ctx) {
    const auto *phy = ctx.get_gearbox_phy();
    if (phy && phy->macsec_supported)
        return m_gb_macsec_sa_stat_manager;   // Gearbox 用
    return m_macsec_sa_stat_manager;           // NPU 用
}
```

## 2. SAI MACsec Capability クエリ (ASIC ベンダー対応差)

### 2.1 ACL SCI フィールドサポート確認

初期化時 (`MACsecOrch::MACsecOrch()`) に `sai_query_attribute_capability` で `SAI_ACL_TABLE_ATTR_FIELD_MACSEC_SCI` の実装有無を確認する。

```cpp
// macsecorch.cpp:672-681
sai_attr_capability_t capability;
if (sai_query_attribute_capability(gSwitchId, SAI_OBJECT_TYPE_ACL_TABLE,
                                    SAI_ACL_TABLE_ATTR_FIELD_MACSEC_SCI,
                                    &capability) == SAI_STATUS_SUCCESS) {
    if (capability.create_implemented == false) {
        SWSS_LOG_DEBUG("SAI_ACL_TABLE_ATTR_FIELD_MACSEC_SCI is not supported");
        saiAclFieldSciMatchSupported = false;
    }
}
```

`saiAclFieldSciMatchSupported = false` の場合、ACL テーブルで SCI フィールドマッチが使えないため、SC ごとの ACL エントリ生成ロジックが変化する。

### 2.2 SCI in Ingress MACsec ACL

```cpp
// macsecorch.cpp:1302-1319
attr.id = SAI_MACSEC_ATTR_SCI_IN_INGRESS_MACSEC_ACL;
status = sai_macsec_api->get_macsec_attribute(...);
// get 失敗 → task_failed でポート有効化中断
// 成功 → m_sci_in_ingress_macsec_acl に格納
```

- `true` (ASIC が SCI を ACL キーとして処理): macsec_flow が 1 つの SecY を表し、複数 SC を flow で束ねられる
- `false` (ASIC が SCI を ACL 外で処理): SC ごとに個別 ACL エントリが必要

### 2.3 SA per SC 最大数クエリ

```cpp
// macsecorch.cpp:1322-1345
attr.id = SAI_MACSEC_ATTR_MAX_SECURE_ASSOCIATIONS_PER_SC;
status = sai_macsec_api->get_macsec_attribute(...);
if (status != SAI_STATUS_SUCCESS)
    m_max_sa_per_sc = 4;  // 非対応 ASIC はデフォルト 4
else {
    // SAI_MACSEC_MAX_SECURE_ASSOCIATIONS_PER_SC_TWO → 2
    // SAI_MACSEC_MAX_SECURE_ASSOCIATIONS_PER_SC_FOUR → 4
    // その他 → SWSS_LOG_WARN + return false
}
```

ASIC によって SC ごとの SA 数が 2 か 4 かが異なる。非対応 ASIC はデフォルト 4 を使用する。

## 3. POST (Power-On Self-Test) 対応差異

`SAI_MACSEC_ATTR_ENABLE_POST` / `SAI_SWITCH_ATTR_MACSEC_POST_STATUS` はベンダー依存機能。

| `STATE_DB.MACSEC_POST_STATUS` | 動作 |
|-------------------------------|------|
| `switch-level-post-in-progress` | Switch init 時に POST 有効化済み。`SAI_SWITCH_ATTR_MACSEC_POST_STATUS` で pass/fail を確認し State DB に記録 |
| `macsec-level-post-in-progress` | MACsec init 時に `SAI_MACSEC_ATTR_ENABLE_POST = true` で POST を有効化。通知コンシューマを設定 |
| その他 | POST 非対応 ASIC。`m_enable_post = false`。POST 通知サブスクリプションをスキップ |

```cpp
// macsecorch.cpp:1246-1251
if (m_enable_post) {
    attr.id = SAI_MACSEC_ATTR_ENABLE_POST;
    attr.value.booldata = true;
    attrs.push_back(attr);
}
```

## 4. Physical Bypass モード (全 ASIC 共通)

egress / ingress 両 MACsec オブジェクト作成時に `SAI_MACSEC_ATTR_PHYSICAL_BYPASS_ENABLE = true` を設定する。MKA ネゴシエーション前の初期状態でバイパスを確保し、SA 確立後に暗号化が有効になる順序を保証する。これは ASIC 種別によらず共通。

## 5. 非対応 / スコープ外

- ベンダー固有 ASIC ドライバの内部実装差 (SAI 抽象化で隠蔽)
- ベンダー版 SONiC (NVIDIA / Edgecore 等) はスコープ外
- master ブランチ以外のバックポート差異はスコープ外

## 引用

- `sonic-swss/orchagent/macsecorch.cpp:359-378, 405-417, 542-559, 672-681, 695-728, 1238-1345, 1390, 2536-2566`
