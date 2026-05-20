---
title: 設定
description: 設定 — ここでは、port 設定と platform 関連設定を、CLI / CONFIG_DB / YANG のどれから入るかという観点で整理します。全オプションは個別リファレンスに任せ、この章では入口の対応関係を示します。
area: topics
verification: meta
last_verified: 2026-05-10
sources:
- docs/reference/cli/config-interface.md
- docs/reference/cli/config-platform-firmware.md
- docs/reference/cli/show-platform.md
- docs/platform/sonic-fw-utility.md
- docs/platform/platform-capability-file-enhancement.md
- docs/reference/config-db/port.md
- docs/reference/yang/sonic-port.md
related:
  cli:
  - config interface
  - show interfaces
  - config platform firmware
  - show platform
  - config snmp
  - config qos
  - show acl
  config_db:
  - PORT
  - DEVICE_METADATA
  - SNMP
  - BREAKOUT_CFG
  - SNMP_AGENT_ADDRESS_CONFIG
  - ACL_RULE
  - ACL_TABLE
  yang:
  - sonic-port
  - sonic-portchannel
  - sonic-snmp
---

# 設定

ここでは、port 設定と platform 関連設定を、CLI / [CONFIG_DB](../../reference/glossary.md#term-config_db) / [YANG](../../reference/glossary.md#term-yang) のどれから入るかという観点で整理します。全オプションは個別リファレンスに任せ、この章では入口の対応関係を示します。

## 入口の対応

| やりたいこと | CLI | CONFIG_DB | YANG |
|---|---|---|---|
| port の speed / FEC / autoneg | [config interface](../../reference/cli/config-interface.md) | [PORT](../../reference/config-db/port.md) | [sonic-port](../../reference/yang/sonic-port.md) |
| breakout モード変更 | [config interface](../../reference/cli/config-interface.md) (breakout サブコマンド) | `PORT` の lanes / speed | [sonic-port](../../reference/yang/sonic-port.md) |
| platform firmware の更新 | [config platform firmware](../../reference/cli/config-platform-firmware.md) | - | - |
| platform 情報の確認 | [show platform](../../reference/cli/show-platform.md) | `DEVICE_METADATA`、`CHASSIS_INFO` 等 | - |

CONFIG_DB を直接いじる場面は限られますが、CLI が未対応のカラムを設定するときは `sonic-cfggen` か `redis-cli` で `PORT` テーブルを更新します。

## 典型操作の最小例

これらはイメージです。実環境の正確な引数は CLI リファレンスを必ず確認してください。

```bash
# admin 状態
config interface startup Ethernet0
config interface shutdown Ethernet0

# 速度と FEC
config interface speed Ethernet0 100000
config interface fec Ethernet0 rs

# auto-negotiation
config interface autoneg Ethernet0 enabled
config interface advertised-speeds Ethernet0 25000,100000

# breakout
config interface breakout Ethernet0 "4x25G"
```

speed や FEC を変更すると、buffer profile や [ACL](../../reference/glossary.md#term-acl) bind が影響を受ける場合があります。[QoS](../../reference/glossary.md#term-qos) / ACL 章とあわせて読んでください。

## 設定シナリオ 1: 100G ポートを 4x25G にブレイクアウト

新しい光モジュールを差してブレイクアウト構成に切り替える場合、CLI 1 本では完結せず、breakout → speed → FEC → admin の順で投入します。`Ethernet0` を `4x25G` に分解する例:

```bash
# 現状確認
show interfaces breakout current-mode Ethernet0
show interfaces status Ethernet0

# breakout
sudo config interface breakout Ethernet0 "4x25G[10G]" -f -y

# 子ポートの起動と FEC
for p in Ethernet0 Ethernet1 Ethernet2 Ethernet3; do
    sudo config interface speed $p 25000
    sudo config interface fec   $p rs
    sudo config interface startup $p
done
```

CONFIG_DB の差分（ブレイクアウト直後）はおおよそ次の形になります。

```json
{
    "PORT": {
        "Ethernet0": {"lanes": "65", "speed": "25000", "fec": "rs", "admin_status": "up", "mtu": "9100", "alias": "etp1a"},
        "Ethernet1": {"lanes": "66", "speed": "25000", "fec": "rs", "admin_status": "up", "mtu": "9100", "alias": "etp1b"},
        "Ethernet2": {"lanes": "67", "speed": "25000", "fec": "rs", "admin_status": "up", "mtu": "9100", "alias": "etp1c"},
        "Ethernet3": {"lanes": "68", "speed": "25000", "fec": "rs", "admin_status": "up", "mtu": "9100", "alias": "etp1d"}
    },
    "BREAKOUT_CFG": {
        "Ethernet0": {"brkout_mode": "4x25G[10G]"}
    }
}
```

確認は `show interfaces status` / `show interfaces transceiver eeprom` です。

```text
Interface    Lanes        Speed    MTU    FEC    Alias    Vlan    Oper    Admin    Type        Asym PFC
-----------  -----------  -------  -----  -----  -------  ------  ------  -------  ----------  ----------
Ethernet0    65           25G      9100   rs     etp1a    routed  up      up       SFP28       N/A
Ethernet1    66           25G      9100   rs     etp1b    routed  up      up       SFP28       N/A
```

## 設定シナリオ 2: 既存ポートの speed と FEC の切替

光モジュール交換に伴い 100G → 400G に上げる、ないし FEC を `rs` から `fc` に切り替える運用です。port が UP のままだと [SAI](../../reference/glossary.md#term-sai) 側で reject される実装があるため、必ず一旦 admin down にします。

```bash
sudo config interface shutdown Ethernet8
sudo config interface speed    Ethernet8 400000
sudo config interface fec      Ethernet8 rs
sudo config interface mtu      Ethernet8 9100
sudo config interface startup  Ethernet8

show interfaces counters errors Ethernet8
```

期待されるエラーカウンタは基本ゼロ近傍です。FEC を変えた直後は `RX_ERR` や `SYMBOL_ERR` が一時的に増えることがあるため、`watch -n 1 show interfaces counters Ethernet8` で 10〜30 秒の収束を待ちます。

## 設定シナリオ 3: platform firmware のステージング更新

`fw-util` は装置上で BIOS / CPLD / [FPGA](../../reference/glossary.md#term-fpga) / SSD / optics を統一して扱います。本番投入前に「DUT 上に新 firmware を仕込み、次回 cold reboot で適用する」というステージング運用が典型です。

```bash
# 現状
show platform firmware status

# 取得
sudo config platform firmware install chassis component BIOS fw /tmp/bios-2.0.bin --yes

# 次回 cold reboot で適用するように予約
sudo config platform firmware update chassis component BIOS fw policy next

# 適用は cold reboot 後
sudo reboot
```

`show platform firmware status` の典型出力:

```text
Chassis    Module    Component    Version       Description
---------  --------  -----------  ------------  --------------------
Chassis1   N/A       BIOS         1.5.0         BIOS firmware
Chassis1   N/A       CPLD1        12            CPLD firmware
Chassis1   N/A       SSD          2024.1        Internal SSD
```

更新後の expected version とコンポーネントの一覧は platform 実装の `platform_components.json` に列挙され、`fw-util` はこの JSON に書かれた component しか触らないため、想定外のデバイスを誤って flash することはありません。

## 設定エラーと対処

| 症状 | 原因 | 対処 |
|---|---|---|
| `config interface breakout` が `Not supported on this platform` で失敗 | `platform.json` / capability に該当 mode が無い | `show platform inventory` と `platform.json` の `breakout_modes` を確認、ベンダー提供版を入手 |
| `config interface speed 400000` が `SAI_STATUS_INVALID_ATTR_VALUE_0` でログに残る | [ASIC](../../reference/glossary.md#term-asic) は対応していても [SerDes](../../reference/glossary.md#term-serdes) / FEC 組合せが NG | `port_config.ini` / `media_settings.json` で許可された組合せを確認 |
| 子ポートが Oper down のまま | 対向側のブレイクアウトモード不一致、または FEC 不一致 | 対向の `show int status` と FEC をそろえる |
| `show int transceiver eeprom` が空 | SFP I2C エラー / `xcvrd` 未起動 | `docker logs pmon`、`xcvrd` のステータスを確認 |
| `fw-util` が `policy next` 後も適用されない | warm reboot を使った / power cycle が必要な component | component の reboot 要件を `platform_components.json` で確認、`cold reboot` で再試行 |

## Platform firmware

`config platform firmware` 系コマンドは、装置内の各種 firmware (BIOS、CPLD、FPGA、SSD、optics) の表示・アップデート・スケジュール管理を扱います。

- [config platform firmware](../../reference/cli/config-platform-firmware.md): CLI の構造。
- [SONiC fw-utility](../../platform/sonic-fw-utility.md): 内部の `fw-util` がどう platform 実装を呼ぶかの設計。

CLI から呼ばれる `fw-util` は、`platform.json` と platform 実装が公開する component に依存して動きます。

## 設定シナリオ 4: 光モジュール DOM の常時モニタリング

`xcvrd` は SFP / QSFP の Digital Optical Monitoring (DOM) 値を `STATE_DB:TRANSCEIVER_DOM_SENSOR|<port>` に書き続けます。アラート閾値を CLI で設定する場合:

```bash
sudo config interface transceiver dom Ethernet0 enable
show interfaces transceiver dom Ethernet0
```

`show interfaces transceiver dom` 出力例:

```yaml
Ethernet0:
        temperature: 43.5C
        voltage:     3.31V
        rx1power:    -2.1 dBm
        tx1power:     0.5 dBm
        tx1bias:     7.5 mA
```

各値の Warning / Alarm 閾値は EEPROM の A0/A2 page から `xcvrd` が読み、`STATE_DB:TRANSCEIVER_STATUS_FLAG_*` に立てます。`COUNTERS_DB` に直接落ちないことに注意。[SNMP](../../reference/glossary.md#term-snmp) / telemetry で監視する場合は `xcvrd` の `TRANSCEIVER_DOM_FLAG_TABLE` を subscribe します。

## 設定シナリオ 5: media_settings.json による per-port preemphasis

ASIC の SerDes preemphasis / 振幅は default では `port_config.ini` の lane に紐づくテンプレートが適用されますが、特定の光モジュール vendor / part-number の組合せだけ調整したいときは `/usr/share/sonic/device/<platform>/<hwsku>/media_settings.json` を編集します。

```json
{
  "GLOBAL_MEDIA_SETTINGS": {
    "0-31": {
      "QSFP28-100GBASE-CR4-1M": {
        "preemphasis": {"lane0":"0x12345678","lane1":"0x12345678","lane2":"0x12345678","lane3":"0x12345678"}
      }
    }
  }
}
```

編集後 `systemctl restart xcvrd` で再ロードされ、次回 link up 時から反映されます。`docker exec xcvrd cat /var/log/xcvrd.log` で `media_settings applied` のログを確認します。

## Platform capability ファイル

ASIC や platform が「何ができるか」を宣言する capability ファイルは、port 設定や機能の可否を実行前に判別するために使われます。詳細は [platform capability file enhancement](../../platform/platform-capability-file-enhancement.md) を参照してください。capability に書かれていない機能を設定で要求した場合、[orchagent](../../reference/glossary.md#term-orchagent) / SAI 層で reject されます。

## 関連リファレンス

- CLI: `config interface`、`config interface breakout`、`config interface speed/fec/mtu/autoneg`、`config platform firmware`、`show interfaces status`、`show interfaces transceiver`、`show platform inventory`、`show platform firmware status`
- CONFIG_DB: `PORT`、`BREAKOUT_CFG`、`PORT_TABLE`（[APPL_DB](../../reference/glossary.md#term-appl_db)）、`TRANSCEIVER_INFO`（[STATE_DB](../../reference/glossary.md#term-state_db)）、`TRANSCEIVER_DOM_SENSOR`（STATE_DB）、`DEVICE_METADATA`、`CHASSIS_INFO`
- YANG: [`sonic-port`](../../reference/yang/sonic-port.md)、`sonic-portchannel`、`sonic-device-metadata`
- platform 実装ファイル: `platform.json`、`port_config.ini`、`media_settings.json`、`platform_components.json`、`hwsku.json`

## 関連ページ

- [config interface](../../reference/cli/config-interface.md)
- [config platform firmware](../../reference/cli/config-platform-firmware.md)
- [show platform](../../reference/cli/show-platform.md)
- [PORT テーブル](../../reference/config-db/port.md)
- [sonic-port YANG](../../reference/yang/sonic-port.md)
- [SONiC fw-utility](../../platform/sonic-fw-utility.md)
- [platform capability file enhancement](../../platform/platform-capability-file-enhancement.md)

<!-- glossary-links-injected: c006405759d8 -->
