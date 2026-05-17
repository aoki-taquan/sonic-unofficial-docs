# SmartSwitch MID_PLANE_BRIDGE / DHCP_SERVER_IPV4_PORT — Phase B 書込み順依存スキャンノート

対象テーブル: `MID_PLANE_BRIDGE`, `DHCP_SERVER_IPV4_PORT`, `DPUS`
Consumer: `dhcpservd` (`dhcp_cfggen.py`, `dhcpservd.py`)、`dhcprelayd` (`dhcprelayd.py`)
スキャン範囲: `dhcp_cfggen.py` `generate()` / `_parse_dpu()` / `_construct_obj_for_template()`、`dhcprelayd.py` `start()` / `refresh_dhcrelay()`、`dhcp_db_monitor.py` `MidPlaneTableEventChecker` / `DpusTableEventChecker`

---

## 検出した順序依存・タイミング依存

### 1. DEVICE_METADATA.subtype — SmartSwitch 経路の分岐条件

- `dhcp_cfggen.py:65-76`: `generate()` は最初に `DEVICE_METADATA` を読み `is_smart_switch(device_metadata)` を評価する。
- `is_smart_switch()` (`utils.py:153-161`) は `device_metadata.get("localhost", {}).get("subtype", "") == "SmartSwitch"` を返す。
- `smart_switch` が `False` の場合、`_parse_dpu()` は呼ばれず `mid_plane = {}`, `dpus = {}` となる（`dhcp_cfggen.py:76`）。
- **順序依存**: `DEVICE_METADATA|localhost.subtype = "SmartSwitch"` が CONFIG_DB に存在しない状態で `dhcpservd` が起動または設定を再生成すると、`MID_PLANE_BRIDGE` / `DHCP_SERVER_IPV4_PORT` / `DPUS` テーブルが存在していても SmartSwitch 用の DHCP 設定が生成されない。
- `config_samples.py:83` では `DEVICE_METADATA` への `subtype` 設定が `MID_PLANE_BRIDGE` 設定よりも先に行われる。
- evidence: `dhcp_cfggen.py:65-76`; `utils.py:153-161`; `config_samples.py:82-90`

### 2. MID_PLANE_BRIDGE|GLOBAL — dhcp_cfggen が bridge/ip_prefix を同時検証

- `dhcp_cfggen.py:84`: `if smart_switch and "bridge" in mid_plane and "ip_prefix" in mid_plane:` の条件をすべて満たしたときのみ SmartSwitch 用サブネットを `dhcpd.conf` に追加する。
- `_parse_dpu()` (`dhcp_cfggen.py:102-121`) は `mid_plane_table.get("GLOBAL", {})` の `bridge` / `ip_prefix` フィールドを取得する。いずれかが欠けていると SmartSwitch サブネット設定がスキップされる。
- **順序依存**: `MID_PLANE_BRIDGE|GLOBAL.bridge` と `MID_PLANE_BRIDGE|GLOBAL.ip_prefix` は**両方同時に**書き込む必要がある。片方のみ書いた状態で `dhcpservd` の再生成が走ると、SmartSwitch ブリッジのサブネットが省略された `dhcpd.conf` が生成される。
- YANG `must` 制約 (`sonic-smart-switch.yang:must "(current()/../ip_prefix)"`) も `bridge` と `ip_prefix` の同時存在を強制する。
- evidence: `dhcp_cfggen.py:84`, `dhcp_cfggen.py:102-121`; `sonic-smart-switch.yang:63-74`

### 3. DPUS — DHCP_SERVER_IPV4_PORT の leafref 源

- `dhcp_cfggen.py:102-121`: `_parse_dpu()` は `dpus_table`（`DPUS` テーブル全体）と `mid_plane_table` の両方を引数に取り、DPUS の `midplane_interface` フィールドを参照して DPU → midplane インターフェース対応を構築する。
- `DHCP_SERVER_IPV4_PORT` の `port` フィールドは `DPUS.<dpu_name>.midplane_interface` への leafref であるため（YANG `sonic-smart-switch.yang`）、`DPUS` エントリが存在しない状態で `DHCP_SERVER_IPV4_PORT` を書いても YANG バリデーションで reject される。
- **順序依存（YANG 強制）**: `DPUS|<dpu_name>` エントリは `DHCP_SERVER_IPV4_PORT` エントリより先に書かなければならない。
- evidence: `dhcp_cfggen.py:102-121`; `sonic-smart-switch.yang:94-103`

### 4. DHCP_SERVER_IPV4|bridge-midplane — relay が参照する前提

- `dhcprelayd.py:84-102`: `refresh_dhcrelay()` は `DHCP_SERVER_IPV4` テーブルを取得し、`dhcp_interface == mid_plane_bridge_name and self.smart_switch` の場合に `MID_PLANE_CHECKER` を有効化する。
- `DHCP_SERVER_IPV4|bridge-midplane.state` が `"enabled"` でなければ `dhcp_interfaces` に追加されず relay は起動しない (`dhcprelayd.py:91-92`)。
- **順序依存**: `DHCP_SERVER_IPV4|bridge-midplane` は `MID_PLANE_BRIDGE|GLOBAL` と同時か直後に書く必要がある。relay が `MID_PLANE_CHECKER` 経由で `MID_PLANE_BRIDGE` 変更を検知する前に `DHCP_SERVER_IPV4` が存在しないと、relay が midplane ブリッジをインターフェースとして認識しない。
- `config_samples.py:133-143` でも `MID_PLANE_BRIDGE` 設定後に `DHCP_SERVER_IPV4` / `DHCP_SERVER_IPV4_PORT` を設定している。
- evidence: `dhcprelayd.py:84-102`; `config_samples.py:133-143`

### 5. dhcp_server Feature — テーブル投入後に有効化

- `dhcpservd.py:89-100`: `dhcpservd.start()` は起動時に `dump_dhcp4_config()` を呼び、その時点の CONFIG_DB 内容を使って Kea 設定を生成する。
- `FEATURE|dhcp_server.state = "enabled"` は `DHCP_SERVER_IPV4` / `MID_PLANE_BRIDGE` / `DPUS` / `DHCP_SERVER_IPV4_PORT` の全テーブルが揃った後に有効化することで、初回起動時から正しい設定が生成される。
- **順序依存（推奨）**: CONFIG_DB の SmartSwitch 関連テーブルをすべて書いてから `dhcp_server` Feature を enable する。Feature 有効化後に `MID_PLANE_BRIDGE` を書くと、`MidPlaneTableEventChecker` 経由で再生成がトリガーされるが、起動直後の空設定期間が生じる可能性がある。
- evidence: `dhcpservd.py:89-100`; `dhcp_db_monitor.py:349-378` (`MidPlaneTableEventChecker`, `DpusTableEventChecker`)

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `DEVICE_METADATA\|localhost.subtype = "SmartSwitch"` → `MID_PLANE_BRIDGE` / `DHCP_SERVER_IPV4_PORT` 処理 | 先行必須（欠如時 SmartSwitch 経路が完全スキップ） | `is_smart_switch()` は後から再評価される。`MidPlaneTableEventChecker` 変更で `dhcpservd` が再生成トリガー |
| 2 | `MID_PLANE_BRIDGE\|GLOBAL.bridge` と `ip_prefix` の**同時書き込み** | 必須（片方欠如で SmartSwitch サブネット生成がスキップ） | YANG `must` 制約が CLI 経由の不整合書き込みを拒否 |
| 3 | `DPUS\|<dpu_name>` → `DHCP_SERVER_IPV4_PORT\|bridge-midplane\|<dpu>` | 先行必須（YANG leafref 制約） | CLI / sonic-cfggen は YANG バリデーションで reject |
| 4 | `MID_PLANE_BRIDGE\|GLOBAL` + `DHCP_SERVER_IPV4\|bridge-midplane` → `dhcprelayd` midplane 認識 | 同時または先行推奨 | `MidPlaneTableEventChecker` で変更後に自動再評価 |
| 5 | 全 SmartSwitch テーブル → `FEATURE\|dhcp_server.state=enabled` | 推奨先行（初回起動時の設定欠落回避） | 後から Feature 有効化しても `MidPlaneTableEventChecker` で自動再生成 |
