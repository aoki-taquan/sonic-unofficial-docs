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
    この HLD は実装詳細を含みます。機能の概念・設定・運用を読み物として読みたい場合は [Topics 14 章: Platform / Port / Optics](../topics/14-platform-port-optics/index.md) を参照。
<!-- /topics-tip -->

!!! info "裏取りステータス: code-verified"
    `sonic-sairedis/syncd/FlexCounter.cpp` master に `querySupportedCounters()` 実装と `use_sai_stats_capa_query` フラグ、`sai_stat_capability_list_t` を使った 2 段呼び出し（count 取得 → list 取り直し）パターン、`SAI_STATUS_NOT_IMPLEMENTED` フォールバックを確認。Port / Queue / PG / RIF / BufferPool で同パターン。HLD の改修は master 取り込み済み。

# sai_query_stats_capability による Counter Capability 一括取得

## 概要

SONiC `syncd` の `FlexCounter` は、各オブジェクト（Port / Queue / Priority Group / [RIF](../reference/glossary.md#term-rif) / [Buffer Pool](../reference/glossary.md#term-buffer-pool)）について **「どの統計 ID が [SAI](../reference/glossary.md#term-sai) でサポートされているか」を `getStats()` を 1 ID ずつ叩いて確認** していた。Port だけでも数十個の counter ID をループで試すため、起動・fast-reboot 時のオーバーヘッドが大きい[^1]。

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

ベンダ SAI が `SAI_STATUS_NOT_IMPLEMENTED` を返した場合は **既存の per-ID 取得方式にフォールバック** する。これにより SAI 未対応ベンダでも互換性を維持する[^1]。

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

各エントリ `sai_stat_capability_t` は `stat_enum`（counter ID）と stats mode のビットマスク（READ / READ_AND_CLEAR 等）を持つ[^1]。

### 改修対象関数

`syncd` の `FlexCounter.cpp` で次の関数が新 API を使うよう書き換わる[^1]:

| 関数 | 対象 |
|------|------|
| `updateSupportedPortCounters(portRid)` | Port |
| `updateSupportedQueueCounters(queueRid, counterIds)` | Queue |
| `updateSupportedPriorityGroupCounters(priorityGroupRid, counterIds)` | PG |
| `updateSupportedRifCounters(rifRid)` | RIF |
| `updateSupportedBufferPoolCounters(bufferPoolRid, counterIds, statsMode)` | Buffer Pool |

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

該当なし（API そのものの追加）。`sai_stat_capability_t.stat_enum` と `stats_modes` ビットマスクが個別 counter の能力情報を返す。

## 制限事項

- **SAI ベンダ実装依存**: 新 API を実装するか、`SAI_STATUS_NOT_IMPLEMENTED` を返すかのいずれかが要求される[^1]。誤った status を返すベンダではフォールバックが働かない可能性。
- **互換のためのコードパス二重化**: 旧 per-ID ループ実装も残す必要があり、メンテナンスコストは増える。
- **mode 情報の扱い**: 新 API は stats mode のビットマスクも返すが、SONiC `FlexCounter` 側でどこまで活用するかは [HLD](../reference/glossary.md#term-hld) では明記されていない（counter 集合判定のみ言及）[^1]。

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

<!-- glossary-links-injected: f7696bbf835c -->
