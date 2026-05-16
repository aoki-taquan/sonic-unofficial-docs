# TUNNEL_DECAP_TABLE — Phase A: コード由来暗黙デフォルト調査

ソース: `sonic-swss/orchagent/tunneldecaporch.cpp` + `tunneldecaporch.h`
SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d

---

## 1. ハードコード定数

| 定数 | 値 | 場所 | 説明 |
|------|----|------|------|
| `OVERLAY_RIF_DEFAULT_MTU` | `9100` | `tunneldecaporch.cpp` L14 | オーバーレイ RIF に設定される MTU。フィールドとして公開されない |
| `SubnetDecapConfig.tunnel` | `"IPINIP_SUBNET"` | `tunneldecaporch.h` L100 | subnet decap 用 v4 トンネル名がハードコード |
| `SubnetDecapConfig.tunnel_v6` | `"IPINIP_SUBNET_V6"` | `tunneldecaporch.h` L101 | subnet decap 用 v6 トンネル名がハードコード |

## 2. 暗黙デフォルト（フィールド省略時の挙動）

| フィールド | 省略時の挙動 | コード根拠 |
|-----------|-------------|-----------|
| `src_ip` | `nullptr` として扱われ P2MP タームが生成される | `p_src_ip = nullptr` (L95), SAI `SAI_TUNNEL_ATTR_ENCAP_SRC_IP` をスキップ |
| `decap_dscp_to_tc_map` | SAI 属性をプッシュしない (`SAI_NULL_OBJECT_ID`) | L832-837: `if (dscp_to_tc_map_id != SAI_NULL_OBJECT_ID)` ガード |
| `decap_tc_to_pg_map` | SAI 属性をプッシュしない (`SAI_NULL_OBJECT_ID`) | L839-845: `if (tc_to_pg_map_id != SAI_NULL_OBJECT_ID)` ガード |
| `encap_ecn_mode` | `encap_ecn.empty()` なら SAI 属性をスキップ | L797: `if (!encap_ecn.empty())` ガード |
| `term_type` (DECAP_TERM) | `TUNNEL_TERM_TYPE_P2MP` | `doDecapTunnelTermTask` L361: デフォルト初期化 |

## 3. Dead-SAI フィールド（記録のみ、SAI に流れない）

| フィールド | SAI 属性 | 状態 |
|-----------|---------|------|
| `encap_tc_to_dscp_map` | なし | `tunnelTable[key].encap_tc_to_dscp_map_id` に記録のみ (L257, L303)。`addDecapTunnel()` に引数として渡されず SAI に設定されない |
| `encap_tc_to_queue_map` | なし | 同上 (L272, L305)。muxorch が読み出す目的でのみ保持 |

## 4. Create-Only 属性（更新時スキップ）

| フィールド | SAI 属性 | 挙動 |
|-----------|---------|------|
| `ecn_mode` | `SAI_TUNNEL_ATTR_DECAP_ECN_MODE` | 既存トンネル更新時 WARN ログを出して `valid = false; break` (L179-182) |
| `encap_ecn_mode` | `SAI_TUNNEL_ATTR_ENCAP_ECN_MODE` | 既存トンネル更新時 NOTICE ログを出して `valid = false; break` (L194-198) |

## 5. 書込み順依存

- `doTask()` は `gPortsOrch->allPortsReady()` が false の場合即座に return する (L55-58)。
  ports 初期化前に TUNNEL_DECAP_TABLE エントリが届いた場合、すべてキューに留まる。
- `processUnhandledDecapTunnelTerms()` が呼ばれるのはトンネル本体の作成成功後のみ (L308-310)。
  DECAP_TERM_TABLE エントリがトンネル本体より先に届いた場合、unhandledDecapTerms に蓄積される。

## 6. プラットフォーム依存（SAI capability）

- `SAI_TUNNEL_ATTR_DECAP_ECN_MODE` / `SAI_TUNNEL_ATTR_ENCAP_ECN_MODE` は SAI 実装依存。
  `SAI_TUNNEL_ATTR_ENCAP_ECN_MODE` の create-only 制約は SAI spec に依存し、
  一部 ASIC では set_tunnel_attribute が success を返す可能性がある。

## 7. unknown フィールドの silent drop

- フィールドループ内で認識されないフィールド名が来ると `"unknown decap tunnel table attribute"` を
  LOG_ERROR して `valid = false; break` し、**エントリ全体をスキップ**する (L275-280)。
  フィールド名の typo が silent な設定欠落を引き起こす。

## 8. YANG-実装 乖離

- `TUNNEL_DECAP_TABLE` は YANG 定義なし（APPL_DB テーブル）。
- `encap_tc_to_dscp_map` / `encap_tc_to_queue_map` は SAI に流れないにもかかわらず、
  ドキュメント上はフィールドとして存在する（dead-SAI フィールド）。
- `OVERLAY_RIF_DEFAULT_MTU = 9100` はどの CONFIG_DB フィールドでも上書き不可。

## 9. Dead Consumer

- `encap_tc_to_dscp_map` / `encap_tc_to_queue_map` は `muxorch` が `getQosMapId()` 経由で読み出す目的でのみ使用される。
  tunnel decap 側の SAI パスには影響しない。

---

*生成日: 2026-05-14*
