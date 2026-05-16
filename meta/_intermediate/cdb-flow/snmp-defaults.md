# SNMP テーブル Phase A — コード由来暗黙デフォルト調査メモ

調査日: 2026-05-14
対象: `docs/reference/config-db/snmp.md` (`SNMP|CONTACT` / `SNMP|LOCATION`)

## 調査対象ファイル

| ファイル | 役割 |
|---------|------|
| `sonic-buildimage/dockers/docker-snmp/snmpd.conf.j2` | Jinja2 テンプレ (consumer) |
| `sonic-buildimage/dockers/docker-snmp/snmp_yml_to_configdb.py` | snmp.yml → CONFIG_DB 注入スクリプト |
| `sonic-utilities/config/main.py` (L4471–4573) | CLI 書き込み経路 |
| `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-snmp.yang` | YANG 定義 |

---

## 発見事項

### D-1: `sysLocation` ハードコードデフォルト = `"public"`

**証拠**: `snmpd.conf.j2` L88–92
```jinja
{% if SNMP is defined and SNMP.LOCATION is defined %}
sysLocation    {{ SNMP.LOCATION.Location | replace('\n', ' ') }}
{% else %}
sysLocation    public
{% endif %}
```

- `SNMP.LOCATION` が CONFIG_DB に存在しない場合、snmpd は `sysLocation = "public"` を使用する
- YANG に `default` ステートメントなし → 完全にハードコード (テンプレート依存)
- 文字列 `"public"` は community 名と同一で紛らわしいが別物

---

### D-2: `sysContact` ハードコードデフォルト = `"Azure Cloud Switch vteam <linuxnetdev@microsoft.com>"`

**証拠**: `snmpd.conf.j2` L93–97
```jinja
{% if SNMP is defined and SNMP.CONTACT is defined %}
sysContact     {{ SNMP.CONTACT.keys() | first | replace('\n', ' ') }} {{ SNMP.CONTACT.values() | first | replace('\n', ' ') }}
{% else %}
sysContact     Azure Cloud Switch vteam <linuxnetdev@microsoft.com>
{% endif %}
```

- `SNMP.CONTACT` が CONFIG_DB に存在しない場合、Microsoft/Azure 固有の連絡先がデフォルト
- YANG に `default` ステートメントなし → ハードコード (テンプレート依存)

---

### D-3: YANG-実装 discrepancy — `SNMP|CONTACT` のフィールド構造

**YANG 定義** (`sonic-snmp.yang`):
```yang
container CONTACT {
  leaf Contact {  # 単一の string leaf
    type string { length "1..255"; pattern '[^\n]+'; }
  }
}
```

**CLI 実装** (`config/main.py` L4483):
```python
db.cfgdb.set_entry('SNMP', 'CONTACT', {contact: contact_email})
# → {<任意の連絡先名>: <email>} という dict で保存
```

**テンプレート参照** (`snmpd.conf.j2` L94):
```jinja
{{ SNMP.CONTACT.keys() | first }} {{ SNMP.CONTACT.values() | first }}
```

- YANG は `Contact` という単一 leaf を定義するが、CLI は `{contact_name: contact_email}` という dict を書き込む
- テンプレートも `.keys()` `.values()` で任意の key を取得しており YANG 定義と乖離
- `Contact` フィールド名は事実上機能しておらず、連絡先名が key、email が value になる独自構造
- コメントも `# TODO: ERROR IN YANG MODEL. Contact name is not defined as key` と明記 (main.py L4483)

---

### D-4: `SNMP_AGENT_ADDRESS_CONFIG` 未定義時のエージェントアドレスフォールバック

**証拠**: `snmpd.conf.j2` L27–34
```jinja
{% if SNMP_AGENT_ADDRESS_CONFIG %}
{% for (agentip, port, vrf) in SNMP_AGENT_ADDRESS_CONFIG %}
agentAddress {{ protocol(agentip) }}:[{{ agentip }}]...
{% endfor %}
{% else %}
agentAddress udp:161
agentAddress udp6:161
{% endif %}
```

- `SNMP_AGENT_ADDRESS_CONFIG` が空の場合、全 IPv4/IPv6 インターフェースの UDP:161 でリッスン (デフォルト全公開)
- これは `SNMP|CONTACT` / `SNMP|LOCATION` テーブルと直接関係はないが、snmpd の到達性に影響

---

### D-5: `snmp.yml` による起動時 LOCATION 注入 (silent drop の可能性)

**証拠**: `snmp_yml_to_configdb.py` L51–56
```python
if yaml_snmp_info.get('snmp_location'):
    if 'LOCATION' not in snmp_general_keys:
        db.set_entry('SNMP', 'LOCATION', {'Location': yaml_snmp_info['snmp_location']})
else:
    logger.log_info('snmp_location does not exist in snmp.yml file')
    sys.exit(1)
```

- `/etc/sonic/snmp.yml` に `snmp_location` がない場合、スクリプトは `sys.exit(1)` で終了 → LOCATION は設定されない
- `LOCATION` が CONFIG_DB に既に存在する場合は上書きしない (idempotent)
- `CONTACT` は `snmp_yml_to_configdb.py` で設定されない。CLI のみが書き込み元

---

### D-6: `sysServices` ハードコード値 `72`

**証拠**: `snmpd.conf.j2` L100
```
sysServices    72
```

- `sysServices` (MIB-II) は CONFIG_DB の SNMP テーブルで管理されず、常に `72` (application + end-to-end layers) が固定
- YANG にも定義なし → 完全なハードコード、変更不可 (snmpd.conf 再生成のたびに上書き)

---

### D-7: agentXTimeout / agentXRetries ハードコード値

**証拠**: `snmpd.conf.j2` L196–197
```
agentXTimeout   5
agentXRetries   4
```

- AgentX サブエージェント (sonic-snmpagent) との通信タイムアウト・リトライ回数が固定
- CONFIG_DB 管理外 → 調整不可

---

### D-8: `disk` / `load` モニタリング閾値ハードコード

**証拠**: `snmpd.conf.j2` L119–131
```
disk       /     10000
disk       /var  5%
includeAllDisks  10%
load   12 10 5
```

- ディスク空き閾値・ロードアベレージ閾値が固定値 → CONFIG_DB 経由で変更不可

---

## 重要度分類

| ID | 分類 | 重要度 |
|----|------|--------|
| D-1 | ハードコードデフォルト (`sysLocation = "public"`) | HIGH — 本番環境で情報漏洩リスク |
| D-2 | ハードコードデフォルト (`sysContact = Microsoft/Azure`) | HIGH — ベンダー固有情報が残存 |
| D-3 | YANG-実装 discrepancy (CONTACT フィールド構造) | HIGH — YANG 検証が事実上機能しない |
| D-4 | `SNMP_AGENT_ADDRESS_CONFIG` フォールバック全公開 | MEDIUM |
| D-5 | `snmp.yml` なし時 LOCATION silent drop | MEDIUM |
| D-6 | `sysServices = 72` ハードコード | LOW |
| D-7 | AgentX タイムアウト/リトライ ハードコード | LOW |
| D-8 | ディスク/ロード閾値ハードコード | LOW |

---

## 証跡 URL

- `snmpd.conf.j2`: <https://github.com/sonic-net/sonic-buildimage/blob/master/dockers/docker-snmp/snmpd.conf.j2>
- `snmp_yml_to_configdb.py`: <https://github.com/sonic-net/sonic-buildimage/blob/master/dockers/docker-snmp/snmp_yml_to_configdb.py>
- `config/main.py`: <https://github.com/sonic-net/sonic-utilities/blob/master/config/main.py>
- `sonic-snmp.yang`: <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-snmp.yang>
