# bfd-state — Phase D (失敗挙動) 中間調査メモ

対象ページ: `docs/reference/config-db/bfd-state.md`
ソース: `.cache/sonic-sources/sonic-swss/orchagent/bfdorch.cpp` (HEAD, 841 行)

## 1. STATE_DB 書き手は `bfdorch` 単独

```bash
grep -n "m_stateBfdSessionTable\|m_stateSoftBfdSessionTable" .cache/sonic-sources/sonic-swss/orchagent/bfdorch.cpp
```

- `m_stateBfdSessionTable` (`swss::Table` 値型): L59 メンバ初期化、L75-78 cleanup、L252 hset、L565 set、L629 del
- `m_stateSoftBfdSessionTable` (`unique_ptr<swss::Table>`): L68 make_unique、L81-84 cleanup、L136/L185/L708/L714 set/del

`swss::Table::set/hset/del` は戻り値なし（void）。Redis I/O 失敗時は `DBConnector` レイヤから `system_error` が伝播し、上位で catch されない → orchagent プロセス abort → systemd 再起動 → cleanup → 再作成。

## 2. SAI セッション作成失敗経路 (`create_bfd_session` L305-575)

```cpp
// L547-562
sai_status_t status = sai_bfd_api->create_bfd_session(&bfd_session_id, gSwitchId, ...);
if (status != SAI_STATUS_SUCCESS)
{
    status = retry_create_bfd_session(bfd_session_id, attrs);
}
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to create bfd session %s, rv:%d", key.c_str(), status);
    task_process_status handle_status = handleSaiCreateStatus(SAI_API_BFD, status);
    if (handle_status != task_success)
    {
        return parseHandleSaiStatusFailure(handle_status);
    }
}

// L565-568
m_stateBfdSessionTable.set(state_db_key, fvVector);
bfd_session_map[key] = bfd_session_id;
bfd_session_lookup[bfd_session_id] = {state_db_key, SAI_BFD_SESSION_STATE_DOWN};
```

- リトライ: `retry_create_bfd_session()` L583-606 はソース UDP ポート `BFD_SRCPORTINIT (49152)` から `BFD_SRCPORTMAX (65535)` 範囲をスキャンしつつ `SAI_BFD_SESSION_ATTR_UDP_SRC_PORT` を変えて再 create。SAI が `SAI_STATUS_ITEM_NOT_FOUND` 等を返した場合のみ。
- `handleSaiCreateStatus == task_success` が返ると `if` を抜けて L565 `m_stateBfdSessionTable.set()` に到達するが、`bfd_session_id` が `SAI_NULL_OBJECT_ID` のまま記録される可能性 → 後続 SAI 通知時に `bfd_session_lookup` 検索ミス。

## 3. SAI セッション削除失敗経路 (`remove_bfd_session` L609-633)

```cpp
if (bfd_session_map.find(key) == bfd_session_map.end()) {
    SWSS_LOG_ERROR("BFD session for %s does not exist", key.c_str());
    return true;  // ← 成功扱い。STATE_DB 操作なし
}
sai_status_t status = sai_bfd_api->remove_bfd_session(bfd_session_id);
if (status != SAI_STATUS_SUCCESS) {
    SWSS_LOG_ERROR("Failed to remove bfd session %s, rv:%d", key.c_str(), status);
    task_process_status handle_status = handleSaiRemoveStatus(SAI_API_BFD, status);
    if (handle_status != task_success) {
        return parseHandleSaiStatusFailure(handle_status);  // ← STATE_DB del 未到達
    }
}
m_stateBfdSessionTable.del(bfd_session_lookup[bfd_session_id].peer);
```

`bfd_session_map` には key 残留。`task_need_retry` の場合は `doTask()` 上位で `it++` され次サイクル再試行。

## 4. SAI 通知ハンドラ登録 (`register_bfd_state_change_notification` L271-303)

```cpp
status = sai_query_attribute_capability(...);
if (status != SAI_STATUS_SUCCESS) { LOG_ERROR; return false; }       // L273-284
if (!capability.set_implemented) { LOG_ERROR; return false; }         // L286-290
attr.value.ptr = (void *)on_bfd_session_state_change;
status = sai_switch_api->set_switch_attribute(gSwitchId, &attr);
if (status != SAI_STATUS_SUCCESS) { LOG_ERROR; return false; }       // L296-301
```

呼び出し元は `BfdOrch` コンストラクタ周辺で、戻り値の失敗扱いはプロセス abort につながらない（observable 動作: state="Down" 固着）。

## 5. SAI 通知受信時 lookup (`doTask(NotificationConsumer)` L220-268)

```cpp
sai_object_id_t id = bfdSessionState[i].bfd_session_id;
sai_bfd_session_state_t state = bfdSessionState[i].session_state;
SWSS_LOG_INFO("... state: %s", session_state_lookup.at(state).c_str());  // ← .at() で範囲外なら例外
if (state != bfd_session_lookup[id].state)                                // ← operator[] が挿入
{
    auto key = bfd_session_lookup[id].peer;                               // ← 未知 id なら空文字列
    m_stateBfdSessionTable.hset(key, "state", session_state_lookup.at(state));
    ...
    bfd_session_lookup[id].state = state;
}
```

`bfd_session_lookup` は `std::map<sai_object_id_t, struct {string peer; sai_bfd_session_state_t state;}>`（推定: ヘッダで定義）。`operator[]` でデフォルト構築されると `peer=""`, `state=0=SAI_BFD_SESSION_STATE_ADMIN_DOWN`。SAI 通知が `_DOWN`/`_UP` 等で来ると差分判定が通り、空 peer での `hset` が発火する可能性。

## 6. 入力バリデーション失敗一覧 (`create_bfd_session` 前半 L305-528)

| 行 | 条件 | ログ |
|---|---|---|
| L316-320 | 既存 key の再 SET | "BFD session for %s already exists" |
| L323-326 | VRF パース失敗 | "Failed to parse key %s, no vrf is given" |
| L330-333 | ifname パース失敗 | "Failed to parse key %s, no ifname is given" |
| L383-387 | type 不正 | "Invalid BFD session type %s" |
| L404-407 | 未対応属性 | "Unsupported BFD attribute %s" |
| L409-413 | `local_addr` 欠落 | "Failed to create BFD session %s because source IP is not provided" |
| L485-489 | ポート解決失敗 | "Failed to locate port %s" |
| L491-495 | `dst_mac` 必須なのに未指定 | "destination MAC address required when hardware lookup not valid" |
| L497-502 | hardware_lookup_valid=false で非 default VRF | "vrf is not supported when hardware lookup not valid" |
| L522-528 | hardware_lookup_valid=true で dst_mac 指定 | "destination MAC address not supported when hardware lookup valid" |

すべて `return false` で `m_stateBfdSessionTable.set()` 未到達。`doTask()` 上位 (`L160 / L173`) で `it++` され次サイクル再試行（バリデーション失敗が直る見込みは低いが恒久スキップ機構はない）。

## 7. 起動時 cleanup (L74-86)

```cpp
m_stateBfdSessionTable.getKeys(keys);
for (auto& alias : keys) { m_stateBfdSessionTable.del(alias); }
m_stateSoftBfdSessionTable->getKeys(keys);
for (auto& alias : keys) { m_stateSoftBfdSessionTable->del(alias); }
```

`getKeys` / `del` の Redis I/O 例外は `try/catch` なし。失敗すれば `BfdOrch` コンストラクタ伝播 → orchdaemon 例外 → systemd 再起動。

## 8. Phase E 観測候補（次フェーズへの申し送り）

1. syslog で `"BFD register change notification not supported"` / `"Failed to register BFD notification handler"` の出現監視
2. `redis-cli -n 6 KEYS 'BFD_SESSION_TABLE|*'` で空 peer (`||` 連続) のキー検知
3. `state="Down"` のまま 10 分以上推移したセッションに対し `bfd_session_id` と SAI 側状態を `sai-redis` で突き合わせる手順
4. SAI 通知欠落時の自動回復は無いので、状態が乖離した場合は orchagent プロセス再起動（cleanup → 再 init）が事実上の唯一の手段
