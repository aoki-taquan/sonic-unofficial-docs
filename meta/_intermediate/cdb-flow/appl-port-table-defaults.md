# APPL_DB PORT_TABLE コード由来デフォルト (Phase A)

**対象ファイル**: `docs/reference/config-db/appl-port-table.md`
**調査日**: 2026-05-14
**ソース精読**: sonic-swss cfgmgr/portmgr.h, cfgmgr/portmgr.cpp, orchagent/portsorch.cpp, orchagent/port.h, portsyncd/portsyncd.cpp, portsyncd/linksync.cpp

---

## 調査サマリー

APPL_DB `PORT_TABLE` は CONFIG_DB `PORT` テーブルの内容を portsyncd / portmgrd が変換・注入したものと、orchagent が SAI 状態変化に基づき書き戻したものの合成。
以下フィールドにコード由来のデフォルト／暗黙値が存在する。

---

## admin_status

- **portmgr.h:14** `#define DEFAULT_ADMIN_STATUS_STR "down"`
- portmgrd が初回 SET 時（ポートが `m_portList` に未登録）に CONFIG_DB の `admin_status` フィールドが存在しなければ `"down"` を APPL_DB に注入 (`portmgr.cpp:175`)
- portsyncd は CONFIG_DB PORT テーブルの値をそのまま APPL_DB に転写 (`portsyncd.cpp:207`) — CONFIG_DB に `admin_status` がある場合はその値を尊重
- linksync は STATE_DB に admin_status を書くが APPL_DB には書かない

**暗黙デフォルト**: `"down"` (CONFIG_DB に `admin_status` がない場合の portmgrd fallback)

---

## mtu

- **portmgr.h:15** `#define DEFAULT_MTU_STR "9100"`
- portmgrd 初回 SET 時に CONFIG_DB に `mtu` フィールドがなければ **9100** を APPL_DB に注入 (`portmgr.cpp:176`)
- orchagent の Port struct: `uint32_t m_mtu = DEFAULT_MTU` (port.h:194)
- **port.h:22-27**: `DEFAULT_MTU 1492` — SAI_PORT_ATTR_MTU デフォルト(1514) から ethernet header/FCS 22 bytes を引いた値。これは orchagent 内部の struct 初期値であり、APPL_DB に書かれる portmgr のデフォルト `9100` とは別物
- 実際に APPL_DB に書き込まれる初期値: `"9100"` (portmgr.cpp 経由)

**暗黙デフォルト**: `"9100"` (portmgrd fallback; CONFIG_DB に mtu がない場合)

---

## oper_status

- **portsorch.cpp:6643** `m_portTable->hset(port.m_alias, "oper_status", "down")` — ポート初期化時に orchagent が `"down"` を書き込む (warmboot 時は既存値を読み戻す)
- updateDbPortOperStatus() が SAI_PORT_OPER_STATUS_UP/DOWN/UNKNOWN に応じて更新 (`portsorch.cpp:3928`)
- **SAI_PORT_OPER_STATUS_UNKNOWN** は `oper_status_strings` マップに存在しない場合 `std::out_of_range` 例外
- warmboot 時は `m_portTable->get()` で既存値を読み込み、oper_status が "up" なら `SAI_PORT_OPER_STATUS_UP` として m_oper_status を初期化 (`portsorch.cpp:6617-6647`)

**暗黙デフォルト**: `"down"` (orchagent 初期書き込み値)

---

## flap_count

- orchagent が `updateDbPortFlapCount()` でカウンタをインクリメント後に APPL_DB に書き込む (`portsorch.cpp:3869`)
- 初期値 = `Port::m_flap_count = 0` (port.h:235 `uint64_t m_flap_count = 0`)
- warmboot 時は既存の flap_count を `m_portTable->get()` で読み戻して継続 (`portsorch.cpp:6655-6656`)

**暗黙デフォルト**: 初期書き込みなし (フラップ発生時に初めて書かれる)

---

## last_down_time / last_up_time

- `updateDbPortFlapCount()` 内でポートが DOWN/UP になった時刻を `"%a %b %d %H:%M:%S %Y"` (UTC) 形式で記録 (`portsorch.cpp:3878, 3887`)
- フラップ発生前は APPL_DB に該当フィールドなし

**暗黙デフォルト**: 存在しない (フラップ初回で初期化)

---

## speed (APPL_DB に書かれる状況)

- portsyncd は CONFIG_DB PORT の全フィールドをそのまま APPL_DB に転写するため `speed` も APPL_DB に存在する
- orchagent は PORT_TABLE に speed を**書き戻さない** (APPL_DB への反映は portsyncd 経由のみ)
- ただし `updateDbPortOperSpeed()` は **STATE_DB** (m_portStateTable) に書く (`portsorch.cpp:9857`) — APPL_DB ではない

**暗黙デフォルト**: CONFIG_DB の `speed` 値をそのまま転写 (portsyncd)

---

## fec (APPL_DB に書かれる状況)

- portsyncd が CONFIG_DB の `fec` 値を APPL_DB に転写
- orchagent の `updateDbPortOperFec()` は STATE_DB に書く (`portsorch.cpp:9869`) — APPL_DB ではない
- portmgrd は fec を APPL_DB に書かない

**暗黙デフォルト**: CONFIG_DB の値のパススルー

---

## system_oper_status / line_oper_status (Gearbox 専用)

- `updateGearboxPortOperStatus()` が gearbox 環境で SAI から system_side_id / line_side_id の oper status を取得し APPL_DB に書く (`portsorch.cpp:11242, 11258`)
- 通常環境（gearbox なし）では書かれない

**暗黙デフォルト**: gearbox 未使用時は存在しない

---

## lanes / alias / index / description / subport 等

- portsyncd が CONFIG_DB PORT テーブルを全フィールド転写するため APPL_DB にも存在する
- デフォルト値は CONFIG_DB 側 (sonic-port.yang / port_config.ini) が決定

---

## portmgrd の APPL_DB 書き込みまとめ

| フィールド | 書き込みタイミング | デフォルト値 | ソース |
|-----------|------------------|------------|--------|
| `admin_status` | 初回 SET (CONFIG_DB に値なし) | `"down"` | portmgr.h:14 |
| `mtu` | 初回 SET (CONFIG_DB に値なし) | `"9100"` | portmgr.h:15 |
| `admin_status` | SET (CONFIG_DB に値あり) | CONFIG_DB の値 | portmgr.cpp:192-198 |
| `mtu` | SET (CONFIG_DB に値あり) | CONFIG_DB の値 | portmgr.cpp:188-191 |
| その他フィールド | SET で受け取ったまま | — | portmgr.cpp:198-200 |

## orchagent の APPL_DB 書き込みまとめ

| フィールド | 書き込みタイミング | 値 | ソース |
|-----------|------------------|-----|--------|
| `oper_status` | 初期化時 | `"down"` | portsorch.cpp:6643 |
| `oper_status` | SAI port oper state change | `"up"`/`"down"` | portsorch.cpp:3928 |
| `flap_count` | ポートフラップ発生時 | 累積カウンタ | portsorch.cpp:3869 |
| `last_down_time` | ポート DOWN 時 | UTC 時刻文字列 | portsorch.cpp:3879 |
| `last_up_time` | ポート UP 時 | UTC 時刻文字列 | portsorch.cpp:3887 |
| `system_oper_status` | Gearbox 環境のみ | `"up"`/`"down"` | portsorch.cpp:11242 |
| `line_oper_status` | Gearbox 環境のみ | `"up"`/`"down"` | portsorch.cpp:11258 |

---

## Evidence ファイル一覧

| ファイル | 行 | 内容 |
|---------|----|------|
| `sonic-swss/cfgmgr/portmgr.h` | 14-15 | `DEFAULT_ADMIN_STATUS_STR "down"`, `DEFAULT_MTU_STR "9100"` |
| `sonic-swss/cfgmgr/portmgr.cpp` | 173-180 | 初回 SET 時の admin_status / mtu デフォルト注入 |
| `sonic-swss/orchagent/port.h` | 22-33 | `DEFAULT_MTU 1492`, `DEFAULT_TPID 0x8100` |
| `sonic-swss/orchagent/port.h` | 194-231 | Port struct フィールドと初期値 |
| `sonic-swss/orchagent/portsorch.cpp` | 6643 | oper_status="down" 初期書き込み |
| `sonic-swss/orchagent/portsorch.cpp` | 3863-3890 | updateDbPortFlapCount() |
| `sonic-swss/orchagent/portsorch.cpp` | 3916-3931 | updateDbPortOperStatus() |
| `sonic-swss/orchagent/portsorch.cpp` | 11220-11261 | updateGearboxPortOperStatus() |
| `sonic-swss/portsyncd/portsyncd.cpp` | 196-208 | CONFIG_DB → APPL_DB 全フィールド転写 |
