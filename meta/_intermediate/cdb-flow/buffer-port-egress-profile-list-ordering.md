# BUFFER_PORT_EGRESS_PROFILE_LIST — 書込順依存 (Phase B)

## ソース

- `sonic-swss/cfgmgr/buffermgrdyn.cpp` L3275–3300 (`checkBufferProfileDirection`)
- `sonic-swss/orchagent/bufferorch.cpp` L1869–1877, L1950–1958 (`processEgressBufferProfileList`)

## 検出した順序依存

### 依存 1: BUFFER_PROFILE 先行 (dynamic model)

`buffermgrdyn.cpp:checkBufferProfileDirection` は `profile_list` の各プロファイルを `m_bufferProfileLookup` で検索する。
プロファイルが未登録の場合は `task_need_retry` を返しエントリを保留する。

```
BUFFER_PROFILE が先に CONFIG_DB に書き込まれ m_bufferProfileLookup に登録されている
  → BUFFER_PORT_EGRESS_PROFILE_LIST SET 成功
BUFFER_PROFILE が未登録
  → task_need_retry → SWSS_LOG_INFO("Profile %s doesn't exist, need retry")
```

evidence: `buffermgrdyn.cpp:3282-3287`

### 依存 2: BUFFER_PROFILE 先行 (orchagent 段)

`bufferorch.cpp:processEgressBufferProfileList` は `resolveFieldRefArray` でプロファイル OID を解決する。
参照先 BUFFER_PROFILE が APPL_DB に未着の場合 `task_need_retry` を返す。

evidence: `bufferorch.cpp:1869-1877`

### 依存 3: PORT 先行 (orchagent 段)

同関数の末尾で `gPortsOrch->getPort(port_name, port)` を呼び出す。
ポートが PortsOrch のマップに存在しない場合は `task_invalid_entry` を返す（retry なし）。

```
PORT が portsorch に登録済み
  → BUFFER_PORT_EGRESS_PROFILE_LIST SAI 設定成功
PORT が未登録
  → task_invalid_entry（再試行なし）
```

evidence: `bufferorch.cpp:1950-1957`

## 書込順序まとめ

```
1. BUFFER_POOL
2. BUFFER_PROFILE  ← egress 方向のプロファイルが m_bufferProfileLookup に登録される
3. PORT            ← PortsOrch に登録される
4. BUFFER_PORT_EGRESS_PROFILE_LIST  ← 上記 2 件が揃って初めて SAI 適用
```

BUFFER_PROFILE 未到着 → `task_need_retry`（自動リトライ）
PORT 未到着 → `task_invalid_entry`（リトライなし、エントリ破棄）
