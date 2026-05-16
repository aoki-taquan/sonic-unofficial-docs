# COPP port-binding フィールド暗黙デフォルト調査メモ (Phase A)

調査日: 2026-05-15
対象: CONFIG_DB `COPP_GROUP` の `genetlink_name` / `genetlink_mcgrp_name` フィールド（port-binding 関連）

## 調査対象ファイル

- `sonic-swss/orchagent/copporch.cpp` (CoppOrch)
- `sonic-swss/orchagent/copporch.h` (定数定義)
- `sonic-buildimage/files/image_config/copp/copp_cfg.j2` (デフォルト設定)

---

## 概要

COPP port-binding とは、`COPP_GROUP` エントリの `genetlink_name` / `genetlink_mcgrp_name` フィールドを通じて、トラップグループをカーネル genetlink ホストインタフェース（例: psample）に束ねる機能を指す。sflow (sample_packet) などの非同期パケットサンプリング向けに使用される。

---

## フィールド別 暗黙デフォルト

### `genetlink_name`

**コード定数**: `"genetlink_name"` (copporch.h:45)

**YANG 定義**: なし（sonic-copp.yang に未定義。APPL_DB 経由での拡張フィールド扱い）

**コード由来デフォルト**: フィールドが CONFIG_DB に**存在しない**場合、`getAttribsFromTrapGroup()` は `genetlink_attribs` リストへ追加しない。
`genetlink_attribs.empty()` が true となり、`createGenetlinkHostIf()` は呼ばれない。
→ SAI HOSTIF は genetlink 型では作成されず、デフォルトの `NETDEV_PHYSICAL_PORT` チャネルが使用される。
<!-- evidence: copporch.cpp L833-844 -->

**値が存在する場合の動作**:
- `SAI_HOSTIF_ATTR_TYPE = SAI_HOSTIF_TYPE_GENETLINK` を genetlink_attribs に追加
- `SAI_HOSTIF_ATTR_NAME = <値>` を追加（最大 `sizeof(chardata)-1` バイト、末尾 NUL 保証）
- `sai_hostif_api->create_hostif()` を呼び出し genetlink ホストインタフェースを作成
<!-- evidence: copporch.cpp L1265-1276 -->

**実際のデフォルト値**: `copp_cfg.j2` では `queue2_group1` (sflow 用) のみに `"genetlink_name": "psample"` が設定される。他のグループにはフィールド自体が存在しない。
<!-- evidence: copp_cfg.j2 L76-88 -->

---

### `genetlink_mcgrp_name`

**コード定数**: `"genetlink_mcgrp_name"` (copporch.h:46)

**YANG 定義**: なし（sonic-copp.yang に未定義）

**コード由来デフォルト**: フィールドが CONFIG_DB に**存在しない**場合、`SAI_HOSTIF_ATTR_GENETLINK_MCGRP_NAME` は genetlink_attribs に追加されない。SAI 実装のデフォルト multicast group 名が適用される（通常は空文字列または実装依存）。
<!-- evidence: copporch.cpp L1279-1286 -->

**値が存在する場合の動作**:
- `SAI_HOSTIF_ATTR_GENETLINK_MCGRP_NAME = <値>` を genetlink_attribs に追加
- `create_hostif()` 呼び出し時に multicast group 名が SAI に渡される

**実際のデフォルト値**: `copp_cfg.j2` では `queue2_group1` のみに `"genetlink_mcgrp_name": "packets"` が設定される。
<!-- evidence: copp_cfg.j2 L79 -->

---

## 暗黙動作まとめ

| 条件 | 動作 | evidence |
|------|------|----------|
| `genetlink_name` フィールドなし | genetlink HostIf 未作成。SAI は NETDEV_PHYSICAL_PORT チャネルで動作 | copporch.cpp L833 |
| `genetlink_name` あり + `genetlink_mcgrp_name` あり | SAI HOSTIF_TYPE_GENETLINK を作成し、trap_id ごとに HOSTIF_TABLE_ENTRY (CHANNEL_TYPE_GENETLINK) を作成 | copporch.cpp L844-848, L419-466 |
| `genetlink_name` あり + `genetlink_mcgrp_name` なし | SAI HostIf を作成するが mcgrp_name は SAI 実装デフォルト（空/実装依存） | copporch.cpp L1279-1286 |
| `genetlink_name` なし + `genetlink_mcgrp_name` あり | 理論上不整合。`genetlink_attribs` は mcgrp_name のみ含み `SAI_HOSTIF_ATTR_TYPE` が未設定となる。SAI 実装次第で失敗する可能性あり | copporch.cpp L1265-1286 |

---

## DEL 後の挙動

`processCoppTrapGroup()` の `DEL_COMMAND` パスで `removeGenetlinkHostIf()` が呼ばれる。

```
removeGenetlinkHostIf(trap_group_name):
  1. getTrapIdsFromTrapGroup() で配下 trap_id 群を取得
  2. removeGenetlinkHostIfTable() で hostif_table_entry を削除
  3. m_trap_group_hostif_map から hostif を削除し sai_hostif_api->remove_hostif() 呼び出し
```
<!-- evidence: copporch.cpp L682-714 -->

DEL 後 init cfg に同名エントリが存在する場合、`coppmgr` は init 値で APPL_DB に再書き込みするため genetlink HostIf が再作成される。
<!-- evidence: coppmgr.cpp L898-921 -->

---

## 証拠リンク

- `copporch.h:45-46` — `copp_genetlink_name` / `copp_genetlink_mcgrp_name` 定数
- `copporch.cpp:1265-1286` — `getAttribsFromTrapGroup()` の genetlink 処理
- `copporch.cpp:657-679` — `createGenetlinkHostIf()`
- `copporch.cpp:419-466` — `createGenetlinkHostIfTable()`
- `copporch.cpp:682-714` — `removeGenetlinkHostIf()`
- `copporch.cpp:833-848` — `processCoppTrapGroup()` の genetlink 分岐
- `copp_cfg.j2:76-88` — `queue2_group1` の genetlink デフォルト設定
