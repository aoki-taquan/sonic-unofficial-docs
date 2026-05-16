# SNMP — Phase B 書込み順依存調査メモ

対象テーブル: `SNMP` (`SNMP|CONTACT`, `SNMP|LOCATION`)
調査日: 2026-05-15

## 調査対象ファイル

| ファイル | 役割 |
|---------|------|
| `sonic-buildimage/dockers/docker-snmp/start.sh` | docker-snmp コンテナ起動スクリプト — `snmp_yml_to_configdb.py` 実行 → `sonic-cfggen` による `snmpd.conf.j2` 展開を順序制御 |
| `sonic-buildimage/dockers/docker-snmp/snmp_yml_to_configdb.py` | `/etc/sonic/snmp.yml` から `SNMP_COMMUNITY` / `SNMP|LOCATION` を CONFIG_DB に書き込む起動時注入スクリプト |
| `sonic-buildimage/dockers/docker-snmp/snmpd.conf.j2` | CONFIG_DB の `SNMP` / `SNMP_COMMUNITY` / `SNMP_USER` / `SNMP_AGENT_ADDRESS_CONFIG` / `SNMP_TRAP_CONFIG` を読み取り `snmpd.conf` を生成 |
| `sonic-buildimage/dockers/docker-snmp/supervisord.conf.j2` | 起動順序制御 — `start:exited` 待機後に `snmpd` を起動 |
| `sonic-utilities/config/main.py` | CLI による `SNMP|CONTACT` / `SNMP|LOCATION` / `SNMP_COMMUNITY` の SET/DEL — 書き込み後に `systemctl restart snmp.service` を実行 |

---

## 1. コンテナ起動時の書込み順序

### start.sh が定義する起動シーケンス

docker-snmp コンテナ内の `supervisord` は以下の依存順序で各プログラムを起動する:

```
1. rsyslogd        起動 (priority=1)
2. start.sh        実行 (priority=1, rsyslogd:running 待機)
   ├─ snmp_yml_to_configdb.py  →  CONFIG_DB へ書き込み
   │     SNMP_COMMUNITY|<name>  TYPE=RO/RW
   │     SNMP|LOCATION          Location=<snmp_location>
   └─ sonic-cfggen -d -t snmpd.conf.j2 → /etc/snmp/snmpd.conf 生成
3. snmpd           起動 (priority=3, start:exited 待機)
4. snmp-subagent   起動 (priority=4, snmpd:running 待機)
```

**順序依存**: `snmpd` は `/etc/snmp/snmpd.conf` 生成完了後に起動する。`snmpd.conf.j2` の展開は `start.sh` の `sonic-cfggen` invocation が担当するため、`start.sh` が完了（`start:exited`）するまで `snmpd` は待機する。

### snmp_yml_to_configdb.py の書込み条件

```python
# SNMP|LOCATION の書込み
if yaml_snmp_info.get('snmp_location'):
    if 'LOCATION' not in snmp_general_keys:   # 既存エントリがある場合はスキップ
        db.set_entry('SNMP', 'LOCATION', {'Location': yaml_snmp_info['snmp_location']})
else:
    sys.exit(1)   # snmp_location がない場合は異常終了 → start.sh が失敗
```

**順序依存**:
- `/etc/sonic/snmp.yml` の `snmp_location` キーが存在しない場合、`snmp_yml_to_configdb.py` は `sys.exit(1)` で終了し、`start.sh` も失敗する。その場合 `snmpd` は起動しない。
- CONFIG_DB に既に `SNMP|LOCATION` が存在する場合 (`'LOCATION' not in snmp_general_keys` が False)、yml からの上書きはスキップされる（**既存エントリが優先**）。
- `SNMP|CONTACT` はこのスクリプトでは一切書き込まれない。CLI 経由のみ。

---

## 2. snmpd.conf.j2 テンプレート展開の読み取り順序

`sonic-cfggen -d -t snmpd.conf.j2` は CONFIG_DB から以下のテーブルを一括読み取りしてテンプレートを展開する（`-d` フラグ）。この読み取りは単一 invocation で行われるため、各テーブルの読み取り間に順序依存はない。

| 読み取り順 | テーブル | テンプレート条件 |
|-----------|----------|----------------|
| 1 | `SNMP_AGENT_ADDRESS_CONFIG` | `{% if SNMP_AGENT_ADDRESS_CONFIG %}` — 未定義時は `agentAddress udp:161` / `udp6:161` のデフォルト |
| 2 | `SNMP_COMMUNITY` | `{% if SNMP_COMMUNITY is defined %}` — 未定義時はコミュニティ行なし（全 SNMP アクセス拒否） |
| 3 | `SNMP_USER` | `{% if SNMP_USER is defined %}` — v3 ユーザ設定 |
| 4 | `SNMP` (LOCATION) | `{% if SNMP is defined and SNMP.LOCATION is defined %}` — 未定義時 `sysLocation public` ハードコード |
| 5 | `SNMP` (CONTACT) | `{% if SNMP is defined and SNMP.CONTACT is defined %}` — 未定義時 `sysContact Azure Cloud Switch vteam <linuxnetdev@microsoft.com>` ハードコード |
| 6 | `SNMP_TRAP_CONFIG` | `{% if SNMP_TRAP_CONFIG and SNMP_TRAP_CONFIG['v1TrapDest'] %}` 等 — trap 設定 |

**重要**: テンプレート展開は**スナップショット**であり、CONFIG_DB への書き込みはテンプレート展開前に完了している必要がある。

---

## 3. CLI 書込みとサービス再起動の順序

CLI (`config snmp contact add/modify/del`, `config snmp location add/modify/del`) は書き込み後に必ず `systemctl restart snmp.service` を実行する。

```python
# config/main.py の共通パターン (L4487-4491, L4606-4611 等)
db.cfgdb.set_entry('SNMP', 'CONTACT', {contact: contact_email})
clicommon.run_command(['systemctl', 'reset-failed', 'snmp.service'])
clicommon.run_command(['systemctl', 'restart', 'snmp.service'])
```

`systemctl restart snmp.service` は docker-snmp コンテナ全体を再起動するため、上記 `start.sh` の起動シーケンスが再実行される。

**順序依存**:
1. `set_entry` → CONFIG_DB 書き込み完了
2. `systemctl restart snmp.service` → コンテナ再起動
3. `snmp_yml_to_configdb.py` が実行されるが、既存エントリ (`SNMP|LOCATION`) はスキップ
4. `sonic-cfggen` で `snmpd.conf.j2` を展開 → `/etc/snmp/snmpd.conf` 更新
5. `snmpd` が新しい `snmpd.conf` で起動

**影響**: CLI でいずれかの SNMP フィールドを変更すると、snmp コンテナ全体が再起動するため、**変更反映まで数秒〜十数秒の SNMP 断が発生する**。

---

## 4. テーブル間の依存関係

### `SNMP_COMMUNITY` が `SNMP|CONTACT`/`SNMP|LOCATION` に依存しない

`SNMP_COMMUNITY` は独立したテーブル。`SNMP|CONTACT`/`SNMP|LOCATION` の存在に依存しない。逆に `SNMP|CONTACT`/`SNMP|LOCATION` も `SNMP_COMMUNITY` の存在に依存しない。

### `SNMP_COMMUNITY` が未定義時は全アクセス拒否

`snmpd.conf.j2` L48-55 の `{% if SNMP_COMMUNITY is defined %}` ガードにより、`SNMP_COMMUNITY` テーブルが空の場合はコミュニティ設定行が一切出力されない。コミュニティなしでは全 SNMP アクセスが拒否される。

**順序依存**: `SNMP|LOCATION` / `SNMP|CONTACT` を設定しても、`SNMP_COMMUNITY` が設定されていなければ SNMP は機能しない。

### `DEVICE_METADATA.hostname` との間接依存

`sysDescription.j2` テンプレートが `DEVICE_METADATA.hostname` を参照して `sysDescr` を生成する。`snmpd.conf.j2` 自体は `DEVICE_METADATA` を直接参照しない。

---

## 5. 書込み順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `/etc/sonic/snmp.yml` の `snmp_location` キー → コンテナ起動成功 | **必須先行** (snmp.yml は事前配置が必要) | なし — `sys.exit(1)` でコンテナ起動が失敗する |
| 2 | `SNMP|LOCATION` CONFIG_DB 書き込み → `sonic-cfggen` 展開 | **必須先行** (start.sh シーケンス内で順序保証) | supervisord `dependent_startup_wait_for=start:exited` |
| 3 | `SNMP_COMMUNITY` 設定 → SNMP アクセス可能 | **必須** | `SNMP_COMMUNITY` なしは全アクセス拒否 |
| 4 | CLI `set_entry` → `systemctl restart snmp.service` | **CLI が自動実行** | CLI が常に再起動を行う |
| 5 | `SNMP|LOCATION` 既存エントリ → `snmp_yml_to_configdb.py` の上書きスキップ | **既存優先** (CONFIG_DB が snmp.yml より優先) | `'LOCATION' not in snmp_general_keys` ガード |
| 6 | `SNMP|CONTACT` 書き込み → CLI のみ | **CLI 専用** (snmp_yml_to_configdb.py は CONTACT を書かない) | CONTACT 未設定時は Azure ハードコードデフォルト |

---

## 6. warm-reboot / reload 影響

| フィールド | コンテナ再起動の要否 | 順序制約 |
|-----------|-------------------|---------|
| `SNMP|LOCATION.Location` | **必要** — snmpd.conf は起動時のみ生成される | CLI が自動で `systemctl restart snmp.service` を実行 |
| `SNMP|CONTACT.<name>` | **必要** — 同上 | CLI が自動で実行 |
| `SNMP_COMMUNITY.<name>` | **必要** — 同上 | CLI が自動で実行 |
| `SNMP_AGENT_ADDRESS_CONFIG` | **必要** — 同上 | CLI が自動で実行 |
| `SNMP_TRAP_CONFIG` | **必要** — 同上 | CLI が自動で実行 |

全フィールドで docker-snmp コンテナ再起動が必要。ランタイム動的更新は不可。warm-reboot 後は `start.sh` が再実行され、`snmp.yml` よりも CONFIG_DB の既存エントリが優先される。
