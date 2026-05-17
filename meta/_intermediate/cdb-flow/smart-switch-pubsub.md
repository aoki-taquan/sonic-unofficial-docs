# SmartSwitch MID_PLANE_BRIDGE / DHCP_SERVER_IPV4_PORT — Phase G: 通信メカニズム スキャンノート

対象テーブル: `MID_PLANE_BRIDGE`, `DHCP_SERVER_IPV4_PORT`, `DPUS`
スキャン範囲:
- `sonic-buildimage/src/sonic-dhcp-utilities/dhcp_utilities/common/dhcp_db_monitor.py`（全行精読）
- `sonic-buildimage/src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcpservd.py`
- `sonic-buildimage/src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcp_cfggen.py:17-100`
- `sonic-buildimage/src/sonic-dhcp-utilities/dhcp_utilities/dhcprelayd/dhcprelayd.py`

---

## 購読構造の全体像

### 1. MID_PLANE_BRIDGE → dhcpservd (MidPlaneTableEventChecker)

- **購読方式**: `SubscriberStateTable` を内包した `MidPlaneTableEventChecker`（`ConfigDbEventChecker` 基底クラス経由）
- **テーブル名定数**: `MID_PLANE_BRIDGE = "MID_PLANE_BRIDGE"` (`dhcp_db_monitor.py:16`)
- **select タイムアウト**: `DEFAULT_SELECT_TIMEOUT = 5000` ms (`dhcpservd.py:25`)
- **登録箇所**: `dhcpservd.py:144` — `checkers.append(MidPlaneTableEventChecker(sel, dhcp_db_connector.config_db))`
- **有効化タイミング**: SmartSwitch モードのとき `SMART_SWITCH_CHECKER` に `"MidPlaneTableEventChecker"` が含まれ、`dhcp_cfggen.py:97-98` の `subscribe_table |= set(SMART_SWITCH_CHECKER)` で `enabled_checker` に追加 → `dhcpservd.py:96` の `enable_checkers()` で `SubscriberStateTable` を生成し `sel.addSelectable()` に登録
- **トリガー条件** (`_process_check()`, `dhcp_db_monitor.py:362-368`):
  - op=`DEL`: 常に再生成トリガー (`return True`)
  - op=`SET`: `bridge` フィールドが `enabled_dhcp_interfaces`（= `DHCP_SERVER_IPV4.state=enabled` のインターフェース集合）に含まれるとき再生成トリガー
- **Consumer**: `DhcpServd.dump_dhcp4_config()` — DHCP 設定ファイル（`/etc/kea/kea-dhcp4.conf`）を再生成し kea-dhcp4 に SIGHUP 送信

### 2. DPUS → dhcpservd (DpusTableEventChecker)

- **購読方式**: `SubscriberStateTable` を内包した `DpusTableEventChecker`（`ConfigDbEventChecker` 基底クラス経由）
- **テーブル名定数**: `DPUS = "DPUS"` (`dhcp_db_monitor.py:17`)
- **select タイムアウト**: `DEFAULT_SELECT_TIMEOUT = 5000` ms
- **登録箇所**: `dhcpservd.py:143` — `checkers.append(DpusTableEventChecker(sel, dhcp_db_connector.config_db))`
- **有効化タイミング**: `MidPlaneTableEventChecker` と同様に SmartSwitch モードのとき有効化
- **トリガー条件** (`_process_check()`, `dhcp_db_monitor.py:384-385`):
  - あらゆるイベント（SET/DEL 問わず）を無条件で再生成トリガーとして扱う（`return True`）
- **Consumer**: 同上（`DhcpServd.dump_dhcp4_config()`）

### 3. MID_PLANE_BRIDGE → dhcprelayd (MidPlaneTableEventChecker)

- **購読方式**: `SubscriberStateTable` を内包した `MidPlaneTableEventChecker`
- **登録箇所**: `dhcprelayd.py:395` — `checkers.append(MidPlaneTableEventChecker(sel, dhcp_db_connector.config_db))`
- **select タイムアウト**: `DEFAULT_SELECT_TIMEOUT = 5000` ms
- **有効化タイミング**: `refresh_dhcrelay()` が `DHCP_SERVER_IPV4` に `bridge-midplane` が `state=enabled` で存在し、かつ `self.smart_switch=True` のとき `MID_PLANE_CHECKER` を `enabled_checkers` に追加 (`dhcprelayd.py:102-103`)
- **トリガー結果**: `check_res[MID_PLANE_CHECKER] = True` のとき `_proceed_with_check_res()` が `refresh_dhcrelay(force_kill=True)` を呼び出す (`dhcprelayd.py:156-158`) — dhcrelay プロセスを強制終了して再起動
- **Consumer**: `dhcprelayd`（`DhcpRelayd`）— dhcrelay プロセスの再起動制御

### 4. DHCP_SERVER_IPV4_PORT → dhcpservd (DhcpPortTableEventChecker)

- **購読方式**: `SubscriberStateTable` を内包した `DhcpPortTableEventChecker`
- **テーブル名定数**: `DHCP_SERVER_IPV4_PORT = "DHCP_SERVER_IPV4_PORT"` (`dhcp_db_monitor.py:9`)
- **登録箇所**: `dhcpservd.py:137` — 常時（非 SmartSwitch でも）有効
- **トリガー条件** (`dhcp_db_monitor.py:230-236`): `key.split("|")[0]`（dhcp_interface 部分）が `enabled_dhcp_interfaces` に含まれるとき再生成トリガー。SmartSwitch の場合 `"bridge-midplane"` が `enabled_dhcp_interfaces` に入るため全 `bridge-midplane|dpu*` エントリの変更がトリガーになる
- **Consumer**: `DhcpServd.dump_dhcp4_config()` — kea-dhcp4 設定再生成

---

## チェッカー有効化フロー（SmartSwitch 固有）

```
dhcpservd 起動
  ↓ dump_dhcp4_config() 呼び出し
  ↓ dhcp_cfggen.generate() 実行
  ↓ is_smart_switch(device_metadata) = True（DEVICE_METADATA.subtype=SmartSwitch）
  ↓ subscribe_table |= {"DpusTableEventChecker", "MidPlaneTableEventChecker"}
  ↓ enabled_checker = subscribe_table を dhcpservd へ返す
  ↓ dhcpservd.enable_checkers(enabled_checker)
  ↓ 各チェッカーの enable() で SubscriberStateTable 生成 + sel.addSelectable()
  → SmartSwitch 固有の2テーブルが購読開始される
```

非 SmartSwitch 環境では `is_smart_switch()` が `False` を返すため `SMART_SWITCH_CHECKER` は `subscribe_table` に追加されず、`MidPlaneTableEventChecker` / `DpusTableEventChecker` は `enable()` されない（ディスパッチャは登録済みだが inactive）。

---

## データフロー概略

```
CONFIG_DB[MID_PLANE_BRIDGE|GLOBAL]
  ↓ SubscriberStateTable (MidPlaneTableEventChecker)
dhcpservd [DEFAULT_SELECT_TIMEOUT=5000ms]
  ↓ bridge in enabled_dhcp_interfaces → need_refresh=True
  ↓ dump_dhcp4_config(): dhcp_cfggen.generate() + /etc/kea/kea-dhcp4.conf 上書き
kea-dhcp4 (SIGHUP) → ミッドプレーン DHCP サブネット再構成

CONFIG_DB[DPUS|dpu*]
  ↓ SubscriberStateTable (DpusTableEventChecker)
dhcpservd [DEFAULT_SELECT_TIMEOUT=5000ms]
  ↓ 全イベント無条件で need_refresh=True
  ↓ dump_dhcp4_config() → kea-dhcp4 設定再生成

CONFIG_DB[MID_PLANE_BRIDGE|GLOBAL]
  ↓ SubscriberStateTable (MidPlaneTableEventChecker)
dhcprelayd [DEFAULT_SELECT_TIMEOUT=5000ms]
  ↓ need_refresh → refresh_dhcrelay(force_kill=True)
dhcrelay プロセス強制再起動 → ミッドプレーン DHCP リレー経路更新

CONFIG_DB[DHCP_SERVER_IPV4_PORT|bridge-midplane|dpu*]
  ↓ SubscriberStateTable (DhcpPortTableEventChecker)
dhcpservd [DEFAULT_SELECT_TIMEOUT=5000ms]
  ↓ dhcp_interface="bridge-midplane" in enabled_dhcp_interfaces → need_refresh=True
  ↓ dump_dhcp4_config() → kea-dhcp4 設定再生成
```

---

## 証跡ファイル

- `dhcp_db_monitor.py:9,16-17,69-75,130-136,220-236,349-388`
- `dhcpservd.py:25,96,130-148` (main())
- `dhcp_cfggen.py:23,97-100` (SMART_SWITCH_CHECKER, generate())
- `dhcprelayd.py:28,84-103,156-158,395` (MID_PLANE_CHECKER, refresh_dhcrelay, main())
