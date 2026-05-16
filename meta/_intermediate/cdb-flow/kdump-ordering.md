# KDUMP — Phase B 書込み順依存 証跡

生成日: 2026-05-16
対象ページ: `docs/reference/config-db/kdump.md`
調査コミット: sonic-buildimage (files/image_config/kdump/kdump-tools), sonic-utilities/scripts/sonic-kdump-config, sonic-host-services/scripts/hostcfgd

---

## 1. kernel crashkernel 予約順序

`crashkernel=` パラメータは GRUB / U-Boot / Aboot のブートローダ設定に埋め込まれ、次のリブート時にカーネルが予約メモリを確保する。

```
[1] config kdump enable / hostcfgd kdump_update()
      └─ sonic-kdump-config --enable
           └─ kdump_enable() 関数
                ├─ grub.cfg / kernel-cmdline / uboot-env に crashkernel=<memory> を追記
                └─ write_use_kdump(1)  →  USE_KDUMP=1 を /etc/default/kdump-tools へ書込み

[2] システムリブート
      └─ ブートローダが crashkernel= を kernel cmdline に渡す
           └─ 物理メモリの一部が crash kernel 用に予約される
                (/sys/kernel/kexec_crash_size > 0 になる)

[3] kexec_load（kdump-tools パッケージ提供の kdump-config load）
      └─ crash kernel イメージを予約メモリへロード
           └─ /usr/sbin/kdump-config load
                (hostcfgd の kdump_update() 内で
                 crash_kernel_in_cmdline != None の場合に実行)
```

evidence:
- `sonic-utilities/scripts/sonic-kdump-config` `kdump_enable()` L640-715
- `sonic-host-services/scripts/hostcfgd` `KdumpCfg.kdump_update()` L1225-1270

---

## 2. systemd kdump.service 起動順序

hostcfgd の `load()` は `wait_till_system_init_done()` 完了後に `kdumpCfg.load(kdump)` を呼ぶ。

```
systemd target: sonic.target
  └─ hostcfgd.service (docker-config-engine)
       ├─ __init__()
       │    ├─ KdumpCfg.__init__()
       │    │    └─ init_kdump_config_from_cmdline()
       │    │         └─ /proc/cmdline に crashkernel= が存在する場合
       │    │              → CONFIG_DB KDUMP|config を上書き (enabled=true, memory=<値>)
       │    │              → update_config_from_proc_cmdline = True フラグセット
       │    └─ (他のハンドラ初期化)
       │
       ├─ load_independent_config()   ← AAA/TACACS/RADIUS のみ（kdump はここに含まれない）
       │
       ├─ wait_till_system_init_done()   ← systemctl is-system-running --wait
       │
       └─ load()                         ← system init 完了後
            ├─ kdumpCfg.load(init_data['KDUMP'])
            │    └─ CONFIG_DB の値がデフォルト未設定なら mod_entry でデフォルト埋め
            │         └─ kdump_update("config", data)
            │              ├─ sonic-kdump-config --enable / --disable
            │              ├─ sonic-kdump-config --memory <size>
            │              ├─ sonic-kdump-config --num_dumps <n>
            │              ├─ sonic-kdump-config --ssh_string <str>
            │              ├─ sonic-kdump-config --ssh_path <path>
            │              └─ sonic-kdump-config --remote
            │
            └─ register_callbacks()
                 └─ config_db.subscribe('KDUMP', kdump_handler)
                      └─ 変更イベント → kdumpCfg.kdump_update(key, data)
```

evidence: `sonic-host-services/scripts/hostcfgd` L2160-2280、L2393-2395、L2468

---

## 3. 起動順依存の要点

| 依存関係 | 詳細 |
|---------|------|
| **crashkernel 予約はリブート必須** | `enabled=true` を DB に書いても現行カーネルでは kdump が動作しない。grub/U-Boot へのパラメータ追記 → リブート → kexec_load が完了して初めて有効化 |
| **/proc/cmdline 先読みによる DB 上書き** | hostcfgd 起動時に `init_kdump_config_from_cmdline()` が `/proc/cmdline` を参照し、`crashkernel=` が既に存在する場合は CONFIG_DB を `enabled=true` に強制上書きする。最初の `kdump_update()` 呼び出しは `update_config_from_proc_cmdline` フラグによりスキップされる |
| **system init 完了待機** | `load()` は `wait_till_system_init_done()` 後に実行。kdump が依存するファイルシステム (`/host/grub/grub.cfg` 等) が安定してからでないと `kdump_enable()` が失敗する |
| **ssh_string / ssh_path の適用タイミング** | `/etc/default/kdump-tools` への SSH 設定書き込みは即時だが、実際のリモートダンプ有効化は次回リブート後のカーネルロード時 |

---

## 4. ブートローダ別パス

| ブートローダ | 設定ファイル | 更新関数 |
|------------|------------|---------|
| GRUB | `/host/grub/grub.cfg` | `rewrite_cfg()` |
| Aboot | `/host/image-<name>/kernel-cmdline` | `rewrite_cfg()` |
| U-Boot | `uboot-env.txt` → `fw_setenv` | `modify_crashkernel_param_uboot_env()` |

evidence: `sonic-utilities/scripts/sonic-kdump-config` L34-36、L165-195、L640-695
