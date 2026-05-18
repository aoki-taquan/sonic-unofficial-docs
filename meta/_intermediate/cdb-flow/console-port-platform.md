# CONSOLE_PORT — Phase H プラットフォーム差異スキャンノート

対象ページ: `docs/reference/config-db/console-port.md`
対象テーブル: `CONFIG_DB.CONSOLE_PORT`, `CONFIG_DB.CONSOLE_SWITCH`
Consumer: `consutil` (CLI ツール、常駐デーモンなし)
スキャン範囲: `sonic-utilities/consutil/lib.py` (`SysInfoProvider.init_device_prefix()`, `list_console_ttys()`)
              `sonic-buildimage/device/*/udevprefix.conf` (全プラットフォーム)
              `sonic-buildimage/src/sonic-config-engine/minigraph.py` (`<Console>` タグ処理)

---

## 検出したプラットフォーム差異

### 1. `udevprefix.conf` による TTY デバイスプレフィックスのプラットフォーム差異

`SysInfoProvider.init_device_prefix()` (`consutil/lib.py:300-307`) は起動時にプラットフォームディレクトリ内の `udevprefix.conf` を読み込み、`DEVICE_PREFIX` を上書きする。

| プラットフォーム | `udevprefix.conf` の値 | 実デバイスプレフィックス | 物理デバイス |
|-----------------|----------------------|----------------------|-------------|
| デフォルト（ファイル不在） | — | `/dev/ttyUSB` | USB-to-serial アダプタ |
| `arm64-nexthop_b27-r0` | `ttySwitchCpu` | `/dev/ttySwitchCpu` | udev ルールで付与されたシンボリック名 |
| `arm64-aspeed_ast2700_evb-r0` | `ttySwitchCpu` | `/dev/ttySwitchCpu` | AST2700 ベースの ARM SoC |
| `arm64-nokia_ixs7215_c1xa-r0` | `ttyCR` | `/dev/ttyCR` | Nokia IXS7215 固有デバイス |
| `x86_64-arista_7800_sup` | `ttySCD` | `/dev/ttySCD` | Arista 7800 シリーズ固有デバイス |

```python
# consutil/lib.py:300-307
@staticmethod
def init_device_prefix():
    platform_path, _ = device_info.get_paths_to_platform_and_hwsku_dirs()
    UDEV_PREFIX_CONF_FILE_PATH = os.path.join(platform_path, UDEV_PREFIX_CONF_FILENAME)

    if os.path.exists(UDEV_PREFIX_CONF_FILE_PATH):
        fp = open(UDEV_PREFIX_CONF_FILE_PATH, 'r')
        lines = fp.readlines()
        SysInfoProvider.DEVICE_PREFIX = "/dev/" + lines[0].rstrip()
```

evidence: `sonic-utilities/consutil/lib.py:297-307`, `sonic-buildimage/device/nexthop/arm64-nexthop_b27-r0/udevprefix.conf`, `sonic-buildimage/device/nokia/arm64-nokia_ixs7215_c1xa-r0/udevprefix.conf`, `sonic-buildimage/device/arista/x86_64-arista_7800_sup/plugins/udevprefix.conf`

### 2. `CONSOLE_PORT.line_num` と物理デバイスの対応プラットフォーム差異

`ConsolePortInfo.connect()` (`consutil/lib.py:205`) は `line_num` から物理デバイスパスを `DEVICE_PREFIX + line_num` で構築する。プラットフォームにより `DEVICE_PREFIX` が異なるため、同じ `line_num=0` でも物理デバイスが変わる。

| プラットフォーム | `line_num=0` の物理デバイス |
|-----------------|-----------------------------|
| デフォルト | `/dev/ttyUSB0` |
| nexthop_b27 / aspeed_ast2700 | `/dev/ttySwitchCpu0` |
| nokia_ixs7215 | `/dev/ttyCR0` |
| arista_7800_sup | `/dev/ttySCD0` |

### 3. ASIC ベンダー固有差異なし

- SAI 非経由（consutil は Linux シリアルデバイスと直接通信）。ASIC ベンダー（Broadcom / Mellanox / Marvell）による差異はなし。
- `CONSOLE_PORT` テーブル自体の構造 (`baud_rate`, `flow_control`, `remote_device`, `escape_char`) はプラットフォーム間で共通。

### 4. minigraph による CONSOLE_PORT 生成はプラットフォーム非依存

`minigraph.py:2516` での `CONSOLE_PORT` 生成は `<Console>` XML タグの内容に基づき、プラットフォーム条件分岐なし。ただし `<Bandwidth>` タグ不在時の `baud_rate=None` については platform 横断のリスクがある（evidence: `minigraph.py:615`）。

---

## 判定サマリ

| 差異種別 | 有無 | 根拠 |
|---------|------|------|
| ASIC ベンダー固有差異 | なし | SAI 非経由 |
| プラットフォーム固有 TTY デバイス名 | **あり** | `udevprefix.conf` による `DEVICE_PREFIX` 上書き |
| YANG / CONFIG_DB スキーマのプラットフォーム差異 | なし | 全プラットフォーム共通スキーマ |
| Multi-ASIC 差異 | なし | consutil は namespace 非対応（シングルホスト前提） |

---

## ページ反映方針

- `<!-- platform -->` ブロックを `<!-- /pubsub -->` の直後（`<!-- ref-triangle:start -->` の前）に挿入する。
- 主要差異は `udevprefix.conf` によるデバイスプレフィックスのプラットフォーム別上書きを中心に説明する。
- ASIC ベンダー固有差異がない旨も明示する（SAI 非経由）。
