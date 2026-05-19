# ipv6-link-local — Phase H platform 調査ノート

調査日: 2026-05-19
調査者: Claude (batch #6)

## 調査対象

- `sonic-swss/cfgmgr/intfmgr.cpp`
- `sonic-swss/cfgmgr/intfmgrd.cpp`
- `sonic-swss/neighsyncd/neighsync.cpp`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-interface.yang`

## 調査手法

以下のキーワードで全ソースファイルを grep:
```
multi_asic|is_multi_npu|chassis|asic[0-9]|namespace|platform|vendor|broadcom|mellanox|barefoot|cisco
```

結果: **全ファイルでヒット 0 件**（`using namespace std;` / `using namespace swss;` のみ）

## 結論

`ipv6_use_link_local_only` の処理は全プラットフォームで同一。SAI API 呼び出しなし、ASIC_DB 書込なし、platform guard なし。

## intfmgrd スコープ確認

`intfmgrd.cpp` はシングルインスタンス起動。multi-asic 構成でも per-asic インスタンスを持たない。
`INTERFACE` / `PORTCHANNEL_INTERFACE` / `VLAN_INTERFACE` は host namespace CONFIG_DB のみ。

## neighsync プラットフォーム独立性確認

`neighsync.cpp:193-243` の `isLinkLocalEnabled()` はプレフィクス文字列比較と CONFIG_DB Table::get のみ。
platform 定数・vendor フラグ・capability クエリ参照なし。

## 残留差異

インターフェース名プレフィクス (`Ethernet` / `PortChannel` / `Vlan`) による振り分けは命名規則依存。
`dpu0` 等の新 DPU インターフェースは未サポート（Phase D #5 で既述）。
これはプラットフォーム差分ではなく未サポートインターフェース種別の問題。
