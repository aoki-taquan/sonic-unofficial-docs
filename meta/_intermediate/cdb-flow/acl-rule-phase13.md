# acl-rule Phase 13 中間ファイル (Directory-sibling exhaustive scan)

## スキャン対象 enum フィールド (tier_mid)

| フィールド | 値数 | grep hit 総数 | 引用済み数 | 未引用 sibling |
|---|---|---|---|---|
| `PACKET_ACTION` (`FORWARD`/`DROP`/`REDIRECT`) | 3 YANG / 6 実装 | 全値 hit | aclorch.h, aclorch.cpp | 0 |
| `IP_TYPE` (7 YANG / 10 実装) | 10 | 全値 hit | aclorch.h, aclorch.cpp | 0 |
| `ETHER_TYPE` (7 YANG) | 7 | 全値 hit | sonic-acl.yang, aclorch.cpp | 0 |
| `stage` (INGRESS/EGRESS) | 2 | 全値 hit | aclorch.cpp | 0 |
| `type` (4 YANG) | 4 | 全値 hit | acltable.h, aclorch.cpp | 0 |

## ディレクトリ別 sibling スキャン結果

### `orchagent/` (sonic-swss)

**引用済み**: aclorch.cpp, aclorch.h, acltable.h  
**sibling ファイルスキャン**: `aclorch.cpp` が aclorch.h を include し、主要 ACL ロジックは既引用の 2 ファイルに集約。`mirrororch.cpp`、`copporch.cpp` は ACL_TABLE type による間接影響を受けるが、PACKET_ACTION/IP_TYPE の直接的な enum 分岐なし。

### `files/image_config/copp/` (sonic-buildimage)

PACKET_ACTION (`DROP`/`FORWARD`) の直接 grep hit: **0** — copp_cfg.j2 は COPP_TABLE.trap_action に独自フィールドを使用 (ACL_RULE.PACKET_ACTION と別テーブル)。

### `src/sonic-config-engine/` (minigraph.py 含む)

ACL_TABLE.stage/type の minigraph.py 派生 (`InAcl`→ingress, `OutAcl`→egress, `erspan*`→MIRROR) は Phase 6/7 で既引用。sibling の `sonic-cfggen`, `config_samples.py` に ACL_RULE 固有の enum 分岐なし。

## 追加 row 数

**0 行** — acl-rule.md は現状で全 hit を網羅。同 dir sibling から新規未引用 evidence なし。
