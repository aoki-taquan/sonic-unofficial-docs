# ROUTE_REDISTRIBUTE side-effects 調査証跡

調査日: 2026-05-18  
調査対象: `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`、`sonic-swss/fpmsyncd/routesync.cpp`

## 主要 side-effects

### 1. FRR bgpd — redistribute コマンド受信による BGP 経路テーブル変化

`frrcfgd` が vtysh 経由で `router bgp <asn> vrf <vrf> / address-family <af> unicast / redistribute <src>` を送出すると、bgpd は対象ソースプロトコルの経路を BGP RIB に取り込む。

- zebra から既に受信済みの `src_proto` の経路が BGP best-path 計算の対象になる
- `route-map` フィールドが指定された場合は当該 route-map でフィルタリング / attribute 書き換えが行われる
- `metric` フィールドが指定された場合は BGP MED (Multi-Exit Discriminator) として付与される

evidence: `frrcfgd.py:3149-3168` (ROUTE_REDISTRIBUTE ハンドラ)、`frrcfgd.py:1979-1980` (route_redist_key_map)

### 2. FRR bgpd → BGP peers への UPDATE 送出

bgpd が redistribution で新規経路を BGP RIB に学習すると、確立済みの BGP ピアへ BGP UPDATE メッセージを送出する。

- IPv4 unicast / IPv6 unicast address-family それぞれのピアに対して NLRI 広告 / 撤回が発生する
- `no redistribute <src>` 実行時 (DEL) は対応する NLRI が WITHDRAW として送出される

evidence: FRR bgpd ソース参照（frrcfgd の管理外: FRR 内部動作）

### 3. FRR zebra — BGP ベストパス経路のカーネル routing table インストール

bgpd は best-path として選択した経路を FRR zebra inter-daemon プロトコルで通知する。zebra はカーネルの routing table (`ip route` / `ip -6 route`) に経路を追加 / 削除する。

- `redistribute connected` の場合は直接接続経路が BGP RIB に取り込まれるのみで、zebra がカーネルに追加する経路は別途 BGP best-path 選択結果に依存する
- `redistribute static` の場合は CONFIG_DB / APPL_DB の STATIC_ROUTE 経路が BGP 経由で広告され、受信側ピアが zebra 経由でカーネルに経路を追加する

evidence: FRR zebra 内部動作（frrcfgd 管理外）

### 4. fpmsyncd → APPL_DB ROUTE_TABLE 書き込み

zebra は FPM (Forwarding Plane Manager) プロトコルで経路変化を fpmsyncd に通知する。fpmsyncd は `ProducerStateTable` 経由で APPL_DB の `ROUTE_TABLE` に経路を書き込む。

```
zebra (FPM) → fpmsyncd → APPL_DB:ROUTE_TABLE (ProducerStateTable)
```

evidence: `sonic-swss/fpmsyncd/routesync.cpp:156` (m_routeTable = createProducerStateTable(APP_ROUTE_TABLE_NAME))、`routesync.cpp:1433` (Write route to ROUTE_TABLE)

### 5. orchagent → SAI/ASIC へのプログラミング

orchagent は APPL_DB `ROUTE_TABLE` を購読し、経路変化を SAI API 経由で ASIC にプログラムする。ROUTE_REDISTRIBUTE の変更は最終的にデータプレーンの FIB エントリ追加 / 削除につながる。

evidence: `sonic-swss/orchagent/routeorch.cpp` (orchagent ROUTE_TABLE 購読)

### 6. bgpcfgd の STATIC_ROUTE 自動 redistribute (特殊ケース)

`bgpcfgd` は `ROUTE_REDISTRIBUTE` を直接購読しない。代わりに STATIC_ROUTE テーブルを購読し、静的経路の追加時に `redistribute static route-map STATIC_ROUTE_FILTER` コマンドを自動生成する。

この自動生成コマンドは CONFIG_DB の `ROUTE_REDISTRIBUTE` エントリとは**独立して**発行される。

evidence: `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_static_rt.py:220-248` (enable_redistribution_command / disable_redistribution_command)

### 7. frrcfgd の SET 前 `no redistribute` 先行発行

`hdl_route_redist_set` は SET 操作前に必ず `no redistribute <src>` を先行発行する (`frrcfgd.py:1334-1336`)。これにより metric / route-map 変更時でも一時的な経路撤回が発生する。BGP ピアには WITHDRAW → UPDATE の順で NLRI 更新が届く。

evidence: `frrcfgd.py:1330-1341` (hdl_route_redist_set)

## 影響しないもの

- `frrcfgd` は CONFIG_DB 以外の DB (APPL_DB / STATE_DB / COUNTERS_DB) に一切書き込まない
- STATE_DB へのエラーステータス書き込みなし（ログ出力のみ）
- ROUTE_REDISTRIBUTE 変更は `ROUTE_MAP` テーブルには影響しない（route_map フィールドは leafref 参照のみ）
