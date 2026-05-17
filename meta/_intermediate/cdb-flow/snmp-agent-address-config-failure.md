# snmp-agent-address-config — Phase D: 失敗挙動スキャン記録

## スキャン対象

- `sonic-buildimage/dockers/docker-snmp/snmpd.conf.j2` (template)
- `sonic-buildimage/dockers/docker-snmp/start.sh`
- `sonic-utilities/config/main.py` (L4140-4210)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-snmp.yang` (L167-201)

## 発見した失敗経路

### 1. key フォーマット不正 → テンプレートレンダリング失敗

`snmpd.conf.j2` L28 は `{% for (agentip, port, vrf) in SNMP_AGENT_ADDRESS_CONFIG %}` で
3 要素タプルをアンパックする。key が `<ip>|<port>|<vrf>` 形式でない場合
（例: `<ip>|<port>` の 2 要素）、sonic-cfggen がテンプレート展開中に ValueError を送出し
`/etc/snmp/snmpd.conf` が生成されない。`start.sh` が non-zero で終了するため
supervisord が snmpd を起動しない。

### 2. VRF 実在確認なし → サイレント bind 失敗

`vrf_name` に `mgmt` / `Vrf<name>` を設定しても VRF がカーネルに存在しない場合、
snmpd は起動後に該当 agentAddress のバインドに失敗する。YANG に VRF 実在チェックは
なく、CONFIG_DB 書き込みは成功するため検知されない。他 agentAddress でのリッスンは
継続する（部分的なサイレント失敗）。

### 3. systemctl restart snmp の戻り値を無視

CLI の `add_snmp_agent_address()` / `del_snmp_agent_address()` はともに
`os.system("systemctl restart snmp")` の戻り値をチェックしない（`config/main.py:4189,4209`）。
再起動に失敗した場合でも CLI はエラーを報告せず、snmpd.conf は更新されないまま
処理を終える（サイレント失敗）。

### 4. UNIQUE 制約違反 → YANG SET 拒否

`sonic-snmp.yang` L172 の `unique "agent_ip port"` 制約により、同一 `(ip, port)` を
異なる `vrf_name` で重複登録しようとすると YANG バリデーションが SET を拒否する。
CLI は `get_keys()` による事前チェックで YANG 層到達前に防ぐが、`sonic-db-cli` 直接
書き込みの場合は YANG エラーが返却される。

### 5. IP が NIC に付与されていない → CLI 拒否（サイレントでない）

CLI は `netifaces.interfaces()` で指定 IP が NIC に付与されているかを確認する
（`config/main.py:4160-4171`）。未付与の場合は "IP address is not available" を
出力して DB 書き込みを行わない。これは検知可能な失敗（エラーメッセージあり）。

## 可観測性

| 確認項目 | コマンド |
|---------|---------|
| snmpd.conf 生成内容確認 | `docker exec snmp cat /etc/snmp/snmpd.conf` |
| snmpd 起動ログ | `docker logs snmp 2>&1 \| grep -iE 'error\|fail'` |
| agentAddress バインド状態 | `docker exec snmp netstat -ulnp \| grep snmpd` |
| CONFIG_DB エントリ確認 | `sonic-db-cli CONFIG_DB keys 'SNMP_AGENT_ADDRESS_CONFIG|*'` |
