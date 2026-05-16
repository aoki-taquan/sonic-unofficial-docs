# SNMP — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-buildimage/dockers/docker-snmp/snmpd.conf.j2`
- `sonic-buildimage/dockers/docker-snmp/supervisord.conf.j2`
- `sonic-buildimage/dockers/docker-snmp/snmp_yml_to_configdb.py`
- `sonic-utilities/config/main.py`

---

## 発見された定数一覧

### snmpd.conf.j2 — agentAddress フォールバック

| 定数名 | 値 | 用途 | ソース |
|--------|-----|------|--------|
| デフォルト agentAddress (IPv4) | `udp:161` | `SNMP_AGENT_ADDRESS_CONFIG` 未定義時の全インターフェース公開 | `snmpd.conf.j2` L32 |
| デフォルト agentAddress (IPv6) | `udp6:161` | `SNMP_AGENT_ADDRESS_CONFIG` 未定義時の全インターフェース公開 (IPv6) | `snmpd.conf.j2` L33 |

### snmpd.conf.j2 — システム情報ハードコード

| 定数名 | 値 | 用途 | ソース |
|--------|-----|------|--------|
| `sysLocation` デフォルト | `"public"` | `SNMP.LOCATION` 未定義時のフォールバック文字列 (YANG に default なし) | `snmpd.conf.j2` L91 |
| `sysContact` デフォルト | `"Azure Cloud Switch vteam <linuxnetdev@microsoft.com>"` | `SNMP.CONTACT` 未定義時の Microsoft/Azure 固有ハードコード (YANG に default なし) | `snmpd.conf.j2` L96 |
| `sysServices` | `72` | Application + End-to-End layers (固定値、CONFIG_DB で管理されない) | `snmpd.conf.j2` L100 |

### snmpd.conf.j2 — ディスク監視閾値

| 定数名 | 値 | 用途 | ソース |
|--------|-----|------|--------|
| disk `/` 最小空き容量 | `10000` (KB = 約 9.8 MB) | `/` パーティションの最小空き容量 (固定) | `snmpd.conf.j2` L119 |
| disk `/var` 最小空き率 | `5%` | `/var` パーティションの最小空き率 (固定) | `snmpd.conf.j2` L120 |
| includeAllDisks 最小空き率 | `10%` | その他全ディスクの最小空き率 (固定) | `snmpd.conf.j2` L121 |

### snmpd.conf.j2 — ロードアベレージ監視閾値

| 定数名 | 値 | 用途 | ソース |
|--------|-----|------|--------|
| load 1 分 上限 | `12` | 1 分ロードアベレージ警告閾値 (固定) | `snmpd.conf.j2` L131 |
| load 5 分 上限 | `10` | 5 分ロードアベレージ警告閾値 (固定) | `snmpd.conf.j2` L131 |
| load 15 分 上限 | `5` | 15 分ロードアベレージ警告閾値 (固定) | `snmpd.conf.j2` L131 |

### snmpd.conf.j2 — AgentX 設定

| 定数名 | 値 | 用途 | ソース |
|--------|-----|------|--------|
| `agentXTimeout` | `5` (秒) | AgentX サブエージェント応答タイムアウト (固定) | `snmpd.conf.j2` L197 |
| `agentXRetries` | `4` | AgentX 再試行回数 (固定) | `snmpd.conf.j2` L198 |
| `agentxsocket` | `tcp:localhost:3161` | snmp-subagent 内部通信ソケット (固定ポート) | `snmpd.conf.j2` L207 |

### snmpd.conf.j2 — sysDescr パススルー

| 定数名 | 値 | 用途 | ソース |
|--------|-----|------|--------|
| sysDescr OID | `.1.3.6.1.2.1.1.1` | MIB-II sysDescr パススルー OID | `snmpd.conf.j2` L213 |
| sysDescr スクリプト | `/usr/share/snmp/sysDescr_pass.py` | sysDescr 生成スクリプトパス | `snmpd.conf.j2` L213 |
| pass priority | `-p 10` | pass スクリプトの優先度 (固定) | `snmpd.conf.j2` L213 |

### snmpd.conf.j2 — SNMP trap デフォルトポート

| 定数名 | 値 | 用途 | ソース |
|--------|-----|------|--------|
| `DestPort` デフォルト (CLI) | `"162"` | `config snmptrap modify` の `--port` オプションデフォルト | `sonic-utilities/config/main.py` L4222 |

### snmp_yml_to_configdb.py — yml キー文字列

| 定数名 | 値 | 用途 | ソース |
|--------|-----|------|--------|
| SNMP community yml キー一覧 | `['snmp_rocommunity', 'snmp_rocommunities', 'snmp_rwcommunity', 'snmp_rwcommunities']` | snmp.yml から読み取るコミュニティ設定キー名 | `snmp_yml_to_configdb.py` L23 |
| SNMP location yml キー | `'snmp_location'` | snmp.yml から読み取る Location キー名 | `snmp_yml_to_configdb.py` L51 |
| snmp.yml パス | `'/etc/sonic/snmp.yml'` | SNMP yml ファイルの固定パス (存在しない場合 sys.exit(1)) | `snmp_yml_to_configdb.py` L25 |

---

## タイミング定数

| 定数名 | 値 | 用途 |
|--------|-----|------|
| `agentXTimeout` | `5` 秒 | AgentX サブエージェントが応答しない場合の最大待機時間 |
| `agentXRetries` | `4` 回 | AgentX 接続再試行上限 |
| CLI 変更後の snmp.service 再起動 | 毎回自動 | `config snmp contact/location/community/agentaddress/trap` 変更後は常に `systemctl reset-failed snmp.service && systemctl restart snmp.service` を実行 |

---

## 特記事項

1. **`sysLocation "public"` は community 名と同一文字列だが無関係**: テンプレート固有ハードコード。YANG に `default` ステートメントなし。本番では必ず `SNMP.LOCATION` を設定すること。
2. **`sysContact` の Microsoft/Azure 固有文字列**: YANG に `default` ステートメントなし。コミュニティ版を Azure 環境以外で使う場合でも変更されない。本番では必ず CLI で設定すること。
3. **`sysServices 72` は変更不可**: CONFIG_DB の `SNMP` テーブルでは管理されず、snmpd.conf.j2 に静的にハードコードされている。72 = 64 (applications) + 8 (end-to-end/IP)。
4. **内部ポート 3161 は docker-snmp 内部専用**: AgentX ソケット `tcp:localhost:3161` は docker-snmp コンテナ内部のみ。FRR (docker-fpm-frr) への extension 用コメントあり (`bgp:/etc/snmp/frr.conf` と一致させること)。
5. **ディスク/ロード監視閾値は固定**: UCD-SNMP-MIB による監視閾値だが CONFIG_DB からは制御できない。閾値超過時に SNMP trap が送信される。
6. **SNMP trap port デフォルト 162**: CLI の `--port` オプションデフォルト値。RFC 3232 で SNMP trap の well-known ポートとして規定。
7. **snmp.yml パスは固定**: `/etc/sonic/snmp.yml` が存在しないと `snmp_yml_to_configdb.py` が `sys.exit(1)` でコンテナ起動失敗。

---

## 出典

- `sonic-buildimage/dockers/docker-snmp/snmpd.conf.j2` L19-33, L88-100, L119-131, L197-213
- `sonic-buildimage/dockers/docker-snmp/snmp_yml_to_configdb.py` L23-56
- `sonic-buildimage/dockers/docker-snmp/supervisord.conf.j2` L42-64
- `sonic-utilities/config/main.py` L4222
