# TUNNEL_DECAP_TERM_TABLE — Phase B 書込み順依存調査

調査日: 2026-05-17
対象ファイル:
- `sonic-swss/orchagent/tunneldecaporch.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/cfgmgr/tunnelmgr.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)

---

## 全体 doTask ガード

`TunnelDecapOrch::doTask()` の先頭で `gPortsOrch->allPortsReady()` が false の場合は
TUNNEL_DECAP_TABLE・TUNNEL_DECAP_TERM_TABLE ともに即 return される (L55-57)。
ports 初期化完了前に届いたエントリはキューに留まり、初期化後に自動再処理される。

## TUNNEL_DECAP_TERM_TABLE SET の先行必須

| 依存 | 理由 | 緩和策 | evidence |
|---|---|---|---|
| PortsOrch 初期化完了 (`allPortsReady()`) | doTask() 先頭ガード — false なら TERM 処理もスキップ | なし（自動待機） | `tunneldecaporch.cpp` L55-57 |
| `TUNNEL_DECAP_TABLE:<tunnel_name>` SET 済み | `tunnel_exists` が false の場合 `addUnhandledDecapTunnelTerm()` に保留。トンネル本体作成成功後に `processUnhandledDecapTunnelTerms()` で一括再処理 | **前後逆でも自動調停** | `tunneldecaporch.cpp` L511-521 |
| subnet decap term の場合: `SUBNET_DECAP` で `enable=true` + `src_ip`/`src_ip_v6` 設定済み | `subnetDecapConfig.enable` が false だとエントリ消費してスキップ。`src_ip` 未設定でも消費 | なし — 先に SUBNET_DECAP を SET | `tunneldecaporch.cpp` L501-514 |

## SET / DEL の推奨順序

```
# SET 時
TUNNEL_DECAP_TABLE:<tunnel_name> SET   (先)
TUNNEL_DECAP_TERM_TABLE:<tunnel_name>:<dst_ip> SET

# DEL 時
TUNNEL_DECAP_TERM_TABLE:<tunnel_name>:<dst_ip> DEL  (先)
TUNNEL_DECAP_TABLE:<tunnel_name> DEL
```

TERM が先に届いた場合: `unhandledDecapTerms` キューに積まれ、
トンネル本体 SET 成功後の `processUnhandledDecapTunnelTerms()` で処理される (L309, L1497-1520)。
エラーログ `"tunnel doesn't exist, added to unhandled list."` が残る点を除き機能上の問題はない。

DEL 時: トンネル本体の `removeDecapTunnel()` は TERM を自動削除しない。
TERM を先に削除しないままトンネル本体を DEL すると SAI リソースリークの恐れがある。

## 変更時の制約

`TUNNEL_DECAP_TERM_TABLE` は更新 (SET on existing entry) を明示サポートしない。
orchagent 内部では `tunnel_exists && entry_exists` の場合に `addDecapTunnelTermEntry()` を再呼び出しするが、
重複エントリのハンドリングは SAI 実装依存。変更が必要な場合は DEL → SET が推奨される。

## ソース参照

- `tunneldecaporch.cpp` L55-57: allPortsReady ガード
- `tunneldecaporch.cpp` L392, L511-521: tunnel_exists チェックと unhandledDecapTerms 保留
- `tunneldecaporch.cpp` L309, L1497-1520: processUnhandledDecapTunnelTerms
- `tunneldecaporch.cpp` L525-541: DEL ハンドリング
