# KDUMP — Phase H: プラットフォーム差異

> 調査日: 2026-05-16  
> ソース: `sonic-utilities/scripts/sonic-kdump-config`、`sonic-buildimage/files/build_templates/init_cfg.json.j2`、`sonic-buildimage/files/Aboot/boot0.j2`、`sonic-buildimage/files/image_config/kdump/kdump-tools`、`sonic-buildimage/device/*/installer.conf`

## 1. ブートローダー別 `memory` 書き込みパス

`sonic-kdump-config` スクリプト (`cmd_kdump_enable`) は起動時にブートローダーを自動検出し、`crashkernel=` パラメータの書き込み先を切り替える。

| ブートローダー | 判定条件 | `crashkernel` 書き込み先 |
|--------------|---------|------------------------|
| GRUB (x86_64 汎用) | `/host/grub/grub.cfg` 存在 | `/host/grub/grub.cfg` |
| Aboot (Arista EOS) | `/host/machine.conf` に `aboot_platform` 文字列が含まれる | `/host/image-<version>/kernel-cmdline` |
| U-Boot (ARM 系) | `fw_printenv` コマンドが存在 (`is_uboot_present()`) | `fw_printenv`/`fw_setenv` 経由で `linuxargs` 環境変数を更新 |
| 非対応 | 上記いずれにも該当しない | `"Feature not supported on this platform"` を出力して処理中断 |

**コード証跡** (`sonic-kdump-config:759-768`):
```python
if os.path.exists(grub_cfg):
    return kdump_enable(verbose, kdump_enabled, memory, num_dumps, image, grub_cfg, ...)
elif open(machine_cfg, 'r').read().find('aboot_platform') >= 0:
    aboot_cfg = aboot_cfg_template % image
    return kdump_enable(verbose, kdump_enabled, memory, num_dumps, image, aboot_cfg, ...)
elif is_uboot_present():
    return kdump_enable(verbose, kdump_enabled, memory, num_dumps, image, uboot_cfg, ...)
else:
    print("Feature not supported on this platform")
    return False
```

## 2. ARM/U-Boot プラットフォームの特殊処理

U-Boot 環境では GRUB の行ベース編集の代わりに `fw_printenv`/`fw_setenv` を使用する。

- `fw_printenv` で `linuxargs` キーを取得
- `crashkernel=<value>` を `linuxargs` 内で検索・更新
- `fw_setenv linuxargs <updated_value>` で書き戻す
- 一時ファイル `uboot-env.txt` を中継に使用し、処理完了後に削除

ARM (U-Boot) 環境での `crashkernel` 値は CONFIG_DB の `KDUMP|config|memory` からそのまま渡される。アーキテクチャ固有のデフォルト値はコード上には存在しない。

## 3. ASIC ベンダー別 `enabled` デフォルト値

`init_cfg.json.j2` (ビルド時テンプレート) において、`sonic_asic_platform` 変数で `enabled` のデフォルトが分岐する。

| `sonic_asic_platform` | `KDUMP|config|enabled` デフォルト |
|-----------------------|--------------------------------|
| `cisco-8000` | `"true"` (kdump デフォルト有効) |
| その他すべて (broadcom, mellanox, vs, ...) | `"false"` (kdump デフォルト無効) |

**コード証跡** (`init_cfg.json.j2:203-207`):
```jinja
{%- if sonic_asic_platform == "cisco-8000" %}
    "enabled": "true",
{% else %}
    "enabled": "false",
{% endif %}
```

`memory` と `num_dumps` のデフォルト値はプラットフォーム非依存で統一されている:

```json
"memory": "0M-2G:256M,2G-4G:320M,4G-8G:384M,8G-:448M",
"num_dumps": "3"
```

## 4. KVM/仮想プラットフォーム (VS) の差異

`sonic_asic_platform == "vs"` では kdump デフォルト無効 (`enabled: false`) のまま変更なし。

KVM/QEMU 環境では `ata_piix.prefer_ms_hyperv=0` パラメータが `kdump-tools` のデフォルト `KDUMP_CMDLINE_APPEND` に含まれており、仮想化環境での ATA ドライバ競合を回避する:

```
KDUMP_CMDLINE_APPEND="irqpoll nr_cpus=1 nousb systemd.unit=kdump-tools.service ata_piix.prefer_ms_hyperv=0"
```

**コード証跡** (`files/image_config/kdump/kdump-tools:1-4`):
このパラメータはすべてのプラットフォームで共通に設定されるが、`ata_piix` ドライバが存在しない実機 (Broadcom/Mellanox ASIC 搭載機) では無害に無視される。

## 5. Aboot (Arista) プラットフォームの特殊処理

Aboot ブートローダー環境では、`write_kdump_cmdline()` が SID (System ID) に基づいて特定モデルのみに `crashkernel` パラメータを自動付与する。

```bash
case "$sid" in
    Lodoga*|*Quicksilver*|*Moby|Shearwater*|Moranda*|Gardena*|PikeIsland*|\
    Wolverine*|Clearwater2*|OtterLake*|QuartzDd*|Redstart8Mk2*Quartz4*|Redstart8Mk2*CitrineDd*)
        if ! cmdline_has crashkernel; then
            cmdline_add crashkernel=0M-2G:256M,2G-4G:320M,4G-8G:384M,8G-16G:448M,16G-32G:768M,32G-:1G
        fi
        ;;
esac
```

**コード証跡** (`files/Aboot/boot0.j2:488-495`):
- 対象 SID のみに `crashkernel` が自動設定される
- Aboot は `crashkernel` を `kernel_cmdline_allowlist` に含めて既存設定の引き継ぎを許可するが、デフォルトの `default_cmdline_blacklist` にも含まれ、初期インストール時は削除される

## 6. デバイス固有の `memory_reserved` (installer.conf)

一部デバイスは `installer.conf` の `ONIE_PLATFORM_EXTRA_CMDLINE_LINUX` で個別の `crashkernel` 値を持つ。CONFIG_DB の `memory` フィールドが更新されると、この値は `sonic-kdump-config` によって上書きされる。

| デバイス | デフォルト `crashkernel` |
|---------|----------------------|
| `x86_64-cel_ds1000-r0` (Celestica) | `0M-2G:256M,2G-4G:320M,4G-8G:384M,8G-:448M` |
| `x86_64-nexthop_5010-r0` / `nexthop_4010-r0` | `512M` (絶対値固定) |
| `x86_64-nokia_ixr7250e_36x400g-r0` / `sup-r0` / `x3b-r0` (Nokia) | `8G-:1G` (高メモリ帯のみ確保) |

**証跡**: `device/*/installer.conf` (sonic-buildimage)

## 7. プラットフォーム識別子の実行時伝播

`kdump-tools` のクラッシュカーネル起動コマンドラインに `sonic_platform=__PLATFORM__` が含まれる。`__PLATFORM__` はビルド時または `hostcfgd` 起動時に実際のプラットフォーム識別子に置換され、クラッシュ後の再起動スクリプト (`/usr/local/bin`) がプラットフォームを識別するために使用される。

## 8. 非対応・スコープ外

- x86_64 と aarch64 の間でコード上の機能差はない。ブートローダー検出ロジックがアーキテクチャ差を吸収する
- ベンダー固有 SONiC (NVIDIA/Edgecore 等) のカスタマイズはスコープ外
- `remote` kdump (SSH 転送) はプラットフォーム非依存でコード上の差異なし

## 引用

- `sonic-utilities/scripts/sonic-kdump-config:34-40,111-123,641-768,851-860`
- `sonic-buildimage/files/build_templates/init_cfg.json.j2:201-209`
- `sonic-buildimage/files/Aboot/boot0.j2:89-90,488-495`
- `sonic-buildimage/files/image_config/kdump/kdump-tools:1-18`
- `sonic-buildimage/device/nexthop/x86_64-nexthop_5010-r0/installer.conf:1`
- `sonic-buildimage/device/nokia/x86_64-nokia_ixr7250e_36x400g-r0/installer.conf:4`
- `sonic-buildimage/device/celestica/x86_64-cel_ds1000-r0/installer.conf:4`
