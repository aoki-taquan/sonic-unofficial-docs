# pfcwd-state 書込み順依存 (Phase B)

## ソース
- sonic-swss/orchagent/pfcwdorch.cpp (master)
- sonic-swss/orchagent/pfcactionhandler.cpp (master)

## 前提条件: allPortsReady() ガード

`doTask()` は `gPortsOrch->allPortsReady()` が false の間は即 return する。
pfcwdorch.cpp:68-70 が該当箇所。ポート初期化完了前は PFC_WD テーブルの
処理がすべてブロックされる。CONFIG_DB への書き込みは受け付けるが、
orchagent が処理するのはポート初期化完了後。

## PORT が PortsOrch に存在しなければならない

`createEntry()` で `gPortsOrch->getPort(key, port)` が失敗すると
`task_invalid_entry` を返してスキップ。PFC_WD|<port> の SET より先に
PORT_TABLE|<port> がポート初期化済みである必要がある。

## pfcMask (PFC 有効 TC) が確定してから registerInWdDb() が実行される

`registerInWdDb()` は `gPortsOrch->getPortPfcWatchdogStatus()` で PFC
有効マスクを取得し、lossless TC が 0 個なら false を返してスキップ。
PORT_QOS_MAP や QUEUE テーブルが PortsOrch に反映される前に PFC_WD が
書き込まれても、losslessTc が空になり COUNTERS_DB への書き込みは行われない。

## FlexCounter 登録は COUNTERS_DB 書き込みと同時

`registerInWdDb()` は COUNTERS_DB への `PFC_WD_*` 書き込みと
FlexCounter の `setCounterIdList()` をシリアルに実行する。
COUNTERS_DB エントリが存在するタイミングで FlexCounter ポーリングも開始される。
