# APPL_DB FIXED_MIRROR_SESSION_TABLE — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-15 (q67-f-phaseD-appl-mirror)

ソース:
- `sonic-net/sonic-swss` `orchagent/p4orch/mirror_session_manager.cpp` / `.h` (master, ref `4305596156d70e9797e8a881b3d19b46de0bce0d`)
- `sonic-net/sonic-swss` `orchagent/mirrororch.cpp` (比較対象、master)

## 1. SET / DEL 失敗パス一覧

P4RT 経路の `MirrorSessionManager::drain()` / `processAddRequest()` / `processUpdateRequest()` /
`processDeleteRequest()` / `deserializeP4MirrorSessionAppDbEntry()` / `prepareSaiAttrs()` を全行精読
した。CONFIG_DB 側 `MirrorOrch` (`mirrororch.cpp`) との差異も併記する。

| # | トリガー | 検出箇所 | 結果 | retry / 救済 |
|---|---------|---------|------|------|
| 1 | APPL_DB key の JSON parse 例外 (`nlohmann::json::parse`) | `deserializeP4MirrorSessionAppDbEntry()` `mirror_session_manager.cpp:199-205` | `SWSS_RC_INVALID_PARAM`。`drain()` L77-86 で `m_publisher->publish()` 後 `break` で当該 drain 終了 | なし。P4RT クライアントが再投入必要 |
| 2 | `action != "mirror_as_ipv4_erspan"` | `deserializeP4MirrorSessionAppDbEntry()` `mirror_session_manager.cpp:307-313` | `SWSS_RC_INVALID_PARAM`。同上、結果通知後 drain `break` | なし (設計時制約) |
| 3 | 未知フィールド (controller_metadata 以外) | `deserializeP4MirrorSessionAppDbEntry()` `mirror_session_manager.cpp:315-319` | `SWSS_RC_INVALID_PARAM` | なし |
| 4 | `param/src_ip` / `param/dst_ip` パース失敗 (`swss::IpAddress` 例外) | 同 L229-253 | `SWSS_RC_INVALID_PARAM` | なし |
| 5 | `param/src_mac` / `param/dst_mac` パース失敗 (`swss::MacAddress` 例外) | 同 L255-279 | `SWSS_RC_INVALID_PARAM` | なし |
| 6 | `param/ttl` / `param/tos` パース失敗 (`std::stoul(value, 0, 16)` 例外) | 同 L281-305 | `SWSS_RC_INVALID_PARAM` | なし |
| 7 | `param/port` が PortsOrch 未登録 (`gPortsOrch->getPort()` false) — deserialize 段 | `deserializeP4MirrorSessionAppDbEntry()` L213-218 | `SWSS_RC_NOT_FOUND`。drain `break` で当該 drain 終了 | **なし** (P4RT クライアント側で再送)。CONFIG_DB 側 `MirrorOrch::doTask()` (`mirrororch.cpp:1567-1574`) の `allPortsReady()` ガード相当が**存在しない**。`m_entries` 滞留せず破棄される |
| 8 | `param/port` が非 PHY (LAG/VLAN) — deserialize 段 | 同 L219-225 | `SWSS_RC_INVALID_PARAM` | なし (設計制約。port 種別は alias で固定) |
| 9 | ADD 時の必須フィールド不足 (`has_port` / `has_src_ip` / `has_dst_ip` / `has_src_mac` / `has_dst_mac` / `has_ttl` / `has_tos` のいずれか false) | `processAddRequest()` L344-360 | `SWSS_RC_INVALID_PARAM`。`createMirrorSession()` を呼ばずに drain `break` | なし |
| 10 | ADD 時に既存 OID マッパに同 key 既存 (`existsOID` true) | `createMirrorSession()` L370-375 | `RETURN_INTERNAL_ERROR_AND_RAISE_CRITICAL`。**critical state 通知 + プロセス致命** (orchagent restart 必要レベル) | なし (内部不整合) |
| 11 | ADD 時 `prepareSaiAttrs()` の port 解決失敗 | `prepareSaiAttrs()` L122-129 | `SWSS_RC_NOT_FOUND`。`createMirrorSession()` 経由で drain `break` | なし。実際には #7 で先に弾かれるが冗長チェック |
| 12 | ADD 時 `prepareSaiAttrs()` の非 PHY 検出 | 同 L130-136 | `SWSS_RC_INVALID_PARAM` | なし (#8 と同じく冗長チェック) |
| 13 | SAI `create_mirror_session()` 失敗 (ADD) | `createMirrorSession()` L381-384 | `CHECK_ERROR_AND_LOG_AND_RETURN` マクロ経由で `SWSS_LOG_ERROR` + SAI status を ReturnCode に変換して return。ref count 加算 / m_p4OidMapper / m_mirrorSessionTable 更新は**行わない** | なし (P4RT 経路は Orch 共通 `m_toSync` 機構を使わない。ZMQ 応答のみ) |
| 14 | UPDATE 時 `existing_mirror_session_entry == nullptr` | `processUpdateRequest()` L406-409 | `RETURN_INTERNAL_ERROR_AND_RAISE_CRITICAL` | なし |
| 15 | UPDATE 時 OID マッパに無い (`existsOID` false) | 同 L410-415 | `RETURN_INTERNAL_ERROR_AND_RAISE_CRITICAL` | なし |
| 16 | UPDATE 時の中間で SAI set 失敗 (port / src_ip / dst_ip / src_mac / dst_mac / ttl / tos のいずれか) | `processUpdateRequest()` L422-465 + 各 `set*()` (L482-678) の `CHECK_ERROR_AND_LOG_AND_RETURN` | `update_fail_in_middle = true` で残りの SET をスキップ。**`setMirrorSessionEntry(before_update, existing)` で前状態に巻き戻し**を試みる (L467-477) | rollback あり。ただし rollback 自体が失敗するとさらに `SWSS_RAISE_CRITICAL_STATE` |
| 17 | UPDATE rollback (`setMirrorSessionEntry`) 失敗 | `processUpdateRequest()` L469-476 | `SWSS_RAISE_CRITICAL_STATE("Failed to recover ...")`。orchagent は critical state 通知し外部監視に escalate。**SAI 状態と内部キャッシュが乖離した不整合状態で継続** | なし (運用介入が必要) |
| 18 | UPDATE で `param/port` 切替時に新 port が PortsOrch 未登録 | `setPort()` L492-497 | `SWSS_RC_NOT_FOUND`。SAI 属性更新も ref count 移管も**行わず**旧 port を保持 | なし (P4RT クライアントが新 port 作成後に UPDATE を再送) |
| 19 | UPDATE で新 port が非 PHY | `setPort()` L498-504 | `SWSS_RC_INVALID_PARAM` | なし |
| 20 | UPDATE での SAI `set_mirror_session_attribute()` 失敗 (port/src_ip/dst_ip/src_mac/dst_mac/ttl/tos) | 各 `set*()` の `CHECK_ERROR_AND_LOG_AND_RETURN` (L511, L541, L567, L593, L619, L644, L669) | SAI status を ReturnCode に変換。呼出側 `processUpdateRequest` の rollback 経路 (#16) に合流 | rollback あり |
| 21 | DEL で内部テーブルに該当 key なし | `processDeleteRequest()` L737-743 | `SWSS_RC_NOT_FOUND`。drain `break`。冪等成功ではなく**失敗扱い** (CONFIG_DB 側 `MirrorOrch::deleteEntry()` `mirrororch.cpp:752-757` は `SWSS_LOG_NOTICE` のみで成功扱いに倒すのと対照的) | なし |
| 22 | DEL で `m_p4OidMapper->getRefCount()` 失敗 | `processDeleteRequest()` L746-751 | `RETURN_INTERNAL_ERROR_AND_RAISE_CRITICAL` | なし |
| 23 | DEL で ref_count > 0 (ACL_RULE 等から参照中) | `processDeleteRequest()` L752-757 | `SWSS_RC_IN_USE`。SAI 削除も内部テーブル削除も**行わない** | なし (参照側 ACL_RULE 先削除が必要)。CONFIG_DB 側は `MirrorOrch::isMirrorSessionInUse()` (`mirrororch.cpp` でセッション削除前にチェック) と類似 |
| 24 | DEL で SAI `remove_mirror_session()` 失敗 | `processDeleteRequest()` L760-762 | `CHECK_ERROR_AND_LOG_AND_RETURN` で `SWSS_LOG_ERROR` + SAI status return。ref count / OID マッパ / 内部テーブルは**未削除のまま** | なし |
| 25 | drain 中の不明 op (SET/DEL 以外) | `drain()` L106-109 | `SWSS_RC_INVALID_PARAM`。publish 後 `break` | なし |
| 26 | drain ループ内のエントリエラー (上記 1〜25 のいずれか) | `drain()` L111-116 | `m_publisher->publish()` で結果通知後 **`break`** で当該 drain ループを抜ける。残りの `m_entries` は `drainWithNotExecuted()` で「未実行」として publisher に返却 | なし。head-of-line blocking。後続も全て未処理に倒れる |

## 2. CONFIG_DB MirrorOrch との差異（救済機構の有無）

P4RT 経路は **Orch 共通の `m_toSync` 自動再試行機構を一切使わない**。`MirrorSessionManager` は
`Orch` 派生ではあるが、`drain()` 内で `m_entries` を `pop_front()` した時点で抜き取り、エラー時も
publisher で結果通知してそのまま破棄する。

CONFIG_DB 側 `MirrorOrch` (`mirrororch.cpp`) は以下のような救済機構を持つ:

| 救済機構 | CONFIG_DB MirrorOrch | P4RT MirrorSessionManager |
|---|---|---|
| `allPortsReady()` 前置 (`mirrororch.cpp:1567-1574`) | あり（PORT 初期化完了まで `doTask()` 全体スキップ） | **なし** (即 `SWSS_RC_NOT_FOUND` で失敗確定) |
| `task_need_retry` による `m_toSync` 残置 | あり（一時 SAI エラー等は次周回再試行） | **なし** (drain で `break`、未実行分は publisher 通知のみ) |
| `task_need_retry` による NEXTHOP/NEIGH/FDB 解決待ち | あり (`mirrororch.cpp:160-198, 760-808`、`SUBJECT_TYPE_*_CHANGE` observer で `updateSession()`) | **なし** (`dst_mac` を APPL_DB 必須フィールドとして直接受領する fail-fast 設計) |
| Policer 未準備時の `task_need_retry` (`mirrororch.cpp:432-443`) | あり (POLICER 先行強制) | **なし** (policer フィールドそのものが APPL_DB に存在しない) |
| SAI mirror_session リソース availability チェック (`mirrororch.cpp:357-379`) | あり (ADD 前に `sai_object_type_get_availability` 呼出、枯渇時は ADD スキップ) | **なし** (SAI create 失敗で初めて検出) |
| ingress/egress mirror ASIC capability チェック (`mirrororch.cpp:816-826`) | あり (bind 前に `SwitchOrch::isPortIngressMirrorSupported()` で fail-fast) | **なし** (P4RT は session 単体作成のみ。bind は ACL_RULE 側で行う) |

これにより、port readiness / policer 準備 / SAI 可用性 / neighbor 解決といった**動的な前提
条件未充足を P4RT 経路は recover できず**、すべて P4RT クライアント側の再送責務になる。

## 3. SAI 失敗の共通ハンドリング（`CHECK_ERROR_AND_LOG_AND_RETURN`）

`mirror_session_manager.cpp` の SAI 呼出は全て `CHECK_ERROR_AND_LOG_AND_RETURN` マクロ経由で
status を ReturnCode に変換し、`SWSS_LOG_ERROR` を出して呼出元に return する。Orch 基底クラスの
`handleSaiCreateStatus` / `handleSaiSetStatus` / `handleSaiRemoveStatus`（`task_need_retry` を返す
可能性のあるパス）は**使われていない**。

つまり SAI が `SAI_STATUS_NOT_EXECUTED` 等の一時エラーを返しても、`MirrorSessionManager` は
それを再試行可能と判断するパスを持たず、`m_publisher->publish()` でエラー status を P4RT に
返して終わる。**再送は P4RT クライアントの責務**。

恒久エラー（プロセス終了相当）に倒すパスも `MirrorSessionManager` には存在しない（`MirrorOrch`
側で `parseHandleSaiStatusFailure()` 経由の process abort 経路がある）が、内部不整合検出
（OID マッパとローカルテーブルの食い違い等）は `RETURN_INTERNAL_ERROR_AND_RAISE_CRITICAL` で
`SWSS_RAISE_CRITICAL_STATE` を発し、外部監視 (criticald) で再起動誘発される設計。

## 4. drain head-of-line blocking

```cpp
// mirror_session_manager.cpp:62-119  (要約)
while (!m_entries.empty()) {
    auto key_op_fvs_tuple = m_entries.front();
    m_entries.pop_front();
    ...
    m_publisher->publish(APP_P4RT_TABLE_NAME, kfvKey(...), kfvFieldsValues(...), status,
                         /*replace=*/true);
    if (!status.ok()) {
      break;     // <-- 最初の失敗で抜ける
    }
}
drainWithNotExecuted();   // 残りは「未実行」publish のみ
```

同一 drain ロット内で N 個の `FIXED_MIRROR_SESSION_TABLE` SET をバッチ投入し、k 番目で失敗すると
(k+1)〜N 番目は**実行されず**、未実行 publish が返るだけ。これは CONFIG_DB 側 `MirrorOrch::doTask()`
(`mirrororch.cpp:1576-1607`) が各エントリを独立に `it++` で進めるのと異なり、**P4RT は順序保証
（orderedQueue=true）と引換えに head-of-line blocking を選択している**設計。

→ 含意: P4RT クライアントは「失敗したロット」を識別したら、続く未実行エントリも個別に再送
する必要がある。

## 5. silent ignore は存在しない（CONFIG_DB との差異）

CONFIG_DB `FdbOrch` や `MirrorOrch` のような「冪等 DEL = 成功扱い」「origin 不一致 = silent
ignore」のパスは `MirrorSessionManager` には**存在しない**:

- DEL で内部テーブル不在 → `SWSS_RC_NOT_FOUND` (#21)
- 既存 ADD への重複 SET → `processUpdateRequest()` 経由で差分のみ SAI に反映（既存と同値なら各
  `set*()` 冒頭の早期 return (`if (new_x == existing->x) return ReturnCode();`) で no-op）
- ref_count > 0 での DEL → `SWSS_RC_IN_USE` (#23、明示的に失敗を返す)

すべてのエラーは publisher を通じて P4RT クライアントに通知される。

## 6. CRITICAL state を引き起こすパス（プロセス継続を諦める経路）

| パス | 箇所 | 影響 |
|---|---|---|
| ADD 時に既に OID マッパに同 key | `createMirrorSession()` L370-375 | `RETURN_INTERNAL_ERROR_AND_RAISE_CRITICAL` |
| UPDATE で `existing_mirror_session_entry == nullptr` | `processUpdateRequest()` L406-409 | 同上 |
| UPDATE で OID マッパに存在しない | 同 L410-415 | 同上 |
| UPDATE 中間失敗からの rollback 失敗 | 同 L469-476 | `SWSS_RAISE_CRITICAL_STATE`。SAI と内部キャッシュが乖離した不整合状態 |
| DEL で `getRefCount()` 失敗 | `processDeleteRequest()` L746-751 | `RETURN_INTERNAL_ERROR_AND_RAISE_CRITICAL` |

これらはいずれも「内部不整合の検出」であり、通常運用では発生しないことが期待される。発生した
場合は criticald が orchagent restart を発火させる前提。

## 7. 観測手段

```bash
# 失敗ログ抽出
docker logs swss 2>&1 | grep -iE 'MirrorSessionManager|mirror_session_manager|FIXED_MIRROR_SESSION|Failed to (create|remove|set) (mirror|new) '

# P4RT 応答キュー (ResponsePublisher → ZmqServer 経由)
# P4RT クライアント側で status (SWSS_RC_*) を観測

# CRITICAL state
docker logs swss 2>&1 | grep -iE 'CRITICAL|RaiseCritical|Failed to recover mirror session'

# ref_count 確認 (P4 OID マッパは redis に書かないため SAI ASIC_DB と内部状態のみ)
redis-cli -n 1 KEYS 'ASIC_STATE:SAI_OBJECT_TYPE_MIRROR_SESSION*'
```

`MirrorSessionManager` は STATE_DB に独自エラーテーブルを書かない。失敗の参照点は syslog と
P4RT 応答 status のみ。

## 8. まとめ — fail-fast 設計の含意

- P4RT 経路は **`m_toSync` 自動再試行を使わない fail-fast 設計**であり、port readiness /
  policer 準備 / neighbor 解決 / SAI 一時失敗のいずれも**自動回復しない**
- 失敗時の再送責務はすべて P4RT controller（典型的には `p4rt-server`）側にある
- バッチ投入では先頭失敗で残りも未実行になるため、controller は未実行 publish を受けたら
  個別再送する設計が必須
- 内部不整合検出時は CRITICAL state で orchagent 再起動を促す
