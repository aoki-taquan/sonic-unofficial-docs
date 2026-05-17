# srv6-counter — Phase H: プラットフォーム依存挙動

<!-- phase: H (platform) -->
<!-- slug: srv6-counter -->
<!-- sources:
     sonic-swss/orchagent/srv6orch.cpp
     sonic-swss/orchagent/srv6orch.h
     sonic-swss/orchagent/main.cpp
     sonic-swss/orchagent/flex_counter/flow_counter_handler.cpp -->

## 調査メモ

### SAI 能力クエリ (queryMySidCountersCapability)

`Srv6Orch::queryMySidCountersCapability()` (`srv6orch.cpp:144-155`) が起動時に一度だけ:

```cpp
sai_query_attribute_capability(gSwitchId,
    SAI_OBJECT_TYPE_MY_SID_ENTRY,
    SAI_MY_SID_ENTRY_ATTR_COUNTER_ID,
    &capability);
return capability.set_implemented && capability.create_implemented;
```

- 成功かつ `set_implemented && create_implemented` が両方 true → `m_mysid_counters_supported = true`
- 失敗 or いずれか false → `m_mysid_counters_supported = false`、`initializeCounters()` で即 return（カウンタ初期化ステップが全スキップ）

### m_mysid_counters_supported の影響範囲

`getMySidCountersSupported()` (`srv6orch.cpp:163-166`) は以下から参照される:

- `setCountersState()` (`srv6orch.cpp:255-259`) — false のとき `"Ignoring SRv6 counters state change as they are not supported on this platform"` WARN ログを出して即 return
- `doTaskMySidTable()` (`srv6orch.cpp:1595`) — MySID 追加時に `addMySidCounter()` を呼ぶ前に `m_mysid_counters_enabled && m_mysid_counters_supported` を確認

### gTraditionalFlexCounter フラグ

`orchagent -c traditional` 起動オプション (`main.cpp:529-532`) で `gTraditionalFlexCounter = true`（デフォルト false）。

SRv6 カウンタへの影響:

| gTraditionalFlexCounter | initializeCounters() での処理 | doTask(SelectableTimer) での動作 |
|---|---|---|
| false (デフォルト) | `m_vid_to_rid_table` を初期化しない | `m_vid_to_rid_table->hget()` をスキップ → `m_pending_counters` のすべての OID を即座に登録 |
| true | `m_vid_to_rid_table = Table(ASIC_DB, "VIDTORID")` を初期化 | ASIC_DB の VIDTORID に OID が現れるまで登録を保留 |

`gTraditionalFlexCounter = true` は syncd の SAI redis 通信モードが "traditional" のときのみ使用する旧互換モード。現行 SONiC master では通常 false。

### プラットフォームサポート確認コマンド

```bash
# orchagent ログで SAI 能力クエリ結果を確認
journalctl -u swss --no-pager | grep -i "SRv6 counters"
# "SRv6 counters are not supported on this platform" → m_mysid_counters_supported = false
# このログが出ない → 対応プラットフォームとして初期化完了

# FlexCounter モード確認 (traditional か否か)
ps aux | grep orchagent | grep -o '\-c [a-z]*'
```
