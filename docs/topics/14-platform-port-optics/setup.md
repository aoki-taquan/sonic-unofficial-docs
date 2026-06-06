---
title: 設定
description: 設定 — ここでは、port 設定と platform 関連設定を、CLI / CONFIG_DB / YANG のどれから入るかという観点で整理します。全オプションは個別リファレンスに任せ、この章では入口の対応関係を示します。
area: topics
verification: code-verified
last_verified: 2026-06-06
sources:
- repo: sonic-net/sonic-utilities
  path: config/main.py
  ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
- repo: sonic-net/sonic-utilities
  path: fwutil/main.py
  ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
- repo: sonic-net/sonic-platform-daemons
  path: sonic-xcvrd/xcvrd/xcvrd_utilities/xcvr_table_helper.py
  ref: 4ba9612cb7756651062d37f977e3df17d57f740d
- repo: sonic-net/sonic-platform-daemons
  path: sonic-xcvrd/xcvrd/xcvrd_utilities/optics_si_parser.py
  ref: 4ba9612cb7756651062d37f977e3df17d57f740d
related:
  cli:
  - config interface
  - show interfaces
  - config platform firmware
  - show platform
  config_db:
  - PORT
  - DEVICE_METADATA
  - BREAKOUT_CFG
  yang:
  - sonic-port
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

`fwutil` は装置上で BIOS / CPLD / [FPGA](../../reference/glossary.md#term-fpga) / SSD / optics を統一して扱います。`config platform firmware install` / `config platform firmware update` は内部で `fwutil install` / `fwutil update` をそのまま呼ぶ薄いラッパーで、引数はそのまま透過されます[^cfg-platform-fw]。本番投入前に「ローカルファイルから直接 flash する」運用と、「次回起動する [SONiC](../../reference/glossary.md#term-sonic) イメージに同梱された firmware を使う」運用の 2 系統があります。

ローカル firmware ファイルを直接インストールする例（`install` 経路、`fw_install` のシグネチャは `fw <fw_path> -y`[^fwutil-install]）:

```bash
# 現状
show platform firmware status

# ローカルパスから flash（-y で確認プロンプトを抑止）
sudo config platform firmware install chassis component BIOS fw /tmp/bios-2.0.bin -y
```

次回起動予定の SONiC イメージに同梱されている firmware を使って更新する場合は `update` 経路を使い、`-i next` で「next image に同梱された fw_package」を参照させます[^fwutil-update]。「現在のイメージ側を更新する」のが default (`-i current`)、`-f` でバージョンチェックを無視して強制更新できます。

```bash
# 次回 boot 用 image に同梱の firmware で更新
sudo config platform firmware update chassis component BIOS fw -i next -y

# 適用に再起動が必要な component なら cold reboot
sudo reboot
```

<!-- evidence:
source: sonic-net/sonic-utilities/config/main.py#L8740-L8775 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)
excerpt: |
  @firmware.command(...)
  @click.argument('args', nargs=-1, type=click.UNPROCESSED)
  def install(args):
      """Install platform firmware"""
      cmd = ["fwutil", "install"] + list(args)
  ...
  def update(args):
      """Update platform firmware"""
      cmd = ["fwutil", "update"] + list(args)
reasoning: config platform firmware install/update は fwutil install/update への passthrough。引数は無加工で渡る。
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/sonic-utilities/config/main.py#L8740-L8775 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)"

    **出典**:

    `sonic-net/sonic-utilities/config/main.py#L8740-L8775 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)`

    **抜粋**:

    ```text
    @firmware.command(...)
    @click.argument('args', nargs=-1, type=click.UNPROCESSED)
    def install(args):
        """Install platform firmware"""
        cmd = ["fwutil", "install"] + list(args)
    ...
    def update(args):
        """Update platform firmware"""
        cmd = ["fwutil", "update"] + list(args)
    ```

    **判断根拠**: config platform firmware install/update は fwutil install/update への passthrough。引数は無加工で渡る。

<!-- evidence-rendered:end -->

<!-- evidence:
source: sonic-net/sonic-utilities/fwutil/main.py#L271-L356 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)
excerpt: |
  @component_install.command(name='fw')
  @click.option('-y', '--yes', ...)
  @click.argument('fw_path', metavar='<fw_path>', callback=validate_fw)
  def fw_install(ctx, yes, fw_path):
      """Install firmware from local path or URL"""
  ...
  @component_update.command(name='fw')
  @click.option('-y', '--yes', ...)
  @click.option('-f', '--force', ...)
  @click.option('-i', '--image', type=click.Choice(["current", "next"]), default="current", ...)
  def fw_update(ctx, yes, force, image):
      """Update firmware from SONiC image"""
reasoning: fwutil の真のサブコマンドツリーは chassis|module|component の component の下に install fw / update fw があり、policy next のような構文は存在しない。next image 参照は `-i next` オプションで行う。
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/sonic-utilities/fwutil/main.py#L271-L356 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)"

    **出典**:

    `sonic-net/sonic-utilities/fwutil/main.py#L271-L356 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)`

    **抜粋**:

    ```text
    @component_install.command(name='fw')
    @click.option('-y', '--yes', ...)
    @click.argument('fw_path', metavar='<fw_path>', callback=validate_fw)
    def fw_install(ctx, yes, fw_path):
        """Install firmware from local path or URL"""
    ...
    @component_update.command(name='fw')
    @click.option('-y', '--yes', ...)
    @click.option('-f', '--force', ...)
    @click.option('-i', '--image', type=click.Choice(["current", "next"]), default="current", ...)
    def fw_update(ctx, yes, force, image):
        """Update firmware from SONiC image"""
    ```

    **判断根拠**: fwutil の真のサブコマンドツリーは chassis|module|component の component の下に install fw / update fw があり、policy next のような構文は存在しない。next image 参照は `-i next` オプションで行う。

<!-- evidence-rendered:end -->

`show platform firmware status` の典型出力:

```text
Chassis    Module    Component    Version       Description
---------  --------  -----------  ------------  --------------------
Chassis1   N/A       BIOS         1.5.0         BIOS firmware
Chassis1   N/A       CPLD1        12            CPLD firmware
Chassis1   N/A       SSD          2024.1        Internal SSD
```

更新後の expected version とコンポーネントの一覧は platform 実装の `platform_components.json` に列挙され、`fwutil` はこの JSON に書かれた component しか触らないため、想定外のデバイスを誤って flash することはありません。

## 設定エラーと対処

| 症状 | 原因 | 対処 |
|---|---|---|
| `config interface breakout` が `Not supported on this platform` で失敗 | `platform.json` / capability に該当 mode が無い | `show platform inventory` と `platform.json` の `breakout_modes` を確認、ベンダー提供版を入手 |
| `config interface speed 400000` が `SAI_STATUS_INVALID_ATTR_VALUE_0` でログに残る | [ASIC](../../reference/glossary.md#term-asic) は対応していても [SerDes](../../reference/glossary.md#term-serdes) / FEC 組合せが NG | `port_config.ini` / `media_settings.json` で許可された組合せを確認 |
| 子ポートが Oper down のまま | 対向側のブレイクアウトモード不一致、または FEC 不一致 | 対向の `show int status` と FEC をそろえる |
| `show int transceiver eeprom` が空 | SFP I2C エラー / `xcvrd` 未起動 | `docker logs pmon`、`xcvrd` のステータスを確認 |
| `fwutil update ... -i next` で更新したのに反映されない | warm reboot を使った / power cycle が必要な component | component の reboot 要件を `platform_components.json` で確認、`cold reboot` で再試行 |

## Platform firmware

`config platform firmware` 系コマンドは、装置内の各種 firmware (BIOS、CPLD、FPGA、SSD、optics) の表示・アップデート・スケジュール管理を扱います。

- [config platform firmware](../../reference/cli/config-platform-firmware.md): CLI の構造。
- [SONiC fw-utility](../../platform/sonic-fw-utility.md): 内部の `fw-util` がどう platform 実装を呼ぶかの設計。

CLI から呼ばれる `fw-util` は、`platform.json` と platform 実装が公開する component に依存して動きます。

## 設定シナリオ 4: 光モジュール DOM の常時モニタリング

`xcvrd` は SFP / QSFP の Digital Optical Monitoring (DOM) 値を STATE_DB の `TRANSCEIVER_DOM_SENSOR` テーブルに書き続けます[^xcvrd-tables]。port ごとの DOM polling は `PORT` テーブルの `dom_polling` カラムで制御され、CLI からは以下で切り替えます[^cfg-dom]:

```bash
sudo config interface transceiver dom Ethernet0 enable
show interfaces transceiver dom Ethernet0
```

なお `config interface transceiver dom` は **非 breakout port、または breakout 時の第 1 サブポート** (`subport=0|1`) でのみ受理されます[^cfg-dom]。

`show interfaces transceiver dom` 出力例:

```yaml
Ethernet0:
        temperature: 43.5C
        voltage:     3.31V
        rx1power:    -2.1 dBm
        tx1power:     0.5 dBm
        tx1bias:     7.5 mA
```

DOM 値や status の閾値超過は `xcvrd` が STATE_DB の `TRANSCEIVER_DOM_FLAG` / `TRANSCEIVER_STATUS_FLAG` 系テーブル群に立てます[^xcvrd-tables]。`COUNTERS_DB` に直接落ちないことに注意。[SNMP](../../reference/glossary.md#term-snmp) / telemetry で監視する場合は `TRANSCEIVER_DOM_FLAG` を subscribe します。

## 設定シナリオ 5: media_settings.json による per-port preemphasis

ASIC の SerDes preemphasis / 振幅は default では `port_config.ini` の lane に紐づくテンプレートが適用されますが、特定の光モジュール vendor / part-number の組合せだけ調整したいときは `/usr/share/sonic/device/<platform>/<hwsku>/media_settings.json` を編集します。トップレベルキーは `GLOBAL_MEDIA_SETTINGS`（全ポートに適用）と `PORT_MEDIA_SETTINGS`（ポート番号レンジごとに適用）の 2 種があり、`xcvrd` の `optics_si_parser.py` が両方を解釈します[^optics-si]。

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

編集後 `docker exec pmon supervisorctl restart xcvrd` で再ロードされ、次回 link up 時から反映されます。`docker exec pmon tail -n 50 /var/log/syslog | grep xcvrd` で `media_settings applied` のログを確認します。

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

## 引用元

[^cfg-platform-fw]: `config platform firmware install` / `update` は `fwutil install` / `update` への薄いラッパー。`sonic-net/sonic-utilities/config/main.py` L8740-L8775 ([sha 39732bceb8](https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/main.py#L8740-L8775))。

[^fwutil-install]: `fwutil` の component スコープ `install fw <fw_path>` は `-y` のみオプションを持ち、ローカルパスまたは URL からの flash を行う。`sonic-net/sonic-utilities/fwutil/main.py` L271-L297 ([sha 39732bceb8](https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/fwutil/main.py#L271-L297))。

[^fwutil-update]: `fwutil` の component スコープ `update fw` は `-y` (確認スキップ) / `-f` (バージョンチェック無視) / `-i {current,next}` (どの SONiC イメージに同梱の fw_package を見るか) の 3 オプション。`policy next` のような構文は存在しない。`sonic-net/sonic-utilities/fwutil/main.py` L301-L356 ([sha 39732bceb8](https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/fwutil/main.py#L301-L356))。

[^xcvrd-tables]: `xcvrd` の STATE_DB テーブル定数は `TRANSCEIVER_DOM_SENSOR` / `TRANSCEIVER_DOM_FLAG` / `TRANSCEIVER_STATUS_FLAG` 等。`sonic-net/sonic-platform-daemons/sonic-xcvrd/xcvrd/xcvrd_utilities/xcvr_table_helper.py` L13-L24 ([sha 4ba9612cb7](https://github.com/sonic-net/sonic-platform-daemons/blob/4ba9612cb7756651062d37f977e3df17d57f740d/sonic-xcvrd/xcvrd/xcvrd_utilities/xcvr_table_helper.py#L13-L24))。

[^cfg-dom]: `config interface transceiver dom <if> (enable|disable)` は `PORT` テーブルの `dom_polling` を書き換える。受理されるのは `subport=0|1` のポートのみ。`sonic-net/sonic-utilities/config/main.py` L6472-L6506 ([sha 39732bceb8](https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/main.py#L6472-L6506))。

[^optics-si]: `media_settings.json` のトップレベルキー `GLOBAL_MEDIA_SETTINGS` / `PORT_MEDIA_SETTINGS` 両方を `xcvrd` が解釈する。`sonic-net/sonic-platform-daemons/sonic-xcvrd/xcvrd/xcvrd_utilities/optics_si_parser.py` L54-L113 ([sha 4ba9612cb7](https://github.com/sonic-net/sonic-platform-daemons/blob/4ba9612cb7756651062d37f977e3df17d57f740d/sonic-xcvrd/xcvrd/xcvrd_utilities/optics_si_parser.py#L54-L113))。

<!-- glossary-links-injected: 8ba32e5aa69d -->
