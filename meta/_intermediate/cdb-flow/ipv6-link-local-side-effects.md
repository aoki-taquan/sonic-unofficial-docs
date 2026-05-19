# ipv6-link-local — Phase F side-effects 調査メモ

## 調査日
2026-05-19

## 調査対象ソース
- `sonic-net/sonic-swss/cfgmgr/intfmgr.cpp` (HEAD)
- `sonic-net/sonic-swss/neighsyncd/neighsync.cpp` (HEAD)

## 概要

`ipv6_use_link_local_only` フィールドへの書込みが起点となる副次的 DB 書込みを調査した。

## 主要な副次書込み

### 1. APP_DB `INTF_TABLE` への転送

`intfmgrd` が CONFIG_DB の SET イベントを受信すると `m_appIntfTableProducer.set(alias, data)` を呼び出し、フィールドを APP_DB `INTF_TABLE|<alias>` に転送する。
- evidence: `intfmgr.cpp:926,1053`
- `enable` / `disable` 両値が転送される

### 2. APP_DB `NEIGH_TABLE` からの link-local エントリ削除

`disable` イベント時（または DEL_COMMAND 時）に `delIpv6LinkLocalNeigh(alias)` が呼ばれ、APP_DB `NEIGH_TABLE` で `<alias>:FE80::*` にマッチする link-local エントリを `ip neigh del` コマンド経由で削除する。
- evidence: `intfmgr.cpp:712-740, 923, 1084`
- 削除対象: `IpAddress::AddrScope::LINK_SCOPE`（FE80::/10）の近傍エントリのみ

### 3. APP_DB `NEIGH_TABLE` への link-local 近傍追加（neighsyncd 経由）

`enable` 設定後、Linux カーネルの NDP が link-local 近傍を学習すると `neighsyncd` が netlink イベントを受信し `isLinkLocalEnabled()` で CONFIG_DB をチェックして `true` ならば `m_neighTable.set(key, fvVector)` で APP_DB に書き込む。
- evidence: `neighsync.cpp:96-100, 188`
- `enable` の場合のみ書込み。`disable` または CONFIG_DB 不在ならば NEIGH ADD を無視

### 4. STATE_DB `INTERFACE_TABLE` の `vrf` フィールド更新

`doIntfGeneralTask()` の最後で `m_stateIntfTable.hset(alias, "vrf", vrf_name)` を呼ぶ。これは `ipv6_use_link_local_only` 変更時にも同一トランザクション内で実行される副次書込み。
- evidence: `intfmgr.cpp:1054`
- ipv6_use_link_local_only フィールドに限定されず、インターフェース属性ロウ処理全体で発生

## 副次書込みなし

- orchagent IntfsOrch は APP_DB `INTF_TABLE` を購読するが `ipv6_use_link_local_only` を SAI に転送しない（dead consumer）
- STATE_DB への ipv6_use_link_local_only 専用フィールドは存在しない
- CONFIG_DB への逆書きはなし
