# QUEUE — Phase H: プラットフォーム/SAI 差異 中間ファイル

生成日: 2026-05-15 (Phase H)

## 調査対象ソース

- `sonic-swss/orchagent/qosorch.cpp`
- `sonic-swss/orchagent/portsorch.cpp`
- `sonic-buildimage/files/build_templates/qos_config.j2`

---

## 1. VoQ シャーシ vs 非 VoQ — QUEUE 処理分岐

`gMySwitchType == "voq"` で 2 本の完全に独立した実装パスが走る。

### 1a. key トークン数

```cpp
// qosorch.cpp:1772-1812
if (gMySwitchType == "voq") {
    // 4 トークン: <hostname>|<asic_name>|<ifname>|<qindex>
    if (tokens.size() != 4) return task_invalid_entry;
} else {
    // 2 トークン: <ifname>|<qindex>
    if (tokens.size() != 2) return task_invalid_entry;
}
```

### 1b. ローカル/リモートポート判定 (VoQ のみ)

```cpp
// qosorch.cpp:1787-1797
// hostname と asic_name が自ノードのものか比較
if((tokens[0] == gMyHostName) && (tmp_token_1 == tmp_gMyAsicName))
    local_port = true;
```

VoQ 環境では、エントリが **リモートシステムポート**向けの場合は SAI scheduler 適用を skip (即 `return true`) し、**ローカルポート**のみに適用する。

### 1c. scheduler 適用 — リモートポートスキップ

```cpp
// qosorch.cpp:1637-1641
if (gMySwitchType == "voq") {
    if (port.m_system_port_info.type == SAI_SYSTEM_PORT_TYPE_REMOTE)
        return true;  // リモートシステムポートは no-op
    // ローカルポートに変換してから処理
    gPortsOrch->getPort(port.m_system_port_info.local_port_oid, port);
}
```

VoQ の scheduler 適用では `port.m_queue_ids` (通常のキューリスト) を使う点は非 VoQ と同じ。ただし **system port → local port** への解決を先に実行する。

### 1d. WRED 適用 — VoQ 専用 API

```cpp
// qosorch.cpp:1715-1732
if (gMySwitchType == "voq") {
    // VoQ 専用リストを取得 (system_port から SAI_SYSTEM_PORT_ATTR_QOS_VOQ_LIST)
    vector<sai_object_id_t> queue_ids = gPortsOrch->getPortVoQIds(port);
    queue_id = queue_ids[queue_ind];
} else {
    queue_id = port.m_queue_ids[queue_ind];
}
// 両パス共通: sai_queue_api->set_queue_attribute(SAI_QUEUE_ATTR_WRED_PROFILE_ID)
```

非 VoQ: `port.m_queue_ids` (egress queue の OID リスト)
VoQ: `m_port_voq_ids[port.m_alias]` — `SAI_SYSTEM_PORT_ATTR_QOS_VOQ_LIST` から取得したバーチャル出力キュー (VoQ) の OID リスト。SAI オブジェクト種別が異なる。

---

## 2. VoQ 用 queue OID の取得元

```cpp
// portsorch.cpp:6542-6578
attr.id = SAI_SYSTEM_PORT_ATTR_QOS_NUMBER_OF_VOQS;
sai_system_port_api->get_system_port_attribute(port.m_system_port_oid, 1, &attr);
m_port_voq_ids[port.m_alias].resize(attr.value.u32);

attr.id = SAI_SYSTEM_PORT_ATTR_QOS_VOQ_LIST;
sai_system_port_api->get_system_port_attribute(port.m_system_port_oid, 1, &attr);
```

VoQ 数はプラットフォーム (SAI 実装) が返す値に完全依存。SONiC 側でハードコードなし。

---

## 3. vendor SAI — WRED 閾値設定の制約

```cpp
// qosorch.cpp:595-632 (コメント)
/*
 * Setting WRED profile can fail in case
 * - the current min threshold > new max threshold
 * - or the current max threshold < new min threshold
 * for any color at any time, on some vendor's platforms.
 *
 * The root cause: vendor SAI は 1 属性ずつ SET するため
 * min/max の逆転を引き起こす中間状態でサニティチェックが失敗する。
 *
 * The fix: 違反する属性を 2nd half リストに分離して適用順を制御
 */
```

WRED 閾値の更新順序は **ベンダー SAI の実装差**に起因する問題への対処として SONiC 側でワークアラウンドを実装済み。特定ベンダー名は明記されていないが、複数ベンダーで発生する一般的問題として対処。

---

## 4. ビルド時 QUEUE デフォルト — プラットフォーム分岐

`qos_config.j2` における QUEUE 生成ロジックは以下の優先順位で分岐する。

### 優先度 1: VoQ シャーシ

```jinja2
{# qos_config.j2:507-551 #}
{% if voq_chassis %}
    "QUEUE": {
        # system_port ごとに q3/q4: wred_profile=AZURE_LOSSLESS
        # SYSTEM_PORT_ACTIVE のみ scheduler=scheduler.1 を付与
        # q0/q1/q2/q5/q6: scheduler=scheduler.0 (SYSTEM_PORT_ACTIVE のみ)
    }
```

VoQ では `QUEUE` の key が `<system_port>|<qindex>` 形式で生成される。`SYSTEM_PORT_ALL` (全ポート) に wred_profile を付与し、`SYSTEM_PORT_ACTIVE` のみに scheduler を付与する点が非 VoQ との差異。

### 優先度 2: SKU カスタム関数 (direction-based / single-queue / generate_queue_config)

プラットフォームが `generate_direction_based_queue_per_sku` / `generate_single_queue_per_sku` / `generate_queue_config` マクロを定義している場合、その関数に委譲される。

### 優先度 3: 標準ロジック (ComputeAI / 標準 / DPC 分岐)

| 条件 | q3/q4 の設定 | q2/q6 の設定 |
|------|------------|------------|
| `resource_type == ComputeAI` | q3: scheduler.2+LOSSLESS, q4: scheduler.3+LOSSLESS | - |
| DPC ポート (`PORT_DPC` 所属) | scheduler.0 のみ (LOSSLESS なし) | scheduler.0 のみ |
| apollo resource_type | q4: scheduler.2+LOSSLESS | - |
| 標準 + `port_names_list_extra_queues` | q2/q6: scheduler.1+LOSSLESS | - |
| 標準 (それ以外) | q3/q4: scheduler.1+LOSSLESS | scheduler.0 のみ |

DPC (Direct Port Connect) ポートは q3/q4 の lossless 設定を行わない。ビルド時 `PORT_DPC` リストへの所属はポート名規則で決定される (実際のハードウェア構成依存)。

---

## 5. CPU queue の特殊性

CPU キューは `<ifname>=CPU` として QUEUE エントリを持てる (YANG で許容)。SAI の CPU queue OID は egress queue とは別系統のオブジェクトであり、プラットフォームにより数が大きく異なる (CPU 0-48 等)。qosorch は CPU ポートに対しても同一の scheduler/WRED 適用パスを通る。

---

## 証跡

- `sonic-swss/orchagent/qosorch.cpp` lines 595-632 (WRED vendor workaround), 1630-1705 (applySchedulerToQueueSchedulerGroup VoQ分岐), 1708-1748 (applyWredProfileToQueue VoQ分岐), 1750-1948 (handleQueueTable VoQ key解析)
- `sonic-swss/orchagent/portsorch.cpp` lines 6540-6578 (getPortVoQIds / SAI_SYSTEM_PORT_ATTR_QOS_VOQ_LIST), 11310-11314 (getPortVoQIds)
- `sonic-buildimage/files/build_templates/qos_config.j2` lines 507-670 (VoQ/DPC/ComputeAI/標準分岐)
