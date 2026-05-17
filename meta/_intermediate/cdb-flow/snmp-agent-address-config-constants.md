# SNMP_AGENT_ADDRESS_CONFIG — ハードコード定数調査 (Phase E)

**調査日**: 2026-05-17  
**調査対象**:
- `sonic-buildimage/dockers/docker-snmp/snmpd.conf.j2`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-snmp.yang`
- `sonic-buildimage/src/sonic-config-engine/minigraph.py`
- `sonic-utilities/config/main.py`

---

## 1. agentAddress フォールバック定数

`snmpd.conf.j2` L32-33:

```jinja2
{% else %}
agentAddress udp:161
agentAddress udp6:161
{% endif %}
```

`SNMP_AGENT_ADDRESS_CONFIG` テーブルにエントリが 1 件もない場合に使われるハードコード値。  
**CONFIG_DB で管理されない** — テンプレート固有の固定値。

| 定数 | 値 | ソース |
|------|----|--------|
| フォールバック agentAddress (IPv4) | `udp:161` | `snmpd.conf.j2` L32 |
| フォールバック agentAddress (IPv6) | `udp6:161` | `snmpd.conf.j2` L33 |

---

## 2. minigraph 経由のポートハードコード

`minigraph.py` L2314:

```python
port = '161'
snmp_key = agent_addr + '|' + port + '|'
results['SNMP_AGENT_ADDRESS_CONFIG'][snmp_key] = {}
```

minigraph.xml からの自動生成時は port を常に `'161'` でハードコードして key を構築する。  
YANG `default` ステートメントなし — minigraph コード固有のハードコード。

| 定数 | 値 | ソース |
|------|----|--------|
| minigraph 生成ポート | `'161'` | `minigraph.py:2314` |
| minigraph 生成 vrf_name | `''` (空文字 = default VRF) | `minigraph.py:2321` (key の最後の `|` 後に空文字) |

---

## 3. YANG key 要素の空文字許容パターン

`sonic-snmp.yang` L181, L190:

```yang
leaf port {
  type union {
    type string { pattern ''; }   // 空文字許容
    type inet:port-number;         // 0-65535
  }
}
leaf vrf_name {
  type union {
    type string { pattern ''; }   // 空文字許容 (default VRF)
    type string { pattern 'mgmt'; }
    type string { pattern "Vrf[a-zA-Z0-9_-]+"; }
  }
}
```

これらは YANG の `default` ではなく **union 型の空文字パターン** でオプション扱いを実現している。CLI が `-p` / `-v` を省略した場合、空文字が key に入る。

---

## 4. CLI デフォルト — 省略時の暗黙値

`sonic-utilities/config/main.py` L4137-4186 (`add_snmp_agent_address` 関数):

| オプション | CLI 省略時の値 | key/フィールドへの影響 |
|-----------|---------------|----------------------|
| `-p / --port` | `''` (空文字) | `snmpd.conf.j2` で `{% if port %}:{{ port }}{% endif %}` が false → ポートサフィックス省略 → snmpd デフォルト 161 を使用 |
| `-v / --vrf` | `''` (空文字) | `snmpd.conf.j2` で `{% if vrf %}@{{ vrf }}{% endif %}` が false → VRF サフィックス省略 → default VRF |

---

## 5. テンプレートマクロ定数

`snmpd.conf.j2` L19-25:

```jinja2
{% macro protocol(ip_addr) %}
{%- if ip_addr.split('%')[0]|ipv6 -%}
{{ 'udp6' }}
{%- else -%}
{{ 'udp' }}
{%- endif -%}
{% endmacro %}
```

agentAddress のプロトコル種別は IP アドレスの種別で自動判定される。IPv6 → `udp6`、IPv4 → `udp`。CONFIG_DB フィールドではなくテンプレート内のロジック。

---

## 結論

`SNMP_AGENT_ADDRESS_CONFIG` に関連するハードコード定数は主に 3 箇所:
1. **テーブル未設定時のフォールバック** (`snmpd.conf.j2`: `udp:161` / `udp6:161`)
2. **minigraph 自動生成時のポート** (`minigraph.py`: `'161'`)
3. **CLI 省略時の暗黙空文字** (YANG の union 空文字パターンと連携)

いずれも CONFIG_DB の YANG `default` ステートメントではなく、テンプレートまたはコードに埋め込まれた値である。
