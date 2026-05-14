# SNMP_AGENT_ADDRESS_CONFIG — Phase 6/7/8 derivation & handler-branching

対象ページ: `docs/reference/config-db/snmp-agent-address-config.md`
バッチ: cdb_batch_9

---

## Phase 6: 自動派生 (minigraph.py 代入)

<!-- derivation -->

### 1. `SNMP_AGENT_ADDRESS_CONFIG` の自動生成

**ソース**: `sonic-buildimage/src/sonic-config-engine/minigraph.py:2313-2324`

```python
results['SNMP_AGENT_ADDRESS_CONFIG'] = {}
...
for snmp_agent_address in snmp_agent_address_list:
    snmp_key = (snmp_agent_address, str(snmp_agent_port), snmp_vrf)
    results['SNMP_AGENT_ADDRESS_CONFIG'][snmp_key] = {}
```

- XML の `<SNMPAgentAddressList>` から SNMP エージェントバインドアドレスとポートを解析して代入。
- キーは `(ip_address, port, vrf)` のタプル形式。
- `snmp_vrf` はデフォルト `""` (空文字) だが、管理 VRF 使用時は `"mgmt"` が付与される。
- エントリの value は空辞書 `{}` — フィールドなしでキー存在のみが意味を持つ。

### 2. `include_snmp` ビルドフラグによる条件実行

- `include_snmp != "y"` のビルドイメージでは `snmp` Feature 自体がないため、このテーブルは populate されない（minigraph.py 内の条件ガード）。

<!-- /derivation -->

---

## Phase 7: 条件付き登録

<!-- derivation -->

### snmpd の listen address 動的登録

**ソース**: `sonic-buildimage/src/sonic-snmpagent/`（sonic-snmpagent）

- `snmpd` は `SNMP_AGENT_ADDRESS_CONFIG` テーブルの変化を `ConfigDBConnector.subscribe()` で監視する。
- エントリが存在する場合のみ `snmpd -Lo -f -I -smux,mteTrigger,mteTriggerConf -p /run/snmpd.pid agentaddress <ip>:<port>` を起動時に挿入。
- エントリが空の場合 `agentaddress udp:161` (デフォルト全インターフェース) にフォールバックする。

<!-- /derivation -->

---

## Phase 8: manager メソッド内 early return / dispatch

<!-- handler-branching -->

### sonic-snmpagent の agentAddressHandler() 分岐

1. **SET イベント**: バインドアドレスが `0.0.0.0` または `::` の場合 VRF フィールドを無視（グローバルバインド）。特定 IP の場合は VRF 名を `ip vrf exec <vrf> snmpd ...` の引数として付加。
2. **DEL イベント**: `snmpd` プロセスを SIGHUP で再起動してアドレスを解除。`restart_service()` 経由のため既存セッションは切断される（early return なし）。
3. **VRF 存在チェック early return**: 指定 VRF が `ip vrf list` に存在しない場合、エントリ処理をスキップしてエラーログを記録。

<!-- /handler-branching -->
