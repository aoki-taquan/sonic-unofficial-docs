# PIM_GLOBALS / PIM_INTERFACE — Phase A: コード由来の暗黙デフォルト調査結果

調査日: 2026-05-15
対象ファイル:
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
- `sonic-frr/pimd/pim_pim.h`
- `sonic-frr/pimd/pim_upstream.h`
- `sonic-frr/pimd/pim_pim.c`
- `sonic-frr/pimd/pimd.c`

---

## 1. テーブル構造

### PIM_GLOBALS

key 構造: `PIM_GLOBALS|<vrf>|<af>`

frrcfgd.py L3805-3821 で `vrf = prefix`, `af = key.split('|')` として解析。
`cmd_prefix = ['configure terminal', 'vrf {}'.format(vrf)]` でコマンド発行。

フィールド定義 (frrcfgd.py L2065-2070):
```python
pim_global_key_map = [
    ('join-prune-interval', '{no:no-prefix}ip pim join-prune-interval {}'),
    ('keep-alive-timer',    '{no:no-prefix}ip pim keep-alive-timer {}'),
    ('ssm-ranges',          '{no:no-prefix}ip pim ssm prefix-list {}'),
    ('ecmp-enabled',        '{no:no-prefix}ip pim ecmp', ['true', 'false']),
    ('ecmp-rebalance-enabled', '{no:no-prefix}ip pim ecmp rebalance', ['true', 'false']),
]
```

### PIM_INTERFACE

key 構造: `PIM_INTERFACE|<vrf>|<af>|<interface>`

frrcfgd.py L3772-3803 で `vrf = prefix`, `af, if_name = key.split('|')` として解析。
`cmd_prefix = ['configure terminal', 'interface {}'.format(if_name)]` でコマンド発行。

フィールド定義 (frrcfgd.py L2059-2064):
```python
pim_interface_key_map = [
    ('mode',           '{no:no-prefix}ip pim', ['sm', '']),
    ('dr-priority',    '{no:no-prefix}ip pim drpriority {}'),
    ('hello-interval', '{no:no-prefix}ip pim hello {:pim_hello_parms}',
                       hdl_set_pim_hello_parms),
    ('bfd-enabled',    '{no:no-prefix}ip pim bfd', ['true', 'false']),
]
```

---

## 2. FRR 側のハードコードデフォルト

### PIM_INTERFACE フィールド

| フィールド | FRR 定数 | 値 | 出典 |
|------------|----------|-----|------|
| `hello-interval` | `PIM_DEFAULT_HELLO_PERIOD` | **30** 秒 | `pimd/pim_pim.h` L30; `pimd/pim_pim.c` L436 |
| `dr-priority` | `PIM_DEFAULT_DR_PRIORITY` | **1** | `pimd/pim_pim.h` L32; `pimd/pim_pim.c` L440 |
| `mode` | — | 未設定（sparse-mode 無効） | `pim_interface_key_map` 定義。`['sm', '']` の後者が OP_DELETE 相当 |
| `bfd-enabled` | — | `false` | `['true', 'false']` の後者がデフォルト |

pim_pim.c L436 での初期化:
```c
pim_ifp->pim_hello_period = PIM_DEFAULT_HELLO_PERIOD;  /* 30 */
pim_ifp->pim_dr_priority  = PIM_DEFAULT_DR_PRIORITY;   /* 1 */
```

### PIM_GLOBALS フィールド

| フィールド | FRR 定数/変数 | 値 | 出典 |
|------------|--------------|-----|------|
| `join-prune-interval` | `PIM_DEFAULT_T_PERIODIC` → `router->t_periodic` | **60** 秒 | `pimd/pim_pim.h` L36; `pimd/pimd.c` L83 |
| `keep-alive-timer` | `PIM_KEEPALIVE_PERIOD` | **210** 秒 | `pimd/pim_upstream.h` L213 |
| `ecmp-enabled` | `pim->ecmp_enable` | **false** | `pimd/pim_instance.c` L81 |
| `ecmp-rebalance-enabled` | `pim->ecmp_rebalance_enable` | **false** | `pimd/pim_instance.c` L82 |
| `ssm-ranges` | — | 省略可 (absent) | フィールドが absent なら FRR コマンド非発行 |

pimd.c L83:
```c
router->t_periodic = PIM_DEFAULT_T_PERIODIC;  /* 60 */
```

pim_upstream.h L213:
```c
#define PIM_KEEPALIVE_PERIOD  (210)
```

pim_instance.c L81-82:
```c
pim->ecmp_enable           = false;
pim->ecmp_rebalance_enable = false;
```

---

## 3. `mode` フィールドの条件付き動作

frrcfgd.py L3787-3803:
`PIM_INTERFACE` エントリ更新時、`mode` が data に含まれる場合のみ `key_map.run_command()` を呼び出す。
つまり `mode` を含まないエントリ更新では **いかなる FRR コマンドも発行されない**。
`mode` は実質的な必須フィールド（YANG mandatory 宣言なしだが動作上必須）。

```python
if 'mode' in data:
    # ...
    if not key_map.run_command(self, table, data, cmd_prefix):
        syslog.syslog(syslog.LOG_ERR, 'failed running PIM config command')
```

`mode = 'sm'` → `ip pim` コマンド発行（sparse-mode 有効化）
`mode = ''` (OP_DELETE) → `no ip pim` + キャッシュフラッシュ（他フィールドを STAT_SUCC + OP_DELETE に設定）

---

## 4. `hello-interval` の pim_hello_parms フォーマット

frrcfgd.py L941-942:
```python
elif format == 'pim_hello_parms':
    self.value = ' '.join(self.value.split(','))
```

CONFIG_DB に `"30,5"` と格納 → FRR コマンド `ip pim hello 30 5` に変換（カンマ区切り → スペース区切り）。
OP_DELETE 時は `hdl_set_pim_hello_parms` が `args = ('',)` に置換して `no ip pim hello` を発行。

---

## 5. `ecmp-rebalance-enabled` の前提条件

`ecmp-rebalance-enabled = true` が機能するには `ecmp-enabled = true` が前提。
FRR pimd は ECMP が無効なら rebalance も無効にする（実装依存）。
CONFIG_DB レベルでの強制はなく、`frrcfgd` はそれぞれ独立したコマンドを発行する。

---

## 6. RFC 4601 との対応

| CONFIG_DB フィールド | RFC 4601 タイマー名 | 既定値 |
|----------------------|---------------------|--------|
| `hello-interval` | Hello Period (4.11) | 30 秒 |
| `dr-priority` | DR Priority (4.3.1) | 1 |
| `join-prune-interval` | t_periodic (4.11) | 60 秒 |
| `keep-alive-timer` | KeepaliveTimer (4.2) | 210 秒 |
