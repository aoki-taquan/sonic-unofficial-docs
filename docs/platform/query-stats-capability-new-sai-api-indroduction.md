---
title: sai_query_stats_capability による Counter Capability 一括取得
description: sai_query_stats_capability による Counter Capability 一括取得 — SONiC syncd
  の FlexCounter は、各オブジェクト（Port / Queue / Priority Group / RIF / Buffer Pool）について 「どの統計
  ID が…
area: platform
verification: code-verified
last_verified: 2026-05-09
sources:
- repo: sonic-net/SONiC
  path: doc/Query_Stats_Capability/Query_Stats_Capability_HLD.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
- repo: sonic-net/sonic-sairedis
  path: syncd/FlexCounter.cpp
  ref: master
related:
  config_db:
  - FLEX_COUNTER_TABLE
  cli:
  - show techsupport
  - show version
  yang:
  - sonic-flex_counter
  - sonic-debug-counter
  - sonic-buffer-pool
  - sonic-crm
---

<!-- topics-tip -->
!!! tip "Topics で読み物として読む"
    この HLD は実装詳細を含む。機能の概念・設定・運用を読み物として読みたい場合は [Topics 14 章: Platform / Port / Optics](../topics/14-platform-port-optics/index.md) を参照。
<!-- /topics-tip -->

!!! info "裏取りステータス: code-verified"
    `sonic-sairedis/syncd/FlexCounter.cpp` master に `querySupportedCounters()` 実装と `use_sai_stats_capa_query` フラグ、`sai_stat_capability_list_t` を使った 2 段呼び出し（count 取得 → list 取り直し）パターンを確認 (L1566-1619)。master ではオブジェクト種別ごとの per-type 関数ではなく、`CounterContext<StatType>` テンプレート上の単一 `updateSupportedCounters()` に統合済み (L1542-1564)。HLD と異なり SAI 側のフォールバック条件は `SAI_STATUS_NOT_IMPLEMENTED` 限定ではなく「`querySupportedCounters()` が `SAI_STATUS_SUCCESS` 以外を返した場合」となっている (L1559)。MACsec / SwitchDebug / PortDebug / Flow / Tunnel など一部 context 種別は `use_sai_stats_capa_query = false` で明示的に旧 per-ID 方式に固定 (L3312, L3346, L3354, L3361, L3368, L3376)。

# sai_query_stats_capability による Counter Capability 一括取得

## 概要

[SONiC](../reference/glossary.md#term-sonic) `syncd` の `FlexCounter` は、各オブジェクト（Port / Queue / [Priority Group](../reference/glossary.md#term-priority-group) / [RIF](../reference/glossary.md#term-rif) / [Buffer Pool](../reference/glossary.md#term-buffer-pool)）について **「どの統計 ID が [SAI](../reference/glossary.md#term-sai) でサポートされているか」を `getStats()` を 1 ID ずつ叩いて確認** していた。Port だけでも数十個の counter ID をループで試すため、起動・fast-reboot 時のオーバーヘッドが大きい[^1]。

本機能は SAI に追加された **`sai_query_stats_capability()`** API を使って **オブジェクトの全 counter capability を 1 コールで取得** するように `FlexCounter` を改修する。fast-reboot のような時間制約のあるパスで特に効果が大きい[^1]。

## 動作仕様

### 既存実装

```cpp
for (int id = SAI_PORT_STAT_IF_IN_OCTETS; id <= SAI_PORT_STAT_IF_OUT_FABRIC_DATA_UNITS; ++id) {
    sai_port_stat_t counter = static_cast<sai_port_stat_t>(id);
    sai_status_t status = m_vendorSai->getStats(SAI_OBJECT_TYPE_PORT, portRid, 1,
                                                (sai_stat_id_t *)&counter, &value);
    if (status != SAI_STATUS_SUCCESS) continue;
    m_supportedPortCounters.insert(counter);
}
```

各 ID について実際に値を取得しに行き、SUCCESS なら supported とみなす。失敗ログも 1 ID ずつ出る[^1]。

### 新実装（2 段呼び出し）

`sai_query_stats_capability` は標準的な「サイズ問い合わせ → 実取得」の 2 段パターンを取る[^1]:

```cpp
sai_stat_capability_list_t stats_capability {0, nullptr};
sai_status_t status = m_vendorSai->queryStatsCapability(portRid, SAI_OBJECT_TYPE_PORT, &stats_capability);
// status == BUFFER_OVERFLOW で count に必要要素数がセットされる

if (status == SAI_STATUS_BUFFER_OVERFLOW) {
    std::vector<sai_stat_capability_t> statCapabilityList(stats_capability.count);
    stats_capability.list = statCapabilityList.data();
    status = m_vendorSai->queryStatsCapability(portRid, SAI_OBJECT_TYPE_PORT, &stats_capability);
    if (status == SAI_STATUS_SUCCESS) {
        for (auto& cap : statCapabilityList)
            m_supportedPortCounters.insert(static_cast<sai_port_stat_t>(cap.stat_enum));
    }
}
```

master 実装では **`querySupportedCounters()` が `SAI_STATUS_SUCCESS` 以外を返した場合に既存の per-ID 取得方式へフォールバック** する設計に拡張されている (HLD は `SAI_STATUS_NOT_IMPLEMENTED` のみと記述していたが、実装はより広く異常系を拾う)[^2]。これにより SAI 未対応ベンダでも互換性を維持する[^1]。

```cpp
// FlexCounter.cpp L1559: 統合された CounterContext テンプレートでの fallback 判定
if (!use_sai_stats_capa_query || querySupportedCounters(rid, stats_mode, m_supportedCounters) != SAI_STATUS_SUCCESS)
{
    /* Fallback to legacy approach */
    getSupportedCounters(rid, counter_ids, stats_mode);
}
```

### SAI ヘッダ定義

```c
/**
 * @brief Query statistics capability for statistics bound at object level
 *
 * @param[in]    switch_id        SAI Switch object id
 * @param[in]    object_type      SAI object type
 * @param[inout] stats_capability List of implemented enum values, and the statistics modes (bit mask) supported per value
 *
 * @return #SAI_STATUS_SUCCESS on success, #SAI_STATUS_BUFFER_OVERFLOW if lists size insufficient,
 *         failure status code on error
 */
sai_status_t sai_query_stats_capability(
        _In_    sai_object_id_t                 switch_id,
        _In_    sai_object_type_t               object_type,
        _Inout_ sai_stat_capability_list_t     *stats_capability);
```

各エントリ `sai_stat_capability_t` は `stat_enum`（counter ID）と `stat_modes`（stats mode のビットマスク。READ / READ_AND_CLEAR 等）を持つ[^1]。実装側は `statCapability.stat_modes & stats_mode` で要求モードとの AND を取り、合致するものだけを supported set に入れる[^2]。

### 改修対象関数 (master 取り込み後)

HLD では Port / Queue / PG / RIF / Buffer Pool ごとに個別の `updateSupportedXxxCounters()` を改修すると記述されていたが[^1]、master では `CounterContext<StatType>` テンプレートクラス上の **単一の `updateSupportedCounters()` メソッドに統合** されている[^2]。対象オブジェクト種別は `m_objectType` メンバで切り替わる。

| Counter context | StatType | object type |
|------|------|------|
| `COUNTER_TYPE_PORT` | `sai_port_stat_t` | `SAI_OBJECT_TYPE_PORT` |
| `COUNTER_TYPE_QUEUE` | `sai_queue_stat_t` | `SAI_OBJECT_TYPE_QUEUE` |
| `COUNTER_TYPE_PG` | `sai_ingress_priority_group_stat_t` | `SAI_OBJECT_TYPE_INGRESS_PRIORITY_GROUP` |
| `COUNTER_TYPE_RIF` | `sai_router_interface_stat_t` | `SAI_OBJECT_TYPE_ROUTER_INTERFACE` |
| `COUNTER_TYPE_BUFFER_POOL` | `sai_buffer_pool_stat_t` | `SAI_OBJECT_TYPE_BUFFER_POOL` |
| `COUNTER_TYPE_ENI` | `sai_eni_stat_t` | `SAI_OBJECT_TYPE_ENI` (DASH) |

一方で次の context 種別は `use_sai_stats_capa_query = false` で明示的に新 API 経路を無効化し、従来の per-ID 列挙のみを使う[^2]:

- `COUNTER_TYPE_PORT_DEBUG` (PortDebug)
- `COUNTER_TYPE_SWITCH_DEBUG` (SwitchDebug)
- `COUNTER_TYPE_MACSEC_FLOW` / `COUNTER_TYPE_MACSEC_SA`
- `COUNTER_TYPE_FLOW`
- `COUNTER_TYPE_TUNNEL`

Meter bucket entry には `querySupportedMeterCounters()` という別エントリポイントが用意され、こちらも 2 段呼び出しパターンを使う[^2]。

<!-- evidence:
source: sonic-net/SONiC/doc/Query_Stats_Capability/Query_Stats_Capability_HLD.md#L20-L30 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
excerpt: |
  The affected functions with this new API will take place on FlexCounter.cpp:
  - void updateSupportedPortCounters(_In_ sai_object_id_t portRid)
  - void updateSupportedQueueCounters(...)
  ...
  The implementation will support backwards compatibility, so if a SAI vendor is currently not supporting this API it will fall back to the legacy approach.
reasoning: 改修対象関数とフォールバック動作の根拠。
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/SONiC/doc/Query_Stats_Capability/Query_Stats_Capability_HLD.md#L20-L30 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)"

    **出典**:

    `sonic-net/SONiC/doc/Query_Stats_Capability/Query_Stats_Capability_HLD.md#L20-L30 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)`

    **抜粋**:

    ```text
    The affected functions with this new API will take place on FlexCounter.cpp:
    - void updateSupportedPortCounters(_In_ sai_object_id_t portRid)
    - void updateSupportedQueueCounters(...)
    ...
    The implementation will support backwards compatibility, so if a SAI vendor is currently not supporting this API it will fall back to the legacy approach.
    ```

    **判断根拠**: 改修対象関数とフォールバック動作の根拠。

<!-- evidence-rendered:end -->

## 設定

### 関連する CONFIG_DB / CLI / YANG

外部設定表面は無い。SAI capability の検出方式が変わるだけで、ユーザに見える挙動は「起動時間が短くなる」のみ。

### 関連する SAI 属性

該当なし（API そのものの追加）。`sai_stat_capability_t.stat_enum` と `stat_modes` ビットマスクが個別 counter の能力情報を返す[^2]。

## 制限事項

- **SAI ベンダ実装依存**: 新 API を実装するか、`SAI_STATUS_NOT_IMPLEMENTED` を返すかのいずれかが要求される[^1]。誤った status を返すベンダではフォールバックが働かない可能性。
- **互換のためのコードパス二重化**: 旧 per-ID ループ実装も残す必要があり、メンテナンスコストは増える。
- **mode 情報の扱い**: 新 API は stats mode のビットマスクも返すが、SONiC `FlexCounter` 側ではリクエスト中の `stats_mode` と AND を取り、bit が立っていない counter は supported set から除外する用途に限定して活用している[^2]。`READ_AND_CLEAR` を要求した context で counter が `READ` のみ対応の場合は除外される。

## 干渉する機能

- **Fast-reboot / Warm-reboot**: 起動経路で counter capability 検出を含むため、本改修は時間制約のある reboot シーケンスで特に意味がある[^1]。
- **`FlexCounter`/`FlexCounterManager`**: 統計収集の中核。同 cpp 内の他関数と連動するため、メンバ変数 `m_supportedPortCounters` 等の読み出し側もそのまま使える設計。
- **個別 vendor SAI**: 実装状況がバラつくと本機能の有効性も差が出る。`SAI_STATUS_NOT_IMPLEMENTED` を正しく返さないベンダはエラー扱いされる可能性。

## トラブルシューティング

- 起動が依然遅い: vendor SAI が新 API を実装していない可能性。`syncd` ログで `queryStatsCapability` の status を確認。`SAI_STATUS_NOT_IMPLEMENTED` ならフォールバック動作中。
- 一部 counter が認識されない: 新 API が返す `stat_enum` 集合と旧 per-ID 列挙の差が無いか、SAI バージョン依存を疑う。

### コマンド例

SAI stats capability を確認する。

```bash
# SAI stats
docker exec syncd saidump 2>&1 | head -40
redis-cli -n 1 keys 'COUNTERS_*' | head
counterpoll show
```

## 引用元

[^1]: `sonic-net/SONiC` `doc/Query_Stats_Capability/Query_Stats_Capability_HLD.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`
[^2]: `sonic-net/sonic-sairedis` `syncd/FlexCounter.cpp` L1542-1619 (`updateSupportedCounters` / `querySupportedCounters`), L2910-2959 (`querySupportedMeterCounters`), L3308-3378 (CounterContext factory での `use_sai_stats_capa_query` 切替), `syncd/FlexCounter.h` L95 (`use_sai_stats_capa_query` メンバ既定値), `syncd/VendorSai.cpp` L376 (`queryStatsCapability` 実装) master

<!-- glossary-links-injected: a841ffc67f6c -->
