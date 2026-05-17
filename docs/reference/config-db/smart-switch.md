---
title: SmartSwitch 関連テーブル (MID_PLANE_BRIDGE / DHCP_SERVER_IPV4_PORT)
description: "SmartSwitch NPU-DPU 間ミッドプレーンブリッジおよびポートベース DHCP 割り当てを管理する CONFIG_DB テーブル群。MID_PLANE_BRIDGE、DHCP_SERVER_IPV4_PORT の構造・デフォルト・ハードコード挙動を詳述。"
area: reference
hard: 0
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

SmartSwitch は SONiC NPU と複数の DPU (Data Processing Unit) を搭載した複合スイッチ筐体。
NPU-DPU 間はミッドプレーンブリッジ (`bridge-midplane`) を介して L2 接続され、DPU への IPv4 割り当ては
DHCP サーバ (`dhcp_server` feature) が `DHCP_SERVER_IPV4_PORT` テーブルを参照してポートごとに固定 IP を払い出す。

SmartSwitch 機能が有効化されるかどうかは `DEVICE_METADATA|localhost.subtype == "SmartSwitch"` で判定される。

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
| `bridge` | string (`"bridge-midplane"` のみ) | - | ミッドプレーンブリッジ名。YANG の `pattern` 制約で `"bridge-midplane"` 固定 |
| `ip_prefix` | IPv4 prefix | - | ブリッジの IP プレフィックス。`bridge` が存在する場合は YANG `must` 制約で必須 |

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

- `<dhcp_interface>`: `DHCP_SERVER_IPV4` のキー（SmartSwitch の場合 `"bridge-midplane"`）
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
## 書込み順依存 (Phase B)

`dhcpservd` の `generate()` と `dhcprelayd` の `refresh_dhcrelay()` はイベントごとに CONFIG_DB を全量スナップショットし Kea / dhcrelay 設定を再生成する。このため書き込み順序が初回起動時の設定完全性に影響する。

### 検出された順序依存

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `DEVICE_METADATA\|localhost.subtype = "SmartSwitch"` → `MID_PLANE_BRIDGE` / `DHCP_SERVER_IPV4_PORT` 処理 | 先行必須（欠如時 SmartSwitch 経路が完全スキップ） | `MidPlaneTableEventChecker` 変更で `dhcpservd` が再生成トリガー |
| 2 | `MID_PLANE_BRIDGE\|GLOBAL.bridge` と `ip_prefix` の同時書き込み | 必須（片方欠如で SmartSwitch サブネット生成がスキップ） | YANG `must` 制約が CLI 経由の不整合書き込みを拒否 |
| 3 | `DPUS\|<dpu_name>` → `DHCP_SERVER_IPV4_PORT\|bridge-midplane\|<dpu>` | 先行必須（YANG leafref 制約） | CLI / sonic-cfggen は YANG バリデーションで reject |
| 4 | `MID_PLANE_BRIDGE\|GLOBAL` + `DHCP_SERVER_IPV4\|bridge-midplane` → `dhcprelayd` midplane 認識 | 同時または先行推奨 | `MidPlaneTableEventChecker` で変更後に自動再評価 |
| 5 | 全 SmartSwitch テーブル → `FEATURE\|dhcp_server.state=enabled` | 推奨先行（初回起動時の設定欠落回避） | 後から Feature 有効化しても `MidPlaneTableEventChecker` で自動再生成 |

### 主要な制約詳細

**DEVICE_METADATA.subtype 先行必須 (依存 #1)**: `dhcp_cfggen.py:65-76` の `generate()` は最初に `DEVICE_METADATA` を読み `is_smart_switch()` を評価する。`subtype != "SmartSwitch"` の場合 `_parse_dpu()` は呼ばれず `MID_PLANE_BRIDGE` / `DHCP_SERVER_IPV4_PORT` / `DPUS` が存在していても SmartSwitch 用 Kea 設定が生成されない。`config_samples.py:83` でも `subtype` 設定を `MID_PLANE_BRIDGE` より先に行う（evidence: `dhcp_cfggen.py:65-76`; `utils.py:153-161`）。

**bridge + ip_prefix の同時書き込み必須 (依存 #2)**: `dhcp_cfggen.py:84` の条件 `"bridge" in mid_plane and "ip_prefix" in mid_plane` を両方満たすとき初めて SmartSwitch サブネットが Kea 設定に追加される。YANG `must "(current()/../ip_prefix)"` 制約も `bridge` と `ip_prefix` の同時存在を強制する（evidence: `dhcp_cfggen.py:84`, `sonic-smart-switch.yang:63-74`）。

**DPUS 先行必須 (依存 #3)**: `DHCP_SERVER_IPV4_PORT.<port>` フィールドは `DPUS.<dpu_name>.midplane_interface` への YANG leafref であるため、`DPUS` エントリが存在しない状態で `DHCP_SERVER_IPV4_PORT` を書いても YANG バリデーションで reject される（evidence: `sonic-smart-switch.yang:94-103`）。

詳細スキャン手順と依存関係の根拠は `meta/_intermediate/cdb-flow/smart-switch-ordering.md` を参照。
<!-- /ordering -->

---

<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

`MID_PLANE_BRIDGE` および `DHCP_SERVER_IPV4_PORT` は CONFIG_DB の複数テーブルを YANG leafref
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

詳細は `meta/_intermediate/cdb-flow/smart-switch-cross-refs.md` を参照。
<!-- /cross-refs -->

---

<!-- defaults -->
## 暗黙デフォルトとハードコード挙動

<!-- evidence: meta/_intermediate/cdb-flow/smart-switch-defaults.md -->

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
## 無効入力・障害時の挙動 (Phase E)

<!-- evidence: meta/_intermediate/cdb-flow/smart-switch-failure.md -->

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
STATE_DB の `DHCP_SERVER_IPV4_SERVER_IP|eth0.ip` を 10 回（合計 100 秒）リトライして
取得できない場合、`LOG_ERR` を出力して `sys.exit(1)` する。コンテナが再起動する。

### 5. dhcp_lease — lease ファイル不在

**lease ファイル不在** (`dhcp_lease.py:116-121`):  
Kea の lease ファイル（デフォルト `/var/lib/kea/kea-lease.csv`）が存在しない場合、
`LOG_ERR` を出力して例外を再送出する。STATE_DB の `DHCP_SERVER_IPV4_LEASE` テーブルは更新されない。

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

---

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `DHCP_SERVER_IPV4`、`DPUS`、`DPU`、`DEVICE_METADATA`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-smart-switch`、`sonic-dhcp-server-ipv4`
- 関連 CLI: SmartSwitch 設定は主に `config_samples.py` / minigraph 経由で自動投入（手動 CLI は限定的）

## 参照

- [SmartSwitch IP アドレス割り当て設計](../../system/smart-switch-ip-address-assignment.md)
- [SmartSwitch データベース設計](../../architecture/smart-switch-database-design.md)
