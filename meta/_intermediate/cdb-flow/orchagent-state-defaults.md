# STATE_DB orchagent 共通 — Phase A コード由来デフォルト調査メモ

調査日: 2026-05-15
対象: orchagent (sonic-swss) が書き込む主要 STATE_DB テーブル
調査対象: sonic-swss/orchagent/ + sonic-swss-common/common/warm_restart.cpp

---

## 調査範囲

orchagent が STATE_DB へ書き込むテーブルを網羅的に洗い出す。
本ページは「orchagent が一次的に書く」共通テーブルのみ対象とし、
個別テーブル（BFD_SESSION_TABLE, MUX_CABLE_TABLE 等）は別ドキュメントへ委譲する。

主要テーブル一覧:
1. `WARM_RESTART_TABLE` — warm restart FSM state
2. `PORT_TABLE` — ポートのランタイム状態 (portsorch)
3. `FDB_TABLE` — ローカル FDB エントリ (fdborch)
4. `VRF_OBJECT_TABLE` — VRF 作成完了通知 (vrforch)
5. `FIPS_MACSEC_POST_TABLE` — MACsec POST テスト結果 (macsecpost.cpp)

---

## 1. WARM_RESTART_TABLE (STATE_WARM_RESTART_TABLE_NAME)

### テーブル名
`schema.h:427`: `#define STATE_WARM_RESTART_TABLE_NAME "WARM_RESTART_TABLE"`

### キー構造
`WARM_RESTART_TABLE|<app_name>`  — e.g. `WARM_RESTART_TABLE|orchagent`

### フィールドと初期値

| フィールド | 初期値 / 可能値 | コード由来 |
|-----------|----------------|----------|
| `restore_count` | `"0"` | `warm_restart.cpp:113, 133` — コールドスタート時は `"0"` 書き込み、warm start 時はインクリメント |
| `state` | `"initialized"` | `warm_restart.cpp:227-229` + `warmStartStateNameMap` (L11-17) — orchagent 起動時: INITIALIZED → RECONCILED / RESTORED |
| `restore_check` | `"ignored"` / `"passed"` / `"failed"` | `warm_restart.cpp:241-249` — DataCheck 結果。STAGE_RESTORE での data check 結果 |
| `shutdown_check` | `"ignored"` / `"passed"` / `"failed"` | `warm_restart.cpp:241-249` — STAGE_SHUTDOWN での data check 結果 |

### state 遷移 (orchagent)
- 起動時: `WarmStart::INITIALIZED` → "initialized" (orchdaemon.cpp:1099)
- warm start 完了: `WarmStart::RECONCILED` → "reconciled" (orchdaemon.cpp:1170)
- restore 完了: `WarmStart::RESTORED` → "restored" (orchdaemon.cpp:1204)

### warmStartStateNameMap 全値
```cpp
// warm_restart.cpp:9-17
{INITIALIZED,   "initialized"},
{RESTORED,      "restored"},
{REPLAYED,      "replayed"},
{RECONCILED,    "reconciled"},
{WSDISABLED,    "disabled"},
{WSUNKNOWN,     "unknown"}
```

---

## 2. PORT_TABLE (STATE_PORT_TABLE_NAME)

### テーブル名
`schema.h:420`: `#define STATE_PORT_TABLE_NAME "PORT_TABLE"`

### キー構造
`PORT_TABLE|<port_alias>` — e.g. `PORT_TABLE|Ethernet0`

### フィールドと初期値

| フィールド | 初期値 | コード由来 |
|-----------|--------|----------|
| `supported_speeds` | SAI から取得 (カンマ区切り文字列) | `portsorch.cpp:3171-3172` — `initPortCapSpeeds()` で SAI_PORT_ATTR_SUPPORTED_SPEED_LIST を取得して書き込み |
| `supported_fecs` | SAI から取得 (カンマ区切り) + `"auto"` suffix | `portsorch.cpp:3318-3320` — `initPortCapFec()` で SAI_PORT_ATTR_SUPPORTED_FEC_MODE を取得、auto FEC サポート時は末尾に `"auto"` を追加 |
| `host_tx_ready` | `"false"` | `portsorch.cpp:2201-2203` — `initHostTxReadyState()` で既存値がなければ `"false"` 初期化 |
| `speed` | SAI 取得値 or `"N/A"` | `portsorch.cpp:9855-9857` — `updateDbPortOperSpeed()` で `speed != 0` なら数値文字列, 0 なら `"N/A"` |
| `fec` | SAI 取得文字列 | `portsorch.cpp:9869-9870` — `updateDbPortOperFec()` |
| `link_training_status` | SAI 取得文字列 | `portsorch.cpp:4907, 11380` — autoneg 設定時または LT 完了通知時に書き込み |
| `rmt_adv_speeds` | SAI 取得 (カンマ区切り) | `portsorch.cpp:11338` — リモート advertised speeds 取得時。未サポート時は hdel: `portsorch.cpp:4862` |
| `phy_ctrl_unreliable_los` | `"true"` / `"false"` | `portsorch.cpp:5200` — PHY LOS 信頼性フラグ |

---

## 3. FDB_TABLE (STATE_FDB_TABLE_NAME)

### テーブル名
`schema.h:426`: `#define STATE_FDB_TABLE_NAME "FDB_TABLE"`

### キー構造
`FDB_TABLE|<vlan>:<mac>` — e.g. `FDB_TABLE|Vlan1000:aa:bb:cc:dd:ee:ff`

### フィールドと初期値

| フィールド | 値 | コード由来 |
|-----------|-----|----------|
| `port` | ポート名文字列 | `fdborch.cpp:133, 1577` — FDB エントリのポート名 |
| `type` | `"dynamic"` / `"static"` | `fdborch.cpp:134, 1579-1582` — `dynamic_local` は `"dynamic"` に正規化 |

### 書き込み条件
- ローカル MAC アドレス (FDB_ORIGIN_LEARN または FDB_ORIGIN_LOCAL) のみ書き込む
- FDB_ORIGIN_ADVERTIZED (VXLAN) / FDB_ORIGIN_MCLAG_ADVERTIZED は原則書かない (例外: `dynamic_local` 由来の MCLAG は書く)
- MAC 移動時: 旧エントリ削除後、新エントリ書き込み

---

## 4. VRF_OBJECT_TABLE (STATE_VRF_OBJECT_TABLE_NAME)

### テーブル名
`schema.h:430`: `#define STATE_VRF_OBJECT_TABLE_NAME "VRF_OBJECT_TABLE"`

### キー構造
`VRF_OBJECT_TABLE|<vrf_name>` — e.g. `VRF_OBJECT_TABLE|Vrf-red`

### フィールドと初期値

| フィールド | 値 | コード由来 |
|-----------|-----|----------|
| `state` | `"ok"` | `vrforch.cpp:120, 150` — VRF SAI 作成成功 / 更新成功後に書き込み |

### 用途
- `vrfmgrd` が VRF 削除前に `isVrfObjExist()` で `"ok"` を確認してから app_db を削除する。
- `VRF_OBJECT_TABLE` に `"ok"` が書かれていない間は VRF 作成が完了していないとみなされる。

---

## 5. FIPS_MACSEC_POST_TABLE (STATE_FIPS_MACSEC_POST_TABLE_NAME)

### テーブル名
`schema.h:471`: `#define STATE_FIPS_MACSEC_POST_TABLE_NAME "FIPS_MACSEC_POST_TABLE"`

### キー構造
`FIPS_MACSEC_POST_TABLE|sai` — 固定キー `"sai"`

### フィールドと初期値

| フィールド | 初期値 / 可能値 | コード由来 |
|-----------|----------------|----------|
| `post_state` | `"disabled"` / `"macsec-level-post-in-progress"` / `"pass"` / `"fail"` | `macsecpost.cpp:13, main.cpp:791-793, 924-930, macsecorch.cpp:705, 710, 786-791` |
| `last_update_time` | 現在時刻 (UTC, `"%a %b %d %H:%M:%S %Y"` 形式) | `macsecpost.cpp:16-20` — 毎 `setMacsecPostState()` 呼び出し時に更新 |

### post_state 遷移
```
orchagent 起動時:
  SAI MACsec POST 非対応 → "disabled"
  SAI_SWITCH_ATTR_MACSEC_POST_STATUS_NOTIFY サポート → "macsec-level-post-in-progress"
  SAI_MACSEC_ATTR_ENABLE_POST サポート → "macsec-level-post-in-progress"

SAI 通知コールバック (macsecorch.cpp):
  SAI_SWITCH_MACSEC_POST_STATUS_PASS → "pass"
  SAI_SWITCH_MACSEC_POST_STATUS_FAIL → "fail"
```

---

## まとめ

orchagent が直接書く STATE_DB テーブルの暗黙デフォルト:

| テーブル | 主キー | 主フィールド | デフォルト |
|---------|--------|------------|----------|
| `WARM_RESTART_TABLE` | `orchagent` | `state` | `"initialized"` (cold start) |
| `WARM_RESTART_TABLE` | `orchagent` | `restore_count` | `"0"` (cold start) |
| `PORT_TABLE` | `<alias>` | `host_tx_ready` | `"false"` (初期化時) |
| `FDB_TABLE` | `<vlan>:<mac>` | `type` | `"dynamic"` (dynamic_local 正規化) |
| `VRF_OBJECT_TABLE` | `<vrf>` | `state` | `"ok"` (作成成功後) |
| `FIPS_MACSEC_POST_TABLE` | `sai` | `post_state` | `"disabled"` (MACsec 非対応時) |
