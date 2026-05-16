# breakout-cfg — Phase F 副次 DB 書込スキャンノート

## 調査対象

- `sonic-utilities/config/main.py` — `breakout()` / `breakout_Ports()` / `breakout_warnUser_extraTables()` (L239–274, L5454–5554)
- `sonic-swss/orchagent/portsorch.cpp` — `initPort()` / `deInitPort()` / `generateQueueMapPerPort()` / `createPortBufferQueueCounters()` / `removePortBufferQueueCounters()` (L3100–4340, L8391–8800)
- `sonic-buildimage/files/scripts/` — breakout 関連スクリプト

## 結果サマリ

| DB | 書込有無 | 根拠 |
|----|---------|------|
| CONFIG_DB (`BREAKOUT_CFG`) | **あり（主書込）** | `config_db.set_entry("BREAKOUT_CFG", interface_name, {'brkout_mode': target_brkout_mode})` `config/main.py:5554` |
| CONFIG_DB (`PORT`) | **あり（副次・ポート再構成）** | `breakout_Ports()` が `ConfigMgmt.breakOutPort()` を呼び、旧子ポートを削除し新子ポートを生成 `config/main.py:5544-5545` |
| COUNTERS_DB (`COUNTERS_QUEUE_PORT_MAP` / `COUNTERS_QUEUE_INDEX_MAP` / `COUNTERS_QUEUE_TYPE_MAP`) | **あり（副次・キューマップ再生成）** | `portsorch.cpp:initPort()` が flex counter 有効時に `generateQueueMapPerPort()` → `m_queuePortTable->set()` / `m_queueIndexTable->set()` / `m_queueTypeTable->set()` を呼ぶ (L8527-8529, L8750-8752) |
| COUNTERS_DB (`COUNTERS_PORT_NAME_MAP`)  | **あり（副次・ポート名マップ更新）** | `deInitPort()` が `m_counterNameMapUpdater->delCounterNameMap(alias)` で旧ポートエントリを削除。`initPort()` 系で新ポートを再登録 |
| STATE_DB (`STATE_PORT_TABLE`) | **あり（副次・ポート状態初期化）** | `initPort()` → `m_portStateTable.set(alias, v)` でポート状態エントリを新規登録 (L3172, L3320); `deInitPort()` → `m_stateBufferMaximumValueTable->del(alias)` で旧エントリ削除 (L4331) |
| APPL_DB (`APP_PORT_TABLE`) | **あり（間接・portsyncd 経由）** | `breakout_Ports()` → `breakOutPort()` が APP_PORT_TABLE を更新; `portsyncd` が CONFIG_DB `PORT` 変更を購読して APPL_DB に反映 |

## 副次書込の詳細

### 1. CONFIG_DB|PORT テーブルの再構成（直接・同期）

`breakout()` は `breakout_Ports(cm, delPorts=final_delPorts, portJson=portJson, ...)` を呼ぶ。  
内部で `ConfigMgmt.breakOutPort()` が:

1. `final_delPorts`（旧モードの子ポート）を `CONFIG_DB|PORT` から削除
2. `portJson['PORT']`（新モードの子ポート）を `CONFIG_DB|PORT` に挿入

**トリガ**: `config interface breakout <port> <mode>` 実行時  
**操作種別**: del + set  
**evidence**: `sonic-utilities/config/main.py:5496-5545`

### 2. COUNTERS_DB|COUNTERS_QUEUE_PORT_MAP 等 — キューマップ更新

breakout 後にポートが再初期化 (`orchagent/portsorch.cpp:initPort()`) されるとき、flex counter が有効であれば `generateQueueMapPerPort()` が呼ばれ、新子ポートのキュー OID → ポート OID / キューインデックス / キュータイプのマッピングが COUNTERS_DB に書き込まれる。

```cpp
// portsorch.cpp L8527-8529 (generateQueueMapPerPort 内)
m_queuePortTable->set("", queuePortVector);
m_queueIndexTable->set("", queueIndexVector);
m_queueTypeTable->set("", queueTypeVector);
```

旧子ポートは `deInitPort()` → `removePortBufferQueueCounters()` で旧マッピングが `hdel` される。

```cpp
// portsorch.cpp L8790-8797 (removePortBufferQueueCounters 内)
m_queuePortTable->hdel("", id);
m_queueTypeTable->hdel("", id);
m_queueIndexTable->hdel("", id);
```

**トリガ**: DPB 後 orchagent がポートを SAI レイヤで再生成したとき（queue flex counter 有効時のみ）  
**操作種別**: set（新マップ）+ hdel（旧マップ）  
**evidence**: `sonic-swss/orchagent/portsorch.cpp:L4211-4248, L4271-4285, L8527-8529, L8750-8797`

### 3. STATE_DB|PORT_TABLE — ポート状態エントリの再初期化

`initPort()` はポートを STATE_DB に登録し `supported_speeds` / `supported_fecs` 等の初期フィールドをセットする。  
`deInitPort()` は `m_stateBufferMaximumValueTable->del(alias)` でバッファ最大値テーブルのエントリを削除する。

```cpp
// portsorch.cpp L3172, L3320 (initPortSupportedSpeeds, initPortSupportedFec 内)
m_portStateTable.set(alias, v);

// portsorch.cpp L4331 (deInitPort 内)
m_stateBufferMaximumValueTable->del(alias);
```

**トリガ**: DPB による SAI ポート再生成 → orchagent ポート初期化パス  
**操作種別**: set（新エントリ）+ del（旧バッファ最大値エントリ）  
**evidence**: `sonic-swss/orchagent/portsorch.cpp:L3172, L3320, L4331`

### 4. COUNTERS_DB|COUNTERS_PORT_NAME_MAP — ポート名マップ更新

`deInitPort()` は `m_counterNameMapUpdater->delCounterNameMap(alias)` で旧ポートの COUNTERS_DB 名前マップエントリを削除する。新ポート (`initPort()`) では `m_counterNameMapUpdater` (CounterNameMapUpdater) が新エントリを追加する。

**トリガ**: DPB 後のポート追加・削除 orchagent パス  
**操作種別**: del（旧エントリ）+ set（新エントリ）  
**evidence**: `sonic-swss/orchagent/portsorch.cpp:L758-759, L4316`

## sonic-buildimage/files/scripts/ スキャン結果

breakout 専用スクリプトは `files/scripts/` 配下に存在しない。  
DPB は `sonic-utilities` の `config/main.py` と `swss` の `ConfigMgmt` ライブラリが主担当。

## 結論

`BREAKOUT_CFG` への書込に伴う副次 DB 書込は以下の 4 系統:

1. **CONFIG_DB|PORT**: 旧子ポートの削除 + 新子ポートの生成（直接・同期、ConfigMgmt 経由）
2. **COUNTERS_DB キューマップ**: 旧子ポートのキュー OID マッピング削除 + 新子ポートのキュー OID マッピング生成（flex counter 有効時のみ）
3. **STATE_DB|PORT_TABLE**: 旧ポートの状態エントリ削除 + 新ポートの状態エントリ初期化（orchagent ポート初期化パス）
4. **COUNTERS_DB|COUNTERS_PORT_NAME_MAP**: ポート名マップの旧エントリ削除 + 新エントリ追加

APPL_DB への書込は `portsyncd` が CONFIG_DB|PORT の変更を購読することにより間接的に発生する（DPB フロー全体の一部）。
