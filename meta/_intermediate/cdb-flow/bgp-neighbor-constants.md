# BGP_NEIGHBOR — Phase E: ハードコード定数調査

## 調査対象ファイル

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/runner.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/frr.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`
- `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/general/instance.conf.j2`
- `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/internal/instance.conf.j2`
- `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/voq_chassis/instance.conf.j2`
- `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/general/peer-group.conf.j2`
- `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/internal/peer-group.conf.j2`
- `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/bgpd.main.conf.j2`
- `sonic-buildimage/files/image_config/constants/constants.yml`

---

## ハードコード定数一覧

### BGP タイマー系（Jinja2 テンプレート由来）

| 定数名 / 用途 | 値 | 対象 peer_type | ソースファイル:行 |
|---|---|---|---|
| `timers connect` | **10** (秒) | general / internal / voq_chassis / dynamic | `general/instance.conf.j2:11` / `internal/instance.conf.j2:7` / `voq_chassis/instance.conf.j2:14` |
| `keepalive` (general デフォルト比較値) | **60** (秒) — この値のときは FRR デフォルトに委任 | general | `general/instance.conf.j2:7-9` |
| `holdtime` (general デフォルト比較値) | **180** (秒) — この値のときは FRR デフォルトに委任 | general | `general/instance.conf.j2:7-9` |
| `keepalive` (internal 強制値) | **3** (秒) | internal | `internal/instance.conf.j2:6` |
| `holdtime` (internal 強制値) | **10** (秒) | internal | `internal/instance.conf.j2:6` |
| `keepalive` (voq_chassis 強制値) | **2** (秒) | voq_chassis | `voq_chassis/instance.conf.j2:13` |
| `holdtime` (voq_chassis 強制値) | **7** (秒) | voq_chassis | `voq_chassis/instance.conf.j2:13` |

### BGP 上限値（constants.yml + Jinja2 Fallback）

| 定数名 / 用途 | 値 | ソースファイル:行 |
|---|---|---|
| `maximum-paths ibgp` IPv4 デフォルト (voq_chassis) | **64** (Jinja2 `\| default(64)`) | `voq_chassis/instance.conf.j2:22` |
| `maximum-paths ibgp` IPv6 デフォルト (voq_chassis) | **64** (Jinja2 `\| default(64)`) | `voq_chassis/instance.conf.j2:29` |
| `maximum_paths.ipv4` (constants.yml 実値) | **514** | `files/image_config/constants/constants.yml:29` |
| `maximum_paths.ipv6` (constants.yml 実値) | **514** | `files/image_config/constants/constants.yml:30` |
| `allowas-in` (general / internal / voq_chassis) | **1** | `general/peer-group.conf.j2:8,11,23,26` / `internal/peer-group.conf.j2:15,29` / `voq_chassis/peer-group.conf.j2:15,26` |
| `ttl-security hops` (chassis-packet internal) | **1** | `internal/peer-group.conf.j2:8,22` |

### Graceful Restart タイマー（ToRRouter 限定）

| 定数名 / 用途 | 値 | ソースファイル:行 |
|---|---|---|
| `bgp graceful-restart restart-time` デフォルト | **240** (秒) | `bgpd.main.conf.j2:119` / `constants.yml:24` |
| `bgp graceful-restart select-defer-time` デフォルト | **45** (秒) | `bgpd.main.conf.j2:122` |

### BMP 接続タイマー

| 定数名 / 用途 | 値 | ソースファイル:行 |
|---|---|---|
| `bmp connect` min-retry | **10000** (ms) | `bgpd.main.conf.j2:136` |
| `bmp connect` max-retry | **15000** (ms) | `bgpd.main.conf.j2:136` |
| `bmp stats interval` | **1000** (ms) | `bgpd.main.conf.j2:133` |
| `bmp mirror buffer-limit` | **4294967214** (bytes) | `bgpd.main.conf.j2:130` |
| BMP listen port | **5000** | `bgpd.main.conf.j2:136` |

### 起動時待機・ポーリング定数（Python）

| 定数名 / 用途 | 値 | ソースファイル:行 |
|---|---|---|
| `wait_for_daemons` タイムアウト | **20** 秒 | `main.py:47` |
| FRR daemon ポーリング sleep | **100** ms (`time.sleep(0.1)`) | `frr.py:30` |
| mgmtd datastore 最大試行回数 | **10** 回 (約 5 秒) | `main.py:51` |
| mgmtd vtysh コマンド timeout | **2** 秒 | `main.py:54` |
| mgmtd ポーリング sleep | **0.5** 秒 | `main.py:64` |
| `Runner.SELECT_TIMEOUT` (メインループ) | **1000** ms | `runner.py:21` |

---

## 特記事項（discrepancy / 注意）

1. **`timers connect 10` は全 peer_type に共通** — YANG で定義される `conn_retry` フィールドとは独立して bgpcfgd がハードコードで発行する。bgpcfgd 経路では `conn_retry` は無視。
2. **general テンプレートの keepalive/holdtime** — CONFIG_DB 値が 60/180 のときはコマンドを省略（FRR デフォルトに委任）。異なる値のときのみ `timers <k> <h>` を発行。
3. **internal / voq_chassis テンプレートの keepalive/holdtime** — CONFIG_DB 値を完全無視して固定値を発行（`internal`: 3/10、`voq_chassis`: 2/7）。DISCREPANCY あり。
4. **maximum-paths Jinja2 fallback** — `constants.bgp.maximum_paths.enabled=true` かつ `constants.yml` に実値 514 が設定される。fallback デフォルト `| default(64)` は constants.yml が存在しない環境でのみ効く。
5. **Graceful restart select-defer-time** — `constants.yml` には `select_defer_time` キーなし。Jinja2 の `| default(45)` が実効値となる。
