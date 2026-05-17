---
title: PORT_STORM_CONTROL テーブル — 暗黙デフォルト詳細
description: "PORT_STORM_CONTROL テーブルの暗黙デフォルト・ハードコード挙動・YANG と実装の乖離を詳細解説。BUM (broadcast / unknown-unicast / unknown-multicast) storm control の Phase A 分析。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-14
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-storm-control.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-swss
    path: orchagent/policerorch.cpp
    ref: master
  - repo: sonic-net/sonic-utilities
    path: config/main.py
    ref: master
related:
  config_db:
    - PORT_STORM_CONTROL
    - PORT
  yang:
    - sonic-storm-control
---

# PORT_STORM_CONTROL テーブル — 暗黙デフォルト詳細

!!! info "ページの位置付け"
    このページは `PORT_STORM_CONTROL` テーブルの **暗黙デフォルト・ハードコード挙動・YANG-実装乖離** を詳述する Phase A 分析ページ。
    テーブル概要・フィールド一覧・運用ヒントは [PORT_STORM_CONTROL テーブル](port-storm-control.md) を参照。

## 概要

BUM (Broadcast / Unknown-unicast / Unknown-multicast) storm control は `PORT_STORM_CONTROL` テーブルで設定される。
`orchagent` の `PolicerOrch::handlePortStormControlTable()` が CONFIG_DB を購読し、SAI policer を作成・適用する。

YANG と実装の間には複数の乖離 (discrepancy) とハードコード挙動が存在する。以下に詳細を示す。

<!-- defaults -->
## 暗黙デフォルトとハードコード挙動

<!-- evidence: meta/_intermediate/cdb-flow/storm-control-defaults.md -->

### 1. kbps — YANG optional だが実装は mandatory

YANG (`sonic-storm-control.yang`) の `kbps` leaf に `default` 文および `mandatory true` 宣言はない (YANG 上は optional)。

しかし `orchagent/policerorch.cpp:194-200` では:

```cpp
/*CIR is mandatory parameter*/
if (!cir)
{
    SWSS_LOG_ERROR("Failed to create storm control policer %s,\
            missing mandatory fields", storm_policer_name.c_str());
    return task_process_status::task_failed;
}
```

`kbps` が欠如したエントリは `task_failed` で破棄される。**YANG-実装 discrepancy**: YANG は optional、実装は mandatory。

証跡: `sonic-swss/orchagent/policerorch.cpp:194-200`

---

### 2. SAI policer ハードコード固定属性 (YANG / CLI 非公開)

YANG および CLI には存在しないが、orchagent が **常に固定値** で SAI policer を作成する属性:

| SAI 属性 | 固定値 | 変更可否 |
|---|---|---|
| `SAI_POLICER_ATTR_METER_TYPE` | `BYTES` | 不可 (ハードコード) |
| `SAI_POLICER_ATTR_MODE` | `STORM_CONTROL` | 不可 (ハードコード) |
| `SAI_POLICER_ATTR_RED_PACKET_ACTION` | `DROP` | 不可 (ハードコード) |
| `SAI_POLICER_ATTR_GREEN_PACKET_ACTION` | 未設定 → SAI/HW デフォルト依存 | 設定不可 |
| `SAI_POLICER_ATTR_YELLOW_PACKET_ACTION` | 未設定 → SAI/HW デフォルト依存 | 設定不可 |
| `SAI_POLICER_ATTR_CBS` | 未設定 → SAI/HW デフォルト依存 | 設定不可 |
| `SAI_POLICER_ATTR_COLOR_SOURCE` | 未設定 → SAI/HW デフォルト依存 | 設定不可 |

METER_TYPE を `BYTES` 以外 (例: `PACKETS`) にしたい場合は実装変更が必要。

証跡: `policerorch.cpp:156-169`

---

### 3. kbps → SAI CIR 変換: integer truncation (silent rounding)

変換式 (`policerorch.cpp:182`):

```
CIR (bytes/s) = kbps * 1000 / 8
```

C++ 整数演算のため `kbps % 8 != 0` の場合に **切り捨て**が発生する (silent rounding)。
kbps は通常大きな値のため実用影響は限定的だが、低レートでは注意が必要。

テストコードの逆変換 (`test_storm_control.py:178`):

```python
kbps = int(int(bps) / int(1000) * 8)
```

この逆変換も切り捨てを含む。ラウンドトリップで丸め誤差が生じる可能性あり。

証跡: `policerorch.cpp:181-184`, `sonic-swss/tests/test_storm_control.py:178`

---

### 4. update 時 remove-then-reapply による瞬間的 storm control 解除

既存エントリを更新する際の orchagent フロー (`policerorch.cpp:273-288`):

1. `port_attr.value.oid = SAI_NULL_OBJECT_ID` で storm control を **一時解除**
2. CIR のみ `set_policer_attribute` で更新 (METER_TYPE / MODE / RED_ACTION は更新対象外)
3. 新 policer oid を再 attach

update 時の CIR のみ更新制約 (`policerorch.cpp:250-255`):

```cpp
if (attr.id != SAI_POLICER_ATTR_CIR)
{
    continue;
}
```

METER_TYPE, MODE, RED_ACTION は作成時のみ設定可能。更新不可 (暗黙制約)。

!!! warning "瞬間 storm control 解除"
    kbps 値を変更すると、remove-then-reapply ウィンドウ中 (ミリ秒オーダー) にポートの storm control が解除される。
    BUM トラフィックが急増するタイミングでの変更は注意が必要。

証跡: `policerorch.cpp:273-288`, `policerorch.cpp:250-270`

---

### 5. allPortsReady ガード: 起動時 silent defer

`policerorch.cpp:379-382`:

```cpp
if (!gPortsOrch->allPortsReady())
{
    return;
}
```

全ポートの初期化完了前に CONFIG_DB に書き込まれたエントリは `doTask()` が即座リターンするため **処理が遅延される** (silent defer、エラーなし・syslog なし)。

証跡: `policerorch.cpp:379-382`

---

### 6. 非 Ethernet / ポート未発見: silent drop

`policerorch.cpp:131-144`:

| 条件 | 動作 |
|---|---|
| インタフェース名が `Ethernet` で始まらない | `SWSS_LOG_ERROR` → `task_success` 返却 → **erase (silent drop)** |
| `gPortsOrch->getPort()` でポート未発見 | `SWSS_LOG_ERROR` → `task_success` 返却 → **erase (silent drop)** |

`task_success` が返されるためエントリは `consumer.m_toSync` から erase される。**リトライなし**。

LAG (`PortChannel`) や VLAN を誤って指定した場合も同様に syslog error のみで黙って破棄される。

証跡: `policerorch.cpp:131-144`

---

### 7. BUM_STORM_CAPABILITY チェック: CLI のみ・orchagent は非チェック

`config/main.py:806-814` の `is_storm_control_supported()`:

```python
supported = state_db.get(state_db.STATE_DB, entry_name, "supported")
return supported
```

CLI (`config interface storm-control add`) は `STATE_DB:BUM_STORM_CAPABILITY|<storm_type>` の `supported` フィールドを確認し、非対応プラットフォームでは書き込みをスキップする。

しかし **orchagent 側には同様のチェックが存在しない**。`sonic-db-cli` 等で直接 CONFIG_DB に書き込んだ場合、capability 非対応プラットフォームでも orchagent が SAI call を試みる (SAI エラーで失敗する可能性あり)。

!!! note "プラットフォーム依存"
    BUM storm control の SAI 対応はプラットフォーム (ASIC) 依存。CLI を経由せず直接 DB 書き込みを行う場合は `BUM_STORM_CAPABILITY` を事前確認すること。

証跡: `config/main.py:806-814`

---

### 8. dead field — CBS, Green/Yellow packet action, Color Source

YANG にも CLI にも公開されていない SAI 属性:

| SAI 属性 | 挙動 |
|---|---|
| `SAI_POLICER_ATTR_CBS` | 未設定。SAI/HW デフォルト (多くの ASIC では 0 または HW 最小値) |
| `SAI_POLICER_ATTR_GREEN_PACKET_ACTION` | 未設定。SAI デフォルト (通常 FORWARD) |
| `SAI_POLICER_ATTR_YELLOW_PACKET_ACTION` | 未設定。SAI デフォルト (通常 FORWARD) |
| `SAI_POLICER_ATTR_COLOR_SOURCE` | 未設定。SAI デフォルト (通常 BLIND) |

プラットフォームにより挙動が異なる可能性がある。

---

### 9. policer 削除失敗後のリソースリーク (TODO コメント残存)

`policerorch.cpp:297-310`:

```cpp
/*TODO: Do the below policer cleanup in an API*/
if (SAI_STATUS_SUCCESS != sai_policer_api->remove_policer(...))
{
    SWSS_LOG_ERROR("Failed to remove policer %s, rv:%d", ...);
    /*TODO: Just doing a syslog. */
}
m_syncdPolicers.erase(storm_policer_name);
m_policerRefCounts.erase(storm_policer_name);
```

SAI `set_port_attribute` が失敗した際の cleanup パスで `remove_policer` に失敗した場合、syslog error のみで続行する。
`m_syncdPolicers` / `m_policerRefCounts` はクリアされるが SAI 側のリソースはリークの可能性あり。TODO コメントが未解決のまま残存。

証跡: `policerorch.cpp:297-310`

---

### 10. scripts/storm_control.py の validate バグ (dead validation)

`scripts/storm_control.py:68-86`:

```python
def validate_kbps(self, kbps):
    return True  # 常に True — バリデーションなし

def add_storm_config(self, port, storm_type, kbps):
    if not validate_interface(port):  # ← self なし → NameError
```

`validate_kbps()` は常に `True` を返す dead validation。
`add_storm_config()` / `del_storm_config()` では `validate_interface(port)` を `self.` なしで参照しており、実行時 `NameError` が発生する可能性がある。

正規の CLI パスは `config/main.py` 側の `storm_control_set_entry()` であり、`scripts/storm_control.py` の add/del パスは実質的に動作しない可能性がある。

証跡: `sonic-utilities/scripts/storm_control.py:68-86`

<!-- /defaults -->

<!-- ordering -->
## 書込み順序依存 (Phase B)

<!-- evidence: meta/_intermediate/cdb-flow/storm-control-ordering.md -->

`PolicerOrch::doTask()` / `handlePortStormControlTable()` (`sonic-swss/orchagent/policerorch.cpp`) の実装から導出した順序制約。

### 検出された順序依存

| # | 依存関係 | 方向 | 緩和策 |
|---|---|---|---|
| 1 | `PORT` (PortsOrch allPortsReady) → `PORT_STORM_CONTROL` | **先行必須** (全ポート初期化完了前は doTask が即 return) | 起動後は自動処理; 手動適用時は起動完了を確認 |
| 2 | `PORT_STORM_CONTROL` キー内ポート名が `Ethernet` で始まること | **先行必須** (PortChannel / VLAN は silent drop) | LAG メンバーポートに直接設定すること |
| 3 | 対象 `PORT` エントリが CONFIG_DB に存在すること | **先行必須** (`getPort()` 失敗 → task_success erase、リトライなし) | PORT を先に設定してから STORM_CONTROL を書き込む |
| 4 | 3 種 (broadcast / unknown-unicast / unknown-multicast) は相互独立 | 順不同で設定可 | — |
| 5 | kbps 値を更新する場合: 旧 policer の NULL → CIR 更新 → reapply の順序 | orchagent 内部固定順序 | — (orchagent 自動制御) |

### 主要な制約詳細

**PORT 先行必須 (依存 #1, #3)**:
`doTask()` 冒頭 (`policerorch.cpp:379-382`):

```cpp
if (!gPortsOrch->allPortsReady())
{
    return;
}
```

`gPortsOrch->allPortsReady()` が `false` の間、`doTask` は即 return する。SONiC 起動シーケンス中は PortsOrch が全ポートを学習し終わるまで PORT_STORM_CONTROL の処理は **自動的にキュー待機**される。

ポートが存在しない場合 (`policerorch.cpp:138-143`):

```cpp
if (!gPortsOrch->getPort(interface_name, port))
{
    SWSS_LOG_ERROR("Failed to apply storm-control %s to port %s. Port not found", ...);
    return task_process_status::task_success;  // サイレント erase
}
```

`task_success` が返されるため `consumer.m_toSync` からエントリが erase される。**リトライなし**。syslog ERROR は出力されるがオペレータ通知手段は限定的。

**Ethernet 以外 silent drop (依存 #2)**:
`policerorch.cpp:131-135` で ETHERNET_PREFIX チェックを行う。`PortChannel`・VLAN インタフェースは `task_success` で erase される (silent drop)。HLD では「physical interfaces のみ対応」と明記されているが、orchagent 側には YANG/CLI バリデーションへの依存がなく、直接 DB 書き込みの場合は同様に drop される。

証跡: `sonic-swss/orchagent/policerorch.cpp:131-143, 379-382`

### orchlist 起動順序

`orchdaemon.cpp:500` の orchlist 定義:

```
gSwitchOrch → gCrmOrch → gPortsOrch → gBufferOrch → ... → gPolicerOrch → ...
```

`gPortsOrch` は `gPolicerOrch` より先に登録されており、PortsOrch が allPortsReady を設定してから PolicerOrch の処理が有効になる設計。

### 順序フロー図

```
CONFIG_DB|PORT (PortsOrch allPortsReady = true)
  ↓ (先行必須)
CONFIG_DB|PORT_STORM_CONTROL|<Ethernet ifname>|<storm_type>
  kbps 値 (mandatory)
  ↓
PolicerOrch::handlePortStormControlTable()
  ├─ create_policer (meter=BYTES, mode=STORM_CONTROL, red_action=DROP, CIR=kbps*1000/8)
  └─ set_port_attribute (SAI_PORT_ATTR_{BROADCAST|FLOOD|MULTICAST}_STORM_CONTROL_POLICER_ID)
```

<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照（テーブル間依存）

`PORT_STORM_CONTROL` テーブルを処理する `PolicerOrch::handlePortStormControlTable()` が実行時に参照する他テーブル・Orch 内状態。YANG の leafref 定義は PORT への参照のみで、それ以外は実装レベルの暗黙依存である。コード調査の詳細は `meta/_intermediate/cdb-flow/storm-control-cross-refs.md` に記録した。

### 1. PORT（キーポート名の OID 解決 — 必須依存）

- **参照先**: CONFIG_DB `PORT` / PortsOrch
- **方向**: 読み取り (`gPortsOrch->getPort(interface_name, port)`)
- **参照元**: `policerorch.cpp:138`（PORT OID 解決）、`policerorch.cpp:206-214`（`SAI_PORT_ATTR_*_STORM_CONTROL_POLICER_ID` 設定）
- **意味**: キーの `<interface_name>` を PortsOrch で解決し、SAI ポート属性に policer OID をアタッチ / デタッチする。解決失敗時は `task_success` 返却で `m_toSync` から erase（**リトライなし**）。
- **YANG leafref**: `sonic-storm-control.yang` の `ifname` leaf は `PORT_LIST/name` への leafref を持つ（実装は orchagent 側実行時確認）。

### 2. `m_syncdPolicers`（Orch 内 policer OID キャッシュ）

- **参照先**: `PolicerOrch::m_syncdPolicers`（`unordered_map<string, sai_object_id_t>`）
- **方向**: 読み取り / 書き込み（Orch 内部状態）
- **参照元**: `policerorch.cpp:151`（update 判定）、`policerorch.cpp:239`（create 後登録）、`policerorch.cpp:245`（update 時 OID 取得）、`policerorch.cpp:309, 368`（delete 時消去）
- **意味**: 作成済み policer の OID を `<ifname>|<storm_type>` キーで保持し、update / delete 時に再利用する。Orch 再起動時はリセットされるため、warm-reboot 等でのリカバリはこのキャッシュに依存しない（SAI 再プログラムで復元）。

### 3. STATE_DB `BUM_STORM_CAPABILITY`（CLI のみ参照 — orchagent は非参照）

- **参照先**: `STATE_DB:BUM_STORM_CAPABILITY|<storm_type>` の `supported` フィールド
- **方向**: CLI (`config/main.py:806-813`) が書き込み前に確認
- **参照元**: `is_storm_control_supported()` in `config/main.py:806-813`
- **意味**: CLI が storm control 設定前に ASIC の BUM storm control サポートを確認する。orchagent 側には同等チェックが存在せず、DB に直接書き込んだ場合は SAI 呼び出しが試みられ、非対応時は SAI エラーで記録される（silent な SAI failure）。
- **非対称性**: CLI → STATE_DB 確認 → スキップ可能。orchagent → 非確認 → SAI fail-through。

### 4. ASIC_DB / SAI（policer と port 属性の書き込み先）

`handlePortStormControlTable()` が呼び出す SAI API と ASIC_DB への波及:

| SAI API | 操作 | コード箇所 |
|---------|------|----------|
| `sai_policer_api->create_policer()` | policer オブジェクト作成 | `policerorch.cpp:197-236` |
| `sai_policer_api->set_policer_attribute()` | CIR 値更新（update 時のみ） | `policerorch.cpp:250-263` |
| `sai_port_api->set_port_attribute()` | ポートへの policer OID アタッチ / NULL デタッチ | `policerorch.cpp:206-214, 283-286, 326-347` |
| `sai_policer_api->remove_policer()` | policer オブジェクト削除 | `policerorch.cpp:293-304, 349-361` |

いずれも syncd 経由で ASIC_DB に反映され、物理 ASIC へのプログラムが行われる。

### 参照関係サマリ

```
PORT_STORM_CONTROL テーブル
  |- [必須]  PORT (ifname → port OID → SAI_PORT_ATTR_*_STORM_CONTROL_POLICER_ID)
  |- [内部]  m_syncdPolicers (Orch 内 policer OID キャッシュ)
  |- [CLI側] STATE_DB:BUM_STORM_CAPABILITY (orchagent は非参照 — SAI fail-through)
  `- [出力]  ASIC_DB (SAI create/set/remove_policer, set_port_attribute)
```

<!-- /cross-refs -->

## 発見された discrepancy / 暗黙デフォルト サマリー

| # | 種別 | 対象 | 内容 |
|---|---|---|---|
| 1 | YANG-実装 discrepancy | `kbps` | YANG optional、実装 mandatory |
| 2 | ハードコード | SAI_POLICER_ATTR_METER_TYPE | 常に BYTES、変更不可 |
| 3 | ハードコード | SAI_POLICER_ATTR_MODE | 常に STORM_CONTROL、変更不可 |
| 4 | ハードコード | SAI_POLICER_ATTR_RED_PACKET_ACTION | 常に DROP、変更不可 |
| 5 | dead field (HW 依存) | CBS, Green/Yellow action, Color Source | YANG/CLI 非公開、HW デフォルト依存 |
| 6 | silent rounding | kbps → CIR 変換 | `kbps * 1000 / 8` の整数切り捨て |
| 7 | 書込み順依存 | update 時 remove-reapply | SAI NULL → CIR 更新 → reapply の間 storm control 解除 |
| 8 | silent drop | 非 Ethernet / ポート未発見 | `task_success` で erase、リトライなし |
| 9 | silent defer | 起動時 allPortsReady ガード | 全ポート初期化前は処理遅延 (エラーなし) |
| 10 | プラットフォーム依存 | capability チェック非対称 | CLI のみチェック、orchagent は非チェック |
| 11 | dead validation | scripts/storm_control.py | validate_kbps 常に True, add/del で NameError 可能性 |
| 12 | リソースリーク TODO | policer remove 失敗後 | SAI リソースリーク可能性、TODO 未解決 |

## 引用元

[^1]: YANG 定義: `sonic-storm-control.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-storm-control.yang>
[^2]: PolicerOrch 実装: `policerorch.cpp`. <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/policerorch.cpp>
[^3]: CLI 実装: `config/main.py`. <https://github.com/sonic-net/sonic-utilities/blob/master/config/main.py>
[^4]: BUM Storm Control HLD: `bum_storm_control_hld.md`. <https://github.com/sonic-net/SONiC/blob/master/doc/bum_storm_control/bum_storm_control_hld.md>

## 関連ページ

- [PORT_STORM_CONTROL テーブル (概要)](port-storm-control.md)
- [CONFIG_DB: PORT](port.md)
- [CONFIG_DB: POLICER](policer.md)
