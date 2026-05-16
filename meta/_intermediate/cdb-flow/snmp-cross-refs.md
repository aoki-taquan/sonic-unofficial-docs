# SNMP — Phase C: 暗黙参照テーブル分析 (cross-refs)

対象ドキュメント: `docs/reference/config-db/snmp.md`
解析日: 2026-05-15
根拠ソース:
- `sonic-buildimage/dockers/docker-snmp/snmpd.conf.j2`
- `sonic-buildimage/dockers/docker-snmp/supervisord.conf.j2`
- `sonic-buildimage/dockers/docker-snmp/snmp_yml_to_configdb.py`
- `sonic-buildimage/dockers/docker-snmp/start.sh`

---

## 目的

`SNMP` テーブルエントリが CONFIG_DB に存在するとき、`snmpd.conf.j2` テンプレートおよび
`docker-snmp` 起動スクリプトが **暗黙的に** 参照・依存する他テーブルを網羅する。
YANG leafref に明示されない「実装上の暗黙前提」を列挙し、`<!-- cross-refs -->` ブロックに変換する。

---

## 1. SNMP_COMMUNITY — snmpd コミュニティ設定の実質的な前提

### 参照箇所

`snmpd.conf.j2` L48–64:

```jinja2
{% if SNMP_COMMUNITY is defined %}
{% for community in SNMP_COMMUNITY %}
{% if SNMP_COMMUNITY[community]['TYPE'] == 'RO' %}
rocommunity {{ community }}
rocommunity6 {{ community }}
{% endif %}
{% endfor %}
{% endif %}
```

### 依存内容

| `SNMP_COMMUNITY` の状態 | 影響 |
|---|---|
| 定義済み (`TYPE=RO/RW`) | snmpd.conf に `rocommunity` / `rwcommunity` 行を生成。SNMP アクセス可能 |
| 未定義 | コミュニティ行なし → 全 SNMP v1/v2c アクセスが拒否される |

**YANG leafref**: なし。テンプレート上の条件分岐のみ。

---

## 2. SNMP_USER — SNMPv3 ユーザ設定

### 参照箇所

`snmpd.conf.j2` L66–77:

```jinja2
{% if SNMP_USER is defined %}
{% for user in SNMP_USER %}
{% if SNMP_USER[user]['SNMP_USER_PERMISSION'] == 'RO' %}
rouser {{ user }} {{ SNMP_USER[user]['SNMP_USER_TYPE'] }}
CreateUser {{ user }} {{ SNMP_USER[user]['SNMP_USER_AUTH_TYPE'] }} ...
```

### 依存内容

| `SNMP_USER` の状態 | 影響 |
|---|---|
| 定義済み (v3 ユーザ) | `rouser` / `rwuser` + `CreateUser` 行を生成。SNMPv3 アクセス可能 |
| 未定義 | SNMPv3 ユーザ設定なし → SNMPv3 での SNMP アクセス不可 |

**YANG leafref**: なし。

---

## 3. SNMP_AGENT_ADDRESS_CONFIG — agentAddress バインド先

### 参照箇所

`snmpd.conf.j2` L27–34:

```jinja2
{% if SNMP_AGENT_ADDRESS_CONFIG %}
{% for (agentip, port, vrf) in SNMP_AGENT_ADDRESS_CONFIG %}
agentAddress {{ protocol(agentip) }}:[{{ agentip }}]{% if vrf %}@{{ vrf }}{% endif %}{% if port %}:{{ port }}{% endif %}
{% endfor %}
{% else %}
agentAddress udp:161
agentAddress udp6:161
{% endif %}
```

### 依存内容

| `SNMP_AGENT_ADDRESS_CONFIG` の状態 | 影響 |
|---|---|
| 定義済み | 指定 IP/ポート/VRF にのみ snmpd をバインド。不要なインターフェース公開を回避 |
| 未定義 | フォールバック: `agentAddress udp:161` / `agentAddress udp6:161` (全インターフェース公開) |

**YANG leafref**: なし。テンプレート条件分岐のみ。

---

## 4. SNMP_TRAP_CONFIG — SNMP トラップ送信先

### 参照箇所

`snmpd.conf.j2` L145–173 (v1/v2/v3 トラップ設定):

```jinja2
{% if SNMP_TRAP_CONFIG and SNMP_TRAP_CONFIG['v1TrapDest'] %}
trapsink {{ v1SnmpTrapIp }}:{{ v1SnmpTrapPort }} ...
{% if SNMP_TRAP_CONFIG and SNMP_TRAP_CONFIG['v2TrapDest'] %}
trap2sink {{ v2SnmpTrapIp }}:{{ v2SnmpTrapPort }} ...
{% if SNMP_TRAP_CONFIG and SNMP_TRAP_CONFIG['v3TrapDest'] %}
trapsink {{ v3SnmpTrapIp }}:{{ v3SnmpTrapPort }} ...
```

### 依存内容

| `SNMP_TRAP_CONFIG` の状態 | 影響 |
|---|---|
| v1/v2/v3TrapDest 設定済み | `trapsink` / `trap2sink` 行を生成してトラップ送信 |
| 未定義 | トラップ設定行をコメントアウト扱い → snmpd はトラップを送出しない |

**YANG leafref**: なし。`SNMP_TRAP_CONFIG` は YANG `sonic-snmp.yang` の外部テーブル
(`config/main.py:4229-4254` が直接書き込む)。

---

## 5. DEVICE_METADATA|localhost (switch_type) — snmp-subagent 起動コマンド分岐

### 参照箇所

`supervisord.conf.j2` L53–57:

```jinja2
{% if DEVICE_METADATA['localhost']['switch_type'] == 'chassis-packet' %}
command=/usr/bin/env python3 -m sonic_ax_impl --enable_dynamic_frequency
{% else %}
command=/usr/bin/env python3 -m sonic_ax_impl
{% endif %}
```

### 依存内容

| `switch_type` の値 | 影響 |
|---|---|
| `chassis-packet` | `--enable_dynamic_frequency` フラグで snmp-subagent 起動 |
| その他 (default) | 通常モードで `sonic_ax_impl` 起動 |

**必須度**: `DEVICE_METADATA.localhost` が存在しない場合 supervisord.conf.j2 テンプレート展開がエラー。
docker-snmp コンテナ起動自体が失敗する。

---

## 6. /etc/sonic/snmp.yml — 起動時 SNMP_COMMUNITY / SNMP|LOCATION 注入元 (ファイル参照)

### 参照箇所

`snmp_yml_to_configdb.py` L29–56: 起動スクリプト `start.sh` が snmpd 設定テンプレ展開前に
`snmp_yml_to_configdb.py` を実行し、snmp.yml の値を CONFIG_DB に書き込む。

- `SNMP_COMMUNITY` テーブルへのエントリ注入
- `SNMP|LOCATION` への `Location` フィールド注入

注: `snmp_location` が snmp.yml に存在しない場合 `sys.exit(1)` でスクリプト終了し
LOCATION は未設定のまま → `sysLocation public` ハードコードフォールバック。

**DB テーブル**: CONFIG_DB 直接読み書き。`SNMP_COMMUNITY` / `SNMP` テーブルが間接的にファイルから初期化される。

---

## 7. SAI 参照

なし。`docker-snmp` / snmpd は純粋にユーザー空間の SNMP デーモンで SAI/ASIC に一切触れない。
APPL_DB 中継もない。snmp-subagent (`sonic_ax_impl`) は COUNTERS_DB / APPL_DB を読み取るが、
SNMP テーブル自体は SAI に書き込まない。

---

## cross-refs ブロック (docs/reference/config-db/snmp.md 向け)

```markdown
<!-- cross-refs -->
## 暗黙参照 — Phase C (cross-table refs)

> **調査根拠**: `snmpd.conf.j2`, `supervisord.conf.j2`, `snmp_yml_to_configdb.py`, `start.sh` 全行精読 (2026-05-15)  
> 詳細証跡: `meta/_intermediate/cdb-flow/snmp-cross-refs.md`

`SNMP` テーブルは YANG leafref を持たないが、`docker-snmp` コンテナ起動時テンプレートと hostcfgd が以下のテーブルを暗黙参照する。

| 参照先 | DB | 参照方向 | YANG leafref | 実装上の必須度 | 証拠 |
|---|---|---|---|---|---|
| `SNMP_COMMUNITY\|<name>` | CONFIG_DB | 読み取り (v1/v2c コミュニティ設定) | なし | 実質必須 (未定義で全 SNMP v1/v2c 拒否) | `snmpd.conf.j2` L48–64 |
| `SNMP_USER\|<name>` | CONFIG_DB | 読み取り (v3 ユーザ設定) | なし | v3 利用時必須 | `snmpd.conf.j2` L66–77 |
| `SNMP_AGENT_ADDRESS_CONFIG\|<ip>\|<port>\|<vrf>` | CONFIG_DB | 読み取り (agentAddress バインド先) | なし | 任意 (未定義で全 IF 公開にフォールバック) | `snmpd.conf.j2` L27–34 |
| `SNMP_TRAP_CONFIG\|<version>TrapDest` | CONFIG_DB | 読み取り (トラップ送信先) | なし | 任意 (未定義でトラップ無効) | `snmpd.conf.j2` L145–173 |
| `DEVICE_METADATA\|localhost` (`switch_type`) | CONFIG_DB | 読み取り (snmp-subagent 起動コマンド分岐) | なし | 必須 (未定義でコンテナ起動失敗) | `supervisord.conf.j2` L53–57 |

### SNMP_COMMUNITY — コミュニティ文字列の前提

snmpd.conf.j2 は `{% if SNMP_COMMUNITY is defined %}` で SNMP_COMMUNITY の有無を確認し、存在する場合のみ `rocommunity` / `rwcommunity` 行を出力する (`snmpd.conf.j2` L48–64)。**SNMP_COMMUNITY が未定義の場合、SNMPv1/v2c での全アクセスが拒否される**。`snmp_yml_to_configdb.py` が起動時に `/etc/sonic/snmp.yml` からエントリを注入するが、snmp.yml が存在しない場合は注入されない。

### SNMP_USER — SNMPv3 ユーザ設定

v3 アクセスが必要な場合は `SNMP_USER` テーブルにユーザを登録する必要がある。テンプレートが `rouser` / `rwuser` + `CreateUser` 行を生成する (`snmpd.conf.j2` L66–77)。YANG leafref なし。

### SNMP_AGENT_ADDRESS_CONFIG — バインドアドレス前提

未定義の場合は `agentAddress udp:161` / `agentAddress udp6:161` (全インターフェース) にフォールバックする。セキュリティ要件がある場合は `SNMP_AGENT_ADDRESS_CONFIG` で明示的に制限すること。

### SNMP_TRAP_CONFIG — トラップ送信先

v1/v2/v3 トラップ送信先を定義するテーブル。未定義の場合はトラップ設定行が出力されず snmpd はトラップを送出しない。このテーブルは YANG `sonic-snmp.yang` の外部に存在し、`config snmp trap` CLI (`config/main.py:4229-4254`) が直接書き込む。

### DEVICE_METADATA.localhost.switch_type — snmp-subagent 起動モード

`supervisord.conf.j2` L53–57 でテンプレート展開される。`switch_type == 'chassis-packet'` の場合は `--enable_dynamic_frequency` フラグ付きで `sonic_ax_impl` を起動する。`DEVICE_METADATA.localhost` が CONFIG_DB に存在しない場合、テンプレート展開が KeyError で失敗し docker-snmp コンテナが起動しない。

### SAI 参照

なし。snmpd は純粋なユーザー空間デーモンで SAI/ASIC に一切触れない。APPL_DB 中継もない。

<!-- /cross-refs -->
```
