# tunnel-state Phase H — STATE_DB TUNNEL プラットフォーム差調査メモ

調査日: 2026-05-17
対象: `docs/reference/config-db/tunnel-state.md`

## 調査対象ソース

| ファイル | コミット |
|---------|---------|
| `orchagent/tunneldecaporch.cpp` | 4305596156d70e9797e8a881b3d19b46de0bce0d |
| `orchagent/vxlanorch.cpp` | 4305596156d70e9797e8a881b3d19b46de0bce0d |
| `cfgmgr/vxlanmgr.cpp` | 4305596156d70e9797e8a881b3d19b46de0bce0d |

## 1. VXLAN_TUNNEL_TABLE — P2P DIP トンネルの SAI 対応可否 (プラットフォーム依存)

`VxlanTunnelOrch` 起動時に `sai_query_attribute_enum_values_capability()` を呼び出し、
`SAI_TUNNEL_ATTR_PEER_MODE` の対応値一覧を問い合わせる。

```cpp
// vxlanorch.cpp:1256-1274
status = sai_query_attribute_enum_values_capability(gSwitchId, SAI_OBJECT_TYPE_TUNNEL,
                                                    SAI_TUNNEL_ATTR_PEER_MODE, &values);
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_WARN("Unable to get supported tunnel peer modes. Defaulting to P2P");
    is_dip_tunnel_supported = true;
}
else
{
    is_dip_tunnel_supported = false;
    for (uint32_t idx = 0; idx < values.count; idx++)
    {
        if (values.list[idx] == SAI_TUNNEL_PEER_MODE_P2P)
        {
            is_dip_tunnel_supported = true;
            break;
        }
    }
}
```

- SAI が `SAI_STATUS_SUCCESS` を返せない ASIC (能力取得未対応) → デフォルト `is_dip_tunnel_supported=true` として扱う
- `SAI_TUNNEL_PEER_MODE_P2P` 未対応 ASIC → `is_dip_tunnel_supported=false` → `createDynamicDIPTunnel()` は実行されない → `VXLAN_TUNNEL_TABLE` に EVPN 由来の DIP エントリが書かれない

## 2. VXLAN_TUNNEL_TABLE — FlexCounter / ASIC_DB 連携の Traditional vs Non-Traditional 差

`gTraditionalFlexCounter` フラグによって `VIDTORID` テーブルの使用有無が変わる:

```cpp
// vxlanorch.cpp:1297-1299
if (gTraditionalFlexCounter)
{
    m_vidToRidTable = make_unique<Table>(m_asic_db.get(), "VIDTORID");
}
```

タイマー発火時に COUNTERS_DB への書き込みを実行するかどうかの判定:

```cpp
// vxlanorch.cpp:1318
if (!gTraditionalFlexCounter || m_vidToRidTable->hget("", id, value))
```

- Traditional FlexCounter 環境: ASIC_DB `VIDTORID` に RID が登録されてから `COUNTERS_DB` 書き込み
- Non-Traditional (syncd-rpc 等): `VIDTORID` 未使用 → SAI 作成完了後すぐに COUNTERS_DB 書き込み
- **VXLAN_TUNNEL_TABLE への書き込みタイミング自体はこのフラグの影響を受けない** (FlexCounter は STATE_DB ではなく COUNTERS_DB に書く)

## 3. TUNNEL_DECAP_TABLE — overlay RIF MTU のハードコード値

```cpp
// tunneldecaporch.cpp:14
#define OVERLAY_RIF_DEFAULT_MTU 9100

// tunneldecaporch.cpp:749-750
overlay_intf_attr.id = SAI_ROUTER_INTERFACE_ATTR_MTU;
overlay_intf_attr.value.u32 = OVERLAY_RIF_DEFAULT_MTU;
```

overlay Router Interface の MTU は `9100` にハードコードされており、プラットフォームや CONFIG_DB での変更はできない。
ASIC の MTU 上限がこれより低い場合、`sai_router_intfs_api->create_router_interface()` が失敗し、
TUNNEL_DECAP_TABLE への STATE_DB 書き込みが行われない (トンネル作成中断)。

## 4. TUNNEL_DECAP_TABLE — SAI create-only 属性のプラットフォーム制約

以下の SAI 属性は `create_tunnel()` 時のみ設定可能で、既存トンネルへの変更はプラットフォームによらず一律スキップされる:

| STATE_DB フィールド | SAI 属性 | 備考 |
|-------------------|---------|------|
| `ecn_mode` | `SAI_TUNNEL_ATTR_DECAP_ECN_MODE` | create-only。変更要求は SWSS_LOG_WARN で黙殺 (`tunneldecaporch.cpp:179`) |
| `encap_ecn_mode` | `SAI_TUNNEL_ATTR_ENCAP_ECN_MODE` | create-only。変更要求は SWSS_LOG_NOTICE で黙殺 (`tunneldecaporch.cpp:195`) |

この制約は SAI 仕様由来であり、ASIC ベンダーによらず共通。

## 5. CRM カウンタとの関連 (tunneldecaporch)

`tunneldecaporch` は TUNNEL TERM の next-hop 作成/削除時に CRM カウンタを増減:

```cpp
// tunneldecaporch.cpp:1346-1350
gCrmOrch->incCrmResUsedCounter(CrmResourceType::CRM_IPV4_NEXTHOP);
// または
gCrmOrch->incCrmResUsedCounter(CrmResourceType::CRM_IPV6_NEXTHOP);
```

CRM (Capacity Resource Manager) の上限は ASIC 依存。CRM の NEXTHOP 上限超過は SAI エラーとして返り、
STATE_DB `TUNNEL_DECAP_TABLE` の next-hop フィールドが書き込まれない原因になり得る。

## 6. VXLAN_TABLE — vxlanmgr の Linux カーネル依存

`createVxlan()` はカーネルの VXLAN 機能に依存:
- `ip link add ... type vxlan` の実行可否はカーネルバージョンおよびカーネルモジュール (`vxlan.ko`) のロード有無に依存
- VS (virtual switch) 環境ではカーネル VXLAN が利用可能なため動作する
- ハードウェアオフロードが有効な ASIC ではカーネル VXLAN デバイスを作成しつつ、データパス処理は ASIC が担う

## まとめ — プラットフォームによる STATE_DB 動作差

| STATE_DB テーブル | 差異の発生条件 | 差異内容 |
|-----------------|--------------|---------|
| `VXLAN_TUNNEL_TABLE` | `SAI_TUNNEL_PEER_MODE_P2P` 非対応 ASIC | EVPN 由来 DIP トンネルが ASIC に作成されず、STATE_DB に書かれない |
| `TUNNEL_DECAP_TABLE` | overlay RIF MTU 9100 未対応 ASIC | トンネル作成失敗 → STATE_DB に書かれない |
| `TUNNEL_DECAP_TABLE` | `ecn_mode` / `encap_ecn_mode` 変更要求 | create-only のため全プラットフォームで黙殺 (SAI 仕様共通) |
| `VXLAN_TABLE` | カーネル VXLAN モジュール未ロード環境 | `createVxlan()` 失敗 → `state=ok` が書かれない |
