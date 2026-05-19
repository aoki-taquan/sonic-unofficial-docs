# NEXTHOP_GROUP_TABLE / CLASS_BASED_NEXT_HOP_GROUP_TABLE — Phase D: 失敗挙動 調査ノート

生成日: 2026-05-19 (chore/q67-f-batch850)

## 調査対象

- `sonic-net/sonic-swss/orchagent/nhgorch.cpp` (全行)
- `sonic-net/sonic-swss/orchagent/cbf/cbfnhgorch.cpp` (全行)

## 根拠

既存中間ファイル `nhg-failure.md` および `cbf-nhg-failure.md` を参照し、
`nhg-table.md` への統合 Phase D ブロックとして整理した。

各ファイルの詳細データ:
- `meta/_intermediate/cdb-flow/nhg-failure.md` — NhgOrch 失敗挙動フル表
- `meta/_intermediate/cdb-flow/cbf-nhg-failure.md` — CbfNhgOrch 失敗挙動フル表

## 主要な知見

1. 起動ガード: 両 Orch が `gPortsOrch->allPortsReady()` == false の間は全エントリが無音 retry
2. フィールド不正系（nexthop/nexthop_group 混在、SRv6 数不一致、members 空/重複）はすべて即 erase で retry なし
3. リソース枯渇（NHG 数上限）は SRv6 と非 SRv6 で挙動が異なる（後者は temp NHG で継続）
4. DEL は ref_count > 0 の間は無制限保留
5. `syncMembers()` の bulk create は部分適用が発生しうる
