# SNMP_AGENT_ADDRESS_CONFIG / SNMP_USER — Phase B 書込み順依存調査

対象テーブル: `SNMP_AGENT_ADDRESS_CONFIG`, `SNMP_USER`
調査日: 2026-05-17
調査ファイル:
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-snmp.yang`
- `sonic-utilities/config/main.py` (add_snmp_agent_address, add_user, del_user)
- `sonic-buildimage/dockers/docker-snmp/snmpd.conf.j2`
- `sonic-buildimage/src/sonic-config-engine/minigraph.py`

---

## SNMP_AGENT_ADDRESS_CONFIG 書込み順依存

### 1. YANG unique 制約 — 同一 (ip, port) は重複不可

`sonic-snmp.yang` L171:
```yang
unique "agent_ip port";
```
同一 (ip, port) を異なる vrf_name で重複登録しようとすると YANG unique 制約で SET が拒否される。
CLI (`config/main.py:4177-4182`) は `get_keys` で事前重複チェックを行い、YANG 層への到達前に防ぐ。
VRF 変更時の正しい順序: 旧エントリ DEL → 新エントリ SET。

### 2. MGMT_VRF_CONFIG が有効な場合は vrf 指定必須 (CLI 強制)

`config/main.py:4153-4157`:
```python
if not vrf:
    entry = config_db.get_entry('MGMT_VRF_CONFIG', "vrf_global")
    if entry and entry['mgmtVrfEnabled'] == 'true':
        click.echo("ManagementVRF is Enabled. Provide vrf.")
        return False
```
Management VRF 有効時に vrf 省略で `agentaddress add` すると CLI がブロックする。
正しい順序: Management VRF 有効化 → `-v mgmt` 明示で agentaddress 登録。

### 3. NIC への IP 付与が先行必須 (CLI 強制)

`config/main.py:4160-4171`: `netifaces.interfaces()` で IP が実際に NIC に付与済みか確認する。
IP 未付与では "IP address is not available" で拒否される。

### 4. VRF が実在してから agentaddress を設定 (推奨先行)

vrf_name に `mgmt`/`Vrf<name>` を指定しても VRF がカーネルに存在しない場合、CONFIG_DB 書込みは成功するが snmpd が agentAddress bind に失敗する。
正しい順序: `config vrf add <vrf>` → `config snmp agentaddress add <ip> -v <vrf>`。

### 5. SET 後は snmp コンテナ再起動が必要

`config/main.py:4189`: CLI は書込み直後に `os.system("systemctl restart snmp")` を自動実行する。
直接 `sonic-db-cli` で書き込む場合は手動での `systemctl restart snmp` が必要。

### 6. minigraph 経路: MGMT_INTERFACE / LOOPBACK_INTERFACE 先行

`minigraph.py:2308-2322`: minigraph は MGMT_INTERFACE / LOOPBACK_INTERFACE を先行して解析した後に SNMP_AGENT_ADDRESS_CONFIG を生成する。multi-asic 環境では自動生成が行われず空辞書となる。

---

## SNMP_USER 書込み順依存

### 1. SNMP_USER_TYPE が mandatory — 他フィールドの MUST 制約が型に連動

`sonic-snmp.yang` の `SNMP_USER_TYPE` は `mandatory true`。
`SNMP_USER_AUTH_TYPE`、`SNMP_USER_AUTH_PASSWORD`、`SNMP_USER_ENCRYPTION_TYPE`、`SNMP_USER_ENCRYPTION_PASSWORD` の各 `must` 制約は `SNMP_USER_TYPE` の値に連動する。
SET を 1 回の操作で全フィールドを同時書き込む必要がある（CLI は `set_entry` で全フィールドを dict 一括書込み、`config/main.py:4779-4784`）。
フィールドを分割して複数回 SET すると YANG `must` 制約が中間状態で違反する可能性がある。

### 2. ユーザ名の重複チェック — DEL してから同名 ADD

`config/main.py:4766-4769`:
```python
snmp_users = db.cfgdb.get_table("SNMP_USER")
if user in snmp_users.keys():
    click.echo("SNMP user {} is already configured".format(user))
    sys.exit(SnmpUserError.UserAlreadyConfigured)
```
同名ユーザが存在する状態で `user add` を実行すると CLI が拒否する。
変更時の正しい順序: `config snmp user del <user>` → `config snmp user add <user> ...`。

### 3. SET 後は snmp コンテナ再起動が必要

`config/main.py:4788-4791`: CLI は書込み後に `systemctl reset-failed snmp.service` + `systemctl restart snmp.service` を実行する。
`snmpd.conf.j2` の `CreateUser` 行 (L70) に反映するためコンテナ再起動が必須。

---

## 書込み順サマリ

| # | テーブル | 依存関係 | 違反時の挙動 |
|---|---------|---------|------------|
| 1 | SNMP_AGENT_ADDRESS_CONFIG | 旧 `(ip,port,vrf_old)` DEL → 新 `(ip,port,vrf_new)` SET | YANG unique 違反（SET 失敗）/ CLI 早期リターン |
| 2 | SNMP_AGENT_ADDRESS_CONFIG | MGMT_VRF_CONFIG 有効時は `-v mgmt` 明示 | CLI ブロック（DB 書込み不達） |
| 3 | SNMP_AGENT_ADDRESS_CONFIG | NIC への IP 付与 先行 | "IP address is not available" 拒否 |
| 4 | SNMP_AGENT_ADDRESS_CONFIG | VRF 作成 先行 → agentaddress 登録 | DB 書込み成功、snmpd bind 失敗 |
| 5 | SNMP_AGENT_ADDRESS_CONFIG | SET 完了 → `systemctl restart snmp` | snmpd.conf 未更新（旧設定継続） |
| 6 | SNMP_AGENT_ADDRESS_CONFIG | minigraph 内部: MGMT_INTERFACE 先行 | 空辞書（multi-asic では常時空） |
| 7 | SNMP_USER | 全フィールドを 1 回の `set_entry` で一括書込み | YANG must 違反（中間状態） |
| 8 | SNMP_USER | 既存同名ユーザ DEL → 新ユーザ ADD | CLI 拒否（UserAlreadyConfigured） |
| 9 | SNMP_USER | SET 完了 → `systemctl restart snmp.service` | snmpd.conf 未更新（旧 CreateUser 行継続） |
