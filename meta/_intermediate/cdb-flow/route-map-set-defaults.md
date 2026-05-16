# ROUTE_MAP_SET defaults — Phase A 調査メモ

## 調査対象

`docs/reference/config-db/route-map-set.md` (新規作成)

## 参照ソース

- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-route-map.yang` L125-134
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` 全行
- `sonic-buildimage/src/sonic-yang-models/tests/yang_model_tests/tests_config/bgp.json` L995-1104 (テスト例)
- `sonic-utilities/scripts/db_migrator.py` (参照なし確認)

## YANG 定義の要点

```yang
container ROUTE_MAP_SET {
    list ROUTE_MAP_SET_LIST {
        key "name";
        leaf name {
            type string;
            description "Route map name";
        }
    }
}
```

フィールドは `name` (key) のみ。データフィールドは一切存在しない。

## frrcfgd の扱い

- `ROUTE_MAP_SET` は `table_handler_list` に **含まれない**（L2293-2338 全確認）。
- `tbl_to_key_map` にも **含まれない**（L2106-2134）。
- frrcfgd は ROUTE_MAP_SET テーブルをイベント購読も初期化も行わない。
- FRR への直接コマンド発行なし。

## 用途

- YANG レベルの名前レジストリ（leafref integrity のため存在）。
- `ROUTE_MAP.call_route_map` が `ROUTE_MAP_SET.name` を leafref で参照。
- `BGP_NEIGHBOR_AF` / `BGP_PEER_GROUP_AF` / `BGP_GLOBALS_AF` 等の route-map 参照先も同じ leafref で参照。

## デフォルト分析

| フィールド | YANG default | コード実効デフォルト | パターン | 根拠 |
|-----------|-------------|-------------------|---------|------|
| `name` | なし（key、必須） | なし（必須キー） | — | YANG key; frrcfgd 非購読 |

### 暗黙デフォルト/落とし穴

1. **frrcfgd 非購読 → FRR 反映なし**: ROUTE_MAP_SET を書き込んでも frrcfgd はイベントを受けない。FRR への反映は ROUTE_MAP テーブル (`ROUTE_MAP|<name>|<seq>`) の書き込みによって行われる。ROUTE_MAP_SET は YANG データモデル上の名前空間のみ。
2. **name のみテーブル**: データフィールドが存在しないため、デフォルト値の概念自体が該当しない。
3. **ROUTE_MAP_SET エントリが存在しない場合の YANG 検証失敗**: YANG strict mode (netconf/gNMI) では ROUTE_MAP.call_route_map が ROUTE_MAP_SET に存在しない名前を参照するとリジェクトされる。CONFIG_DB への sonic-db-cli 直接書き込みは YANG 検証をバイパスするため、この制約は発生しない。

## 購読者サマリ

なし（YANG レベル定義のみ、frrcfgd/bgpcfgd/orch は非購読）。

## 書き込み経路

CONFIG_DB `config load` / `sonic-db-cli` による手動投入のみ。CLI・minigraph・db_migrator いずれも ROUTE_MAP_SET への書き込みなし（db_migrator.py grep 確認済み）。
