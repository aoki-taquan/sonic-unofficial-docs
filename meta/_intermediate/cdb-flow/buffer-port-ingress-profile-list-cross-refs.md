# BUFFER_PORT_INGRESS_PROFILE_LIST — Phase C: 暗黙参照テーブル分析 (cross-refs)

対象ドキュメント: `docs/reference/config-db/buffer-port-ingress-profile-list.md`
解析日: 2026-05-16
根拠ソース:
- `sonic-net/sonic-swss/cfgmgr/buffermgrdyn.cpp`
- `sonic-net/sonic-swss/orchagent/bufferorch.cpp`

---

## 目的

`BUFFER_PORT_INGRESS_PROFILE_LIST` エントリが CONFIG_DB に書かれたとき、`buffermgrd` および `BufferOrch` が**暗黙的に**参照・依存する他テーブルを列挙する。YANG 定義では leafref として明示されるが、実装側ではコード内の lookup / resolve で処理されるため、「コード由来の暗黙参照」を記録する。

---

## 1. BUFFER_PROFILE テーブル (暗黙 leafref)

### 参照箇所

**buffermgrdyn.cpp**:

```cpp
// L3280-3285: profile_list 内の各プロファイル名を m_bufferProfileLookup で解決
auto profileSearchRef = m_bufferProfileLookup.find(profileName);
if (profileSearchRef == m_bufferProfileLookup.end())
{
    SWSS_LOG_INFO("Profile %s doesn't exist, need retry", profileName.c_str());
    return task_process_status::task_need_retry;
}
```

**bufferorch.cpp**:

```cpp
// L1683-1688: resolveFieldRefArray で APPL_DB の BUFFER_PROFILE テーブルを参照
ref_resolve_status resolve_status = resolveFieldRefArray(m_buffer_type_maps, buffer_profile_list_field_name,
                                                         buffer_to_ref_table_map.at(buffer_profile_list_field_name), tuple,
                                                         profile_list, profile_name_list);
if (ref_resolve_status::success != resolve_status)
{
    if(ref_resolve_status::not_resolved == resolve_status)
    {
        SWSS_LOG_INFO("Missing or invalid ingress buffer profile reference specified for:%s", key.c_str());
        return task_process_status::task_need_retry;
    }
    ...
}
```

### 依存内容

| 参照元フィールド | 参照先テーブル | 参照先キー形式 | 解決主体 | 未解決時の挙動 |
|---|---|---|---|---|
| `profile_list` (各要素) | `BUFFER_PROFILE` | `BUFFER_PROFILE\|<name>` | `buffermgrd` の `m_bufferProfileLookup` | `task_need_retry`（silent retry） |
| `profile_list` (各要素) | APPL_DB `BUFFER_PROFILE_TABLE` | `BUFFER_PROFILE_TABLE:<name>` | `BufferOrch` の `resolveFieldRefArray` | `task_need_retry` |

### 特記事項

- `profile_list` に指定したプロファイルの `direction` が `ingress` でなければ `task_failed`（egress プロファイル混入不可）— `buffermgrdyn.cpp:3289-3296`
- `packet_discard_action=trim` のプロファイルは `BufferOrch` が拒否（`bufferorch.cpp:1725-1731`）

---

## 2. BUFFER_POOL テーブル (暗黙 ingress 系 pool 依存)

### 参照箇所

**buffermgrdyn.cpp**:

```cpp
// L3408-3414: m_bufferPoolReady フラグチェック
if (!m_bufferPoolReady)
{
    const auto &direction = m_bufferDirectionNames[dir];
    SWSS_LOG_NOTICE("Buffer pools are not ready when configuring buffer %s profile list %s, pending",
                    direction.c_str(), key.c_str());
    m_bufferObjectsPending = true;
    return task_process_status::task_success;
}
```

**buffermgrdyn.cpp** (zero profile 構築):

```cpp
// L1185-1188: zero profile が存在しないプールはスキップ（admin-down 代替処理内）
```

### 依存内容

| 参照元の状態 | 参照先テーブル | 依存内容 | 解決主体 | 未解決時の挙動 |
|---|---|---|---|---|
| テーブルへの SET 処理時 | `BUFFER_POOL` | `m_bufferPoolReady == true` (ingress pool 全ロード完了) | `buffermgrd` | APPL_DB 書き込みを pending、BUFFER_POOL 完了後自動再処理 |
| admin-down ポートの zero profile 置換時 | `BUFFER_POOL` | ingress 系プールに対応する zero profile の存在 | `buffermgrd` の `constructZeroProfileListFromNormalProfileList` | 当該プールをスキップ（WARN ログのみ）— 部分置換 |

---

## 3. PORT テーブル (暗黙 leafref)

### 参照箇所

**bufferorch.cpp**:

```cpp
// L1762-1765: PortsOrch のポートマップで key をルックアップ
// port_names = tokenize(key, list_item_delimiter)
// 各 port_name に対して gPortsOrch->getPort() 呼び出し
```

**buffermgrdyn.cpp**:

```cpp
// L3509-3513: キー（ポート名）が空文字なら task_invalid_entry
// L3536-3547: カンマ区切りポート列挙時に各ポート名に対して handleSingleBufferPortIngressProfileListEntry を呼び出し
```

### 依存内容

| 参照元フィールド | 参照先テーブル | 参照先キー形式 | 解決主体 | 未解決時の挙動 |
|---|---|---|---|---|
| キー `<port>` (ポート名) | `PORT` | `PORT\|<port>` | `BufferOrch` の PortsOrch ポートマップ | `task_invalid_entry`（エントリ消去、永続エラー） |
| キー `<port>` (ポート名) | `PORT` | `PORT\|<port>` | `buffermgrd` の `m_portInfoLookup` | `task_invalid_entry`（空文字キー）または admin-down 判定 |

### 特記事項

- PortsOrch が未登録のポートは `task_invalid_entry` を返しエントリを消去する（バッファ系テーブルは PORT 先行必須）。
- `m_portInfoLookup[port].state == PORT_ADMIN_DOWN` のとき、通常 profile_list の代わりに zero profile list を APPL_DB に書き込む（`buffermgrdyn.cpp:3418-3438`）。

---

## まとめ — `buffer-port-ingress-profile-list.md` cross-refs 記載対象

| カテゴリ | 参照元フィールド / 状態 | 参照先テーブル | 参照解決主体 |
|---|---|---|---|
| BUFFER_PROFILE 暗黙 leafref | `profile_list` 各要素 | `BUFFER_PROFILE` / APPL_DB `BUFFER_PROFILE_TABLE` | `buffermgrd` `m_bufferProfileLookup` + `BufferOrch` `resolveFieldRefArray` |
| BUFFER_POOL ingress 系 pool 依存 | SET 処理時の `m_bufferPoolReady` チェック | `BUFFER_POOL` (ingress 系全プール) | `buffermgrd` |
| PORT 暗黙 leafref | キー `<port>` | `PORT` | `BufferOrch` PortsOrch + `buffermgrd` `m_portInfoLookup` |

## 検証コマンド

```bash
grep -n "m_bufferProfileLookup\|task_need_retry\|profile_list" \
    .cache/sonic-sources/sonic-swss/cfgmgr/buffermgrdyn.cpp | grep -v "^.*//.*$" | head -20

grep -n "resolveFieldRefArray\|processIngressBufferProfileList\|isTrimmingEligible\|m_bufferPoolReady" \
    .cache/sonic-sources/sonic-swss/orchagent/bufferorch.cpp | head -20
```

このスキャン結果から派生して `docs/reference/config-db/buffer-port-ingress-profile-list.md` の `<!-- cross-refs -->` ブロックを生成する。
