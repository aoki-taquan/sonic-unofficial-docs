# smart-switch — Phase F: 副次 DB 書込・ファイルシステム副作用

調査日: 2026-05-17
調査対象: dhcpservd.py, dhcp_cfggen.py, dhcp_lease.py, dhcprelayd.py, config_samples.py

---

## 1. STATE_DB: DHCP_SERVER_IPV4_LEASE（SmartSwitch 専用キー形式）

`MID_PLANE_BRIDGE` / `DPUS` / `DHCP_SERVER_IPV4_PORT` を CONFIG_DB へ書き込むと、`dhcpservd` が kea-dhcp4 と連携して DPU へ IP アドレスをリース割り当てする。kea-dhcp4 がリースイベント（割当・更新・解放）を `lease_update.sh` 経由で `SIGUSR1` で dhcpservd に通知する。`KeaDhcp4LeaseHandler._update_lease()` が `/var/lib/kea/kea-lease.csv` を読み取り STATE_DB に書き込む。

**SmartSwitch でのキー形式** (`dhcp_lease.py:108-112`):

```
DHCP_SERVER_IPV4_LEASE|bridge-midplane|<mac_address>
```

通常 VLAN モードの `DHCP_SERVER_IPV4_LEASE|Vlan<subnet_id>|<mac_address>` とは異なり、`bridge-midplane` をプレフィックスに使用する。`MID_PLANE_BRIDGE.GLOBAL.bridge` の値が `midplane_bridge_name` として使われる (`dhcp_lease.py:37-39`)。

**フィールド**:

| フィールド | 説明 |
|---|---|
| `ip` | DPU に割り当てた IPv4 アドレス（`169.254.200.x`） |
| `lease_start` | リース開始 UNIX タイムスタンプ（`lease_end - valid_lifetime` で算出） |
| `lease_end` | リース終了 UNIX タイムスタンプ（kea-lease.csv の expire カラム） |

**書き込み条件**: `lease_start != lease_end` かつ `now < lease_end`（有効リース）の場合のみ `hset`。期限切れリースは `state_db.delete`。`lease_update_interval=2` 秒のレートリミットあり。

> **Evidence**: `src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcp_lease.py:34-39,108-112,79-93`

---

## 2. STATE_DB: DHCP_SERVER_IPV4_SERVER_IP

dhcpservd 起動時（`start()` 内）に 1 回のみ実行。dhcp_server コンテナの `eth0` IPv4 アドレスを STATE_DB に書き込む。SmartSwitch / 非 SmartSwitch 共通の書き込みだが、SmartSwitch 環境ではこの IP が DPU → NPU 向け DHCP リレーの参照先となる。

**key 形式**: `DHCP_SERVER_IPV4_SERVER_IP|eth0`  
**フィールド**: `ip` — eth0 の IPv4 アドレス文字列  
eth0 アドレス取得失敗時は 5 秒間隔で最大 10 回リトライ。10 回失敗で `sys.exit(1)`。

> **Evidence**: `src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcpservd.py:70-87`

---

## 3. ファイルシステム: /etc/kea/kea-dhcp4.conf

`MID_PLANE_BRIDGE` / `DPUS` / `DHCP_SERVER_IPV4_PORT` の変更を `DpusTableEventChecker` / `MidPlaneTableEventChecker` が検知するたびに `dump_dhcp4_config()` が `/etc/kea/kea-dhcp4.conf` を上書きし、kea-dhcp4 に SIGHUP を送信して設定を再読込させる (`dhcpservd.py:51-68`)。

SmartSwitch 固有の差異（`dhcp_cfggen.py:251`）:
- `subnet_id` に VLAN 番号の代わり `MID_PLANE_BRIDGE_SUBNET_ID = 10000` を使用
- `bridge-midplane` が `subnet4` の対象ネットワークとして追加される

> **Evidence**: `src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcpservd.py:51-68`; `src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcp_cfggen.py:97-100,251`

---

## 4. CONFIG_DB: FEATURE テーブル（初期投入時の連鎖書き込み）

`config_samples.py` の `generate_t1_smartswitch_switch_sample_config()` は `DPUS` エントリが存在する場合（`if dhcp_server_ports:`）に限り、CONFIG_DB の `FEATURE` テーブルへ `dhcp_relay` / `dhcp_server` エントリを自動投入する (`config_samples.py:105-131`)。この書き込みは minigraph 変換・`sonic-cfggen` 実行時に発生する。

```python
data['FEATURE'] = {
    "dhcp_relay": {"state": "enabled", ...},
    "dhcp_server": {"state": "enabled", ...}
}
```

`DPUS` が空のとき `FEATURE` エントリは投入されない（dhcp_server コンテナが起動しない）。

> **Evidence**: `src/sonic-config-engine/config_samples.py:105-131`

---

## 5. dhcprelayd — midplane ブリッジのリレープロセス制御

`dhcprelayd.py` は SmartSwitch の場合、`MID_PLANE_BRIDGE.GLOBAL.bridge` を読み取り、`DHCP_SERVER_IPV4` テーブルに `bridge-midplane` エントリが存在しかつ `state=enabled` のとき、midplane ブリッジを対象とした `dhcrelay` プロセスを起動・再起動する (`dhcprelayd.py:82-103`)。`MidPlaneTableEventChecker` で `MID_PLANE_BRIDGE` の変更を購読し、変更時に `refresh_dhcrelay()` を呼び出す。

> **Evidence**: `src/sonic-dhcp-utilities/dhcp_utilities/dhcprelayd/dhcprelayd.py:82-113`; `src/sonic-dhcp-utilities/dhcp_utilities/common/dhcp_db_monitor.py:351-356`
