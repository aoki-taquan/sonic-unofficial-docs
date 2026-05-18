# SNMP_COMMUNITY — Phase E ハードコード定数 調査メモ

生成日: 2026-05-18
対象ページ: `docs/reference/config-db/community-list.md`
調査ソース:
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-snmp.yang`
- `sonic-buildimage/dockers/docker-snmp/snmpd.conf.j2`
- `sonic-buildimage/dockers/docker-snmp/snmp_yml_to_configdb.py`
- `sonic-utilities/config/main.py` L4309-4324

---

## 1. YANG レベル固定値（name フィールド）

`sonic-snmp.yang` の `SNMP_COMMUNITY_LIST` に定義された固定制約:

| 制約 | 値 | ソース |
|------|----|--------|
| `name` 最小長 | 4 文字 | `sonic-snmp.yang L61: length "4..32"` |
| `name` 最大長 | 32 文字 | `sonic-snmp.yang L61: length "4..32"` |
| `name` 禁止文字（YANG） | SPACE / `'` (シングルクォート) / `@` / `,` / `\` | `sonic-snmp.yang L62: pattern '[^ @,\\' +"']*"` |
| `TYPE` 有効値 | `RO` / `RW`（大文字 2 値のみ） | `sonic-snmp.yang L71-74: enum RO; enum RW;` |

---

## 2. CLI レベル固定値（snmp_community_secret_check）

`config/main.py` の `snmp_community_secret_check` 関数内のリテラル:

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `excluded_special_symbols` | `['@', ':']` | CLI 追加禁止文字リスト（YANG 制約外の `:` を含む） | `config/main.py L4310` |
| CLI 最大長 | `32` | `len(snmp_secret) > 32` の閾値 | `config/main.py L4311` |

**注意**: YANG の禁止文字（`,` / `\`）は CLI リストに含まれない。CLI の `:` 禁止は YANG に存在しない。両者の禁止文字集合は非対称。

---

## 3. テンプレートレベル固定値（snmpd.conf.j2）

`snmpd.conf.j2` 内のハードコードリテラル:

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| デフォルト SNMP UDP ポート（IPv4） | `161` | `SNMP_AGENT_ADDRESS_CONFIG` 未設定時のデフォルト | `snmpd.conf.j2 L32: agentAddress udp:161` |
| デフォルト SNMP UDP ポート（IPv6） | `161` | 同上（IPv6） | `snmpd.conf.j2 L33: agentAddress udp6:161` |
| AgentX ソケット | `tcp:localhost:3161` | docker-fpm-frr (FRR SNMP subagent) との IPC | `snmpd.conf.j2 L207: agentxsocket tcp:localhost:3161` |
| AgentX タイムアウト | `5` 秒 | `agentXTimeout 5` | `snmpd.conf.j2 L197` |
| AgentX リトライ | `4` 回 | `agentXRetries 4` | `snmpd.conf.j2 L198` |
| sysLocation フォールバック | `public` | `SNMP.LOCATION` 未設定時の値 | `snmpd.conf.j2 L91: sysLocation public` |
| sysContact フォールバック | `Azure Cloud Switch vteam <linuxnetdev@microsoft.com>` | `SNMP.CONTACT` 未設定時の値 | `snmpd.conf.j2 L93` |
| TYPE 大文字比較文字列 | `'RO'` / `'RW'` | community 行生成条件の厳格文字列比較 | `snmpd.conf.j2 L50, L59` |
| disk 監視閾値 `/` | `10000` (MB) | `disk / 10000` — snmpd.conf 固定 | `snmpd.conf.j2 L119` |
| disk 監視閾値 `/var` | `5%` | `disk /var 5%` — snmpd.conf 固定 | `snmpd.conf.j2 L120` |
| disk 監視閾値 その他 | `10%` | `includeAllDisks 10%` — snmpd.conf 固定 | `snmpd.conf.j2 L121` |
| load 監視閾値 | `12 10 5`（1/5/15 分） | `load 12 10 5` — snmpd.conf 固定 | `snmpd.conf.j2 L130` |

---

## 4. snmp_yml_to_configdb.py 固定値

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| 処理対象 community type キー一覧 | `['snmp_rocommunity', 'snmp_rocommunities', 'snmp_rwcommunity', 'snmp_rwcommunities']` | `snmp.yml` から読み取るキー名（固定順） | `snmp_yml_to_configdb.py L23` |
| RO community の DB TYPE 値 | `"RO"` | `set_entry` 引数（大文字固定） | `snmp_yml_to_configdb.py L37, L41` |
| RW community の DB TYPE 値 | `"RW"` | `set_entry` 引数（大文字固定） | `snmp_yml_to_configdb.py L45, L49` |
| snmp.yml パス | `/etc/sonic/snmp.yml` | ハードコードファイルパス | `snmp_yml_to_configdb.py L25` |

---

## 5. CONFIG_DB から変更不可能な固定値のまとめ

以下の値は CONFIG_DB エントリでは制御できず、コードまたはテンプレートにリテラルで固定されている:

- SNMP デフォルト待受ポート: **UDP 161**（`SNMP_AGENT_ADDRESS_CONFIG` で上書き可能だが、未設定時は常に 161）
- AgentX ソケット: **`tcp:localhost:3161`**（変更不可）
- TYPE 比較文字列: **大文字 `RO`/`RW`** のみ有効（小文字は機能しない）
- sysLocation フォールバック: **`public`**（`SNMP.LOCATION` で上書き可能だが、デフォルトは `public`）
- sysContact フォールバック: **`Azure Cloud Switch vteam`** アドレス
