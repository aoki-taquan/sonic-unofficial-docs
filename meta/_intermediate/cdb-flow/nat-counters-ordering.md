# nat-counters — Phase B 書込み順依存 (intermediate)

slug: nat-counters
phase: B (ordering)
status: done

## 検出された主な依存

1. SAI NAT エントリ登録成功 → COUNTERS_NAT* 初期値 0 書込み (強制先行)
2. NAT_GLOBAL_TABLE.admin_mode=enabled → SAI 登録 → カウンタ初期化 (強制先行)
3. COUNTERS_GLOBAL_NAT|Values は起動時コンストラクタで 1 回のみ書込み
4. 5 秒タイマ → SAI ポーリング → 実値反映 (非同期)
5. admin_mode=disabled → deleteNatCounters() → カウンタエントリ削除

## evidence

- natorch.cpp:789 (updateNatCounters 0 初期化)
- natorch.cpp:1907-1913 (isNatEnabled チェック)
- natorch.cpp:2577-2582 (enableNatFeature → addAllNatEntries)
- natorch.cpp:128-130 (COUNTERS_GLOBAL_NAT コンストラクタ書込み)
- natorch.cpp:4486-4585 (エントリ数カウンタ更新)
