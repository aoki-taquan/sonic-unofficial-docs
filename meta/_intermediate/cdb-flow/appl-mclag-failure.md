# appl-mclag — Phase D 失敗挙動 中間調査

対象: `docs/reference/config-db/appl-mclag.md` (APPL_DB MCLAG/ICCP 関連テーブル群)

ソース ref:
- sonic-swss `mclagsyncd/mclaglink.cpp` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`
- sonic-swss `mclagsyncd/mclagsyncd.cpp` @ 同上
- sonic-buildimage `src/iccpd/src/iccp_csm.c`, `src/iccpd/include/scheduler.h` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`

## スキャン方法

```bash
grep -n -E 'throw|MclagConnectionClosed|SWSS_LOG_ERROR|SWSS_LOG_WARN|return;|exit|abort' \
  .cache/sonic-sources/sonic-swss/mclagsyncd/mclaglink.cpp
grep -n -E 'catch|exit|return' \
  .cache/sonic-sources/sonic-swss/mclagsyncd/mclagsyncd.cpp
```

## 失敗パス一覧

### 1. ICCP セッション切断 (read EOF)

- 箇所: `mclaglink.cpp:1883-1885` (`readData()`)
- トリガー: `::read(m_connection_socket, ...)` が `0` を返す (peer close)
- 動作: `throw MclagConnectionClosedException()`
- 捕捉: `mclagsyncd.cpp:112-115` の `catch (MclagLink::MclagConnectionClosedException&)`
- 結果:
  - `MclagLink` インスタンス破棄 → server socket close、APPL_DB writer (`ProducerStateTable`) 破棄
  - 外側 `while(1)` で `MclagLink` を再生成し `accept()` を再呼び出し（**明示 sleep / backoff 無し**、即時 retry）
  - 既に書込済みの APPL_DB エントリは **delete されず保持**（特に `ISOLATION_GROUP_TABLE` は `is_iccp_up == false` 時に `del("MCLAG_ISO_GRP")` するロジックがあるが、これは iccpd からの空 dst port メッセージで駆動されるため、TCP 切断のみでは発火しない）
- retry: あり (無限・即時)

### 2. read システムエラー / 不正メッセージ

- 箇所: `mclaglink.cpp:1886-1887` (`read < 0`)、`mclaglink.cpp:1901-1902` (`!mclag_msg_ok`)
- 動作: `throw system_error(...)` (`bad_message` または `errno`)
- 捕捉: `mclagsyncd.cpp:116-120` `catch (const exception&)` → **`return 0`** (デーモン終了)
- 結果: mclagsyncd プロセス終了。supervisord により再起動される（docker レベル）
- retry: プロセス再起動 (supervisord 依存)

### 3. iccpd 向け write のバッファフル / write 失敗

- 箇所:
  - `mclaglink.cpp:589-594` `mclagsyncdSendFdbEntries` (中間 flush)
  - `mclaglink.cpp:617-620` 同 (末尾 flush)
  - `mclaglink.cpp:870-874`, `:897-900` `mclagsyncdSendMclagDomainCfg`
  - `mclaglink.cpp:1057-1061`, `:1081-1084` `mclagsyncdSendMclagIfaceCfg`
  - `mclaglink.cpp:1150-1154`, `:1175-1178` `mclagsyncdSendMclagUniqueIpCfg`
  - `mclaglink.cpp:1256-1260`, `:1280-1283` VLAN member updates
- 動作: `SWSS_LOG_ERROR("... write to m_connection_socket failed")` のみ。throw も return も無く処理続行
- 結果: iccpd への通知が **欠落**（APPL_DB / STATE_DB 側の書込整合は次回イベントまで非同期に乖離）
- retry: なし（イベント駆動なので次の CONFIG_DB / STATE_DB 更新で再送される可能性あり）

### 4. 無効な op_type / 不明パラメータ (iccpd → mclagsyncd)

- 箇所例: `mclaglink.cpp:1302-1303` (`mclagsyncdSetTrafficDisable`), `:1348` (`mclagsyncdSetIccpState`), `:1363` (`mlag_id` 不正), `:1404`, `:1419`, `:1452`, `:1466`, `:1498`, `:1575`, `:1590`, `:1625`, `:1639`, `:1678`, `:1691`, `:1725`, `:1738`
- 動作: `SWSS_LOG_ERROR("Invalid option type %u")` / `SWSS_LOG_ERROR("Invalid parameter ...")` → `return`
- 結果: 当該メッセージのみスキップ。APPL_DB / STATE_DB 書込は発生しない。**他のメッセージ処理には影響しない**
- retry: なし（iccpd が再送するまで待つ）

### 5. CONFIG_DB の system MAC 未取得

- 箇所: `mclaglink.cpp:126-128` (`mclagsyncdFetchSystemMacFromConfigdb`)
- 動作: `DEVICE_METADATA|localhost` の `mac` が無い → `SWSS_LOG_ERROR` → `return`
- 結果: `m_system_mac` 未初期化（空文字列）のまま `accept()` 経路へ。後続 iccpd 通知時に空 MAC を送る
- retry: なし（次の outer-loop で再 fetch される）

### 6. setFdbEntry の不明 type

- 箇所: `mclaglink.cpp:487-492`
- 動作: `MCLAG_FDB_TYPE_STATIC / DYNAMIC / DYNAMIC_LOCAL` 以外は `fdb.type` が空文字列のまま書き込まれる（throw 無し）
- 結果: APPL_DB の `MCLAG_FDB_TABLE|VlanX:MAC` に `type=""` が登録 → fdborch 側で **invalid type 扱い**（fdborch の `fdbAttrCallback` で reject されるが本ページ範囲外）
- retry: なし

### 7. port 未準備（fdborch 側の retry）

- 箇所: 本ファイル範囲外。`mclagsyncd` は port 存在チェックを **行わず** APPL_DB に書く
- fdborch 側 (`fdborch.cpp`) で port が `m_portsOrch->getPort()` で取得できない場合 `task_need_retry` で次回 `doTask()` まで保留
- 本ページの mclagsyncd 視点では「書いた後の結末」だけが該当: APPL_DB エントリは残り続け、port 準備完了後に成功反映される
- retry: あり（fdborch 側 1 秒間隔で SELECT_TIMEOUT 駆動）

### 8. SAI 書込失敗（下流 orch）

- 箇所: 本ページの mclagsyncd は SAI を直接呼ばない (Phase F で確認済み)。APPL_DB 経由で `isolationGroupOrch` / `fdborch` / `aclOrch` / `portOrch` / `intfOrch` / `lagOrch` が SAI を叩く
- 失敗時挙動:
  - `isolationGroupOrch::createIsolationGroup()` で SAI fail → `task_failed` → orchagent 該当 doTask 停止
  - `fdborch` の MCLAG_FDB_TABLE 反映 SAI fail → `task_need_retry`（恒久エラーは `task_failed`）
- mclagsyncd 側にはフィードバックされない (一方向の write-only)
- retry: 各 orch 依存

### 9. accept / socket / bind 失敗

- 箇所: `mclaglink.cpp:1755-1786`, `:1853-1854`
- 動作: `throw system_error(errno, system_category())`
- 結果: `mclagsyncd.cpp` の outer `catch (const exception&)` → `return 0` でデーモン終了 → supervisord 再起動
- retry: プロセス再起動

## STATE_DB / ERROR_TABLE への記録

mclagsyncd 自身は失敗を `STATE_DB` の `ERROR_*` 系には書かない。`STATE_MCLAG_TABLE` の `oper_status` が `down` になるのは iccpd から `MCLAG_MSG_TYPE_SET_ICCP_STATE` で `down` を受信した場合のみ。

ログは `syslog` (`SWSS_LOG_ERROR` / `SWSS_LOG_WARN`) に出る。

```bash
journalctl -u mclag | grep -i mclagsyncd
docker logs mclag 2>&1 | grep -iE 'invalid|failed|exception'
```

## 確認手順

1. ICCP 切断: `docker exec mclag pkill iccpd` → `mclagsyncd` ログに `Connection lost, reconnecting...` が出ること
2. iccpd 再起動後 ISOLATION_GROUP / LAG / PORT エントリが再投入されることを `redis-cli -n 0 KEYS 'ISOLATION_GROUP_TABLE*'` で確認
3. SAI 書込失敗のシミュレーションは下流 orchagent 側でテストする（本ページ範囲外）
