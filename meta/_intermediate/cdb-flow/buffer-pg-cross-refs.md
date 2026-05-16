# BUFFER_PG — 暗黙参照 (cross-table refs) 調査メモ

## 調査対象

`docs/reference/config-db/buffer-pg.md` Phase C 追加分。
YANG leafref は `profile → BUFFER_PROFILE.name` の 1 件のみ定義。以下に示す他テーブルへの依存は全て実装レベルの暗黙参照。

## ソースファイル精読

| ファイル | 役割 |
|---------|------|
| `sonic-swss/cfgmgr/buffermgrdyn.cpp` | `handleSingleBufferPgEntry()` / `handleCableLenTable()` / `handlePortTable()` / `handleDefaultLossLessBufferParam()` |
| `sonic-swss/cfgmgr/buffermgr.cpp` | `doCableTask()` / `doSpeedUpdateTask()` (static モード) |
| `sonic-swss/orchagent/bufferorch.cpp` | `processPriorityGroup()` — SAI 書き込み直前の BUFFER_PROFILE + PORT OID 解決 |

## YANG leafref

| フィールド | leafref 先 |
|-----------|-----------|
| `profile` | `BUFFER_PROFILE.name` |

## 暗黙参照 (実装レベル)

### 1. BUFFER_PROFILE（profile 値解決）

- **参照先テーブル**: `BUFFER_PROFILE`
- **参照方向**: 存在確認 + 属性取得（`dynamic_calculated`, `lossless`, `direction`）
- **条件**: `profile` フィールドが非 NULL のとき（headroom override モード）
- **参照元 (dynamic)**:
  - `buffermgrdyn.cpp` L3141 — `m_bufferProfileLookup.find(profileName)` 未発見 → `task_need_retry`
  - `buffermgrdyn.cpp` L3156 — `profileRef.direction == BUFFER_EGRESS` → `task_failed`（egress profile は ingress PG に使用不可）
  - `buffermgrdyn.cpp` L3163–3168 — `dynamic_calculated`, `lossless`, `configured_profile_name` をプロファイル属性から取得
- **参照元 (static)**: `buffermgr.cpp` L247 — `m_cfgBufferProfileTable.get(buffer_profile_key, ...)` で既存プロファイルを読み取り
- **意味**: プロファイルが未設定なら `task_need_retry`（orchagent で再試行）。egress 方向のプロファイルを PG に使用すると即 `task_failed`。プロファイルの `lossless` 属性に基づき PG の lossless フラグを継承。

### 2. BUFFER_POOL（headroom 計算のブロッカー）

- **参照先テーブル**: `BUFFER_POOL`
- **参照方向**: 存在確認（`m_bufferPoolReady` フラグ）
- **条件**: 常時。BUFFER_POOL が APPL_DB に存在しない間は全 PG 書き込みをデファー
- **参照元 (dynamic)**: `buffermgrdyn.cpp` L933–935 — `m_bufferObjectsPending = true`、BUFFER_POOL 書き込み完了まで PG を処理しない
- **参照元 (static)**: `buffermgr.cpp` L118 — `m_cfgLosslessPgPoolTable.get(INGRESS_LOSSLESS_PG_POOL_NAME, ...)` で ingress lossless pool の属性を取得して BUFFER_PROFILE を生成
- **意味**: BUFFER_POOL (特に ingress lossless pool) が確立するまで BUFFER_PG の lossless profile は作成・書き込みされない。

### 3. PORT（speed / admin_status / mtu 取得）

- **参照先テーブル**: `PORT`（CONFIG_DB）および `STATE_PORT_TABLE`（STATE_DB）
- **参照方向**: 読み取り（speed, mtu, admin_status, lanes 数）
- **条件**: 常時。PORT の speed + mtu が揃っていないと headroom 計算不可
- **参照元 (dynamic)**:
  - `buffermgrdyn.cpp` L449 — `CFG_PORT_TABLE_NAME` を `handlePortTable` にバインド
  - `buffermgrdyn.cpp` L451 — `STATE_PORT_TABLE_NAME` を `handlePortStateTable` にバインド
  - `buffermgrdyn.cpp` L1485–1487 — `effectiveSpeed.empty()` の場合 `"Nothing to be done for %s since port is not ready"` → スキップ
  - `buffermgrdyn.cpp` L2276 — `m_portInfoLookup[port]` で speed / cable_length / mtu / state を管理
- **参照元 (static)**:
  - `buffermgr.cpp` L155,167 — `doSpeedUpdateTask()` で `port_name`, `speed`, `pfc_enable` を取得
  - `buffermgr.cpp` L175–179 — `PORT_QOS_MAP.pfc_enable` が未設定なら silent skip
  - `buffermgr.cpp` L565 — `admin_status` 未取得時は `"assuming default down"` で扱う
- **参照元 (orchagent)**: `bufferorch.cpp` L1431 — `gPortsOrch->getPort(port_name, port)` 失敗 → `task_invalid_entry`
- **意味**: PORT speed が未設定なら headroom 計算をスキップ（warn のみ）。lanes 数は Mellanox 8-lane 判定に使用。

### 4. CABLE_LENGTH（headroom 計算パラメータ）

- **参照先テーブル**: `CABLE_LENGTH`（CONFIG_DB）
- **参照方向**: 読み取り（ポートごとのケーブル長文字列 `"5m"` 等）
- **条件**: dynamic buffer モードで lossless PG の headroom 計算時
- **参照元 (dynamic)**:
  - `buffermgrdyn.cpp` L450 — `CFG_PORT_CABLE_LEN_TABLE_NAME` を `handleCableLenTable` にバインド
  - `buffermgrdyn.cpp` L2142 — `"Handling CABLE_LENGTH table field %s length %s"` デバッグログ
  - `buffermgrdyn.cpp` L2148 — `portInfo.cable_length = cable_length;` で内部状態を更新後 `refreshPgsForPort()` を呼び出し
  - `buffermgrdyn.cpp` L1492–1509 — `cable_length == "0m"` の lossless PG は APPL_DB から削除（silent）
  - `buffermgrdyn.cpp` L1523 — `getDynamicProfileName(speed, cable_length, ...)` にパラメータとして渡す
- **参照元 (static)**: `buffermgr.cpp` L101–106 — `doCableTask(port, cable_length)` で `m_cableLenLookup[port] = cable_length` を更新後 `doSpeedUpdateTask()` を呼ぶ
- **意味**: ケーブル長が 0m の場合、lossless PG は書き込まずに APPL_DB から削除される（silent drop）。ケーブル長変更で既存 PG の profile が自動再計算・更新される。

### 5. DEFAULT_LOSSLESS_BUFFER_PARAMETER（閾値デフォルト値）

- **参照先テーブル**: `DEFAULT_LOSSLESS_BUFFER_PARAMETER`（CONFIG_DB）
- **参照方向**: 読み取り（`default_dynamic_th` フィールド）
- **条件**: dynamic buffer モードで lossless PG の threshold を決定する際
- **参照元**:
  - `buffermgrdyn.cpp` L40 — `m_cfgDefaultLosslessBufferParam(cfgDb, CFG_DEFAULT_LOSSLESS_BUFFER_PARAMETER)` 初期化
  - `buffermgrdyn.cpp` L150–153 — 起動時に `default_dynamic_th` を `m_defaultThreshold` に読み込む
  - `buffermgrdyn.cpp` L442 — `handleDefaultLossLessBufferParam` ハンドラに登録（動的更新対応）
  - `buffermgrdyn.cpp` L1460 — `m_defaultThreshold.empty()` → PG 書き込みデファー（BUFFER_POOL ready 後も待機）
  - `buffermgrdyn.cpp` L1521 — `threshold = m_defaultThreshold;`（profile 未指定 lossless PG のデフォルト threshold）
- **意味**: `DEFAULT_LOSSLESS_BUFFER_PARAMETER` が未設定の場合、dynamic モードの lossless PG 書き込みがデファーされる。設定変更時は全 lossless PG の threshold が自動再計算される。

### 6. LOSSLESS_TRAFFIC_PATTERN（Lua スクリプト経由の間接参照）

- **参照先テーブル**: `LOSSLESS_TRAFFIC_PATTERN`（CONFIG_DB）
- **参照方向**: 読み取り（Redis KEYS コマンド経由、Lua スクリプト内）
- **条件**: Mellanox / Barefoot (Intel Tofino) プラットフォームで headroom 計算時
- **参照元**:
  - `cfgmgr/buffer_headroom_mellanox.lua` L9,91 — `redis.call('KEYS', 'LOSSLESS_TRAFFIC_PATTERN*')` で全エントリ取得
  - `cfgmgr/buffer_headroom_barefoot.lua` L8,80 — 同様に `LOSSLESS_TRAFFIC_PATTERN*` を参照
  - `buffermgrdyn.cpp` L76–78 — `buffer_headroom_<platform>.lua` をベンダー別に選択して `evalsha` で呼び出し
  - `buffermgrdyn.cpp` L605 — `argv.emplace_back(headroom.cable_length)` 等でパラメータを渡す
- **意味**: 汎用プラットフォームは Lua スクリプトが `LOSSLESS_TRAFFIC_PATTERN` を参照しないため、`buffermgrdyn.cpp` 本体からの直接購読はない。Mellanox/Barefoot 環境でのみ有効な間接参照。テスト用 `buffer_model.py` では `LOSSLESS_TRAFFIC_PATTERN|AZURE` エントリを直接書き込んで検証する（`tests/buffer_model.py` L55,90）。

## まとめ

| 参照先テーブル | YANG leafref | 参照種別 | 非充足時の挙動 |
|---------------|:------------:|---------|--------------|
| `BUFFER_PROFILE` | ✅ (profile フィールド) | 必須: 属性取得・egress チェック | `task_need_retry` / `task_failed` |
| `BUFFER_POOL` | ✗ | ブロッキング: 書き込みデファー | 全 PG デファー（`m_bufferPoolReady=false`） |
| `PORT` | ✗ | 必須: speed/mtu/admin_status | headroom 計算スキップ / `task_invalid_entry` |
| `CABLE_LENGTH` | ✗ | 必須: headroom 計算パラメータ | 0m → lossless PG を APPL_DB から silent delete |
| `DEFAULT_LOSSLESS_BUFFER_PARAMETER` | ✗ | 必須: threshold デフォルト値 | `m_defaultThreshold.empty()` → デファー |
| `LOSSLESS_TRAFFIC_PATTERN` | ✗ | 間接: Lua スクリプト経由 | Mellanox/Barefoot のみ有効 |
