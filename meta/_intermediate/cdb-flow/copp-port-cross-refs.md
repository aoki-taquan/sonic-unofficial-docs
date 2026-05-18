# COPP_GROUP genetlink — Phase C: 暗黙参照テーブル分析 (cross-refs)

中間ファイル。最終成果は `docs/reference/config-db/copp-port.md` の `<!-- cross-refs -->` ブロックに反映済み。

## 分析対象ソース

- `sonic-swss/orchagent/copporch.cpp` (`createGenetlinkHostIf` L657-714, `createGenetlinkHostIfTable` L419-493, `processCoppRule` L844-855, `initDefaultHostIntfTable` L302-330, コンストラクタ L209-211)
- `sonic-swss/cfgmgr/coppmgr.cpp` (`isTrapIdDisabled` L173-191, `doFeatureTask` L928-965, `doCoppGroupTask` L898-921)
- `sonic-buildimage/files/image_config/copp/copp_cfg.j2` (L76-88: queue2_group1 genetlink フィールド)

## 主要依存関係

1. `FEATURE|sflow` → `sample_packet` trap の APPL_DB 登録状態（genetlink HostIf は残るが trap が届かない）
2. `m_syncdTrapIds` 内部マップ → genetlink HostIfTable の TRAP_ID OID 解決
3. `m_trap_group_hostif_map` 内部マップ → genetlink HostIfTable の HOST_IF OID 解決
4. `copp_cfg.j2` → queue2_group1 の genetlink_name / genetlink_mcgrp_name 初期値
5. `initDefaultHostIntfTable()` wildcard エントリ → genetlink 未登録 trap の fallback 保証
