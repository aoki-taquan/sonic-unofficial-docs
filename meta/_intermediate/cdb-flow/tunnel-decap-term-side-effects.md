# TUNNEL_DECAP_TERM_TABLE — Phase F 副作用・連鎖変更調査

調査日: 2026-05-17
対象ファイル:
- `sonic-swss/orchagent/tunneldecaporch.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/tunneldecaporch.h` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)

---

## SET 時の副作用

### 1. SAI トンネル term エントリ作成
`addDecapTunnelTermEntry()` 内で `sai_tunnel_api->create_tunnel_term_table_entry()` を呼び出す (L979)。
ASIC_DB → syncd → ASICへの反映が連鎖する。

### 2. `tunnelTable[tunnel_name].ref_count` インクリメント
SET 成功後に `increaseTunnelRefCount(tunnel_name)` (L997, tunneldecaporch.h L157-160) が呼ばれ、親トンネルの参照カウントが +1 される。
参照カウントが 1 以上の間は親トンネルが DEL されても `RemoveTunnelIfNotReferenced()` により実際の SAI 削除が抑制される。

### 3. `tunnel.tunnel_term_info[dst_ip]` へのキャッシュ登録
`TunnelTermEntry` 構造体が `tunnel_term_info` マップに追加される (L990-996)。
この in-memory キャッシュが後続の DEL / 参照カウント管理に使われる。

### 4. STATE_DB への書き込み
`setDecapTunnelTermStatus()` (L1539-1561) が呼ばれ、`STATE_TUNNEL_DECAP_TERM_TABLE_NAME` テーブルのキー `<tunnel_name>|<dst_ip>` にフィールドを書き込む。
書き込まれるフィールド: `term_type`（常時）、`src_ip`（非空の場合）、`subnet_type`（非空の場合）。

## DEL 時の副作用

### 1. SAI トンネル term エントリ削除
`removeDecapTunnelTermEntry()` (L1248) で `sai_tunnel_api->remove_tunnel_term_table_entry()` を呼び出す。

### 2. `ref_count` デクリメント
`decreaseTunnelRefCount(tunnel_name)` (L1260, tunneldecaporch.h L161-163) で親トンネルの参照カウントが -1 される。

### 3. 親トンネルの自動削除（条件付き）
`RemoveTunnelIfNotReferenced()` (L531, L1569-1576) で `ref_count == 0` になった場合、`removeDecapTunnel()` を呼び出して親トンネル (`TUNNEL_DECAP_TABLE`) も ASIC_DB から自動削除する。
これは **意図的なカスケード削除** である。

### 4. STATE_DB エントリ削除
`removeDecapTunnelTermStatus()` (L1261, L1563-1567) で STATE_DB の対応エントリを削除する。

## unhandledDecapTerms キューへの副作用

tunnel_exists が false の場合 (L520-521)、`addUnhandledDecapTunnelTerm()` でキューに積まれる。
後に `TUNNEL_DECAP_TABLE` SET が成功すると `processUnhandledDecapTunnelTerms()` が呼ばれて連鎖的に TERM が処理される。
この連鎖処理も SAI 呼び出し・ref_count 更新・STATE_DB 書き込みを発生させる。

## subnet decap 更新時の副作用

`doSubnetDecapTask()` が `SUBNET_DECAP` の `src_ip` / `src_ip_v6` を更新した場合 (L661-690)、既存 unhandled term の `src_ip` フィールドを上書きする (`updateUnhandledDecapTunnelTermsSrcIp()`, L1483-1494)。
また、subnet decap が再有効化された場合は保留中の TERM を再処理する。
