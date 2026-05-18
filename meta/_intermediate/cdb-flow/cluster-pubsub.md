# cluster フィールド — 通信メカニズム (Phase G) 調査メモ

調査日: 2026-05-18
対象: DEVICE_METADATA|localhost.cluster / DEVICE_NEIGHBOR_METADATA|<device>.cluster

## 調査範囲

- `sonic-buildimage/src/sonic-config-engine/minigraph.py`
- `sonic-swss/cfgmgr/buffermgr.cpp` / `buffermgrdyn.cpp`
- `sonic-swss/cfgmgr/buffermgrd.cpp`
- `sonic-swss/cfgmgr/vlanmgrd.cpp`, `teammgr.cpp`, `nbrmgr.cpp`, `intfmgr.cpp`, `stpmgrd.cpp`, `vxlanmgrd.cpp`
- `sonic-swss/orchagent/` (全 .cpp grep)

## 結論: Producer 1 名・Consumer 0 名

`cluster` フィールドを**書く (Producer)** コンポーネントは 1 つのみ:
- `sonic-cfggen` + `minigraph.py` — 起動時に minigraph XML の `<ClusterName>` から CONFIG_DB へ直接 `HSET` で書き込む

**購読 (Consumer / Subscriber) するランタイムデーモンは存在しない**:

- `BufferMgr` (`buffermgr.cpp:373-408`) は DEVICE_METADATA を SubscriberStateTable で購読するが、参照するのは `buffer_model` フィールドのみ。`cluster` フィールドは完全に無視される。
- `BufferMgrDyn` (`buffermgrdyn.cpp:87`) は起動時に `hget("localhost", "platform", ...)` で platform フィールドを 1 回だけ読む。cluster は参照しない。
- `VlanMgr`, `TeamMgr`, `NbrMgr`, `IntfMgr`, `StpMgr`, `VxlanMgr` は DEVICE_METADATA のうち `mac`, `type`, `hostname`, `hwsku` 等を参照するが、`cluster` は一切参照しない。
- sonic-swss/orchagent/ 全体で "cluster" を grep するとコメント 1 件 (DASH ENI コメント) のみ。フィールド参照なし。

## 通信チャンネルの確認

`DEVICE_METADATA` は CONFIG_DB (dbId=4) テーブル。
`sonic-cfggen` は Redis `HSET` を通じて直接書き込む（ProducerStateTable 経由ではない）。
したがって keyspace 通知は発生するが、実際にこの通知を受信して `cluster` フィールドを処理するデーモンは存在しない。

`DEVICE_NEIGHBOR_METADATA` も同様。minigraph.py が書き込むが、读み出すランタイムデーモンは存在しない（bgpcfgd は `type` フィールドのみ参照）。

## Evidence リスト

- `minigraph.py:2170-2172` — DEVICE_METADATA|localhost.cluster 書き込み
- `minigraph.py:662-668, 806-811` — DEVICE_NEIGHBOR_METADATA|<dev>.cluster 書き込み
- `buffermgr.cpp:373-408` — doBufferMetaTask は `buffer_model` のみ参照
- `buffermgrdyn.cpp:87` — `hget("localhost", "platform", ...)` のみ
- sonic-swss 全体 grep: "cluster" ヒット 1 件 (DASH ENI コメント行のみ)
