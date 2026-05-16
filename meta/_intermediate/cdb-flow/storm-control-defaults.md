# Phase A: STORM_CONTROL / PORT_STORM_CONTROL — 暗黙デフォルト調査

対象テーブル: `PORT_STORM_CONTROL`
YANG モジュール: `sonic-storm-control.yang`
消費コード: `sonic-swss/orchagent/policerorch.cpp` (`handlePortStormControlTable`)

---

## 1. kbps — YANG デフォルトなし・orchagent が実質 mandatory 扱い

`sonic-storm-control.yang` の `kbps` leaf:
- `default` 文 **なし**
- `mandatory true` 宣言 **なし** (YANG 上は optional leaf)

実装 (`policerorch.cpp:194-200`):
```cpp
/*CIR is mandatory parameter*/
if (!cir)
{
    SWSS_LOG_ERROR("Failed to create storm control policer %s,\
            missing mandatory fields", storm_policer_name.c_str());
    return task_process_status::task_failed;
}
```

→ kbps が欠如したエントリは `task_failed` で破棄。YANG-実装 discrepancy: YANG は optional、実装は mandatory。

---

## 2. SAI policer ハードコード固定属性 (YANG / CLI 非公開)

`policerorch.cpp:156-169`:
```cpp
/*Meter type hardcoded to BYTES*/
attr.id = SAI_POLICER_ATTR_METER_TYPE;
attr.value.s32 = (sai_meter_type_t) meter_type_map.at("BYTES");

/*Policer mode hardcoded to STORM_CONTROL*/
attr.id = SAI_POLICER_ATTR_MODE;
attr.value.s32 = (sai_policer_mode_t) policer_mode_map.at("STORM_CONTROL");

/*Red Packet Action hardcoded to DROP*/
attr.id = SAI_POLICER_ATTR_RED_PACKET_ACTION;
attr.value.s32 = packet_action_map.at("DROP");
```

固定属性一覧:

| SAI 属性 | 固定値 | 可変か |
|---|---|---|
| `SAI_POLICER_ATTR_METER_TYPE` | `BYTES` | 不可 |
| `SAI_POLICER_ATTR_MODE` | `STORM_CONTROL` | 不可 |
| `SAI_POLICER_ATTR_RED_PACKET_ACTION` | `DROP` | 不可 |
| `SAI_POLICER_ATTR_GREEN_PACKET_ACTION` | 未設定 (SAI/HW デフォルト依存) | 設定不可 |
| `SAI_POLICER_ATTR_YELLOW_PACKET_ACTION` | 未設定 (SAI/HW デフォルト依存) | 設定不可 |
| `SAI_POLICER_ATTR_CBS` | 未設定 (SAI/HW デフォルト依存) | 設定不可 |
| `SAI_POLICER_ATTR_COLOR_SOURCE` | 未設定 (SAI/HW デフォルト依存) | 設定不可 |

---

## 3. kbps → SAI CIR 変換: integer truncation (silent rounding)

`policerorch.cpp:181-184`:
```cpp
attr.id = SAI_POLICER_ATTR_CIR;
/*convert kbps to bps*/
attr.value.u64 = (stoul(value)*1000/8);
```

変換式: `CIR_bytes_per_s = kbps * 1000 / 8`

C++ 整数演算のため、`kbps % 8 != 0` の場合に切り捨て。ただし kbps は通常 1000 単位以上の大きな値のため実用影響は小さい。

逆変換 (test_storm_control.py:178):
```python
kbps = int(int(bps) / int(1000) * 8)
```

この逆変換も切り捨てを含む。アサーション `assert str(kbps) == str(kbps_value)` はテストでのみ検証。

---

## 4. update 時 remove-then-reapply による瞬間的 storm control 解除

`policerorch.cpp:273-288`:
```cpp
if (update)
{
    SWSS_LOG_NOTICE("update storm-control policer %s", storm_policer_name.c_str());
    port_attr.value.oid = SAI_NULL_OBJECT_ID;
    /*Remove and re-apply policer*/
    sai_status_t status = sai_port_api->set_port_attribute(port.m_port_id, &port_attr);
    ...
}
```

update フロー:
1. port_attr を `SAI_NULL_OBJECT_ID` にセット → storm control 一時解除
2. CIR のみ `set_policer_attribute` で更新 (METER_TYPE/MODE/RED_ACTION は更新不可)
3. 新 policer oid を再 attach

`policerorch.cpp:250-270` で更新時は CIR のみ更新し他属性はスキップ:
```cpp
if (attr.id != SAI_POLICER_ATTR_CIR)
{
    continue;
}
```

→ METER_TYPE, MODE, RED_ACTION は作成時のみ設定、更新不可 (暗黙)。
→ remove-reapply ウィンドウ中、ポートで storm control が一時的に解除される (ミリ秒オーダー)。

---

## 5. allPortsReady ガード: 起動時 silent defer

`policerorch.cpp:379-382`:
```cpp
if (!gPortsOrch->allPortsReady())
{
    return;
}
```

全ポート初期化前に CONFIG_DB へ書き込まれたエントリは `doTask()` が即座リターンするため処理遅延。エラーなし、syslog なし。

---

## 6. 非 Ethernet / ポート未発見: silent drop (task_success 返却)

`policerorch.cpp:131-144`:
```cpp
if (strncmp(interface_name.c_str(), ETHERNET_PREFIX, strlen(ETHERNET_PREFIX)))
{
    SWSS_LOG_ERROR("...: Unsupported / Invalid interface %s", ...);
    return task_process_status::task_success;  // ← silent drop
}
if (!gPortsOrch->getPort(interface_name, port))
{
    SWSS_LOG_ERROR("Failed to apply storm-control %s to port %s. Port not found", ...);
    return task_process_status::task_success;  // ← silent drop
}
```

SWSS_LOG_ERROR は出るが `task_success` → エントリは `erase()` され **リトライなし**。
LAG/VLAN インタフェースを指定しても syslog error のみで黙って破棄。

---

## 7. BUM_STORM_CAPABILITY チェック: CLI のみ・orchagent は未チェック

`config/main.py:806-814`:
```python
def is_storm_control_supported(storm_type, namespace):
    ...
    supported = state_db.get(state_db.STATE_DB, entry_name,"supported")
    return supported
```

`storm_control_set_entry()` は `is_storm_control_supported()` == 0 の場合に書き込みをスキップ。
ただし orchagent (`handlePortStormControlTable`) には同様のチェックなし。
直接 `sonic-db-cli` 等で CONFIG_DB に書き込んだ場合は capability 非対応プラットフォームでも orchagent が SAI call を試みる。

---

## 8. dead field — CBS, Green/Yellow packet action

YANG に存在しない (公開されていない) SAI 属性:
- `SAI_POLICER_ATTR_CBS` (Committed Burst Size)
- `SAI_POLICER_ATTR_GREEN_PACKET_ACTION`
- `SAI_POLICER_ATTR_YELLOW_PACKET_ACTION`
- `SAI_POLICER_ATTR_COLOR_SOURCE`

これらは orchagent がセットせず、SAI/HW のデフォルト値が使われる。プラットフォームにより挙動が異なる可能性あり。

---

## 9. update 時 remove 失敗後のリソースリーク TODO

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

SAI set_port_attribute 失敗 → remove_policer 試行 → 失敗しても syslog のみで続行。
`m_syncdPolicers` / `m_policerRefCounts` はリークの可能性。TODO コメントが残存 (未解決)。

---

## 10. policer 内部名: `_<ifname>_<storm_type>`

`policerorch.cpp:146`:
```cpp
const auto storm_policer_name = "_"+interface_name+"_"+storm_type;
```

内部 policer 名はアンダースコアプレフィックス + インタフェース名 + ストームタイプ。
CONFIG_DB の key とは異なる形式 (`_Ethernet0_broadcast` 等)。
`PolicerOrch::policerExists()` などの API ではこの内部名で管理。

---

## 11. storm_control.py (scripts/) の validate 関数バグ

`scripts/storm_control.py:68-69`:
```python
def validate_kbps(self, kbps):
    return True  # 常に True を返す (バリデーションなし)
```

`validate_interface()` では `port.startswith("Eth")` のみチェック。
`validate_kbps()` は常に True で実質バリデーションなし (dead validation)。

`add_storm_config()` / `del_storm_config()` では `validate_interface()` が未バインドの関数として参照 (`validate_interface(port)` → `self.validate_interface(port)` であるべきところ self なし)。
→ scripts/storm_control.py の add/del パスは実際にはバグで動作しない可能性 (NameError)。
CLI の正規パスは `config/main.py` 側。

---

## まとめ: 発見された discrepancy / implicit defaults 一覧

| # | 種別 | フィールド/属性 | 内容 |
|---|---|---|---|
| 1 | YANG-実装 discrepancy | `kbps` | YANG optional だが実装は mandatory |
| 2 | ハードコード | SAI_POLICER_ATTR_METER_TYPE | 常に BYTES |
| 3 | ハードコード | SAI_POLICER_ATTR_MODE | 常に STORM_CONTROL |
| 4 | ハードコード | SAI_POLICER_ATTR_RED_PACKET_ACTION | 常に DROP |
| 5 | dead field (HW 依存) | CBS, Green/Yellow action | YANG/CLI 非公開、HW デフォルト依存 |
| 6 | silent rounding | kbps → CIR 変換 | kbps * 1000 / 8 の整数切り捨て |
| 7 | 書込み順依存 | update 時 remove-reapply | SAI NULL → CIR更新 → reapply の間 storm control 解除 |
| 8 | silent drop | 非 Ethernet / ポート未発見 | task_success で erase、リトライなし |
| 9 | dead consumer | orchestrator path | allPortsReady() ガードで silent defer |
| 10 | プラットフォーム依存 | capability チェック非対称 | CLI のみチェック、orchagent は非チェック |
| 11 | dead validation | scripts/storm_control.py | validate_kbps 常に True、add/del に self なし参照バグ |
| 12 | リソースリーク TODO | policer remove 失敗後 | m_syncdPolicers から erase するが SAI リソースリーク |
