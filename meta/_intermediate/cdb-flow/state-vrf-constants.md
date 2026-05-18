# state-vrf Phase E — ハードコード定数調査

調査日: 2026-05-18
ソース: `sonic-net/sonic-swss cfgmgr/vrfmgr.cpp`

## vrfmgr.cpp — ルーティングテーブル ID 管理定数

```
#define VRF_TABLE_START   1001   // L12
#define VRF_TABLE_END     5097   // L13
#define TABLE_LOCAL_PREF  1001   // L14 — ip rule の local テーブル優先度 (after l3mdev-table)
#define MGMT_VRF_TABLE_ID 6000   // L15 — mgmt VRF の固定テーブル ID
#define MGMT_VRF          "mgmt" // L16 — mgmt VRF の固定名称文字列
```

### VRF_TABLE_START / VRF_TABLE_END

コンストラクタ (L28-30) で `VRF_TABLE_START` から `VRF_TABLE_END - 1` の範囲の整数を `m_freeTables` set に格納する。
最大割り当て可能数 = 5097 - 1001 = **4096 個**。

`getFreeTable()` (L114-125) が `m_freeTables` の先頭要素を取り出す。枯渇時は `0` を返し、
`setLink()` 内で `SWSS_LOG_ERROR("Not enough tables to create vrf netdev %s")` を出力して処理を継続する。

### TABLE_LOCAL_PREF

起動時 (L103-104) に `ip rule add pref 1001 table local && ip rule del pref 0` を実行する。
`local` テーブルを優先度 0 から 1001 に移動させることで、l3mdev-table がルックアップを先に処理できるようにする。
この定数は CONFIG_DB / YANG で変更不可。

### MGMT_VRF_TABLE_ID

mgmt VRF に対して固定値 `6000` のテーブル ID が割り当てられる (L180)。
通常の VRF (`VRF_TABLE_START`〜`VRF_TABLE_END-1`) とは別の名前空間にあり、`m_freeTables` 管理外。

### MGMT_VRF

`"mgmt"` は mgmt VRF を識別するための固定文字列。`CFG_MGMT_VRF_CONFIG_TABLE_NAME` で受信したエントリはこの名称を vrfName として使用する。

## STATE_DB テーブル名定数 (sonic-swss-common/common/schema.h)

| 定数名 | 値 | 定義箇所 |
|-------|----|---------|
| `STATE_VRF_TABLE_NAME` | `"VRF_TABLE"` | schema.h (VRF 系定数) |
| `STATE_VRF_OBJECT_TABLE_NAME` | `"VRF_OBJECT_TABLE"` | schema.h |

これらは `vrfmgr.cpp` のコンストラクタ引数として使用される。

## まとめ

- CONFIG_DB / YANG で管理されないハードコード定数は計 5 個（すべて vrfmgr.cpp 由来）
- 最大 VRF 数 4096 は `VRF_TABLE_END - VRF_TABLE_START = 5097 - 1001` から来る
- mgmt VRF は通常の ID 管理から外れた固定値 6000 を使用
- `TABLE_LOCAL_PREF` は Linux ルーティング規則の優先度制御に使用される（変更不可）
