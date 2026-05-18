# stp-state ordering (Phase B) — 調査メモ

## 対象ページ
`docs/reference/config-db/stp-state.md`

## 要約
STATE_DB `STP_TABLE` は orchagent (`StpOrch`) が起動時の SAI 属性取得成功時に 1 回だけ書き込む。stpmgrd (`StpMgr`) は 60 秒のポーリングで読み取り、タイムアウト時はフォールバック値 255 を使用する。書き込みは起動時の 1 回のみで動的更新なし。

## 根拠コード

### orchagent 側 — stporch.cpp

```
StpOrch コンストラクタ (stporch.cpp:17-43):
  sai_switch_api->get_switch_attribute(gSwitchId, 2, attrs)
    - attrs[0]: SAI_SWITCH_ATTR_DEFAULT_STP_INST_ID
    - attrs[1]: SAI_SWITCH_ATTR_MAX_STP_INSTANCE
  if (status == SAI_STATUS_SUCCESS):
    updateMaxStpInstance(attrs[1].value.u32)
      → m_maxStpInstance = u32 - 1
      → m_stpTable->set("GLOBAL", [("max_stp_inst", str(m_maxStpInstance))])
  else:
    STATE_DB 書き込みなし

updateMaxStpInstance は他の箇所からは呼ばれていない（コンストラクタのみ）
```

### stpmgrd 側 — stpmgr.cpp

```
StpMgr::getStpMaxInstances() (stpmgr.cpp:1381-1413):
  max_delay = 60
  while(max_delay):
    if m_stateStpTable.get("GLOBAL", vmEntry):
      max_stp_instances = vmEntry["max_stp_inst"]
      break
    sleep(1)
    max_delay--
  if max_stp_instances == 0:
    max_stp_instances = STP_DEFAULT_MAX_INSTANCES  # = 255 (stpmgr.h:38)
  return max_stp_instances
```

## 依存関係
1. orchagent (StpOrch) の起動 → SAI 取得成功 → STATE_DB 書き込み: 先行必須
2. SAI 取得失敗時: STATE_DB 未書き込み → stpmgrd 60 秒ポーリングタイムアウト → フォールバック 255
3. 書き込みは起動時 1 回のみ: 実行中の再更新なし
