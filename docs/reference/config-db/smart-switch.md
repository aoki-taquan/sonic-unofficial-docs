---
title: SmartSwitch 関連テーブル (MID_PLANE_BRIDGE / DHCP_SERVER_IPV4_PORT)
description: "SmartSwitch NPU-DPU 間ミッドプレーンブリッジおよびポートベース DHCP 割り当てを管理する CONFIG_DB テーブル群。MID_PLANE_BRIDGE、DHCP_SERVER_IPV4_PORT の構造・デフォルト・ハードコード挙動を詳述。"
area: reference
verification: code-verified
last_verified: 2026-05-14
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-smart-switch.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-dhcp-server-ipv4.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-config-engine/config_samples.py
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcp_cfggen.py
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-dhcp-utilities/dhcp_utilities/dhcprelayd/dhcprelayd.py
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - MID_PLANE_BRIDGE
    - DHCP_SERVER_IPV4_PORT
    - DHCP_SERVER_IPV4
    - DPUS
    - DEVICE_METADATA
  yang:
    - sonic-smart-switch
    - sonic-dhcp-server-ipv4
---

# SmartSwitch 関連テーブル (MID_PLANE_BRIDGE / DHCP_SERVER_IPV4_PORT)

## 概要

[SmartSwitch](../../reference/glossary.md#term-smartswitch) は [SONiC](../../reference/glossary.md#term-sonic) [NPU](../../reference/glossary.md#term-npu) と複数の [DPU](../../reference/glossary.md#term-dpu) (Data Processing Unit) を搭載した複合スイッチ筐体。
[NPU](../../reference/glossary.md#term-npu)-[DPU](../../reference/glossary.md#term-dpu) 間はミッドプレーンブリッジ (`bridge-midplane`) を介して L2 接続され、[DPU](../../reference/glossary.md#term-dpu) への IPv4 割り当ては
DHCP サーバ (`dhcp_server` feature) が `DHCP_SERVER_IPV4_PORT` テーブルを参照してポートごとに固定 IP を払い出す。

[SmartSwitch](../../reference/glossary.md#term-smartswitch) 機能が有効化されるかどうかは `DEVICE_METADATA|localhost.subtype == "SmartSwitch"` で判定される。

---

## MID_PLANE_BRIDGE テーブル

### key 構造

```text
MID_PLANE_BRIDGE|GLOBAL
```

固定のシングルエントリ (`GLOBAL`) のみ。

### フィールド一覧

| フィールド | 型 | 必須 | 説明 |
|-----------|------|------|------|
| `bridge` | string (`"bridge-midplane"` のみ) | - | ミッドプレーンブリッジ名。[YANG](../../reference/glossary.md#term-yang) の `pattern` 制約で `"bridge-midplane"` 固定 |
| `ip_prefix` | IPv4 prefix | - | ブリッジの IP プレフィックス。`bridge` が存在する場合は [YANG](../../reference/glossary.md#term-yang) `must` 制約で必須 |

!!! note "`bridge` フィールドの取りうる値"
    YANG (`sonic-smart-switch.yang:63-69`) の `type string { pattern "bridge-midplane"; }` により、
    `bridge` に設定できる値は `"bridge-midplane"` のみ。デフォルト宣言はなく、エントリ自体が任意だが、
    設定する場合は必ずこの値を使用する。

### 設定例

```json
{
  "MID_PLANE_BRIDGE": {
    "GLOBAL": {
      "bridge": "bridge-midplane",
      "ip_prefix": "169.254.200.254/24"
    }
  }
}
```

### 購読者

- `dhcpservd` (`dhcp_cfggen.py`): `GLOBAL.bridge` / `GLOBAL.ip_prefix` を読み取り DHCP サーバのサブネット設定を生成
- `dhcprelayd` (`dhcprelayd.py`): `GLOBAL.bridge` からブリッジ名を取得し、`DHCP_SERVER_IPV4` のインターフェース照合に使用

---

## DHCP_SERVER_IPV4_PORT テーブル

### key 構造

```text
DHCP_SERVER_IPV4_PORT|<dhcp_interface>|<port>
```

- `<dhcp_interface>`: `DHCP_SERVER_IPV4` のキー（[SmartSwitch](../../reference/glossary.md#term-smartswitch) の場合 `"bridge-midplane"`）
- `<port>`: DPU ミッドプレーンインターフェース名（`dpu0`, `dpu1`, ...）

### フィールド一覧

| フィールド | 型 | 必須 | 説明 |
|-----------|------|------|------|
| `ips` | IPv4 アドレスリスト | ※ | 静的 IP 割り当てリスト。`ranges` と排他 |
| `ranges` | leafref リスト | ※ | IP レンジ名参照リスト。`ips` と排他 |

※ `ips` または `ranges` のどちらか一方が必要。YANG の `must` 制約で両方同時設定は不可。

### SmartSwitch での使用パターン

SmartSwitch では `ips` が使用され、各 DPU に `169.254.200.<dpu_id+1>` が自動割り当てられる:

| エントリキー | `ips` |
|------------|-------|
| `bridge-midplane\|dpu0` | `["169.254.200.1"]` |
| `bridge-midplane\|dpu1` | `["169.254.200.2"]` |
| `bridge-midplane\|dpu2` | `["169.254.200.3"]` |
| `bridge-midplane\|dpu3` | `["169.254.200.4"]` |

```json
{
  "DHCP_SERVER_IPV4_PORT": {
    "bridge-midplane|dpu0": { "ips": ["169.254.200.1"] },
    "bridge-midplane|dpu1": { "ips": ["169.254.200.2"] },
    "bridge-midplane|dpu2": { "ips": ["169.254.200.3"] },
    "bridge-midplane|dpu3": { "ips": ["169.254.200.4"] }
  }
}
```

### 購読者

- `dhcpservd` (`dhcp_cfggen.py`): `DHCP_SERVER_IPV4_PORT` を `_parse_port()` で解析し、`dhcpd.conf` の `host` 節に展開

---

<!-- ordering -->
## 書込み順依存

`dhcpservd` の `generate()` と `dhcprelayd` の `refresh_dhcrelay()` はイベントごとに [CONFIG_DB](../../reference/glossary.md#term-config_db) を全量スナップショットし Kea / dhcrelay 設定を再生成する。このため書き込み順序が初回起動時の設定完全性に影響する。

### 検出された順序依存

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `DEVICE_METADATA\|localhost.subtype = "SmartSwitch"` → `MID_PLANE_BRIDGE` / `DHCP_SERVER_IPV4_PORT` 処理 | 先行必須（欠如時 SmartSwitch 経路が完全スキップ） | `MidPlaneTableEventChecker` 変更で `dhcpservd` が再生成トリガー |
| 2 | `MID_PLANE_BRIDGE\|GLOBAL.bridge` と `ip_prefix` の同時書き込み | 必須（片方欠如で SmartSwitch サブネット生成がスキップ） | YANG `must` 制約が CLI 経由の不整合書き込みを拒否 |
| 3 | `DPUS\|<dpu_name>` → `DHCP_SERVER_IPV4_PORT\|bridge-midplane\|<dpu>` | 先行必須（YANG leafref 制約） | CLI / [sonic-cfggen](../../reference/glossary.md#term-sonic-cfggen) は YANG バリデーションで reject |
| 4 | `MID_PLANE_BRIDGE\|GLOBAL` + `DHCP_SERVER_IPV4\|bridge-midplane` → `dhcprelayd` midplane 認識 | 同時または先行推奨 | `MidPlaneTableEventChecker` で変更後に自動再評価 |
| 5 | 全 SmartSwitch テーブル → `FEATURE\|dhcp_server.state=enabled` | 推奨先行（初回起動時の設定欠落回避） | 後から Feature 有効化しても `MidPlaneTableEventChecker` で自動再生成 |

### 主要な制約詳細

**[DEVICE_METADATA](../../reference/glossary.md#term-device_metadata).subtype 先行必須 (依存 #1)**: `dhcp_cfggen.py:65-76` の `generate()` は最初に `DEVICE_METADATA` を読み `is_smart_switch()` を評価する。`subtype != "SmartSwitch"` の場合 `_parse_dpu()` は呼ばれず `MID_PLANE_BRIDGE` / `DHCP_SERVER_IPV4_PORT` / `DPUS` が存在していても SmartSwitch 用 Kea 設定が生成されない。`config_samples.py:83` でも `subtype` 設定を `MID_PLANE_BRIDGE` より先に行う（evidence: `dhcp_cfggen.py:65-76`; `utils.py:153-161`）。

**bridge + ip_prefix の同時書き込み必須 (依存 #2)**: `dhcp_cfggen.py:84` の条件 `"bridge" in mid_plane and "ip_prefix" in mid_plane` を両方満たすとき初めて SmartSwitch サブネットが Kea 設定に追加される。YANG `must "(current()/../ip_prefix)"` 制約も `bridge` と `ip_prefix` の同時存在を強制する（evidence: `dhcp_cfggen.py:84`, `sonic-smart-switch.yang:63-74`）。

**DPUS 先行必須 (依存 #3)**: `DHCP_SERVER_IPV4_PORT.<port>` フィールドは `DPUS.<dpu_name>.midplane_interface` への YANG leafref であるため、`DPUS` エントリが存在しない状態で `DHCP_SERVER_IPV4_PORT` を書いても YANG バリデーションで reject される（evidence: `sonic-dhcp-server-ipv4.yang:231-233`）。

<!-- /ordering -->

---

<!-- cross-refs -->
## 暗黙参照テーブル

`MID_PLANE_BRIDGE` および `DHCP_SERVER_IPV4_PORT` は [CONFIG_DB](../../reference/glossary.md#term-config_db) の複数テーブルを YANG leafref
またはコード側の implicit 参照で依存する。

| 参照元テーブル | 参照元フィールド | 参照先テーブル | 参照先フィールド | 参照種別 | 参照箇所 |
|---|---|---|---|---|---|
| `DHCP_SERVER_IPV4` | `name` (SmartSwitch 用値 `"bridge-midplane"`) | `MID_PLANE_BRIDGE\|GLOBAL` | `bridge` | YANG leafref | `sonic-dhcp-server-ipv4.yang:61-63` |
| `DHCP_SERVER_IPV4_PORT` | `name` | `DHCP_SERVER_IPV4` | `name` (キー) | YANG leafref | `sonic-dhcp-server-ipv4.yang:217-219` |
| `DHCP_SERVER_IPV4_PORT` | `port` (`dpu0` 等) | `DPUS` | `midplane_interface` | YANG leafref | `sonic-dhcp-server-ipv4.yang:231-233` |
| `dhcpservd` (コード) | — | `DEVICE_METADATA` | `localhost.subtype` | 暗黙参照 | `dhcp_cfggen.py:65-67` |
| `dhcpservd` (コード) | — | `DPUS` | `midplane_interface` | 暗黙参照 | `dhcp_cfggen.py:74,119` |
| `dhcprelayd` (コード) | — | `DHCP_SERVER_IPV4` | `state` | 暗黙参照 | `dhcprelayd.py:82-103` |

### 解決タイミング

- YANG leafref は CONFIG_DB への書き込み時に `sonic-cfggen` / CLI の YANG バリデーションで確認される。
  参照先が存在しない場合は書き込みが reject される。
- `dhcpservd` の暗黙参照は `generate()` 呼び出し時 (起動時 + テーブル変更イベント時) に評価される。
  `DEVICE_METADATA.subtype` が `"SmartSwitch"` でない場合、`MID_PLANE_BRIDGE` / `DPUS` /
  `DHCP_SERVER_IPV4_PORT` への参照コードは実行されない。

### 必須先行順序

```text
DEVICE_METADATA|localhost.subtype = "SmartSwitch"   ← SmartSwitch 経路を有効化
DPUS|<dpu_name>                                      ← DHCP_SERVER_IPV4_PORT.port の leafref 源
MID_PLANE_BRIDGE|GLOBAL                              ← DHCP_SERVER_IPV4.name の leafref 源
DHCP_SERVER_IPV4|bridge-midplane                    ← DHCP_SERVER_IPV4_PORT.name の leafref 源
DHCP_SERVER_IPV4_PORT|bridge-midplane|<dpu>         ← 全依存が揃ってから書き込む
```

<!-- /cross-refs -->

---

<!-- defaults -->
## 暗黙デフォルトとハードコード挙動


### 1. MID_PLANE_BRIDGE|GLOBAL.bridge — YANG pattern で値を固定

YANG (`sonic-smart-switch.yang:63-69`) の定義:

```yang
leaf bridge {
    type string {
        pattern "bridge-midplane";
    }
    must "(current()/../ip_prefix)";
}
```

- `pattern "bridge-midplane"` により設定可能な文字列は `"bridge-midplane"` のみ。
- `default` 宣言はないが、設定する際は値が固定される。
- `must` 制約: `bridge` が存在するなら `ip_prefix` も必須（YANG レベル強制）。

証跡: `sonic-smart-switch.yang:63-69`、`config_samples.py:88`

### 2. MID_PLANE_BRIDGE|GLOBAL.ip_prefix — 事実上のデフォルト `169.254.200.254/24`

YANG に `default` 宣言なし。ただし SmartSwitch 設定生成コード (`config_samples.py:85-94`) でハードコードされる:

```python
mpbr_prefix = '169.254.200'
mpbr_address = '{}.254'.format(mpbr_prefix)  # "169.254.200.254"
data['MID_PLANE_BRIDGE'] = {
    "GLOBAL": {
        "bridge": bridge_name,
        "ip_prefix": "169.254.200.254/24"
    }
}
```

リンクローカル帯 `169.254.200.0/24` を使用。テスト用 mock データも同値。

証跡: `config_samples.py:85-94`、`tests/sample_output/t1-smartswitch.json`

### 3. DHCP_SERVER_IPV4_PORT.ips — DPU ID から計算されるハードコードルール

YANG に `default` 宣言なし。設定生成コード (`config_samples.py:99-103`):

```python
dpu_id = int(midplane_interface.replace('dpu', ''))
dhcp_server_ports['{}|{}'.format(bridge_name, midplane_interface)] = {
    'ips': ['{}.{}'.format(mpbr_prefix, dpu_id + 1)]
}
```

DPU ごとに `169.254.200.<dpu_id+1>` が計算・割り当てられる。これは YANG デフォルトではなく
`config_samples.py` のコード生成ルール。ユーザが手動設定する際は任意の値を指定可能。

証跡: `config_samples.py:99-103`

### 4. smart_switch フラグによるハンドラ分岐

`dhcp_cfggen.py:67, 76, 84` および `dhcprelayd.py:65, 102`:

```python
smart_switch = is_smart_switch(device_metadata)  # DEVICE_METADATA.subtype == "SmartSwitch"
mid_plane, dpus = self._parse_dpu(...) if smart_switch else ({}, {})
if smart_switch and "bridge" in mid_plane and "ip_prefix" in mid_plane:
    # MID_PLANE_BRIDGE の処理を実行
```

`MID_PLANE_BRIDGE` と `DHCP_SERVER_IPV4_PORT` の SmartSwitch 向け処理は `smart_switch` フラグが
`True` の場合のみ実行される。非 SmartSwitch 環境では両テーブルが存在しても DHCP サーバは
これらを SmartSwitch ブリッジとして扱わない。

証跡: `dhcp_cfggen.py:67-90`、`dhcprelayd.py:84-103`

### 5. DPUS.midplane_interface — dpu_name と等値の YANG 強制

YANG (`sonic-smart-switch.yang:94-103`):

```yang
leaf midplane_interface {
    type string { pattern "dpu[0-9]+"; }
    must "(current() = current()/../dpu_name)";
}
```

`must` 制約により `midplane_interface` は常に `dpu_name` と等しい値でなければならない。
これが `DHCP_SERVER_IPV4_PORT` の `port` フィールドへの leafref の根拠となる。

証跡: `sonic-smart-switch.yang:94-103`

### 暗黙デフォルト・乖離サマリー

| # | テーブル | フィールド | YANG default | 実装デフォルト/制約 | 種別 |
|---|---------|-----------|-------------|-------------------|------|
| 1 | MID_PLANE_BRIDGE\|GLOBAL | `bridge` | なし | `"bridge-midplane"` 固定 (YANG pattern 制約) | YANG 制約 |
| 2 | MID_PLANE_BRIDGE\|GLOBAL | `ip_prefix` | なし | `169.254.200.254/24` (`config_samples.py` ハードコード) | 実装デフォルト |
| 3 | DHCP_SERVER_IPV4_PORT | `ips` | なし | `169.254.200.<dpu_id+1>` (`config_samples.py` 計算式) | 実装生成ルール |
| 4 | DPUS | `midplane_interface` | なし | `== dpu_name` (YANG `must` 制約) | YANG 制約 |
| 5 | DHCP_SERVER_IPV4 | `lease_time` | なし | `3600` 秒 (`config_samples.py` ハードコード) | 実装デフォルト |
| 6 | DHCP_SERVER_IPV4 | `gateway` | なし | `169.254.200.254` (mpbr_address 計算値) | 実装生成ルール |

<!-- /defaults -->

---

<!-- failure -->
## 無効入力・障害時の挙動


### 1. YANG バリデーション失敗（書き込み拒否）

**`MID_PLANE_BRIDGE.bridge` パターン違反**  
`sonic-smart-switch.yang:63-69` の `pattern "bridge-midplane"` により、`"bridge-midplane"` 以外の値は
CLI 書き込み時に即座に拒否される。`must "(current()/../ip_prefix)"` 制約により、`bridge` のみを書いて
`ip_prefix` を省略した場合も同様に拒否される。

**`DHCP_SERVER_IPV4_PORT` leafref 解決失敗**  
`DHCP_SERVER_IPV4|bridge-midplane` が存在しない状態で `DHCP_SERVER_IPV4_PORT|bridge-midplane|dpu0` を
書き込むと YANG leafref 制約違反で拒否される（`sonic-dhcp-server-ipv4.yang:217-219`）。
同様に `DPUS|dpu0` が存在しない状態での `port` フィールド参照も拒否される（同:231-233）。

### 2. dhcpservd — サイレント失敗

SmartSwitch 向け DHCP 処理の多くは失敗時にエラーログを出さずスキップする。

| 条件 | コード位置 | 挙動 |
|------|-----------|------|
| `DEVICE_METADATA.subtype != "SmartSwitch"` | `dhcp_cfggen.py:67,76` | `_parse_dpu()` を呼ばず空辞書返却。`MID_PLANE_BRIDGE` / `DPUS` を完全無視 |
| `bridge` または `ip_prefix` 欠落 | `dhcp_cfggen.py:84` | midplane が `dhcp_interfaces` に未登録。DPU への IP 払い出しが停止 |
| `DHCP_SERVER_IPV4_PORT` のポートが `dhcp_members` に不在 | `dhcp_cfggen.py:424-425` | `LOG_WARNING` を出力して当該ポートをスキップ。他ポートは処理継続 |
| `dhcp_interface` に IPv4 アドレスなし | `dhcp_cfggen.py:432-433` | `LOG_WARNING` を出力してスキップ |
| `ips` と `ranges` の同時指定 | `dhcp_cfggen.py:418-420` | `LOG_WARNING` を出力して当該ポートをスキップ（YANG は通常書き込み時に弾く） |

上記の「サイレント失敗」はいずれも CONFIG_DB を変更せず、他テーブルや他ポートの処理に影響を与えない。

### 3. dhcpservd — 致命的エラー（generate() 全体失敗）

**hostname 未設定** (`dhcp_cfggen.py:171-174`):

```python
if localhost_entry is None or "hostname" not in localhost_entry:
    syslog.syslog(syslog.LOG_ERR, "Cannot get hostname")
    raise Exception("Cannot get hostname")
```

`DEVICE_METADATA|localhost.hostname` が存在しない場合、`LOG_ERR` を出力して例外を送出する。
`generate()` 全体が失敗し Kea 設定ファイルが更新されない。

### 4. dhcprelayd — プロセス起動失敗

**dhcrelay ゾンビ起動** (`dhcprelayd.py:306-313`):  
dhcrelay プロセスが起動直後にゾンビ状態になった場合、`LOG_ERR` を出力してプロセスを
強制終了し `sys.exit(1)` する。`dhcprelayd` コンテナが再起動する。

**dhcp_server IP タイムアウト** (`dhcprelayd.py:375-385`):  
[STATE_DB](../../reference/glossary.md#term-state_db) の `DHCP_SERVER_IPV4_SERVER_IP|eth0.ip` を 10 回（合計 100 秒）リトライして
取得できない場合、`LOG_ERR` を出力して `sys.exit(1)` する。コンテナが再起動する。

### 5. dhcp_lease — lease ファイル不在

**lease ファイル不在** (`dhcp_lease.py:116-121`):  
Kea の lease ファイル（デフォルト `/var/lib/kea/kea-lease.csv`）が存在しない場合、
`LOG_ERR` を出力して例外を再送出する。[STATE_DB](../../reference/glossary.md#term-state_db) の `DHCP_SERVER_IPV4_LEASE` テーブルは更新されない。

### 障害影響まとめ

| 障害シナリオ | ログレベル | CONFIG_DB への影響 | 挙動 |
|---|---|---|---|
| YANG pattern/must 制約違反 | — | 書き込み拒否 | CLI がエラーを返す |
| `subtype != SmartSwitch` | なし | 不変 | サイレント。DHCP 設定不生成 |
| `bridge`/`ip_prefix` 片欠落 | なし | 不変 | サイレント。midplane DHCP 停止 |
| port が dhcp_members に不在 | WARNING | 不変 | 当該ポートのみスキップ |
| IPv4 アドレスなし dhcp_interface | WARNING | 不変 | 当該インターフェースのみスキップ |
| `ips` + `ranges` 同時指定 | WARNING | 不変 | 当該ポートのみスキップ |
| hostname 未設定 | ERR | 不変 | `generate()` 全体失敗 |
| dhcrelay ゾンビ起動 | ERR | 不変 | コンテナ再起動 |
| dhcp_server IP タイムアウト | ERR | 不変 | コンテナ再起動 |
| lease ファイル不在 | ERR | 不変 | `DHCP_SERVER_IPV4_LEASE` 更新停止 |

<!-- /failure -->

<!-- constants -->
## ハードコード定数

> **Evidence**: `src/sonic-yang-models/yang-models/sonic-smart-switch.yang`, `src/sonic-config-engine/config_samples.py`, `src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcp_cfggen.py` (2026-05-17)

### `MID_PLANE_BRIDGE` — ハードコード値

| 定数 / 値 | コード位置 | 意味 |
|---|---|---|
| `"bridge-midplane"` | `config_samples.py:88`; YANG `pattern` (`sonic-smart-switch.yang:65`) | ミッドプレーンブリッジ名。YANG pattern 制約により唯一有効な値 |
| `"169.254.200.254/24"` | `config_samples.py:93` | `MID_PLANE_BRIDGE.GLOBAL.ip_prefix` の実装値。サブネットプレフィックス `169.254.200` は `config_samples.py:85` で定数化 |
| `"169.254.200.254"` | `config_samples.py:86` | [NPU](../../reference/glossary.md#term-npu) 側ブリッジ IP（`mpbr_prefix + ".254"`）。`DHCP_SERVER_IPV4.bridge-midplane.gateway` に設定 |

### `DHCP_SERVER_IPV4_PORT` — DPU IP アドレス計算式

DPU の midplane IP は以下の計算式で自動生成される (`config_samples.py:102-103`):

```python
dpu_id = int(midplane_interface.replace('dpu', ''))   # "dpu0" → 0
dhcp_ip = '169.254.200.{}'.format(dpu_id + 1)        # "169.254.200.<dpu_id+1>"
```

| エントリキー | `ips[0]` |
|---|---|
| `bridge-midplane\|dpu0` | `169.254.200.1` |
| `bridge-midplane\|dpu1` | `169.254.200.2` |
| `bridge-midplane\|dpu7` | `169.254.200.8` |

NPU ブリッジ IP (`169.254.200.254`) は最大値 `.8`（`dpu7`）と衝突しない設計。

### `DHCP_SERVER_IPV4|bridge-midplane` — 固定パラメータ

`config_samples.py:133-141` でハードコードされた値がそのまま CONFIG_DB に投入される。

| フィールド | 値 | 注記 |
|---|---|---|
| `mode` | `"PORT"` | ポートベース割り当てモード固定 |
| `netmask` | `"255.255.255.0"` | `/24` サブネット固定 |
| `gateway` | `"169.254.200.254"` | NPU ブリッジ IP 固定 |
| `lease_time` | `"3600"` 秒 (1 時間) | SmartSwitch 固定値（通常モードのデフォルト `900` 秒と異なる） |
| `state` | `"enabled"` | SmartSwitch では最初から有効化 |

### `dhcp_cfggen.py` — 内部定数

| 定数名 | 値 | 意味 |
|---|---|---|
| `MID_PLANE_BRIDGE_SUBNET_ID` | `10000` | kea-dhcp4 の subnet ID（[VLAN](../../reference/glossary.md#term-vlan) 番号転用の代わりに固定値を使用） |
| `SMART_SWITCH_CHECKER` | `["DpusTableEventChecker", "MidPlaneTableEventChecker"]` | SmartSwitch 環境で追加購読するイベントチェッカー |

### YANG pattern 制約（ハードコード範囲）

| テーブル | フィールド | 制約 | 実質的な意味 |
|---|---|---|---|
| `MID_PLANE_BRIDGE.GLOBAL` | `bridge` | `pattern "bridge-midplane"` | 1 値のみ。変更不可 |
| `DPUS` | `dpu_name`, `midplane_interface` | `pattern "dpu[0-9]+"` | `dpu` プレフィックス + 数字 |
| `DPUS` | `midplane_interface` | `must (current() = current()/../dpu_name)` | インターフェース名 = DPU 名を強制 |
| `DPU` | `dpu_id` | `pattern [0-7]` | 0〜7 の 1 桁（最大 8 DPU） |

> **Evidence**: `src/sonic-config-engine/config_samples.py:83-103,133-143`; `src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcp_cfggen.py:17-31`; `src/sonic-yang-models/yang-models/sonic-smart-switch.yang:63-70,88-101,155-162`
<!-- /constants -->

<!-- side-effects -->
## 副次 DB 書込・ファイルシステム副作用

> **Evidence**: `dhcpservd.py`, `dhcp_cfggen.py`, `dhcp_lease.py`, `dhcprelayd.py`, `config_samples.py` (2026-05-17)

`MID_PLANE_BRIDGE` / `DPUS` / `DHCP_SERVER_IPV4_PORT` を CONFIG_DB へ書き込むと、以下の副次書き込みが発生する。

### STATE_DB: DHCP_SERVER_IPV4_LEASE（SmartSwitch 専用キー形式）

kea-dhcp4 が DPU へ IP アドレスをリース割り当てするたびに SIGUSR1 で dhcpservd に通知し、`KeaDhcp4LeaseHandler` が `/var/lib/kea/kea-lease.csv` を読み取って [STATE_DB](../../reference/glossary.md#term-state_db) に書き込む。SmartSwitch では `Vlan<id>` の代わりに `bridge-midplane` をプレフィックスに使用する。

**key 形式**:

```
DHCP_SERVER_IPV4_LEASE|bridge-midplane|<mac_address>
```

`MID_PLANE_BRIDGE.GLOBAL.bridge` の値（`"bridge-midplane"`）が `midplane_bridge_name` として使われる (`dhcp_lease.py:37-39`)。

**フィールド**:

| フィールド | 説明 |
|---|---|
| `ip` | DPU に割り当てた IPv4 アドレス（`169.254.200.x`） |
| `lease_start` | リース開始 UNIX タイムスタンプ（`lease_end - valid_lifetime` で算出） |
| `lease_end` | リース終了 UNIX タイムスタンプ（kea-lease.csv の expire カラム） |

有効リース（`lease_start != lease_end` かつ `now < lease_end`）のみ `hset`。期限切れは `state_db.delete`。`lease_update_interval=2` 秒のレートリミットあり。

> **Evidence**: `src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcp_lease.py:34-39,108-112,79-93`

### STATE_DB: DHCP_SERVER_IPV4_SERVER_IP

dhcpservd 起動時に 1 回のみ実行。dhcp_server コンテナの `eth0` IPv4 アドレスを STATE_DB に書き込む。SmartSwitch 環境ではこの IP が DPU → NPU 向け DHCP リレーの参照先となる。

**key 形式**: `DHCP_SERVER_IPV4_SERVER_IP|eth0`  
**フィールド**: `ip` — eth0 の IPv4 アドレス文字列  
取得失敗時は 5 秒間隔で最大 10 回リトライ。10 回失敗で `sys.exit(1)`。

> **Evidence**: `src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcpservd.py:70-87`

### ファイル: /etc/kea/kea-dhcp4.conf（SmartSwitch 固有の差異）

`DpusTableEventChecker` / `MidPlaneTableEventChecker` が変更を検知するたびに `dump_dhcp4_config()` が `/etc/kea/kea-dhcp4.conf` を上書きして kea-dhcp4 に SIGHUP を送信する。SmartSwitch 固有の差異:

- `subnet_id` に [VLAN](../../reference/glossary.md#term-vlan) 番号の代わり固定値 `MID_PLANE_BRIDGE_SUBNET_ID = 10000` を使用
- `bridge-midplane` が `subnet4` の対象ネットワークとして追加される

> **Evidence**: `src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcpservd.py:51-68`; `src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcp_cfggen.py:97-100,251`

### CONFIG_DB: FEATURE テーブル（minigraph 投入時の連鎖書き込み）

`config_samples.py` の `generate_t1_smartswitch_switch_sample_config()` は `DPUS` エントリが存在する場合（`if dhcp_server_ports:`）に限り、`FEATURE` テーブルへ `dhcp_relay` / `dhcp_server` エントリを自動投入する。`DPUS` が空のとき `FEATURE` エントリは投入されず dhcp_server コンテナは起動しない。

```python
data['FEATURE'] = {
    "dhcp_relay": {"state": "enabled", ...},
    "dhcp_server": {"state": "enabled", ...}
}
```

> **Evidence**: `src/sonic-config-engine/config_samples.py:105-131`

### dhcrelay プロセス制御（dhcprelayd 経由）

`dhcprelayd` は SmartSwitch の場合、`MidPlaneTableEventChecker` で `MID_PLANE_BRIDGE` の変更を購読する。`bridge-midplane` が `DHCP_SERVER_IPV4` で `state=enabled` のとき、midplane ブリッジを対象とした `dhcrelay` プロセスを起動・再起動する。

> **Evidence**: `src/sonic-dhcp-utilities/dhcp_utilities/dhcprelayd/dhcprelayd.py:82-113`
<!-- /side-effects -->

<!-- pubsub -->
## 通信メカニズム

> **Evidence**: `src/sonic-dhcp-utilities/dhcp_utilities/common/dhcp_db_monitor.py:9,16-17,69-75,130-136,220-236,349-388`; `src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcpservd.py:25,96,130-148`; `src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcp_cfggen.py:23,97-100`; `src/sonic-dhcp-utilities/dhcp_utilities/dhcprelayd/dhcprelayd.py:28,84-103,156-158,395` (2026-05-17)

### Producer / Consumer ペア

| CONFIG_DB テーブル | Producer | Consumer / 購読方式 | select タイムアウト |
|---|---|---|---|
| `MID_PLANE_BRIDGE\|GLOBAL` | [sonic-cfggen](../../reference/glossary.md#term-sonic-cfggen) / config_samples.py | `dhcpservd` — `MidPlaneTableEventChecker`（`SubscriberStateTable` 内包） | 5000 ms |
| `MID_PLANE_BRIDGE\|GLOBAL` | [sonic-cfggen](../../reference/glossary.md#term-sonic-cfggen) / config_samples.py | `dhcprelayd` — `MidPlaneTableEventChecker`（`SubscriberStateTable` 内包） | 5000 ms |
| `DPUS\|dpu*` | sonic-cfggen / config_samples.py | `dhcpservd` — `DpusTableEventChecker`（`SubscriberStateTable` 内包） | 5000 ms |
| `DHCP_SERVER_IPV4_PORT\|bridge-midplane\|dpu*` | sonic-cfggen / config_samples.py | `dhcpservd` — `DhcpPortTableEventChecker`（`SubscriberStateTable` 内包） | 5000 ms |

### MID_PLANE_BRIDGE / DPUS → dhcpservd

`dhcpservd.py` は起動時に `MidPlaneTableEventChecker` と `DpusTableEventChecker` を `swsscommon.Select` に登録するが (`dhcpservd.py:143-144`)、これらは **SmartSwitch モードのときのみ有効化** される。

有効化フロー:

1. `dhcp_cfggen.generate()` 内で `is_smart_switch(device_metadata)` が `True` を返すと `SMART_SWITCH_CHECKER = ["DpusTableEventChecker", "MidPlaneTableEventChecker"]` が `subscribe_table` に追加される (`dhcp_cfggen.py:23,97-98`)
2. `generate()` の戻り値 `enable_checker` を受け取った `dump_dhcp4_config()` が `dhcp_servd_monitor.enable_checkers(enable_checker)` を呼び出す
3. 各チェッカーの `enable()` メソッドで `SubscriberStateTable` が生成され `sel.addSelectable()` で登録される (`dhcp_db_monitor.py:69-75`)

非 SmartSwitch 環境では `is_smart_switch()` が `False` を返すため、両チェッカーはオブジェクトとして存在するものの `enable()` されず購読が発生しない。

**トリガー条件**:

| チェッカー | トリガー条件 | コード位置 |
|---|---|---|
| `MidPlaneTableEventChecker` | op=`DEL` の場合は常にトリガー。op=`SET` の場合は `bridge` フィールドが `enabled_dhcp_interfaces` に含まれるときのみトリガー | `dhcp_db_monitor.py:362-368` |
| `DpusTableEventChecker` | あらゆるイベント（SET/DEL 問わず）を無条件でトリガー（`_process_check()` が常に `True` を返す） | `dhcp_db_monitor.py:384-385` |

イベント検知後、`DhcpServd.dump_dhcp4_config()` が `/etc/kea/kea-dhcp4.conf` を再生成し kea-dhcp4 に SIGHUP を送信してミッドプレーン DHCP プールが再構成される。

### MID_PLANE_BRIDGE → dhcprelayd

`dhcprelayd.py` も独立して `MidPlaneTableEventChecker` を `sel` に登録する (`dhcprelayd.py:395`)。こちらの有効化は `refresh_dhcrelay()` 内で決定される:

- `DHCP_SERVER_IPV4` テーブルに `bridge-midplane` が `state=enabled` で存在し、かつ `self.smart_switch=True` のとき `MID_PLANE_CHECKER` が `enabled_checkers` に追加される (`dhcprelayd.py:102-103`)
- イベント検知時 (`check_res[MID_PLANE_CHECKER] = True`) は `_proceed_with_check_res()` が `refresh_dhcrelay(force_kill=True)` を呼び出す (`dhcprelayd.py:156-158`)
- `force_kill=True` は既存の dhcrelay プロセスを強制終了して再起動することを意味する

### DHCP_SERVER_IPV4_PORT → dhcpservd

`DhcpPortTableEventChecker` は非 SmartSwitch でも常時有効。`key.split("|")[0]`（dhcp_interface 部分）が `enabled_dhcp_interfaces` に含まれるときのみ再生成トリガーとなる (`dhcp_db_monitor.py:230-236`)。SmartSwitch 環境では `"bridge-midplane"` が `enabled_dhcp_interfaces` に入るため、`DHCP_SERVER_IPV4_PORT|bridge-midplane|dpu*` の全エントリ変更がトリガーになる。

### データフロー図

```
CONFIG_DB[MID_PLANE_BRIDGE|GLOBAL]
  ↓ SubscriberStateTable (MidPlaneTableEventChecker)
dhcpservd [DEFAULT_SELECT_TIMEOUT=5000ms]
  ↓ bridge in enabled_dhcp_interfaces → need_refresh=True
  ↓ dump_dhcp4_config(): /etc/kea/kea-dhcp4.conf 上書き
kea-dhcp4 (SIGHUP) → ミッドプレーン DHCP サブネット再構成

CONFIG_DB[MID_PLANE_BRIDGE|GLOBAL]
  ↓ SubscriberStateTable (MidPlaneTableEventChecker)
dhcprelayd [DEFAULT_SELECT_TIMEOUT=5000ms]
  ↓ check_res[MID_PLANE_CHECKER]=True → refresh_dhcrelay(force_kill=True)
dhcrelay プロセス強制再起動 → ミッドプレーン DHCP リレー経路更新

CONFIG_DB[DPUS|dpu*]
  ↓ SubscriberStateTable (DpusTableEventChecker)
dhcpservd [DEFAULT_SELECT_TIMEOUT=5000ms]
  ↓ 全イベント無条件で need_refresh=True → dump_dhcp4_config()
kea-dhcp4 設定再生成

CONFIG_DB[DHCP_SERVER_IPV4_PORT|bridge-midplane|dpu*]
  ↓ SubscriberStateTable (DhcpPortTableEventChecker)
dhcpservd [DEFAULT_SELECT_TIMEOUT=5000ms]
  ↓ "bridge-midplane" in enabled_dhcp_interfaces → need_refresh=True
  ↓ dump_dhcp4_config() → kea-dhcp4 設定再生成
```

<!-- /pubsub -->

---

<!-- platform -->
## プラットフォーム依存・ハードウェア固有挙動

> **Evidence**: `sonic-chassisd/scripts/chassisd:1571-1583,717-731,1074-1110,1180-1228,236-256`; `sonic_platform_base/chassis_base.py:171-184,317-340` (2026-05-17)

### 1. chassisd のデーモン分岐 — is_smartswitch() / is_dpu()

`chassisd` の `main()` は起動時にプラットフォーム API で SmartSwitch / DPU を判定し、3 種類のデーモンに分岐する。

```python
# chassisd:1576-1581
if chassis.is_smartswitch() and chassis.is_dpu():
    chassisd = DpuChassisdDaemon(SYSLOG_IDENTIFIER, chassis)
else:
    chassisd = ChassisdDaemon(SYSLOG_IDENTIFIER, chassis)
```

| 条件 | デーモンクラス | 役割 |
|---|---|---|
| `is_smartswitch() and is_dpu()` | `DpuChassisdDaemon` | DPU 上で動作。control/data plane 状態を CHASSIS_STATE_DB に更新 |
| `is_smartswitch() and not is_dpu()` | `ChassisdDaemon`（SmartSwitch モード） | NPU 上で動作。`SmartSwitchModuleUpdater` で全 DPU を管理 |
| `not is_smartswitch()` | `ChassisdDaemon`（通常モード） | スーパバイザ / ラインカード構成で動作 |

`chassis_base.py:317-325` のデフォルト実装は `is_smartswitch()` が `False` を返す。SmartSwitch プラットフォームはこのメソッドをオーバーライドして `True` を返す必要がある。

### 2. init_midplane_switch() — MID_PLANE_BRIDGE との分担

CONFIG_DB の `MID_PLANE_BRIDGE|GLOBAL` はブリッジ名と IP プレフィックスを保持するが、
`bridge-midplane` カーネルインターフェースの実際の初期化はプラットフォーム API で行われる。

```python
# chassis_base.py:171-184
def init_midplane_switch(self):
    """
    Initializes the midplane functionality of the modular chassis.
    The expectation is that the required kernel modules, ip-address assignment
    etc are done before the pmon, database dockers are up.
    """
    return NotImplementedError
```

`SmartSwitchModuleUpdater.__init__()` はこのメソッドの戻り値を `self.midplane_initialized` に保存する。`False` の場合は `LOG_ERR` を出力し、`check_midplane_reachability()` が全面スキップされる（`chassisd:1074-1076`）。CONFIG_DB は参照しない。

### 3. DPU 再起動タイムアウト — platform.json による上書き

`SmartSwitchModuleUpdater` は DPU 再起動タイムアウトのデフォルト値（`DEFAULT_DPU_REBOOT_TIMEOUT = 360` 秒）を `/usr/share/sonic/platform/platform.json` で上書きできる。

```python
# chassisd:721-730
self.dpu_reboot_timeout = DEFAULT_DPU_REBOOT_TIMEOUT
if os.path.isfile(PLATFORM_JSON_FILE):
    with open(PLATFORM_JSON_FILE, 'r') as f:
        platform_cfg = json.load(f)
    self.dpu_reboot_timeout = int(platform_cfg.get("dpu_reboot_timeout",
                                                    DEFAULT_DPU_REBOOT_TIMEOUT))
```

| 定数 | 値 | 意味 |
|---|---|---|
| `DEFAULT_DPU_REBOOT_TIMEOUT` | `360` 秒 | プラットフォーム設定がない場合のデフォルト |
| `MAX_DPU_REBOOT_DURATION` | `800` 秒 | 再起動判定の有効期間上限 |
| `PLATFORM_JSON_FILE` | `/usr/share/sonic/platform/platform.json` | プラットフォーム固有設定ファイル |

YANG / CONFIG_DB フィールドではなく、ファイルシステム上のプラットフォーム構成ファイルによる制御。

### 4. midplane 到達性チェックと STATE_DB 書き込み

`check_midplane_reachability()` が `CHASSIS_INFO_UPDATE_PERIOD_SECS = 10` 秒周期で呼ばれ、
プラットフォーム API からの結果を STATE_DB / CHASSIS_STATE_DB に反映する。

| プラットフォーム API | 役割 |
|---|---|
| `module.get_midplane_ip()` | DPU の midplane IP アドレスを返す |
| `module.is_midplane_reachable()` | midplane 到達可能性を返す（ping / [ARP](../../reference/glossary.md#term-arp) 等） |

書き込み先:

| DB | テーブル | フィールド | 内容 |
|---|---|---|---|
| STATE_DB | `CHASSIS_MIDPLANE_TABLE\|<DPU名>` | `ip_address` | `get_midplane_ip()` の戻り値 |
| STATE_DB | `CHASSIS_MIDPLANE_TABLE\|<DPU名>` | `access` | `str(is_midplane_reachable())` |
| CHASSIS_STATE_DB | `DPU_STATE\|<DPU名>` | `dpu_midplane_link_state` | `"up"` / `"down"` |
| CHASSIS_STATE_DB | `DPU_STATE\|<DPU名>` | `dpu_midplane_link_time` | 状態変化時刻 |

到達性が `True→False` に変化した場合、`update_dpu_state()` は `dpu_midplane_link_state` を `"down"` にするとともに `dpu_control_plane_state` / `dpu_data_plane_state` も `"down"` に設定する（`chassisd:880-885`）。

### 5. CHASSIS_MODULE テーブルと DPU 名前制約

CONFIG_DB の `CHASSIS_MODULE` テーブルを `SmartSwitchConfigManagerTask` が `SubscriberStateTable` で購読し、DPU の管理状態（`admin_status`）変更を `set_admin_state_gracefully()` に反映する。

SmartSwitch 環境では `CHASSIS_MODULE` のキーは `"DPU"` プレフィックスで始まる必要がある。それ以外のキーを受信すると `LOG_ERR` を出力してスキップする（`chassisd:236-239`）。`MODULE_TYPE_DPU = "DPU"` は `module_base.py:37` で定義。

### CONFIG_DB を経由しない主なプラットフォーム動作

| 動作 | 依存先 | 説明 |
|---|---|---|
| ミッドプレーン初期化 | `chassis.init_midplane_switch()` | `bridge-midplane` カーネル IF 作成。CONFIG_DB 非経由 |
| DPU midplane IP 取得 | `module.get_midplane_ip()` | プラットフォーム実装。CONFIG_DB 非経由 |
| midplane 到達性確認 | `module.is_midplane_reachable()` | プラットフォーム実装（ping / [ARP](../../reference/glossary.md#term-arp) 等） |
| DPU 再起動タイムアウト | `/usr/share/sonic/platform/platform.json` | `dpu_reboot_timeout` キー（YANG 非経由） |
| DPU 再起動原因の永続化 | `/host/reboot-cause/module/<dpu>/` | ファイルシステム直接書き込み |
| SmartSwitch / DPU 判定 | `chassis.is_smartswitch()` / `chassis.is_dpu()` | プラットフォームオーバーライド必須 |

<!-- /platform -->

---

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `DHCP_SERVER_IPV4`、`DPUS`、`DPU`、`DEVICE_METADATA`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-smart-switch`、`sonic-dhcp-server-ipv4`
- 関連 CLI: SmartSwitch 設定は主に `config_samples.py` / minigraph 経由で自動投入（手動 CLI は限定的）

## 参照

- [SmartSwitch IP アドレス割り当て設計](../../system/smart-switch-ip-address-assignment.md)
- [SmartSwitch データベース設計](../../architecture/smart-switch-database-design.md)

<!-- glossary-links-injected: cb19324c27cb -->
