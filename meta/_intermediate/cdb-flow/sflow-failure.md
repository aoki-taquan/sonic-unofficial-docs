# SFLOW — Phase D 失敗挙動 証跡

## ソース
- `sonic-swss/cfgmgr/sflowmgr.cpp`
- `sonic-swss/orchagent/sfloworch.cpp`

## 抽出した失敗挙動

### 1. PORT_TABLE consumer 未初期化 (PORT 未解決 → retry)

`readPortConfig()` 呼び出し時に `m_consumerMap` に `CFG_PORT_TABLE_NAME` が存在しない場合、
`SWSS_LOG_ERROR("Consumer object for PORT_TABLE not found")` を出力してリターンする。
per-port サンプリングレートの速度依存デフォルト算出が不可能となり、
`findSamplingRate()` は `ERROR_SPEED` を返し続ける。

```
sflowmgr.cpp:34  SWSS_LOG_ERROR("Consumer object for PORT_TABLE not found");
```

### 2. findSamplingRate — ポート名未登録 (不正 sample_rate 相当)

`findSamplingRate(alias)` 呼び出し時に `m_sflowPortConfMap` にエントリが存在しない場合、
`SWSS_LOG_ERROR("%s not found in port configuration map", alias.c_str())` を出力し `ERROR_SPEED` を返す。
その値が APP_DB に書き込まれると `sflowExtractInfo()` で `rate=0` に落とされ、
`rate == 0` チェック (`if (rate == 0) { it++; continue; }`) によりセッション作成がスキップされる。
結果としてそのポートの sFlow セッションが作成されない。

```
sflowmgr.cpp:391  SWSS_LOG_ERROR("%s not found in port configuration map", alias.c_str());
sfloworch.cpp:275-278  if (fvValue(i) != "error") { rate = stoul(...); } else { rate = 0; }
sfloworch.cpp:411-414  if (rate == 0) { it++; continue; }
```

### 3. SAI samplepacket セッション作成失敗

`sai_samplepacket_api->create_samplepacket()` が `SAI_STATUS_SUCCESS` 以外を返した場合、
`SWSS_LOG_ERROR("Failed to create sample packet session with rate %d", rate)` を出力し、
`handleSaiCreateStatus` → `parseHandleSaiStatusFailure` の結果次第で `false` を返す。
呼び出し元 `doTask` では `it++; continue;` でそのエントリをリトライ対象に残す。

```
sfloworch.cpp:33  SWSS_LOG_ERROR("Failed to create sample packet session with rate %d", rate);
sfloworch.cpp:427-430  if (!sflowCreateSession(rate, session)) { it++; continue; }
```

### 4. SAI samplepacket セッション削除失敗 (クリーンアップ失敗)

レート変更時に古いセッションの `remove_samplepacket()` が失敗した場合、
`SWSS_LOG_ERROR("Failed to destroy sample packet session with id %" PRIx64 "", ...)` を出力する。
`sflowUpdateRate()` はこの失敗をログのみで続行するため、
古いレートのセッションが ASIC に残留し、複数レートのセッションが混在するリスクがある。

```
sfloworch.cpp:52   SWSS_LOG_ERROR("Failed to destroy sample packet session with id ...");
sfloworch.cpp:99-102  SWSS_LOG_ERROR("Failed to clean old session %" PRIx64 " with rate %d", ...);
```

### 5. SAI ポート属性設定失敗 (sflowAddPort / sflowDelPort)

`sai_port_api->set_port_attribute()` が `SAI_PORT_ATTR_INGRESS_SAMPLEPACKET_ENABLE` または
`SAI_PORT_ATTR_EGRESS_SAMPLEPACKET_ENABLE` の設定に失敗した場合、
`SWSS_LOG_ERROR("Failed to set session %" PRIx64 " on port %" PRIx64, ...)` を出力し `false` を返す。
呼び出し元 `doTask` では `it++; continue;` でそのポートエントリを次回処理に持ち越す (retry)。

```
sfloworch.cpp:126  SWSS_LOG_ERROR("Failed to set session ... on port ...");  // ingress
sfloworch.cpp:143  SWSS_LOG_ERROR("Failed to set session ... on port ...");  // egress
sfloworch.cpp:438-442  if (!sflowAddPort(...)) { it++; continue; }
```

### 6. hsflowd サービス制御失敗

`swss::exec("service hsflowd restart/stop", res)` が 0 以外の終了コードを返した場合、
`SWSS_LOG_ERROR("Command '%s' failed with rc %d", ...)` を出力する。
処理は続行するため CONFIG_DB の `admin_state` と実際の hsflowd サービス状態がずれたままになる。

```
sflowmgr.cpp:70  SWSS_LOG_ERROR("Command '%s' failed with rc %d", cmd.str().c_str(), ret);
```

### 7. グローバル無効がローカル有効を上書き (静的条件)

`isPortEnabled()` は `m_gEnable && (m_intfAllConf || (local_admin && status))` で判定する。
グローバル `admin_state=down` (`m_gEnable=false`) の場合、
per-port `admin_state=up` が設定されていても全ポートで sFlow が停止する。
エラーログは出力されないが、設定と動作が乖離しているように見える静的失敗条件。

```
sflowmgr.cpp:48  return m_gEnable && (m_intfAllConf || (local_admin && status));
```
