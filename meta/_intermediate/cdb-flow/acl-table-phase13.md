# acl-table Phase 13 中間ファイル (Directory-sibling exhaustive scan)

## スキャン対象 enum フィールド (tier_mid)

ACL_TABLE と ACL_RULE は同じ YANG ファイル (sonic-acl.yang) を共有。type/stage/PACKET_ACTION/IP_TYPE/ETHER_TYPE は acl-rule.md と同一コードパスから引用。

| フィールド | 値数 | grep hit 総数 | 引用済み数 | 未引用 sibling |
|---|---|---|---|---|
| `type` (4 YANG / 14+ 実装) | 14+ | 全実装値 hit | acltable.h, aclorch.cpp | 0 |
| `stage` (INGRESS/EGRESS) | 2 | 全値 hit | aclorch.cpp | 0 |
| `ETHER_TYPE` / `IP_TYPE` / `PACKET_ACTION` | N/A (非フィールド) | — | — | 0 |

## ディレクトリ別 sibling スキャン結果

### `orchagent/` (sonic-swss)

acltable.h / aclorch.cpp が ACL_TABLE type を定義・処理。minigraph.py の type/stage 自動派生は Phase 6 で既引用。  
**sibling の orchdaemon.cpp**: AclOrch 登録は無条件 (`orchdaemon.cpp:533,569`) — Phase 7 で既引用。  
**sibling の mirrororch.cpp**: MIRROR/MIRRORV6 type 時に MirrorOrch が ACL entry にミラーセッション OID を設定するが、type enum の分岐自体は aclorch.cpp に集約。

### `files/build_templates/` (sonic-buildimage)

`init_cfg.json.j2` に ACL_TABLE の直接 type/stage 設定なし (FEATURE の type/stage 分岐のみ)。

## 追加 row 数

**0 行** — acl-table.md は現状で全 hit を網羅。
