# VRRP — Phase B 書込み順依存スキャンノート

対象テーブル: `VRRP` / `VRRP6` / `VRRP_TRACK` / `VRRP6_TRACK`
Consumer: `macvlanmgrd` (VRRP インスタンス → Linux macvlan デバイス作成・vrrpd 設定)
スキャン範囲: `sonic-utilities/config/main.py` (vrrp / vrrp6 サブコマンド全行精読)、`sonic-vrrp.yang` (custom-validation 宣言)、VRRP_Adaptation_HLD.md 全行精読

---

## 検出した順序依存・タイミング依存

### 1. インターフェース先行必須 — INTERFACE / VLAN_INTERFACE / PORTCHANNEL_INTERFACE が存在しないと CLI が reject

- `add_vrrp_ip()` (config/main.py:6889-6890):
  ```python
  if interface_name not in config_db.get_table(table_name):
      ctx.fail("Router Interface '{}' not found".format(interface_name))
  ```
  `get_interface_table_name()` は `Ethernet` → `INTERFACE`、`Vlan` → `VLAN_INTERFACE`、`PortChannel` → `PORTCHANNEL_INTERFACE` に解決する。
  LOOPBACK_INTERFACE は明示的に reject される。
- **順序依存**: `VRRP|<ifname>|<vrid>` を書く前に、対応するインターフェーステーブル (`INTERFACE|Ethernet0`、`VLAN_INTERFACE|Vlan100` 等) の親エントリが CONFIG_DB に存在しなければならない。
- evidence: `config/main.py:6886-6892`

### 2. VRRP インスタンス先行必須 — VRRP_TRACK は VRRP の存在を前提とする

- `add_track_interface()` (config/main.py:7017-7019):
  ```python
  vrrp_entry = config_db.get_entry("VRRP", (interface_name, str(vrrp_id)))
  if not vrrp_entry:
      ctx.fail("vrrp instance {} not found on interface {}".format(vrrp_id, interface_name))
  ```
- **順序依存**: `VRRP_TRACK|<ifname>|<vrid>|<trackifname>` は `VRRP|<ifname>|<vrid>` が存在するときのみ書き込み可能。直接 redis-cli で書く場合は CLI ガードをバイパスできるが、macvlanmgrd が VRRP インスタンスのコンテキストなしに TRACK エントリを受け取った際の挙動は未定義。
- evidence: `config/main.py:7017-7020`

### 3. トラック対象インターフェース先行必須 — track_interface も存在チェック

- `add_track_interface()` (config/main.py:7014-7016):
  ```python
  if track_interface not in config_db.get_table(table_name_t):
      ctx.fail("Router Interface '{}' not found".format(track_interface))
  ```
- **順序依存**: `VRRP_TRACK` の `trackifname` に指定するインターフェース (`Ethernet`/`Vlan`/`PortChannel`) も CONFIG_DB に既存のインターフェースエントリがなければならない。
- evidence: `config/main.py:7013-7016`

### 4. VRRP6 は VRRP6_TRACK の前提 — 同様の依存

- `VRRP6_TRACK` に対応する IPv6 系の `add_track_interface_v6()` も同様に `VRRP6` エントリの存在チェックを行う (対称構造、HLD p.17)。
- **順序依存**: `VRRP6_TRACK|<ifname>|<vrid>|<trackifname>` は `VRRP6|<ifname>|<vrid>` の後。
- evidence: VRRP_Adaptation_HLD.md, sonic-vrrp.yang:`VRRP6_TRACK_LIST.baseifname` leafref

### 5. VIP アドレス重複防止 — 他インスタンスに既存の VIP は reject

- `check_vrrp_ip_exist()` (config/main.py:~6894) により、CONFIG_DB 内の全 `VRRP` / `VRRP6` エントリを走査してすでに登録済みの VIP アドレスがないか確認する。
- **順序依存なし**（重複は同時書き込みでなければ自然に検出される）が、同一 VIP を複数インスタンスに設定しようとすると CLI が abort する。
- evidence: `config/main.py:6894`

### 6. macvlanmgrd の起動順 — VRRP コンテナ起動前の CONFIG_DB 書き込みは safe

- HLD の "ADD/DEL VRRP instance" フロー図によると、macvlanmgrd は CONFIG_DB の `VRRP` テーブルを subscribe し、起動後に全エントリをリプレイする。
- **順序依存なし**（CONFIG_DB 書き込みが macvlanmgrd 起動前でも、起動後に一括処理される）。ただし macvlan デバイスへの反映は macvlanmgrd 起動以降になるため、**書き込み後即時に FRR vrrpd が動作することは保証されない**。
- evidence: VRRP_Adaptation_HLD.md "ADD/DEL VRRP instance" セクション

### 7. YANG leafref — VRRP_TRACK の baseifname は VRRP_LIST/ifname を参照

- `sonic-vrrp.yang`:
  ```yang
  leaf baseifname {
      type leafref {
          path "../../../VRRP/VRRP_LIST/ifname";
      }
  }
  ```
- YANG バリデーション経路（sonic-yang-mgmt / GNMI / REST）では `VRRP_TRACK` 書き込み時に `VRRP` の当該 `ifname` エントリが存在しないと leafref エラーで reject される。
- evidence: `SONiC/doc/vrrp/sonic-vrrp.yang`

---

## 順序依存サマリ

| # | 依存関係 | 区分 | 破った場合の挙動 |
|---|----------|------|----------------|
| 1 | INTERFACE / VLAN_INTERFACE / PORTCHANNEL_INTERFACE エントリ → VRRP インスタンス作成 | 強制先行 (CLI reject) | `ctx.fail("Router Interface '{}' not found")` |
| 2 | VRRP\|<ifname>\|<vrid> → VRRP_TRACK\|<ifname>\|<vrid>\|<trackifname> | 強制先行 (CLI reject) | `ctx.fail("vrrp instance {} not found")` |
| 3 | INTERFACE / VLAN_INTERFACE / PORTCHANNEL_INTERFACE エントリ → VRRP_TRACK の trackifname | 強制先行 (CLI reject) | `ctx.fail("Router Interface '{}' not found")` |
| 4 | VRRP6\|<ifname>\|<vrid> → VRRP6_TRACK | 強制先行 (YANG leafref + CLI) | leafref reject または macvlanmgrd 未定義挙動 |
| 5 | VIP 重複 | 非順序（重複禁止制約） | CLI abort（`check_vrrp_ip_exist` reject） |
| 6 | macvlanmgrd 起動 → VRRP 反映 | 一過性（起動後リプレイで解消） | macvlan デバイス作成が起動後に遅延 |
| 7 | YANG leafref: VRRP_TRACK.baseifname → VRRP_LIST.ifname | 強制先行 (YANG) | sonic-yang-mgmt が leafref エラーで reject |

### スケール制約（書き込み前に確認が必要な上限値）

| 制約 | 上限 | evidence |
|------|------|---------|
| 全 VRRP インスタンス数 | 254 | `config/main.py:6912-6913` |
| 1 インターフェースあたり VRRP インスタンス数 | 16 | `config/main.py:6921-6924` |
| 1 VRRP インスタンスあたり VIP 数 | 4 | `config/main.py:6908-6910`、YANG `max-elements 4` |
| 1 VRRP インスタンスあたりトラック インターフェース数 | 8 | `config/main.py:7034-7038` |
| VRRP_LIST / VRRP6_LIST max-elements | 128 | `sonic-vrrp.yang:max-elements 128` |
