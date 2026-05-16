# KDUMP — Phase D 失敗挙動分析

生成日: 2026-05-16

<!-- failure -->
## crashkernel メモリ確保失敗

**ソース**: `sonic-utilities/scripts/sonic-kdump-config` L94-99, L669-683

```python
# sonic-kdump-config:94
def get_crash_kernel_size():
    try:
        with open(kdump_mem_file, 'r') as fp:
            return fp.read().rstrip('\n')
    except Exception as e:
        return "0"
```

`/sys/kernel/kexec_crash_size` の読み取りに失敗した場合、`"0"` を返す（例外を呑み込む）。

`kdump_enable()` 内では `crashkernel=<memory>` をブートローダ設定に書き込むが、カーネル起動時に指定サイズのメモリが確保できない場合（物理メモリ不足・HugeTLB 競合等）、`kexec_crash_size` が `0` のまま残り kdump カーネルがロードされない。

| 失敗条件 | 挙動 |
|---------|------|
| `memory` 値が小さすぎる（例: `32M`）でリブート | kdump カーネルがロードされず `kexec_crash_size = 0`。`show kdump status` は `Not Ready` を表示 |
| 物理メモリ不足で crashkernel 確保不可 | 同上。DB の値は正常のまま。エラーログはカーネルブート時にのみ出力 |
| `crashkernel=` パラメータがブートローダ設定に書き込めない | `locate_image()` が `-1` を返した場合、`lines[-1]` を誤って更新する（インデックス `-1` は最終行）。クラッシュは発生しないが無効行が更新される |

## systemd / kdump-config サービス起動失敗

**ソース**: `sonic-kdump-config` L483-496, L694-716

```python
# sonic-kdump-config:483
def write_use_kdump(use_kdump):
    (rc, lines, err_str) = run_command(
        "/bin/sed -i -e 's/USE_KDUMP=.*/USE_KDUMP=%s/' %s" % (use_kdump, kdump_cfg), use_shell=False)
    if rc == 0 and type(lines) == list and len(lines) == 0:
        ...
        if use_kdump == 0:
            (rc, lines, err_str) = run_command("/usr/sbin/kdump-config unload", use_shell=False)
            if rc != 0:
                print_err("Error Unable to unload the Kdump kernel '%s'", err_str)
                sys.exit(1)
    else:
        print_err("Error while writing USE_KDUMP into %s" % kdump_cfg)
        sys.exit(1)
```

```python
# sonic-kdump-config:713
(rc, lines, err_str) = run_command("/usr/sbin/kdump-config load", use_shell=False)
if rc != 0:
    print_err("Error: Unable to reload kdump configuration", err_str)
    sys.exit(1)
```

| 失敗条件 | 挙動 |
|---------|------|
| `/etc/default/kdump-tools` の `USE_KDUMP` 書き換え失敗（パーミッション等） | `print_err("Error while writing USE_KDUMP into ...")` → `sys.exit(1)` でスクリプト終了 |
| `kdump-config unload` が非ゼロ終了 | `print_err("Error Unable to unload the Kdump kernel ...")` → `sys.exit(1)` |
| `kdump-config load` が非ゼロ終了 | `print_err("Error: Unable to reload kdump configuration")` → `sys.exit(1)` |
| リモート設定時 `kdump-config set-remote` 失敗 | `print_err("Error: Unable to set remote crash dump configuration")` → `sys.exit(1)` |

いずれの場合も CONFIG_DB への巻き戻しは行われない。DB の `enabled: true` は残ったまま、実際の kdump サービスは停止状態となる不整合が生じる。

## 不正 num_dumps 値

**ソース**: `sonic-kdump-config` L501-529, `config/kdump.py` L90-98

```python
# sonic-kdump-config:521
def write_num_dumps(num_dumps):
    (rc, lines, err_str) = run_command(
        "/bin/sed -i -e 's/#*KDUMP_NUM_DUMPS=.*/KDUMP_NUM_DUMPS=%d/' %s" % (num_dumps, kdump_cfg),
        use_shell=False)
    if rc == 0 and type(lines) == list and len(lines) == 0:
        num_dumps_in_cfg = read_num_dumps()
        if num_dumps_in_cfg != num_dumps:
            print_err("Unable to write KDUMP_NUM_DUMPS into %s" % kdump_cfg)
            sys.exit(1)
    else:
        print_err("Error while writing KDUMP_NUM_DUMPS into %s" % kdump_cfg)
        sys.exit(1)
```

| 失敗条件 | 挙動 |
|---------|------|
| `num_dumps = 0` | CLI (`config/kdump.py`) は `type=int` で受け取るが下限チェックなし。`sonic-kdump-config --num_dumps 0` で `KDUMP_NUM_DUMPS=0` を `/etc/default/kdump-tools` に書き込む。kdump-tools はローテーションを無制限として扱う可能性がある |
| `num_dumps` が負値 | 同様に下限チェックなし。`KDUMP_NUM_DUMPS=-1` が書き込まれる。kdump-tools の動作は実装依存 |
| YANG 検証（`uint8` 型、range `1..9`）は mgmt-framework 経由時のみ有効 | CLI / `sonic-kdump-config` の直接呼び出しではバイパスされる |

<!-- /failure -->
