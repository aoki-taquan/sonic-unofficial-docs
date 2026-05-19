# subnet-decap — Phase D (failure-behavior) スキャンノート

## ソース

- `sonic-net/sonic-swss` `orchagent/tunneldecaporch.cpp` HEAD
- `sonic-net/sonic-swss` `orchagent/tunneldecaporch.h` HEAD

## 調査対象ハンドラ

`TunnelDecapOrch::doSubnetDecapTask()` (L566-703) が `CFG_SUBNET_DECAP_TABLE_NAME` を消費する。
`TunnelDecapOrch::doDecapTunnelTermTask()` (L336-563) が `APP_TUNNEL_DECAP_TERM_TABLE_NAME` を消費し、
`IPINIP_SUBNET` / `IPINIP_SUBNET_V6` トンネルの decap term 処理でも失敗パスが発生する。

## SUBNET_DECAP テーブル処理 (`doSubnetDecapTask`) の失敗パス

### フィールドバリデーション失敗

`doSubnetDecapTask()` は `valid = true` で開始し、バリデーション失敗時に `valid = false` をセットしてループを break する。
その後 `if (valid)` ブロックをスキップして `subnetDecapConfig` を更新しない。
**エラーログ出力後にエントリは `consumer.m_toSync.erase(it)` で破棄される — 再試行なし**。

| # | 失敗条件 | ログ | 再試行 | 影響 |
|---|---------|------|--------|------|
| 1 | `src_ip` が IPv4 プレフィックスとしてパース不能 | `SWSS_LOG_ERROR("Invalid source IP prefix %s.")` L593 | なし (erase) | `subnetDecapConfig` 更新されず |
| 2 | `src_ip` が IPv4 でない (IPv6 アドレスを `src_ip` に指定) | `SWSS_LOG_ERROR("Invalid source IP prefix %s.")` L599 | なし (erase) | 同上 |
| 3 | `src_ip_v6` が IPv6 プレフィックスとしてパース不能 | `SWSS_LOG_ERROR("Invalid source IPv6 prefix %s.")` L613 | なし (erase) | 同上 |
| 4 | `src_ip_v6` が IPv4 アドレス (isV4() == true) | `SWSS_LOG_ERROR("Invalid source IPv6 prefix %s.")` L619 | なし (erase) | 同上 |
| 5 | 未知フィールド名 | `SWSS_LOG_ERROR("unknown subnet decap table attribute '%s'.")` L630 | なし (erase) | 同上 |
| 6 | `src_ip` と `src_ip_v6` の両方が空文字列 | `SWSS_LOG_ERROR("Both src_ip and src_ip_v6 of subnet decap are not set.")` L638 | なし (erase) | 同上 |

### DEL コマンド処理

`op == DEL_COMMAND` の場合、バリデーションなしで `subnetDecapConfig.enable = false` をセットし、
既存の decap term は無効化 (APP_DB への変更なし) される。SAI への影響は RouteOrch / VNetRouteOrch が
`gTunneldecapOrch->getSubnetDecapConfig().enable` を参照した際に発生。**DEL 失敗はない**。

### 未知コマンド

`SET` / `DEL` 以外のコマンドは `SWSS_LOG_ERROR("Unknown operation type %s.")` L697 を出力して
処理をスキップし `erase` される。再試行なし。

## TUNNEL_DECAP_TERM_TABLE 処理 (subnet decap 関連) の失敗パス

`IPINIP_SUBNET` / `IPINIP_SUBNET_V6` トンネルに対する term 処理で以下の失敗が発生する。

| # | 失敗条件 | ログ | 再試行 | 影響 |
|---|---------|------|--------|------|
| 7 | subnet decap term が MP2MP 型以外 | `SWSS_LOG_ERROR("%s: only MP2MP tunnel decap term is allowed for subnet decap tunnel.")` L448 | なし (erase) | SAI 未作成 |
| 8 | `is_subnet_decap_term` でないのに MP2MP かつ `src_ip` なし | `SWSS_LOG_ERROR("%s: no source IP is provided.")` L458 / L463 | なし (erase) | SAI 未作成 |
| 9 | subnet decap が disable 状態で term が来た | `SWSS_LOG_ERROR("%s: subnet decap is disabled, ignored.")` L506 | なし (erase) | SAI 未作成 |
| 10 | tunnel が存在しない (IPINIP_SUBNET 未作成) | `SWSS_LOG_NOTICE("%s: tunnel doesn't exist, added to unhandled list.")` L521 | 自動再試行あり (`unhandledDecapTerms` に積む) | SAI 未作成、tunnel 作成後に `processUnhandledDecapTunnelTerms()` が再処理 |
| 11 | `addDecapTunnelTermEntry()` → SAI `create_tunnel_term_table_entry()` 失敗 | `SWSS_LOG_ERROR("%s: failed to add tunnel decap term to ASIC_DB.")` L515 | なし (erase) | SAI 未作成 |
| 12 | `src_ip` が設定されていない状態で subnet decap term を処理 | `SWSS_LOG_ERROR("%s: source IP is not configured for subnet decap term, ignored.")` L484 | `unhandledDecapTerms` に積む (SUBNET_DECAP SET 受信後に `updateUnhandledDecapTunnelTerms` が更新) | SAI 未作成、src_ip 設定後に自動解消 |

## `unhandledDecapTerms` キューの挙動

tunnel が存在しない場合 (`#10`) の term は `unhandledDecapTerms[tunnel_name][key] = term` に積まれる。
`TunnelDecapOrch::processUnhandledDecapTunnelTerms()` (L1499-L1521) が
tunnel の `addDecapTunnel()` 成功直後 (L309: `processUnhandledDecapTunnelTerms(key)`) に呼ばれ、
積み残し term を `addDecapTunnelTermEntry()` で再処理する。
SAI 作成に成功したエントリは `unhandledDecapTerms` から削除され、失敗したエントリは残留する。

`src_ip` が空の場合 (`#12`) は `unhandledDecapTerms` に積まれ、
`SUBNET_DECAP` の `src_ip` フィールドが SET された際に
`updateUnhandledDecapTunnelTerms()` (L1474-L1493) が src_ip を埋め直し、
その後 `processUnhandledDecapTunnelTerms()` がない限り **SAI へは反映されない** 点に注意。

## `doSubnetDecapTask` での `src_ip` 変更時の SAI 更新失敗パス

`src_ip` が変わった場合 (`subnetDecapConfig.src_ip != src_ip_str` L655) かつ `enable == true` の場合に
`setIpAttribute(subnetDecapConfig.tunnel, src_ip_str)` (L660) が呼ばれ、既存 SAI tunnel term の
`SAI_TUNNEL_TERM_TABLE_ENTRY_ATTR_SRC_IP` を `set_tunnel_term_table_entry_attribute()` で更新する。
この SAI 呼び出しが失敗しても `subnetDecapConfig.src_ip` は新しい値で上書きされる (L664)。
**SAI と CONFIG/APP_DB の不整合が残る可能性がある**。

## 結論

`SUBNET_DECAP` テーブルのバリデーション失敗はすべて「エラーログ + erase = 再試行なし」パターン。
唯一の自動回復経路は tunnel 未存在時の `unhandledDecapTerms` キューへの積み置きで、
tunnel が後で作成されると自動再処理される。src_ip 変更時の SAI 更新失敗は黙過される点に注意。
