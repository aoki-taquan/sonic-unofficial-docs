# SNMP_AGENT_ADDRESS_CONFIG / SNMP_USER — Phase D 失敗挙動調査メモ

対象ページ: `docs/reference/config-db/snmp-agent.md`
調査日: 2026-05-17

## 調査対象ファイル

| ファイル | 役割 |
|---------|------|
| `sonic-buildimage/dockers/docker-snmp/start.sh` | コンテナ起動スクリプト — snmp_yml_to_configdb.py → sonic-cfggen の実行 |
| `sonic-buildimage/dockers/docker-snmp/snmp_yml_to_configdb.py` | snmp.yml → CONFIG_DB 注入スクリプト |
| `sonic-buildimage/dockers/docker-snmp/snmpd.conf.j2` | snmpd.conf テンプレート |
| `sonic-buildimage/dockers/docker-snmp/supervisord.conf.j2` | supervisord 設定テンプレート |
| `sonic-utilities/config/main.py` | CLI add_snmp_agent_address / add_user |
| `src/sonic-yang-models/yang-models/sonic-snmp.yang` | YANG must 制約 |

---

## SNMP_AGENT_ADDRESS_CONFIG の失敗経路

### 1. snmpd.conf.j2 レンダリング失敗（key フォーマット不正）

`snmpd.conf.j2` L28: `{% for (agentip, port, vrf) in SNMP_AGENT_ADDRESS_CONFIG %}` — タプルアンパックで agentip / port / vrf の 3 要素を期待する。

CONFIG_DB の key が `<ip>|<port>|<vrf>` の 3 要素でない場合（例: `|` 区切りが不正）、sonic-cfggen がテンプレートレンダリング時に ValueError / IndexError で失敗し `/etc/snmp/snmpd.conf` が生成されず snmpd が起動しない。

| 失敗条件 | 検出箇所 | 結果 |
|---|---|---|
| key フォーマット不正（`<ip>|<port>|<vrf>` でない） | `start.sh`（sonic-cfggen 呼び出し） | snmpd.conf 生成失敗 → snmpd 未起動 |

### 2. VRF が実在しない場合の bind 失敗（サイレント）

`vrf_name` に `mgmt` や `Vrf<name>` を指定しても VRF がカーネルに存在しない場合、snmpd は起動後に `agentAddress udp:[<ip>]@<vrf>` のバインドに失敗する。snmpd はバインドエラーを警告ログとして記録するが、致命的エラーとはせず他の agentAddress でのリッスンを継続する（またはデフォルト全 IF でリッスン）。

| 失敗条件 | 結果 | 可観測性 |
|---|---|---|
| `vrf_name` が実在しない VRF | snmpd の agentAddress bind 失敗（サイレント） | `journalctl -u docker-snmp` で snmpd の bind エラーを確認 |

### 3. systemctl restart snmp の失敗（CLI 経路）

CLI の `add_snmp_agent_address()` は書き込み後に `os.system("systemctl restart snmp")` を実行する（`config/main.py:4189`）。このコマンドが失敗しても CLI はエラーを返さない（戻り値チェックなし）。snmpd.conf は更新されず旧設定で継続。

| 失敗条件 | 結果 |
|---|---|
| `systemctl restart snmp` 失敗 | CLI はエラーを報告しない。snmpd.conf 未更新で旧設定継続 |

---

## SNMP_USER の失敗経路

### 4. YANG must 制約違反（フィールド不整合）

`sonic-snmp.yang` L120-163 の `must` 制約は SNMP_USER_TYPE に連動する。

| 失敗条件 | YANG 制約 | 結果 |
|---|---|---|
| `noAuthNoPriv` ユーザに `SNMP_USER_AUTH_TYPE != ""` を SET | `must` 制約違反 | SET 拒否 |
| `AuthNoPriv` / `Priv` ユーザに `SNMP_USER_AUTH_TYPE = ""` を SET | `must` 制約違反 | SET 拒否 |
| `Priv` ユーザに `SNMP_USER_ENCRYPTION_TYPE` が DES/AES 以外 | `must` 制約違反 | SET 拒否 |
| `noAuthNoPriv` / `AuthNoPriv` ユーザに `SNMP_USER_ENCRYPTION_PASSWORD != ""` | `must` 制約違反 | SET 拒否 |

CLI `add_user()` は `set_entry()` 呼び出し前にすべての制約を Python レベルで検証するため、CLI 経由では YANG 層到達前に防がれる（`config/main.py:4717-4780`）。ただし `sonic-db-cli` で直接書き込む場合は YANG バリデーション層が直撃する。

### 5. snmpd.conf.j2 の CreateUser 行展開（空フィールド）

`snmpd.conf.j2` L70:
```jinja
CreateUser {{ user }} {{ SNMP_USER[user]['SNMP_USER_AUTH_TYPE'] }} {{ SNMP_USER[user]['SNMP_USER_AUTH_PASSWORD'] }} {{ SNMP_USER[user]['SNMP_USER_ENCRYPTION_TYPE'] }} {{ SNMP_USER[user]['SNMP_USER_ENCRYPTION_PASSWORD'] }}
```

フィールドが欠落している場合（`SNMP_USER_AUTH_TYPE` キー自体が CONFIG_DB に存在しない）、Jinja2 テンプレートが `KeyError` / `UndefinedError` で失敗し snmpd.conf 生成が停止する。sonic-cfggen は `-d` オプションで CONFIG_DB 全体を dict にロードするため、YANG バリデーションを通過していれば空文字が格納されており KeyError は発生しない。ただし、YANG バリデーションをバイパスして SET した場合はこのリスクがある。

| 失敗条件 | 結果 |
|---|---|
| SNMP_USER にフィールドが欠落（YANG バイパスで直接 SET） | snmpd.conf 生成失敗 → snmpd 未起動 |

### 6. snmpd.conf CreateUser と snmpd の関係

snmpd は `CreateUser` 行をランタイムに処理する。認証情報が不正（例: HMAC-SHA-2 アルゴリズムが snmpd バージョンで未サポート）の場合、snmpd は起動するが該当ユーザでの v3 認証が失敗する（CONFIG_DB レベルでは検知不可）。

---

## コンテナ起動経路の失敗

### 7. start.sh の全体的な失敗連鎖

```
snmp_yml_to_configdb.py → /etc/sonic/snmp.yml 不在時 sys.exit(1)
sonic-cfggen → snmpd.conf.j2 レンダリング失敗時 exit(1)
```

supervisord は `start:exited` を待機してから `snmpd` を起動する。`start.sh` が non-zero で終了した場合、`snmpd` は起動されない。

| 失敗条件 | 結果 |
|---|---|
| `/etc/sonic/snmp.yml` の `snmp_location` キー不在 | `snmp_yml_to_configdb.py` が `sys.exit(1)` → `start.sh` 失敗 → `snmpd` 未起動 |
| `sonic-cfggen` の snmpd.conf.j2 レンダリング失敗 | `start.sh` 失敗 → `snmpd` 未起動 |
| `supervisord.conf.j2` の `DEVICE_METADATA.localhost.switch_type` KeyError | supervisord 設定生成失敗 → コンテナ起動不可 |

---

## 失敗の可観測性

| 確認項目 | コマンド |
|---------|---------|
| docker-snmp コンテナ状態 | `docker ps \| grep snmp` |
| start.sh ログ | `docker logs snmp 2>&1 \| grep -E 'ERROR\|snmp_yml'` |
| snmpd バインドエラー | `journalctl -u docker-snmp` または `docker exec snmp cat /var/log/supervisor/snmpd.log` |
| snmpd.conf 内容確認 | `docker exec snmp cat /etc/snmp/snmpd.conf` |
| YANG バリデーション確認 | `sonic-db-cli CONFIG_DB hgetall 'SNMP_USER|<user>'` |
