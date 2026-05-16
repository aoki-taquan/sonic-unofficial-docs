# APPL_DB BUFFER_* テーブル群 暗黙参照スキャン (Phase C)

`docs/reference/config-db/appl-buffer.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソースは `sonic-net/sonic-swss/orchagent/bufferorch.cpp` (ref `4305596156d70e9797e8a881b3d19b46de0bce0d`)。
`BufferOrch` が APPL_DB の `BUFFER_POOL_TABLE` / `BUFFER_PROFILE_TABLE` / `BUFFER_PG_TABLE` / `BUFFER_QUEUE_TABLE` / `BUFFER_PORT_INGRESS_PROFILE_LIST_TABLE` / `BUFFER_PORT_EGRESS_PROFILE_LIST_TABLE` を購読する際に、間接的に読み出す関連テーブル / Orch / DB を列挙する。

## スキャン手順

```
grep -nE 'gPortsOrch->getPort|resolveFieldRefValue|setObjectReference|flexCounterOrch|setFlexCounterGroup|m_buffer_type_maps|tokenize\(key' \
    .cache/sonic-sources/sonic-swss/orchagent/bufferorch.cpp
```

`BufferOrch` の handler ディスパッチ (`bufferorch.cpp:73-83`) から各 `processXxx()` を辿り、SAI OID 解決のために他テーブルや他 Orch を読み出す箇所を抽出する。

## 検出された暗黙参照

### BUFFER_PROFILE_TABLE の参照

| 参照先 | 参照方向 | 条件 | evidence |
|---|---|---|---|
| `BUFFER_POOL_TABLE\|<pool>` | OID 解決 (`resolveFieldRefValue`) — 必須 | `pool` フィールドが指定された profile の `SET`。プール未作成だと `field_not_resolved` で task 再試行 | `bufferorch.cpp:640-650` |
| `m_buffer_type_maps[APP_BUFFER_POOL_TABLE_NAME]` | object reference map 経由 | profile が pool を参照しており、削除時に `isObjectBeingReferenced()` で逆引きされる | `bufferorch.cpp:560-565,821` |

### BUFFER_QUEUE_TABLE の参照

| 参照先 | 参照方向 | 条件 | evidence |
|---|---|---|---|
| `BUFFER_PROFILE_TABLE\|<profile>` | OID 解決 (`resolveFieldRefValue`) — 必須 | `profile` フィールド指定の `SET`。未作成なら task 再試行 | `bufferorch.cpp:961-975` |
| `PORT\|<name>` (PortsOrch) | `gPortsOrch->getPort(port_name, port)` — 必須 | key の port 部分。未 ready なら task 再試行 (`m_ready_list` 未収載で `field_not_ready`) | `bufferorch.cpp:1033-1051,1111,1431,1488` |
| `getPortVoQIds(port)` | VoQ 解決 | `gPortsOrch->isSwitchTypeVoq()` 真のとき。VoQ スイッチでは port 単位 queue ではなく VoQ id を使用 | `bufferorch.cpp:1051` |
| FlexCounter — `QUEUE_STAT_COUNTER` / `QUEUE_WATERMARK_STAT_COUNTER` | flex counter 動的登録 | 非 VoQ かつ `FlexCounterOrch::isCreateOnlyConfigDbBuffers()` 真、かつ `QUEUE_*` counter 群有効時 | `bufferorch.cpp:1135-1158` |

### BUFFER_PG_TABLE の参照

| 参照先 | 参照方向 | 条件 | evidence |
|---|---|---|---|
| `BUFFER_PROFILE_TABLE\|<profile>` | OID 解決 (`resolveFieldRefValue`) — 必須 | `profile` フィールド指定の `SET` | `bufferorch.cpp:1339-1397` |
| `PORT\|<name>` (PortsOrch) | `gPortsOrch->getPort(port_name, port)` — 必須 | key の port 部分。未 ready なら task 再試行 | `bufferorch.cpp:1431,1488` |
| FlexCounter — `PG_STAT_COUNTER` / `PG_WATERMARK_STAT_COUNTER` | flex counter 動的登録 | `FlexCounterOrch::isCreateOnlyConfigDbBuffers()` 真、かつ `PG_*` counter 群有効時 | `bufferorch.cpp:1513-1531` |
| CONFIG_DB `BUFFER_PG\|<port>\|<pg>` / APPL_DB `BUFFER_PG_TABLE\|<port>\|<pg>` | warm-reboot 復旧スキャン | `BufferOrch` コンストラクタが warm-reboot 時に PG 設定有無を検出して queue 既定値を補完 | `bufferorch.cpp:113-141` |

### BUFFER_PORT_INGRESS/EGRESS_PROFILE_LIST_TABLE の参照

| 参照先 | 参照方向 | 条件 | evidence |
|---|---|---|---|
| `BUFFER_PROFILE_TABLE\|<profile>` (複数) | OID 解決ループ — 必須 | `profile_list` カンマ区切り各要素を `resolveFieldRefValue` で解決 | `bufferorch.cpp:1672-1739,1862-1929` |
| `PORT\|<name>` (PortsOrch) | `gPortsOrch->getPort(port_name, port)` — 必須 | port 単位の SAI `SET_PORT_ATTRIBUTE` 発行のため。未 ready なら task 再試行 | `bufferorch.cpp:1762,1952` |

### BUFFER_POOL_TABLE の参照（および書き込み）

| 参照先 | 参照方向 | 条件 | evidence |
|---|---|---|---|
| `STATE_BUFFER_MAXIMUM_VALUE_TABLE\|global.mmu_size` | 書き込み (`STATE_DB`) — side-effect | pool 生成時に MMU 総量 query。詳細は side-effects ブロック | `bufferorch.cpp:226-227` |
| `COUNTERS_BUFFER_POOL_NAME_MAP` / `COUNTERS_DB` | 書き込み — side-effect | pool name → OID マップ。詳細は side-effects ブロック | `bufferorch.cpp:55,277-348` |
| FlexCounter — `BUFFER_POOL_WATERMARK_STAT_COUNTER` | flex counter group 登録 | `generateBufferPoolWatermarkCounterIdList()` 発火時 | `bufferorch.cpp:247,281,316-348` |

### 全テーブル共通の前提

| 参照先 | 参照方向 | 条件 | evidence |
|---|---|---|---|
| `PORT` 全体（PortsOrch 初期化） | `gPortsOrch->isInitDone()` / `isConfigDone()` 待ち | コンストラクタおよび各 handler の早期 return | `bufferorch.cpp:22 (extern PortsOrch *gPortsOrch)` |
| `m_buffer_type_maps` 内 object reference graph | 削除時整合性 | profile→pool / queue→profile / pg→profile / profile_list→profile の 4 種参照関係を辿り、参照されている間は `m_pendingRemove` で削除を保留 | `bufferorch.cpp:35-48,560-585,837-872` |

## 共依存テーブル（Direction A の構成材料）

`BufferOrch` は APPL_DB のみを購読する。CONFIG_DB の `BUFFER_*` テーブルは **`buffermgrd` (buffermgrdyn / buffermgr)** が中継変換するため、`bufferorch` から直接読まれることはない（warm-reboot 復旧時の `Table confDb` 読み出し `bufferorch.cpp:129-141` を除く）。

| テーブル | 役割 | evidence |
|---|---|---|
| CONFIG_DB `BUFFER_POOL` / `BUFFER_PROFILE` / `BUFFER_PG` / `BUFFER_QUEUE` / `BUFFER_PORT_*_PROFILE_LIST` | `buffermgrd` 入力 → APPL_DB 出力 | `cfgmgr/buffermgrdyn.cpp` (中継変換側) |
| CONFIG_DB `DEVICE_METADATA.localhost.buffer_model` | static / dynamic 切替 | `buffermgrdyn` 初期化（Phase A 文書済） |
| CONFIG_DB `PORT` / `PORT_QOS_MAP` | buffer profile 展開時の参照（buffermgr 側） | Direction A 範囲外。`buffermgrdyn.cpp` |

> これら CONFIG_DB 側テーブルは APPL_DB 段では暗黙参照に含めない。**`buffermgrd` の cross-refs** として CONFIG_DB ページ側で扱う。

## 検証コマンド

```bash
grep -nE 'gPortsOrch->getPort|resolveFieldRefValue|setObjectReference|flexCounterOrch->(getQueue|getPg|isCreateOnly)|m_buffer_type_maps\[' \
    .cache/sonic-sources/sonic-swss/orchagent/bufferorch.cpp

grep -n 'getPortVoQIds\|isSwitchTypeVoq' \
    .cache/sonic-sources/sonic-swss/orchagent/bufferorch.cpp
```

このスキャン結果から派生して `docs/reference/config-db/appl-buffer.md` の `<!-- cross-refs -->` ブロックを生成する。
