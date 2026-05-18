# SAG — Phase G pubsub 調査メモ

## 調査日

2026-05-18

## 調査対象

- HLD: `SONiC/doc/sag/sag-HLD.md` (sha=49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
- sonic-swss master: `cfgmgr/intfmgrd.cpp`, `cfgmgr/intfmgr.cpp`, `orchagent/intfsorch.cpp`
- sonic-swss-common: `common/schema.h` (sha=158de8d3463ff4b841653f6d57190bb142b80d9c)

## 結論

**sonic-swss master に SAG 専用実装コードは存在しない**。

`intfmgrd.cpp` の `cfg_intf_tables` ベクターに `CFG_SAG_TABLE_NAME` は含まれておらず、`intfmgr.cpp` / `intfsorch.cpp` にも SAG / SAG_TABLE への参照は一切ない。従って現行 master では `SAG|GLOBAL` を CONFIG_DB に書き込んでも intfmgrd は購読しない。

HLD §sonic-swss に "Intfs Orch and Intf Mgr will be updated to include a new handler for static anycast gateway configuration" と記載されており、実装は intfmgrd / IntfsOrch への統合として設計されているが、**master への実装は未マージ**。

schema.h には `CFG_SAG_TABLE_NAME = "SAG"` (line 393) と `APP_SAG_TABLE_NAME = "SAG_TABLE"` (line 127) の定数のみが存在する。

## HLD に記載された pubsub 設計（実装未確認）

HLD §High-Level Design / §DB に記載されたデータフローを以下に整理する。

### 1. CONFIG_DB → intfmgrd (SubscriberStateTable)

HLD 設計では IntfMgr が `CFG_SAG_TABLE_NAME`（`"SAG"`）を他の interface テーブルと同様に
`SubscriberStateTable` (CONFIG_DB, keyspace notification) で購読する想定。

```
PSUBSCRIBE __keyspace@4__:SAG|*
```

HSET により `SAG|GLOBAL gateway_mac <mac>` が書き込まれると Redis が
`PUBLISH __keyspace@4__:SAG|GLOBAL hset` を発行し、IntfMgr がキャッチして
`gateway_mac` を APPL_DB へ転送するハンドラを呼び出す。

### 2. intfmgrd → APPL_DB (ProducerStateTable)

HLD 設計では IntfMgr が `APP_SAG_TABLE_NAME`（`"SAG_TABLE"`）へ
`ProducerStateTable` 経由で書き込む想定。VLAN_INTERFACE テーブルの場合と同様に
Lua スクリプトアトミック実行で下記を行う（参考: `intfmgr.cpp` の INTF_TABLE 書込パターン）：

```
EVALSHA <luaSet>
  SADD SAG_TABLE_KEY_SET "GLOBAL"
  HSET _SAG_TABLE|GLOBAL gateway_mac <mac>
  PUBLISH SAG_TABLE_CHANNEL@0 "G"
```

### 3. APPL_DB → orchagent/IntfsOrch (ConsumerStateTable)

HLD 設計では orchagent の IntfsOrch が APPL_DB の `SAG_TABLE` を
`ConsumerStateTable` で購読し、対象 VLAN インターフェースの SAI RIF
`SAI_ROUTER_INTERFACE_ATTR_SRC_MAC_ADDRESS` を更新する。

## 実装状態の整理

| 項目 | 状態 |
|-----|------|
| `schema.h` 定数 (`CFG_SAG_TABLE_NAME`, `APP_SAG_TABLE_NAME`) | 存在（確認済み） |
| intfmgrd の CFG_SAG_TABLE_NAME 登録 | **未実装**（intfmgrd.cpp に不在） |
| IntfMgr の SAG ハンドラ | **未実装**（intfmgr.cpp に不在） |
| IntfsOrch の SAG_TABLE 購読 | **未実装**（intfsorch.cpp に不在） |
| HLD 記載の設計 | 存在（sag-HLD.md §sonic-swss, §DB） |

## 参考: 類似テーブルの pubsub パターン

VLAN_INTERFACE テーブルは同じ intfmgrd / IntfsOrch パイプラインで実装済みであり、
SAG はこれに Handler を追加する形で設計されている。VLAN_INTERFACE の pubsub 実装は
`docs/reference/config-db/vlan-interface.md` Phase G を参照。
