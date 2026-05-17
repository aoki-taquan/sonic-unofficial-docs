# SNMP_AGENT_ADDRESS_CONFIG / SNMP_USER — Phase B 書込み順依存調査メモ

対象ページ: `docs/reference/config-db/snmp-agent.md`
調査日: 2026-05-17

## SNMP_USER の書込み順依存

### 1. SNMP_USER_TYPE が全 must 制約の前提 — アトミック SET が必須

`sonic-snmp.yang` L118-165 の `must` 制約は `SNMP_USER_AUTH_TYPE`, `SNMP_USER_AUTH_PASSWORD`, `SNMP_USER_ENCRYPTION_TYPE`, `SNMP_USER_ENCRYPTION_PASSWORD` のすべてが `current()/../SNMP_USER_TYPE` の値に連動する。

CLI `add_user()` は全フィールドを 1 回の `set_entry()` でアトミックに書き込む (`config/main.py:4779-4786`)。フィールドを分割して SET すると `SNMP_USER_TYPE` が未確定な状態で `must` 評価が走り、YANG バリデーション違反になる可能性がある。

**順序依存**:
- `SNMP_USER_TYPE` / `SNMP_USER_PERMISSION` / auth・encrypt フィールドは単一の `set_entry()` でアトミックに書き込むこと。フィールドを順次 SET する方式は `must` 制約違反を引き起こす。
- `SNMP_USER_TYPE` を変更する場合（例: `noAuthNoPriv` → `Priv`）は、一度 DEL してから新しいフィールドセットで SET し直す（CLI `config snmp user del` → `config snmp user add`）。

### 2. SNMP_USER 登録後は docker-snmp 再起動が必要

`snmpd.conf.j2` L66-77 の `SNMP_USER` ブロックは docker-snmp コンテナ起動時の一括レンダリングで生成される。CLI `add_user()` は SET 後に `systemctl reset-failed && restart snmp.service` を自動実行する (`config/main.py:4784-4793`)。

**順序依存**:
- `sonic-db-cli` で直接 SNMP_USER を SET した場合は `systemctl restart snmp` を手動実行しなければ snmpd.conf に反映されない。
- SNMPv3 ユーザを有効化するには `snmpd.conf` の `CreateUser` 行が必要であり、snmpd の起動が完了してから初めて v3 認証が機能する。

## SNMP_AGENT_ADDRESS_CONFIG の書込み順依存

### 3. 同一 (agent_ip, port) 重複: DEL 先行が必須

`sonic-snmp.yang` L171: `unique "agent_ip port"` — 同一 (ip, port) を異なる vrf_name で重複登録すると YANG バリデーション拒否。VRF を変更する場合は旧エントリを DEL してから新エントリを SET する。CLI は `get_keys` で事前重複チェックを行い YANG 層到達前に防ぐ (`config/main.py:4177-4182`)。

### 4. Management VRF 有効時は -v mgmt が必須

`MGMT_VRF_CONFIG|vrf_global.mgmtVrfEnabled = 'true'` の状態で VRF 指定なしに `config snmp agentaddress add <ip>` を実行すると CLI がブロックする (`config/main.py:4153-4157`)。

### 5. IP アドレスが NIC に付与済みであること

CLI は `netifaces.interfaces()` でアドレス実在確認を行う (`config/main.py:4160-4171`)。IP 未付与の場合は "IP address is not available" で拒否。

### 6. VRF が実在してから agentaddress を設定

VRF フィールドを設定しても VRF がカーネルに存在しない場合、CONFIG_DB 書込みは成功するが snmpd の bind が失敗する。正しい順序: `config vrf add <vrf>` → `config snmp agentaddress add <ip> -v <vrf>`。

### 7. SET 後は snmp コンテナ再起動が必要

CLI は書込み直後に `os.system("systemctl restart snmp")` を呼ぶ (`config/main.py:4189`)。直接 sonic-db-cli で書き込む場合は手動で再起動が必要。

## 書込み順依存サマリ

| # | テーブル | 依存関係 | 方向 | 違反時の挙動 |
|---|---------|----------|------|------------|
| 1 | SNMP_USER | 全フィールドをアトミック SET | **必須** | YANG must 違反 |
| 2 | SNMP_USER | SNMP_USER_TYPE 変更時: DEL → SET | **必須** | must 制約違反（部分 SET 失敗） |
| 3 | SNMP_USER | SET 完了 → `systemctl restart snmp` | **必須後続** | snmpd.conf 未更新 |
| 4 | SNMP_AGENT_ADDRESS_CONFIG | 旧エントリ DEL → 同 (ip,port) 新エントリ SET | **必須先行** | YANG unique 違反 |
| 5 | SNMP_AGENT_ADDRESS_CONFIG | MGMT_VRF 有効時は -v mgmt 明示 | **CLI 強制** | CLI ブロック |
| 6 | SNMP_AGENT_ADDRESS_CONFIG | NIC への IP 付与 → agentaddress add | **CLI 強制** | "IP address is not available" |
| 7 | SNMP_AGENT_ADDRESS_CONFIG | VRF 作成 → agentaddress add -v <vrf> | **推奨先行** | DB 成功・snmpd bind 失敗 |
| 8 | SNMP_AGENT_ADDRESS_CONFIG | SET 完了 → `systemctl restart snmp` | **必須後続** | snmpd.conf 未更新 |
