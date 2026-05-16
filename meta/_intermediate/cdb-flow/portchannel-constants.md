# PORTCHANNEL ハードコード定数調査 (Phase E)

## 調査ソース

- `sonic-swss/cfgmgr/portmgr.h:14-15`
- `sonic-swss/cfgmgr/shellcmd.h:7,13-14`
- `sonic-swss/cfgmgr/teammgr.cpp:181-183,248-252,564-649,683-727`
- `sonic-buildimage/src/sonic-config-engine/minigraph.py:969-971`

## ハードコード定数一覧

### MTU

| 定数名 | 値 | 定義箇所 | 用途 |
|---|---|---|---|
| `DEFAULT_MTU_STR` | `"9100"` | `portmgr.h:15` | LAG・メンバポートの MTU フォールバック値 |

- `teammgr.cpp:252`: LAG 作成時の初期 MTU: `string mtu = DEFAULT_MTU_STR;`
- `teammgr.cpp:805,812,850`: `addLagMember()` / `removeLagMember()` でもメンバポートに `DEFAULT_MTU_STR` をフォールバック
- コメント `teammgr.cpp:805`: `// Get the LAG MTU (by default 9100)`
- YANG range: 1..9216 — YANG 上限と異なる (`9100 != 9216`)

### min_links (min_ports)

| 定수名 | 値 | 定義箇所 | 用途 |
|---|---|---|---|
| `min_links` 初期値 | `0` | `teammgr.cpp:248` | min_links 省略時のフォールバック (`int min_links = 0;`) |

- `min_links == 0` の場合、`addLag()` の teamd conf に `min_ports` フィールドを**出力しない** (`teammgr.cpp:611`)
- teamd 側デフォルト: min_ports 未指定 → 1 ポートでも LAG が operational up
- minigraph.py による自動算出: `ceil(メンバ数 × 0.75)` (`minigraph.py:969,971`)

### LACP タイマ (fast_rate / slow)

| 定数名 | 値 | 定義箇所 | 用途 |
|---|---|---|---|
| `fast_rate` 初期値 | `false` | `teammgr.cpp:250` | fast_rate 省略時フォールバック (`bool fast_rate = false;`) |

- `fast_rate == false` の場合、teamd conf に `fast_rate` フィールドを出力しない (`teammgr.cpp:621`)
- teamd デフォルト: LACP PDU 送受信間隔 **30 秒** (slow rate)
- `fast_rate == true` 時: LACP PDU 送受信間隔 **1 秒** (fast rate)
- LAG 作成後の変更は teamd 再起動まで無効 (`teammgr.cpp:258-259`)

### LACP key 生成

| 定数名 | 値 | 定義箇所 | 用途 |
|---|---|---|---|
| `lacp_key` backward compat 値 | `0` | `teammgr.cpp:726` | lacp_key 未設定または空文字列時のフォールバック |
| `lacp_key == "auto"` プレフィックス | `"1"` | `teammgr.cpp:709` | PortChannel 名末尾数字に "1" プレフィックスを付加してキー生成 |

- 例: `PortChannel0001` → LACP key = `10001`
- 例: `PortChannel10` → LACP key = `110` (PortChannel010 との衝突回避のため prefix "1")

### 管理状態デフォルト

| 定数名 | 値 | 定義箇所 | 用途 |
|---|---|---|---|
| `DEFAULT_ADMIN_STATUS_STR` | `"down"` | `portmgr.h:14` | admin_status 省略時フォールバック |

- YANG mandatory=true なのに実装は "down" フォールバック → discrepancy

### リトライ / スリープ

| 定数名 | 値 | 定義箇所 | 用途 |
|---|---|---|---|
| クリーンアップ間スリープ | `10` ms | `teammgr.cpp:183,227` | LAG 削除時 netlink バッファ溢れ防止 |

- リトライ上限なし: `task_need_retry` は無限ループ。外部障害が恒久的な場合は手動介入が必要。

### バイナリパス (ハードコード)

| 定数名 | 値 | 定義箇所 |
|---|---|---|
| `TEAMD_CMD` | `"/usr/bin/teamd"` | `shellcmd.h:13` |
| `TEAMDCTL_CMD` | `"/usr/bin/teamdctl"` | `shellcmd.h:14` |
| `IP_CMD` | `"/sbin/ip"` | `shellcmd.h:7` |
| warm reboot dump path | `"/var/warmboot/teamd/"` | `teammgr.cpp:573` |
| teamd PID ファイルパス | `"/var/run/teamd/<alias>.pid"` | `teammgr.cpp:659,187` |
| `partner_system_id_offset` | `40` (bytes) | `teammgr.cpp:581` (LACP PDU 内パートナー MAC オフセット) |

## 結論

- YANG スキーマに `default` 文がない `mtu`・`min_links`・`fast_rate`・`admin_status` はすべて実装内でハードコード定数によりフォールバック。
- `mtu = "9100"` は YANG range 上限 9216 と異なる。
- `min_links = 0` → teamd に `min_ports` 未出力 → 1 ポート up で LAG が up。
- `fast_rate = false` → slow rate (30 秒) が teamd デフォルトとなる。
- リトライ上限なし。クリーンアップ時のみ 10 ms sleep が存在。
