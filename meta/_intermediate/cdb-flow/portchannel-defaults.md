# PORTCHANNEL — Phase A コード由来暗黙デフォルト調査

生成日: 2026-05-14

## 調査ソース

- `sonic-swss/cfgmgr/teammgr.cpp` (全行精読)
- `sonic-swss/cfgmgr/portmgr.h` (DEFAULT 定数)
- `sonic-buildimage/src/sonic-config-engine/minigraph.py:954-971`
- `sonic-utilities/config/main.py:2832-2867`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-portchannel.yang`
- `sonic-utilities/scripts/db_migrator.py:1154-1158`

---

## フィールド別デフォルト・暗黙挙動

### `admin_status`

- **YANG**: `mandatory true` — デフォルト値なし。省略すると検証 reject。
- **teammgr.cpp:251**: `string admin_status = DEFAULT_ADMIN_STATUS_STR;` → **ハードコード `"down"`** (portmgr.h:14)
  - CONFIG_DB に `admin_status` が存在しない場合、`doLagTask()` は `setLagAdminStatus(alias, "down")` を呼ぶ。
  - これは YANG mandatory と乖離: YANG は省略不可だが、実装は省略時に "down" fallback する。
- **CLI (config/main.py:2844)**: `'admin_status': 'up'` を明示書き込み。
- **minigraph.py**: `admin_status` を明示設定しない (minigraph 経由の場合、フィールドなしで pcs[] に投入 → teammgr が "down" fallback)。
- **discrepancy**: YANG=mandatory(省略不可) ↔ 実装=省略時"down"フォールバック。

### `mtu`

- **YANG**: オプション (range 1..9216)、デフォルト値定義なし。
- **teammgr.cpp:252**: `string mtu = DEFAULT_MTU_STR;` → **ハードコード `"9100"`** (portmgr.h:15)
  - CONFIG_DB に `mtu` が存在しない場合でも `setLagMtu(alias, "9100")` を呼ぶ。
  - member 追加時 (addLagMember) も同じ `DEFAULT_MTU_STR = "9100"` を LAG の mtu fallback として使用 (teammgr.cpp:812)。
- **CLI (config/main.py:2845)**: `'mtu': '9100'` を明示書き込み。
- **minigraph.py**: `mtu` を明示設定しない → teammgr が "9100" fallback。
- **注意**: YANG range 上限は 9216 だが、ハードコードデフォルトは 9100。混同注意。

### `min_links`

- **YANG**: オプション (range 1..1024)。デフォルト値なし。
- **teammgr.cpp:248**: `int min_links = 0;`
  - `min_links == 0` の場合、`addLag()` の teamd conf に `"min_ports"` を出力しない → **teamd のデフォルト動作** (= 1メンバーでもupになる)。
- **CLI (config/main.py:2834)**: `--min-links` は `default=1`。ただし `if min_links != 0: fvs['min_links'] = str(min_links)` であるため、`--min-links 1` 指定時はフィールドあり。
- **minigraph.py:969,971**: `str(int(math.ceil(len(pcmbr_list) * 0.75)))` — **メンバ数の 75% 切り上げを自動計算**。例: 4メンバ → `min_links=3`。フィールドあり。
- **dead field**: なし (teamd conf に min_ports として伝達される)。
- **silent behavior**: `min_links` が CONFIG_DB にない場合、teamd は min_ports なしで起動し、1ポート以上でLAGがup。ユーザに見えないデフォルト。

### `fallback`

- **YANG**: オプション (boolean_type)。デフォルト値なし。
- **teammgr.cpp:249**: `bool fallback = false;`
  - `fallback == false` の場合、`addLag()` の teamd conf に `"fallback"` キーを出力しない → LACP ネゴシエーション完了まで up しない。
  - `min_links` / `fallback` はコメント (teammgr.cpp:258-259) で「LAG 作成後は変更不可」と明記。
- **CLI (config/main.py:2835)**: `--fallback` `default='false'`。`fallback != 'false'` のときのみ `fvs['fallback'] = 'true'` をセット → **`fallback=false` はフィールド自体を書かない (silent drop)**。
- **minigraph.py:968-971**: `Fallback` XML ノードが存在する場合のみ `fallback` を設定。存在しない場合はフィールドなし。
- **書込み順依存**: fallback は LAG 作成時 (`addLag()`) のみ反映。作成後に CONFIG_DB を更新しても teamd conf は変わらない (再起動しないと効かない)。

### `fast_rate`

- **YANG**: オプション (boolean_type)。デフォルト値なし。
- **teammgr.cpp:250**: `bool fast_rate = false;`
  - `fast_rate == false` の場合、`addLag()` の teamd conf に `"fast_rate"` キーを出力しない → LACP slow rate (30秒間隔)。
  - `min_links` / `fallback` と同様に LAG 作成時のみ反映。**作成後の変更は teamd 再起動まで無効**。
- **CLI (config/main.py:2836-2847)**: `--fast-rate` `default='false'`。`fast_rate.lower()` を常に書き込む。ただし値が `"false"` のときも DB に書く (fallback と異なり常にフィールドあり)。
- **経路依存乖離**: `fast_rate=false` は CLI では常にフィールド書き込まれるが、minigraph 経由ではフィールドなし。動作は同じ (両方ともデフォルトの slow rate)。

### `lacp_key`

- **YANG**: オプション。`auto` または uint16 (1..65535)。デフォルト値なし。
- **teammgr.cpp:690-726 `generateLacpKey()`**:
  - フィールドなし or 空文字 → **戻り値 `0`** (LACP key = 0、backward compatibility)。
  - `"auto"` → `"1" + PortChannel名末尾数字` → uint16 変換。例: PortChannel1 → 11、PortChannel100 → 1100。
  - 数値文字列 → そのまま uint16 変換。
  - **ハードコード fallback**: `lacp_key` フィールドなし → key=0。LACP key=0 は「グループなし」扱い (IEEE 802.3ad)。
- **CLI (config/main.py:2846)**: `'lacp_key': 'auto'` を常に明示書き込み。
- **minigraph.py:969,971**: `'lacp_key': 'auto'` を常に書き込み。
- **db_migrator.py:1156**: version_3_0_1 → 3_0_2 移行時に既存エントリ全件に `lacp_key='auto'` を付与 (retroactive)。ただし warmreboot 時はスキップ。
- **discrepancy**: フィールドなし時 key=0 は IEEE 802.3ad 的に問題あり (peer と key 不一致でLACP negotiation 失敗の可能性)。

### `tpid`

- **YANG**: オプション (tpid_type)。デフォルト値なし。
- **teammgr.cpp:321-324**: `if (!tpid.empty()) { setLagTpid(alias, tpid); }` → **フィールドなし時は `setLagTpid()` を呼ばない (silent skip)**。
  - HW デフォルト TPID は SAI 実装依存。ほとんどの場合 0x8100 (802.1Q)。
- **portsorch.cpp:6169**: `if (tpid != 0) { setLagTpid(...) }` → APP_DB の tpid フィールドなし (=0) では SAI 設定をスキップ。
- **プラットフォーム依存**: TPID 設定は HW 対応必須。未対応プラットフォームでは `setLagTpid()` が `SWSS_LOG_ERROR` (portsorch.cpp:8280)。
- **経路依存乖離**: CLI / minigraph いずれも tpid を設定しない。tpid は手動 DB 操作または将来的な CLI 拡張でのみ設定される。

### `mode`

- **YANG**: オプション (switchport_mode)。デフォルト値なし (YANG leaf に default 記述なし)。
  - ただし YANG の description は "Default value for mode is routed"。
- **teammgr.cpp**: `mode` フィールドを一切読み取らない (**dead consumer in teammgr**)。
- **portsorch.cpp**: APP_LAG_TABLE 購読時も `mode` フィールドを読み取らない。
- **switchport.py**: `mode` フィールドを読み書きするが、実際の L2/L3 動作制御は VLAN_MEMBER / PORTCHANNEL_INTERFACE テーブルの存在で決まり、`mode` フィールドは UI ヒント的存在。
- **dead field (partial)**: `mode` は CONFIG_DB に書かれるが、teamd・portsorch のいずれの consumer も実行時に読み取らない。スイッチポートモード切替は `mode` フィールドではなく VLAN テーブル操作によって暗黙的に決まる。
- **注意**: YANG default の記述は "routed" だが、YANG leaf に `default` 文がなく、実装でも参照されない。

### `description`

- **YANG**: オプション (string 1..255)。デフォルト値なし。
- **teammgr.cpp / portsorch.cpp**: `description` フィールドを読み取らない (**dead consumer**)。
- **dead field**: CONFIG_DB に書いても動作に影響しない。コメント目的のみ。

---

## サマリー表

| フィールド | YANG default | コード fallback | 経路 | 備考 |
|---|---|---|---|---|
| `admin_status` | mandatory (なし) | `"down"` (portmgr.h:14) | teammgr.cpp:251 | YANG-実装 discrepancy: mandatory なのにコードは省略時 "down" |
| `mtu` | なし | `"9100"` (portmgr.h:15) | teammgr.cpp:252,812 | ハードコード、YANG range 上限 9216 と混同注意 |
| `min_links` | なし | `0` → teamd min_ports 省略 | teammgr.cpp:248,611 | 省略時は 1 ポートでも LAG が up; LAG 作成後変更不可 |
| `fallback` | なし | `false` → teamd fallback 省略 | teammgr.cpp:249,616 | CLI は `false` 時フィールド書かない (silent drop); LAG 作成後変更不可 |
| `fast_rate` | なし | `false` → teamd fast_rate 省略 | teammgr.cpp:250,621 | CLI は常にフィールド書く; 作成後変更不可 (teamd 再起動要) |
| `lacp_key` | なし | key=0 (backward compat) | teammgr.cpp:726 | db_migrator が既存エントリに 'auto' を retroactive 付与 |
| `tpid` | なし | silent skip (SAI HW デフォルト) | teammgr.cpp:321 | HW 依存; 未対応 HW で ERROR |
| `mode` | なし (YANG説明"routed") | N/A — dead consumer | switchport.py のみ | teammgrd/portsorch が読まない dead field |
| `description` | なし | N/A — dead consumer | なし | 純粋な dead field; 動作影響なし |

---

## 主要 discrepancy

1. **`admin_status` YANG-実装 discrepancy**: YANG は `mandatory true` (省略不可) だが、teammgr は省略時に `"down"` でフォールバック。minigraph 経由では `admin_status` が CONFIG_DB に書かれないケースがあり、その場合 LAG は admin-down で起動する。
2. **`mode` dead consumer**: YANG description は "default routed" と記述するが、YANG leaf に `default` 文なし。また teammgrd / portsorch のいずれも runtime に `mode` フィールドを参照しない。switchport.py が DB に書くのみで、実挙動は VLAN テーブル操作が決定する。
3. **`fallback` / `fast_rate` LAG 作成後変更不可**: CONFIG_DB 更新後も teamd conf は変わらない。teamd プロセスを再起動するまで変更が反映されない (運用上の silent 罠)。
4. **`lacp_key` フィールドなし → key=0**: LACP negotiation で peer と key 不一致 → LAG 組めない可能性。db_migrator が retroactive に 'auto' 付与するが、warmreboot 中はスキップ。
