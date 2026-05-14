# DASH_VNET フィールド暗黙デフォルト調査メモ

調査日: 2026-05-14
対象テーブル: CONFIG_DB `DASH_VNET`

## 調査対象ファイル

- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-dash.yang` — YANG スキーマ定義
- `sonic-swss/orchagent/dash/dashvnetorch.cpp` — DASH VNET orch ハンドラ
- `sonic-swss/orchagent/dash/dashvnetorch.h` — DASH VNET データ構造
- `sonic-swss/tests/dash/test_dash_vnet.py` — 統合テスト
- `sonic-utilities/dump/plugins/dash_vnet.py` — dump プラグイン

---

## テーブル概要

DASH VNET は DPU (Data Processing Unit) 上で動作する DASH (Disaggregated APIs for SONiC Hosts) 仮想ネットワーク定義。
CONFIG_DB の `DASH_VNET` テーブルがスキーマの起点。

key 構造: `DASH_VNET|<name>`

`<name>` は `Vnet[a-zA-Z0-9_-]+` パターン必須（YANG バリデーション）。

## フィールド別 暗黙デフォルト

### `vni`

**YANG**: `uint32 { range 1..16777215; }` — デフォルト宣言なし、必須に近いが YANG 上 mandatory 未指定

**コード挙動**: `addVnet()` (dashvnetorch.cpp:72-74) で直接 SAI 属性 `SAI_VNET_ATTR_VNI` に
`ctxt.metadata.vni()` を渡す。protobuf の `vni` フィールドが省略された場合、protobuf デフォルト値 `0` が
SAI に渡る。ただし YANG の range `1..16777215` バリデーションが通過前に弾く。

**実質デフォルト**: 省略不可（YANG range で `0` は弾かれる）。

```cpp
// dashvnetorch.cpp:72-74
sai_attribute_t dash_vnet_attr;
dash_vnet_attr.id = SAI_VNET_ATTR_VNI;
dash_vnet_attr.value.u32 = ctxt.metadata.vni();
```

### `guid`

**YANG**: `string { length 1..255; }` — デフォルト宣言なし、任意フィールド

**コード挙動**: `dashvnetorch.cpp` および `dashvnetorch.h` を全行精読したが、`guid` フィールドを
読み取るコードが存在しない。`VnetEntry` 構造体 (dashvnetorch.h:20-24) には `vni`・`metadata`・
`underlay_ips` しかなく、guid は格納されない。protobuf `Vnet` メッセージに存在するが
`addVnet()` / `addVnetPost()` どちらも参照しない。

**実質デフォルト**: orchagent が参照しない dead field。省略しても SAI 動作に影響なし。
APPL_DB `DASH_VNET_TABLE` 経由でテストデータ (appl_db.json) には protobuf バイナリのみ。

### `address_spaces`

**YANG**: `leaf-list stypes:sonic-ip-prefix; ordered-by user;` — デフォルト宣言なし、任意

**コード挙動**: `dashvnetorch.cpp` 全行において `address_spaces` を直接読み取る処理が確認できない。
YANG スキーマ上は IP prefix リストとして定義されているが、orch ハンドラは protobuf `Vnet` メッセージを
`parsePbMessage()` で解析し、`vni` のみを SAI へ送る。`address_spaces` の SAI への反映経路なし。

**実質デフォルト**: 空リスト `[]` — orchagent 未使用 (dead field)。設定しても SAI 動作に影響なし。

## orchagent の protobuf 解析フロー

```text
CONFIG_DB DASH_VNET → (sonic-db-cli) → APPL_DB DASH_VNET_TABLE → DashVnetOrch
  └─ parsePbMessage(kfvFieldsValues, Vnet metadata)  // dashvnetorch.cpp:204
       └─ metadata.vni() → SAI_VNET_ATTR_VNI         // dashvnetorch.cpp:74
```

YANG → CONFIG_DB への書き込みは `sonic-config-engine` 経由ではなく、テスト環境では
protobuf シリアライズ済みバイナリを直接 APPL_DB に投入する方式。
CONFIG_DB の `DASH_VNET` は YANG スキーマの検証層として機能し、orchagent は APPL_DB 側の
protobuf バイナリを消費する。

## appliance 依存性

`addVnet()` (dashvnetorch.cpp:64-68) は `DashOrch::hasApplianceEntry()` が `false` の場合、
`SWSS_LOG_INFO("Retry as no appliance table entry found")` を記録してリトライ待ちになる。
つまり `DASH_APPLIANCE` テーブルが先に存在しないと VNET エントリは SAI に反映されない。

## まとめ表

| フィールド | YANG default | コード実装デフォルト | 備考 |
|-----------|-------------|---------------------|------|
| `vni` | なし (range 1..16777215) | 省略不可 (YANG range で 0 弾き) | 唯一 SAI に送られるフィールド |
| `guid` | なし | orchagent 未参照 (dead field) | protobuf に存在するが orch は無視 |
| `address_spaces` | なし (空リスト) | orchagent 未参照 (dead field) | SAI への反映経路なし |
