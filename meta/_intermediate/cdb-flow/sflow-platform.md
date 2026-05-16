# SFLOW — Phase H: プラットフォーム差異 証跡

## 調査ソース

- `sonic-swss/orchagent/sfloworch.cpp`
- `sonic-swss/orchagent/sfloworch.h`
- `sonic-swss/cfgmgr/sflowmgr.cpp`
- `sonic-swss/cfgmgr/sflowmgr.h`

## 1. ASIC capability クエリ

`sfloworch.cpp` の `sflowCreateSession()` は `sai_samplepacket_api->create_samplepacket()` を呼ぶ際に `SAI_SAMPLEPACKET_ATTR_SAMPLE_RATE` のみを渡す。

```cpp
attr.id = SAI_SAMPLEPACKET_ATTR_SAMPLE_RATE;
attr.value.u32 = rate;
sai_rc = sai_samplepacket_api->create_samplepacket(&session_id, gSwitchId, 1, &attr);
```

**ASIC capability の事前クエリなし**。SAI レイヤで拒否された場合は `SAI_STATUS_SUCCESS` 以外が返り、`handleSaiCreateStatus` がエラー処理するが、上位に率の限界は伝達されない。ASIC が対応する最小・最大 sample rate は SAI 実装（ベンダー固有）に依存する。

## 2. ベンダー sample rate 限界差

`sflowmgr.cpp` の `findSamplingRate()` は `oper_speed` または設定済み `speed` の数値文字列をそのまま sample_rate として使う（例: 100GE → "100000"）。

```cpp
string SflowMgr::findSamplingRate(const string& alias)
{
    string oper_speed = m_sflowPortConfMap[alias].oper_speed;
    string cfg_speed = m_sflowPortConfMap[alias].speed;
    if (!oper_speed.empty() && oper_speed != NA_SPEED)
        return oper_speed;
    return cfg_speed;
}
```

YANG 制約では `sample_rate` は `uint32 (256..8388608)`。範囲外の値はアプリ層で拒否される。ベンダー ASIC によってはこの範囲内でも実際には対応できないレートがあるが、orchagent はそれを検出せず SAI エラーとして処理する。

## 3. tx サンプリング方向のプラットフォーム依存性

`sfloworch.cpp` の `sflowAddPort()` は `both` または `tx` の場合に `SAI_PORT_ATTR_EGRESS_SAMPLEPACKET_ENABLE` を設定する。

```cpp
if (direction == "both" || direction == "tx")
{
    attr.id = SAI_PORT_ATTR_EGRESS_SAMPLEPACKET_ENABLE;
    attr.value.oid = sample_id;
    sai_rc = sai_port_api->set_port_attribute(port_id, &attr);
    if (sai_rc != SAI_STATUS_SUCCESS)
    {
        SWSS_LOG_ERROR("Failed to set session %" PRIx64 " on port %" PRIx64, sample_id, port_id);
        ...
    }
}
```

egress samplepacket を**サポートしない ASIC**では `set_port_attribute` が失敗し、tx / both 方向のサンプリングは動作しない。rx 方向は `SAI_PORT_ATTR_INGRESS_SAMPLEPACKET_ENABLE` で、こちらはほぼ全ベンダーが対応している。

## 4. VOQ chassis

`sfloworch.cpp` および `sflowmgr.cpp` に VOQ chassis 固有のコードパスは存在しない。sFlow は物理ポートレベルで管理され、VOQ / system port の概念は sflow パスに組み込まれていない。VOQ chassis では fabric port や system port への sFlow 設定はサポートされない（物理フロントパネルポートのみ）。

## 5. oper_speed 優先処理

STATE_PORT_TABLE の `speed` フィールドを `oper_speed` として追跡し、auto-neg 等でリンク速度が変化した場合に自動的にデフォルト sample rate を更新する。ただしこれも `local_rate_cfg` が設定されている場合は上書きしない。

```cpp
/* oper_speed is updated by orchagent if the vendor supports and oper status is up */
if (m_sflowPortConfMap[alias].oper_speed != oper_speed && !oper_speed.empty())
{
    rate_update = true;
    ...
    m_sflowPortConfMap[alias].oper_speed = oper_speed;
}
```

oper_speed を STATE_DB に書き込むかどうかはベンダー orchagent 実装依存（コメント内に明示）。

## まとめ（platform ブロック記載内容）

| 差異 | 内容 |
|------|------|
| ASIC capability クエリ | なし。SAI 失敗時のみエラーログ |
| sample_rate 下限 / 上限 | YANG: 256..8388608。ベンダー ASIC の実サポート範囲は SAI 依存 |
| tx / egress サンプリング | `SAI_PORT_ATTR_EGRESS_SAMPLEPACKET_ENABLE` 非対応 ASIC では失敗 |
| VOQ chassis | 物理フロントパネルポートのみ対応。system port / fabric port は非対応 |
| oper_speed 追跡 | vendor が STATE_DB に oper_speed を書くかどうかに依存 |
