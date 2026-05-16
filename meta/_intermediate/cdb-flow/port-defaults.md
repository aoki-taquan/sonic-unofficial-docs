# PORT — Phase A コード由来暗黙デフォルト調査

生成日: 2026-05-14

## 調査ソース

- `sonic-swss/cfgmgr/portmgr.h` — `DEFAULT_ADMIN_STATUS_STR` / `DEFAULT_MTU_STR`
- `sonic-swss/cfgmgr/portmgr.cpp` — `PortMgr::doTask()`, `setPortMtu()`, `setPortAdminStatus()`
- `sonic-swss/orchagent/portsorch.cpp` — `PortsOrch::addPortBulk()`, `doPortTask()`, `initPortCapAutoNeg()`, `initPortCapLinkTraining()`, `setPortMtu()`, `isSpeedSupported()`

---

## 1. フィールド別コード由来デフォルト

### `admin_status`

- **YANG デフォルト**: `down`（sonic-port.yang `default "down"`）
- **portmgr.h ハードコード**: `#define DEFAULT_ADMIN_STATUS_STR "down"`
  - `portmgr.cpp:175` — 初回 SET 時に `admin_status = DEFAULT_ADMIN_STATUS_STR` を代入してから CONFIG_DB 値で上書き
  - **経路依存注意**: ポートが初回設定の場合（`!configured`）、admin_status フィールドが CONFIG_DB に存在しなければ `"down"` が APP_DB に書き込まれる
- **admin_status はポート設定の最終ステップ**: `portsorch.cpp:5507` で `admin_status` の SAI 反映を最後に行う（speed / fec / autoneg などより後）。speed 変更中は一時的に `down` に落とされる（portsorch.cpp:5035-5050）

### `mtu`

- **YANG デフォルト**: なし（range 68..9216 のみ）
- **portmgr.h ハードコード**: `#define DEFAULT_MTU_STR "9100"`
  - `portmgr.cpp:176` — 初回 SET 時に `mtu = DEFAULT_MTU_STR` を代入してから CONFIG_DB 値で上書き
  - ポートが未設定かつ CONFIG_DB に `mtu` フィールドがなければ **9100** が APP_DB に書き込まれる（silent fallback）
- **SAI MTU 加算**: `portsorch.cpp:setPortMtu()` で SAI に渡す値は `mtu + sizeof(ether_header) + FCS_LEN + VLAN_TAG_LEN = mtu + 22` bytes
  - MACsec ポートの場合はさらに `MAX_MACSEC_SECTAG_SIZE` を加算（プラットフォーム依存）
- **portsorch の DEFAULT_SYSTEM_PORT_MTU**: `#define DEFAULT_SYSTEM_PORT_MTU 9100`（portsorch.cpp:79）— VoQ system port 用

### `speed`

- **YANG**: mandatory（range 1..1600000）
- **デフォルト**: なし（port_config.ini 由来の値を使用）
- **Silent Drop**: `isSpeedSupported()` で SAI サポート speed リストと照合。リストが空（SAI 非対応プラットフォーム）の場合は **常に true を返す**（portsorch.cpp:3093-3096）。つまりプラットフォームが速度検証をサポートしない場合は任意の speed 値が通過する
- **Speed 変更時の autoneg off 条件**: `p.m_admin_state_up && !p.m_autoneg` の場合のみ admin_status を一時的に down（portsorch.cpp:5034-5050）。autoneg が on の場合はポートを down せずに speed 変更を試みる（adv_speeds 扱い）

### `autoneg`

- **YANG デフォルト**: なし（`on`/`off`）
- **能力チェック fallback**: `initPortCapAutoNeg()` で SAI_PORT_ATTR_SUPPORTED_AUTO_NEG_MODE が取得失敗した場合は `port.m_cap_an = 1`（サポートありとみなす）(portsorch.cpp:3189-3192)
  - これにより既存プラットフォームで AN 能力問い合わせが非対応でも `autoneg` 設定が通る
- **autoneg 非サポート確定時**: `m_cap_an < 1` → `SWSS_LOG_ERROR("autoneg is not supported (cap=%d)")` → task をスキップ（opsorch.cpp:4817-4822）

### `link_training`

- **YANG デフォルト**: なし
- **能力チェック always 1**: `initPortCapLinkTraining()` は SAI 問い合わせをせず `port.m_cap_lt = 1` を無条件セット（portsorch.cpp:3201）。コメントに `// TODO: Add SAI_PORT_ATTR_SUPPORTED_LINK_TRAINING_MODE query`
  - **全プラットフォームでリンクトレーニング設定が通る** — ただし非対応 HW では SAI が失敗を返す

### `fec`

- **YANG デフォルト**: なし
- **Auto FEC (fec=auto / override_fec=false)**:
  - `!pCfg.fec.override_fec && !fec_override_sup` → `SWSS_LOG_ERROR("Auto FEC mode is not supported")` → task_failed（opsorch.cpp:5317-5321）
  - `fec_override_sup` は SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE 対応有無でブート時に判定（プラットフォーム依存）
- **FEC サポート確認 fallback**: `isFecModeSupported()` で `getPortSupportedFecModes()` が非対応の場合（`!obj.supported`）は **常に true を返す**（opsorch.cpp:3211-3213）

### `tpid`

- **YANG デフォルト**: なし（0x8100 / 0x9100 / 0x9200 / 0x88a8）
- **DEFAULT_TPID スキップ**: `addPortBulk()` で `cit.tpid.value != DEFAULT_TPID` の場合のみ SAI 属性を追加（opsorch.cpp:1337-1344）。DEFAULT_TPID（0x8100）はハードウェアデフォルトとして SAI に送らない

### `pfc_asym`

- **YANG デフォルト**: なし（`on`/`off`）
- **SAI_NOT_SUPPORTED 時の特殊扱い**: `setPortPfcAsym()` で SAI 返値が `SAI_STATUS_NOT_SUPPORTED` の場合は **true を返す**（エラーなし扱い）(opsorch.cpp:2540-2543)
  - 非サポートプラットフォームでは pfc_asym の設定が silent succeed する
- **SAI_PORT_PRIORITY_FLOW_CONTROL_RX を 0xff に設定**: `pfc_asym == SAI_PORT_PRIORITY_FLOW_CONTROL_MODE_SEPARATE` の場合に PFC RX を全ビット有効に強制セット（opsorch.cpp:2556-2570）— CONFIG_DB に PFC RX の明示指定フィールドなし

### `index` / `role`

- **YANG デフォルト**: role = `Ext`（コード確認済み）
- `addPortBulk()` で `p.m_role = cit.role.value`、`p.m_index = cit.index.value` を設定。ポート作成時に PORT Config から受け取るが、値が未設定の場合は Port 構造体のデフォルト値（ゼロ/空）が使われる

### `host_tx_ready`（隠れた状態フィールド）

- CONFIG_DB フィールドではなく STATE_DB フィールドだが、`admin_status` 変更の副作用で変更される
- `cmisModuleAsicSync` が disabled の場合:
  - admin_status DOWN → `host_tx_ready = "false"`
  - admin_status UP かつ gearbox status も成功 → `host_tx_ready = "true"`

---

## 2. Silent Drop / Dead Consumer 候補

| フィールド | 問題 | ソース |
|-----------|------|--------|
| `link_training` | LT 能力チェックが常時 cap=1 で非対応 HW に設定試行 → SAI 失敗のみで CONFIG_DB は変更されない | opsorch.cpp:3201 |
| `fec=auto` | `fec_override_sup=false` のプラットフォームでは silent task_failed — ユーザーに見えない | opsorch.cpp:5317-5321 |
| `pfc_asym` | 非サポート HW では SAI_NOT_SUPPORTED を受け取っても成功扱い | opsorch.cpp:2540-2543 |
| `tpid=0x8100` | DEFAULT_TPID は SAI に送らない（HW デフォルト前提）— 他の TPID から 0x8100 に戻す操作が安全かはプラットフォーム次第 | opsorch.cpp:1337 |

---

## 3. 書き込み順依存

- `admin_status` は PORT doTask の**最後**に適用される（opsorch.cpp:5506-5529）
- `speed` / `autoneg` / `fec` 変更時に一時的に `admin_status = down` にしてから元に戻す
  - CONFIG_DB に `admin_status=up` が入っていても、speed/fec/autoneg の変更完了後に up に戻す
  - 変更失敗時（task_need_retry）はポートが down のままになる可能性あり

---

## 4. YANG-実装 Discrepancy

| フィールド | YANG | 実装 |
|-----------|------|------|
| `mtu` | デフォルト指定なし（range 68..9216） | portmgr が初回設定時に `"9100"` を暗黙注入 |
| `admin_status` | `default "down"` | portmgr が `DEFAULT_ADMIN_STATUS_STR "down"` で二重確認 |
| `autoneg` 能力チェック | SAI 問い合わせ失敗時に non-support 扱い | SAI 失敗時は cap=1（サポートあり）と楽観的に扱う |
| `link_training` 能力 | SAI 問い合わせ予定（TODO） | 現在は cap=1 を無条件セット |
| `fec=auto` | YANG では `auto` は通常の値 | `fec_override_sup=false` プラットフォームでは task_failed |
