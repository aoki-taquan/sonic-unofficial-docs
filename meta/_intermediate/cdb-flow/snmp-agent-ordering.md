# SNMP_AGENT_ADDRESS_CONFIG — Phase B 書込み順依存調査メモ

対象テーブル: `SNMP_AGENT_ADDRESS_CONFIG`
調査日: 2026-05-15

## 調査対象ファイル

| ファイル | 役割 |
|---------|------|
| `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-snmp.yang` | YANG スキーマ — `SNMP_AGENT_ADDRESS_CONFIG_LIST` の key / unique 制約定義 |
| `sonic-utilities/config/main.py` | CLI `config snmp agentaddress add` — MGMT_VRF_CONFIG の mgmtVrfEnabled を事前確認してから SET |
| `sonic-buildimage/src/sonic-config-engine/minigraph.py` | minigraph 経路 — MGMT_VRF_CONFIG / MGMT_INTERFACE / LOOPBACK_INTERFACE を先行生成後に SNMP_AGENT_ADDRESS_CONFIG を書込み |
| `sonic-buildimage/dockers/docker-snmp/snmpd.conf.j2` | snmpd.conf 生成テンプレート — docker-snmp コンテナ起動時に CONFIG_DB から全エントリを読み込む |

---

## 1. YANG unique 制約による同一 (ip, port) 重複禁止

`sonic-snmp.yang` L171:

```yang
list SNMP_AGENT_ADDRESS_CONFIG_LIST {
    key "agent_ip port vrf_name";
    unique "agent_ip port";
    ...
}
```

`unique "agent_ip port"` により、同一 `(agent_ip, port)` の組み合わせを異なる `vrf_name` で重複登録することは YANG バリデーション層でリジェクトされる。

**順序依存**:
- 既存エントリと同一 `(ip, port)` を持つ新エントリを SET しようとすると、YANG unique 制約違反で拒否される。
- 変更する場合の正しい順序: 既存の `SNMP_AGENT_ADDRESS_CONFIG|<ip>|<port>|<vrf_old>` を DEL → 新エントリ `SNMP_AGENT_ADDRESS_CONFIG|<ip>|<port>|<vrf_new>` を SET。
- CLI (`config snmp agentaddress add`) はこの重複チェックを事前に `get_keys` で確認して早期リターンするため、YANG レベルに到達する前に防がれる（`config/main.py:4177-4182`）。

---

## 2. MGMT_VRF_CONFIG との順序依存（CLI 経路）

`config/main.py` L4153-4157:

```python
if not vrf:
    entry = config_db.get_entry('MGMT_VRF_CONFIG', "vrf_global")
    if entry and entry['mgmtVrfEnabled'] == 'true' :
        click.echo("ManagementVRF is Enabled. Provide vrf.")
        return False
```

`vrf` 引数なしで `config snmp agentaddress add <ip>` を実行した場合、CLI が `MGMT_VRF_CONFIG|vrf_global.mgmtVrfEnabled` を参照する。Management VRF が有効化されているにもかかわらず VRF 指定を省略すると、CLI がエラーを返し CONFIG_DB への書込みをブロックする。

**順序依存**:
- `MGMT_VRF_CONFIG|vrf_global.mgmtVrfEnabled = 'true'` が先行して SET されている状態で、`-v mgmt` 等の VRF 指定なしに agentaddress を追加しようとすると CLI レベルで拒否される。
- 正しい順序: Management VRF を有効化する場合は、`-v mgmt` を明示して `config snmp agentaddress add <ip> -v mgmt` を実行する。

---

## 3. minigraph 経路: MGMT_INTERFACE / LOOPBACK_INTERFACE 先行書込み

`minigraph.py` L2308-2322:

```python
results['MGMT_VRF_CONFIG'] = mvrf  # L2308

# Update SNMP_AGENT_ADDRESS_CONFIG with Management IP and Loopback IP
if not is_multi_asic() and asic_name is None:
    results['SNMP_AGENT_ADDRESS_CONFIG'] = {}
    port = '161'
    for intf in list(mgmt_intf.keys()) + list(lo_intfs.keys()):  # L2315
        ip_addr = ipaddress.ip_address(UNICODE_TYPE(intf[1].split('/')[0]))
        ...
        snmp_key = agent_addr + '|' + port + '|'
        results['SNMP_AGENT_ADDRESS_CONFIG'][snmp_key] = {}
```

minigraph.py は `MGMT_VRF_CONFIG` を先行して `results` に格納した後、`mgmt_intf`（MGMT_INTERFACE）と `lo_intfs`（LOOPBACK_INTERFACE）のアドレスを列挙して `SNMP_AGENT_ADDRESS_CONFIG` エントリを生成する。これらのアドレス情報が未解決の場合は `SNMP_AGENT_ADDRESS_CONFIG` が空辞書になる（L2324: multi-asic の場合）。

**順序依存**:
- `sonic-cfggen` が minigraph から CONFIG_DB を一括構築する場合は自動的に正しい順序が保証される（`MGMT_INTERFACE` / `LOOPBACK_INTERFACE` → `SNMP_AGENT_ADDRESS_CONFIG`）。
- 手動で `SNMP_AGENT_ADDRESS_CONFIG` に listen IP を追加する場合、その IP が実際に NIC に付与されていることを CLI が `netifaces.interfaces()` で確認する（`config/main.py:4160-4171`）。IP が付与されていない場合は "IP address is not available" で拒否される。

---

## 4. docker-snmp コンテナ起動タイミングとの依存

`snmpd.conf.j2` L27-34:

```jinja2
{% if SNMP_AGENT_ADDRESS_CONFIG %}
{% for (agentip, port, vrf) in SNMP_AGENT_ADDRESS_CONFIG %}
agentAddress {{ protocol(agentip) }}:[{{ agentip }}]{% if vrf %}@{{ vrf }}{% endif %}{% if port %}:{{ port }}{% endif %}
{% endfor %}
{% else %}
agentAddress udp:161
agentAddress udp6:161
{% endif %}
```

snmpd.conf は `docker-snmp` コンテナ起動時に `sonic-config-engine` が CONFIG_DB を読み込んでテンプレートレンダリングする。テーブルへの変更はコンテナ再起動または snmpd プロセスリロードまで反映されない。

**順序依存**:
- `SNMP_AGENT_ADDRESS_CONFIG` エントリを SET した後、`systemctl restart snmp`（または CLI が自動実行するコマンド）でコンテナを再起動しなければ snmpd は旧 agentAddress で動作し続ける。
- エントリが 0 件のまま docker-snmp が起動すると、テンプレートのデフォルト (`agentAddress udp:161` / `agentAddress udp6:161`) が使用される。
- エントリ追加後、コンテナ再起動前の短期間は旧設定で listen 継続（既存 SNMP セッションは切断されない）。

---

## 5. VRF が実在しない場合の経路依存乖離

`vrf_name` フィールドに `mgmt` や `Vrf<name>` を指定しても、その VRF がカーネル上に実際に存在しない場合、snmpd は agentAddress バインドに失敗する。CONFIG_DB レベルおよび YANG バリデーションは VRF の実在チェックを行わない。

**順序依存**:
- Management VRF を使う場合: `config vrf add mgmt`（および MGMT_VRF_CONFIG の有効化）→ `config snmp agentaddress add <ip> -v mgmt` の順。VRF 作成前に agentaddress を設定しても CONFIG_DB への書込みは成功するが、snmpd が bind に失敗する。
- データ VRF (`Vrf<name>`) を使う場合: `config vrf add Vrf<name>` → `config snmp agentaddress add <ip> -v Vrf<name>` の順。

---

## 6. 書込み順序依存サマリ

| # | 依存関係 | 方向 | 違反時の挙動 |
|---|----------|------|------------|
| 1 | 旧 `SNMP_AGENT_ADDRESS_CONFIG\|<ip>\|<port>\|<vrf_old>` DEL → 新 `\|<ip>\|<port>\|<vrf_new>` SET | **必須先行** | YANG unique 制約違反（SET 失敗）/ CLI が早期リターン |
| 2 | `MGMT_VRF_CONFIG\|vrf_global.mgmtVrfEnabled=true` 状態で `-v mgmt` 指定が必要 | **CLI 強制** | vrf 指定なしは CLI がブロック（DB 書込み不達） |
| 3 | NIC への IP 付与 先行 → `config snmp agentaddress add <ip>` | **CLI 強制** | "IP address is not available" で拒否 |
| 4 | VRF 作成（`config vrf add`）先行 → `config snmp agentaddress add <ip> -v <vrf>` | **推奨先行** | DB 書込み成功、snmpd が bind 失敗 |
| 5 | `SNMP_AGENT_ADDRESS_CONFIG` SET 完了 → `systemctl restart snmp` | **必須後続** | snmpd.conf 未更新（旧設定継続） |
| 6 | `MGMT_INTERFACE`/`LOOPBACK_INTERFACE` 先行 → minigraph 自動生成 | **minigraph 内部** | 空辞書（multi-asic では常時空） |
