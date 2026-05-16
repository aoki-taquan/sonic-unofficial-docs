# PBH — Phase H プラットフォーム差異 中間ファイル

生成日: 2026-05-16 (q67-f-phaseH-pbh-rule)
対象ドキュメント: `docs/reference/config-db/pbh.md`
ソース: `sonic-swss/orchagent/pbh/pbhcap.cpp`, `pbhcap.h`, `pbhorch.cpp`

## 調査サマリ

### ASIC ベンダー検出

- 環境変数: `ASIC_VENDOR` (`pbhcap.cpp:20`)
- 有効値: `"mellanox"` → `PbhMellanoxFieldCapabilities`、それ以外 → `PbhGenericFieldCapabilities`
- 未設定時: `SWSS_LOG_WARN` + GENERIC fallback (`pbhcap.cpp:297`)
- 結果は `STATE_DB:PBH_CAPABILITIES_TABLE` へ書き込まれる

### capability 差分 (pbhcap.cpp:107-141)

#### Generic

```
table.interface_list = {UPDATE}
table.description    = {UPDATE}
rule.priority        = {UPDATE}
rule.gre_key         = {ADD, UPDATE, REMOVE}  ← setPbhDefaults
rule.ether_type      = {ADD, UPDATE, REMOVE}
rule.ip_protocol     = {ADD, UPDATE, REMOVE}
rule.ipv6_next_header= {ADD, UPDATE, REMOVE}
rule.l4_dst_port     = {ADD, UPDATE, REMOVE}
rule.inner_ether_type= {ADD, UPDATE, REMOVE}
rule.hash            = {UPDATE}
rule.packet_action   = {ADD, UPDATE, REMOVE}
rule.flow_counter    = {ADD, UPDATE, REMOVE}
hash.hash_field_list = {UPDATE}
```

#### Mellanox

Generic と同一だが `hash.hash_field_list` の行が**存在しない** (空 set):

```
... (ruleフィールドは Generic と同一) ...
hash.hash_field_list = {}  ← 行なし → 空 set
```

`hashField` (hash_field, ip_mask, sequence_id) はいずれのベンダーも constructor で未設定 → 空 set。

### Mellanox W/A (pbhorch.cpp:838-863)

条件: `getAsicVendor() == PbhAsicVendor::MELLANOX` かつ update フィールドに `rule.hash.meta.name` または `rule.packet_action.meta.name` が含まれる。

処理:
1. `AclRulePbh* pbhRulePtr = dynamic_cast<AclRulePbh*>(aclOrch->getAclRule(...))`
2. `pbhRulePtr->disableAction()` — ACL entry の action attr を無効化
3. `aclOrch->updateAclRule(pbhRule)` — 通常の ACL rule 更新

Generic では手順 1-2 をスキップ。

### VOQ/chassis

`orchagent/pbh/` 全ファイルを grep: VOQ, chassis, SYSTEM_PORT の記述なし。
`PbhOrch` は `orchdaemon.cpp:565` で unconditionally 生成。VOQ 分岐なし。

### capability 確認コマンド

```bash
sonic-db-cli STATE_DB hgetall 'PBH_CAPABILITIES_TABLE|table'
sonic-db-cli STATE_DB hgetall 'PBH_CAPABILITIES_TABLE|rule'
sonic-db-cli STATE_DB hgetall 'PBH_CAPABILITIES_TABLE|hash'
sonic-db-cli STATE_DB hgetall 'PBH_CAPABILITIES_TABLE|hash-field'
```
