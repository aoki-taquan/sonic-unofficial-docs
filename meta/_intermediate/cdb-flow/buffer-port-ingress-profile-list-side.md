# buffer-port-ingress-profile-list — Phase F: 副次 DB 書込調査

## 調査対象ソース

- `sonic-swss/cfgmgr/buffermgrdyn.cpp`
- `sonic-swss/orchagent/bufferorch.cpp`

## 副次 DB 書込の有無

### STATE_DB

`buffermgrdyn.cpp` は STATE_DB に BUFFER_POOL (`m_stateBufferPoolTable`) および BUFFER_PROFILE (`m_stateBufferProfileTable`) を書き込むが、BUFFER_PORT_INGRESS_PROFILE_LIST の処理パス (`handleBufferObjectTables` / `handleSingleBufferPortProfileListEntry`) では STATE_DB への書き込みは行わない。

STATE_DB は初期化時の `mmu_size` 読み取り (`L142`) および BUFFER_POOL/BUFFER_PROFILE の完了通知用途に限定される。

**結論: STATE_DB への副次書込なし（BUFFER_PORT_INGRESS_PROFILE_LIST ハンドラ経路）**

### APPL_STATE_DB

`buffermgrdyn.cpp` は APPL_STATE_DB に BUFFER_POOL (`m_applStateBufferPoolTable`) および BUFFER_PROFILE (`m_applStateBufferProfileTable`) を読み書きするが、いずれも BUFFER_POOL/BUFFER_PROFILE ハンドラ内のみ。BUFFER_PORT_INGRESS_PROFILE_LIST の処理経路には APPL_STATE_DB への書き込みコードは存在しない。

**結論: APPL_STATE_DB への副次書込なし**

### COUNTERS_DB

`bufferorch.cpp` は COUNTERS_DB に buffer pool watermark の name-map を書き込む (`m_counterNameMapUpdater`, `L55-56`, `L546`)。これは BUFFER_POOL の set/del 時に呼ばれる `saiObjectTypeProcessed` 経由であり、BUFFER_PORT_INGRESS_PROFILE_LIST ハンドラ (`processIngressBufferProfileList` / `processIngressBufferProfileListBulk`) からは呼ばれない。

**結論: COUNTERS_DB への副次書込なし（ingress profile list 経路）**

### FLEX_COUNTER_DB

`bufferorch.cpp` は buffer pool watermark 統計に FLEX_COUNTER_DB (`BUFFER_POOL_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP`) を使用するが、これも BUFFER_POOL ハンドラ内のみ。BUFFER_PORT_INGRESS_PROFILE_LIST のハンドラは SAI bulk API (`sai_port_api->set_ports_attribute`) を呼ぶのみで FLEX_COUNTER_DB には触れない。

**結論: FLEX_COUNTER_DB への副次書込なし**

## 根拠まとめ

| 副次 DB | 書込有無 | 根拠コード箇所 |
|--------|---------|--------------|
| STATE_DB | **なし** | `buffermgrdyn.cpp:313,361,887,920` — BUFFER_POOL/PROFILE ハンドラのみ |
| APPL_STATE_DB | **なし** | `buffermgrdyn.cpp:43-51` — 接続はあるが ingress list 経路に書込なし |
| COUNTERS_DB | **なし** | `bufferorch.cpp:55-56,546` — BUFFER_POOL watermark name-map のみ |
| FLEX_COUNTER_DB | **なし** | `bufferorch.cpp:247,337,344` — BUFFER_POOL watermark のみ |
