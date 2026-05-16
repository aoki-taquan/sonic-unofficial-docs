# SNMP_AGENT_ADDRESS_CONFIG — コード由来デフォルト調査 (Phase A)

## スコープ

`docs/reference/config-db/snmp-agent-address-config.md` に対する Task F Phase A（コード由来デフォルト）の根拠まとめ。

## 対象ソース

- `sonic-buildimage/dockers/docker-snmp/snmpd.conf.j2` (master) — `agentAddress` 行を生成する Jinja2 テンプレート
- `sonic-utilities/config/main.py` (`@snmpagentaddress.command('add')` 周辺、L4137–4190) — CLI 入り口
- `sonic-host-services/scripts/hostcfgd` — `SNMP_AGENT_ADDRESS_CONFIG` を購読する Handler は **存在しない**（grep で 0 hit）。snmpd.conf の生成はテンプレ直接レンダリングで行われ、hostcfgd 経由ではない。

## 検出したコード由来デフォルト

### 1. `port` 既定 = 161（テンプレ + CLI 両側）

`snmpd.conf.j2` L28–29:

```jinja
{% for (agentip, port, vrf) in SNMP_AGENT_ADDRESS_CONFIG %}
agentAddress {{ protocol(agentip) }}:[{{ agentip }}]{% if vrf %}@{{ vrf }}{% endif %}{% if port %}:{{ port }}{% endif %}
{% endfor %}
```

- `port` フィールドが空文字または未指定の場合、`{% if port %}:{{ port }}{% endif %}` で `:<port>` 部分そのものが省略される。
- net-snmp 側の仕様で port 指定なしの `agentAddress udp:<ip>` は **161/udp** にバインドする。
- すなわち CONFIG_DB に `port=""` を書いても、生成される snmpd 設定は実質 161 で listen する。
- YANG (`sonic-snmp.yang`) は `pattern ''` で空文字を許容しているのみで `default` 宣言は持たない。**161 という値はコード（net-snmp 既定）由来**。

### 2. エントリ 0 件時の fallback = `udp:161` + `udp6:161`（テンプレ）

`snmpd.conf.j2` L27–34:

```jinja
{% if SNMP_AGENT_ADDRESS_CONFIG %}
{% for ... %} ... {% endfor %}
{% else %}
agentAddress udp:161
agentAddress udp6:161
{% endif %}
```

- テーブルにエントリが 1 件もない場合、IPv4 (`udp:161`) と IPv6 (`udp6:161`) の両方で 161/udp listen が **コードによりハードコード** で出力される。
- YANG 側にはこの fallback の宣言なし。完全にテンプレ由来。

### 3. `vrf` 既定 = default VRF（テンプレ）

`snmpd.conf.j2` L29 の `{% if vrf %}@{{ vrf }}{% endif %}`:

- `vrf` が空文字なら `@<vrf>` サフィックスが省略され、net-snmp はカーネルの default routing namespace（= default VRF）でリッスンする。
- YANG は `pattern ''` で空文字を許容、`default` 宣言なし。**「空文字 = default VRF」というセマンティクスはコード由来**。
- ただし CLI 側 (`config/main.py:4153–4157`) は `MGMT_VRF_CONFIG.mgmtVrfEnabled=true` の状態で `-v` 省略を **CLI レイヤで拒否** する（DB 書き込み前ブロック）。つまり「vrf 空＝default」が成立するのは Management VRF 無効時のみ。

### 4. プロトコル（`udp` / `udp6`）の自動選択 = `protocol()` macro

`snmpd.conf.j2` L19–25:

```jinja
{% macro protocol(ip_addr) %}
{%- if ip_addr.split('%')[0]|ipv6 -%}
{{ 'udp6' }}
{%- else -%}
{{ 'udp' }}
{%- endif -%}
{% endmacro %}
```

- CONFIG_DB に `agent_ip` を入れただけで、IPv6 リテラルなら `udp6:`、それ以外なら `udp:` が自動付与される。
- ユーザは IPv4/IPv6 のプロトコル選択を明示する必要がない。**完全にコード由来の派生フィールド**。
- `agent_ip` に `%<zone_id>` (link-local の scope id) が付いていても `split('%')[0]` で除去してから判定する。

### 5. CLI 側の補助デフォルト

`sonic-utilities/config/main.py:4139–4140`:

```python
@click.option('-p', '--port', help="SNMP AGENT LISTENING PORT")
@click.option('-v', '--vrf', help="VRF Name mgmt/DataVrfName/None")
```

- `-p` / `-v` のいずれも click `default=` 宣言なし。省略時は CONFIG_DB key に空文字部分 (`<ip>||` 等) が入る。これがテンプレ側で「port/vrf 空文字 → 161/default」に展開される（上記 1, 3）。

## まとめ表

| デフォルト | 値 | 由来 | YANG `default` | 注記 |
|---|---|---|---|---|
| `port` 空 → 実効ポート | 161 | テンプレ + net-snmp 既定 | なし | snmpd.conf 行から `:<port>` が省略される |
| エントリ 0 件 → fallback | `udp:161` + `udp6:161` | テンプレ (`{% else %}` 分岐) | なし | 完全ハードコード |
| `vrf` 空 → 実効 VRF | default VRF | テンプレ + net-snmp 既定 | なし | mgmtVrfEnabled=true 時は CLI が拒否 |
| プロトコル選択 | `udp` / `udp6` 自動 | テンプレ macro `protocol()` | なし | `agent_ip` の IPv6 判定で派生 |

## 検証

- `grep -n SNMP_AGENT_ADDRESS hostcfgd` → 0 hit。hostcfgd を経由しない。
- `snmpd.conf.j2` L27–34 がデフォルト fallback の単一の真実源 (single source of truth)。
- CLI (`config/main.py:4142–4190`) は click default 宣言を持たず、空文字を CONFIG_DB に格納してテンプレに委ねる設計。

## 結論

`SNMP_AGENT_ADDRESS_CONFIG` のコード由来デフォルトは **すべて `snmpd.conf.j2` テンプレートに集約** されている。hostcfgd / db_migrator / sonic-cfggen のいずれも `SNMP_AGENT_ADDRESS_CONFIG` テーブルにデフォルト値を注入しない。YANG `default` 宣言も存在せず、空文字許容 (`pattern ''`) のみで実値はテンプレが補う構造。
