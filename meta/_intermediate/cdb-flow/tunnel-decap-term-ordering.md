# TUNNEL_DECAP_TERM_TABLE — Phase B 処理順・依存順調査

調査日: 2026-05-17
対象ファイル:
- `sonic-swss/orchagent/tunneldecaporch.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/cfgmgr/tunnelmgr.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)

---

## 前提条件 (doTask ゲート)

`tunneldecaporch` の `doTask()` (L51-79) は最初に `gPortsOrch->allPortsReady()` を確認する。
ポートが未初期化の場合は即座にリターンし、`TUNNEL_DECAP_TERM_TABLE` イベントを処理しない。

## 処理分岐

`doTask()` 内でテーブル名を確認し、`APP_TUNNEL_DECAP_TERM_TABLE_NAME` の場合は `doDecapTunnelTermTask()` (L338-551) へ委譲する。

## 親トンネルとの依存順

`doDecapTunnelTermTask()` (L392) では `tunnelTable.find(tunnel_name)` で親トンネル (TUNNEL_DECAP_TABLE) の存在を確認する。

- **tunnel_exists == true**: `addDecapTunnelTermEntry()` を即座に呼び出して SAI に反映する (L513)
- **tunnel_exists == false**: `addUnhandledDecapTunnelTerm()` でキュー (`unhandledDecapTerms`) に登録する (L521)

これにより APPL_DB の書き込み順序は問わない設計になっている。`TUNNEL_DECAP_TABLE` エントリが後から来ても、`addDecapTunnel()` 成功後に `processUnhandledDecapTunnelTerms()` (L309, L1497-1519) が保留済みの term エントリを一括処理する。

## subnet decap term の追加制約

subnet decap tunnel (`subnetDecapConfig.tunnel` / `subnetDecapConfig.tunnel_v6`) に属する term は、`subnetDecapConfig.enable == true` かつ対応する `src_ip` / `src_ip_v6` が設定済みでなければ処理されない (L472-508)。
`SUBNET_DECAP` の `doSubnetDecapTask()` が先に呼ばれて設定を反映していることが必要である。

## warm-start 時の順序保証

`tunnelmgrd` は warm-start 時、既存の CONFIG_DB TUNNEL キーを `m_tunnelReplay` に登録し、処理済みになるまで `finalizeWarmReboot()` を遅延させる (tunnelmgr.cpp L133-146)。
orchagent 側は既存の APPL_DB エントリを `allPortsReady()` 後に再消費する通常フローで対応する。

## 処理完了後の STATE_DB 書き込み

`addDecapTunnelTermEntry()` 成功後、`setDecapTunnelTermStatus()` (L1539) が呼ばれて STATE_DB へミラーされる。
STATE_DB 書き込みは SAI 呼び出しの *後* に行われる。

## 削除順序

DEL_COMMAND (L525-542) では:
1. `tunnel_exists` を確認
2. `removeDecapTunnelTermEntry()` で SAI エントリを削除
3. `RemoveTunnelIfNotReferenced()` で参照カウントが 0 になった場合に親トンネルも削除

親トンネルの削除より先に term エントリを削除する必要がある。逆順では参照カウント不整合になる。
