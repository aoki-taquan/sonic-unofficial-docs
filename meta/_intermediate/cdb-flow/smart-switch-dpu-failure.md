# smart-switch-dpu — Phase D: failure / invalid-input handling

調査日: 2026-05-17  
調査対象: chassisd, dhcp_cfggen, sonic-smart-switch.yang, sonic-yang-models

---

## 1. YANG バリデーション失敗（書き込み拒否）

### MID_PLANE_BRIDGE — bridge フィールドのパターン違反

`sonic-smart-switch.yang:65` に `pattern "bridge-midplane"` があり、`bridge` フィールドが
`"bridge-midplane"` 以外の値で書き込まれると YANG バリデーション違反となり、CLI 経由の
書き込みは即座に拒否される。`must "(current()/../ip_prefix)"` 制約（行 69）により `ip_prefix`
なしで `bridge` のみを書き込んでもバリデーション違反となる。

### DPUS — midplane_interface must 制約違反

`sonic-smart-switch.yang:101` の `must "(current() = current()/../dpu_name)"` は
`midplane_interface` が `dpu_name` と異なる値を持つことを禁止する。不一致な値を書き込むと
CLI が拒否。

### DPU — dpu_id パターン違反

`dpu_id` フィールドは `pattern [0-7]`（行 160）。`"8"` 以上の値、2 桁の値、負数はすべて
YANG バリデーション違反で書き込み拒否。

### DASH_HA_GLOBAL_CONFIG — leafref 解決失敗

`dpu_vnet`（行 305）は VNET テーブルへの `leafref`。存在しない VNET 名を `dpu_vnet` に
書き込むと YANG バリデーション違反（`error-message "dpu_vnet length must be between 1 and
255 characters"` は長さチェックのみ; 実際の leafref 解決は YANG ランタイムが行う）。

---

## 2. dhcpservd — midplane DHCP 設定の部分的失敗

### smart_switch が False の場合の静かなスキップ

`dhcp_cfggen.py:76`:
```python
mid_plane, dpus = self._parse_dpu(dpus_table, mid_plane_table) if smart_switch else ({}, {})
```
`DEVICE_METADATA|localhost.subtype != "SmartSwitch"` の場合、戻り値が空辞書になりエラーログなし。
`MID_PLANE_BRIDGE` / `DPUS` の内容は完全に無視される（サイレント失敗）。

### bridge / ip_prefix いずれか欠如

`dhcp_cfggen.py:84`:
```python
if smart_switch and "bridge" in mid_plane and "ip_prefix" in mid_plane:
```
どちらか一方のフィールドが欠如すると条件が `False` になり、ミッドプレーンブリッジが
`dhcp_interfaces` に登録されない。`DPUS` エントリが存在しても DPU への IP 払い出しは停止する。
エラーログは出力されない。

### midplane_interface なしの DPUS エントリ

`dhcp_cfggen.py:119`:
```python
dpus = set([dpu_value["midplane_interface"] for dpu_value in dpus_table.values()
           if "midplane_interface" in dpu_value])
```
`midplane_interface` フィールドが存在しない `DPUS` エントリはリスト内包表記でフィルタアウトされる。
エラーログなし。対応する DPU への IP 払い出しが発生しない。

---

## 3. chassisd — midplane 初期化失敗

`chassisd:719`:
```python
self.midplane_initialized = try_get(chassis.init_midplane_switch, default=False)
if not self.midplane_initialized:
    self.log_error("Chassisd midplane intialization failed")
```
`init_midplane_switch()` が `False` または例外を返した場合、`midplane_initialized = False`。
後続の `check_midplane_reachability()` は行頭で `if not self.midplane_initialized: return` 
（行 1075-1076）し全体をスキップ。`CHASSIS_STATE_DB.DPU_STATE` の midplane state は更新されない。

`CHASSIS_MODULE` エントリが存在しない DPU（admin_state = empty）は起動時に
`MODULE_ADMIN_DOWN` として扱われ `set_admin_state_gracefully()` が呼ばれる（行 1382-1397）。

---

## 4. DPU offline → CHASSIS_STATE_DB 伝播

`module_db_update()` がポーリング周期ごとに DPU の oper_status を取得し、
`MODULE_STATUS_OFFLINE` へ遷移したことを検知すると:

1. `persist_dpu_reboot_time(key)` — `/host/reboot-cause/module/<dpu>/prev_reboot_time.txt` に記録
2. `persist_dpu_reboot_cause(reboot_cause, key)` — JSON ファイルへ保存 + symlink 更新 +
   最大 `MAX_HISTORY_FILES=10` 件でローテーション
3. `update_dpu_reboot_cause_to_db(key)` — `CHASSIS_STATE_DB.REBOOT_CAUSE|<DPU>|<time>` に書き込み

midplane 疎通切断時 (`check_midplane_reachability`:1093-1105):
- `midplane_access=False` かつ 前回 `True` → `log_warning("Unexpected: Module lost midplane connectivity")`
- `update_dpu_state(key, "down")` が `CHASSIS_STATE_DB.DPU_STATE` の
  `dpu_midplane_link_state`, `dpu_control_plane_state`, `dpu_data_plane_state` を全て `"down"` に設定

CONFIG_DB の `DPU` / `DPUS` / `MID_PLANE_BRIDGE` テーブル自体は書き換えられない。

---

## 5. DPU リブート判定ロジック（MAX_DPU_REBOOT_DURATION）

`module_db_update()` の online 復帰時処理（行 812-839）:
- `stored_cause` と `current_cause` が同一で、かつ down から online への経過時間が
  `MAX_DPU_REBOOT_DURATION=800` 秒未満 → `is_reboot=True`（reboot cause の再書き込みをスキップ）
- 条件未達（原因不一致 / 800 秒超過 / ファイルなし）→ reboot cause を新規書き込み

`DEFAULT_DPU_REBOOT_TIMEOUT=360` は `platform.json` の `dpu_reboot_timeout` フィールドで
上書き可能（行 727）。`MAX_DPU_REBOOT_DURATION=800` はハードコード（行 83）。

---

## 6. CONFIG_DB への影響（まとめ）

| 障害シナリオ | CONFIG_DB への影響 | 挙動 |
|---|---|---|
| YANG パターン/must 制約違反 | 書き込み拒否 | CLI がエラーを返す |
| `subtype != SmartSwitch` | 影響なし（読み取りのみスキップ） | サイレント。DHCP 設定不生成 |
| `bridge`/`ip_prefix` 片欠落 | 影響なし（スキップ） | サイレント。midplane DHCP 停止 |
| `midplane_interface` 欠落 DPUS | 影響なし（フィルタアウト） | サイレント。当該 DPU の IP 払い出しなし |
| DPU offline 遷移 | CONFIG_DB は不変。CHASSIS_STATE_DB 更新 | reboot cause/time 記録 |
| midplane 切断 | CONFIG_DB は不変。CHASSIS_STATE_DB 更新 | cp/dp state → `down` |
| midplane 初期化失敗 | CONFIG_DB 不変 | midplane state 更新停止。syslog ERROR |

---

## 証拠コード参照

- `chassisd:82-83` — `DEFAULT_DPU_REBOOT_TIMEOUT=360`, `MAX_DPU_REBOOT_DURATION=800`
- `chassisd:106` — `MAX_HISTORY_FILES=10`
- `chassisd:718-720` — midplane 初期化失敗ログ
- `chassisd:801-840` — offline → online 遷移 + reboot cause 記録
- `chassisd:1075-1105` — `check_midplane_reachability()` + DPU_STATE 更新
- `dhcp_cfggen.py:76,84,119` — smart_switch/bridge/ip_prefix/midplane_interface 各チェック
- `sonic-smart-switch.yang:65,69,90,98,101,160,198,233,295-306` — YANG 制約
