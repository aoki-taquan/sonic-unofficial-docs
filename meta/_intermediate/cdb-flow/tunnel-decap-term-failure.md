# tunnel-decap-term — Phase D: 失敗挙動・リトライ・リカバリ

## 調査対象

- `sonic-swss/orchagent/tunneldecaporch.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
  - `doDecapTunnelTermTask()` L338-545
  - `addDecapTunnelTermEntry()` L886-1000
  - `removeDecapTunnelTermEntry()` L1131-1262

## SET 失敗経路

| 失敗条件 | 検出箇所 | ログメッセージ | 結果 | リトライ |
|---------|---------|--------------|------|--------|
| キー区切り文字 (`DEFAULT_KEY_SEPARATOR`) が欠落 | `doDecapTunnelTermTask()` L368 | `"<key>: invalid tunnel decap term key <key>."` (LOG_ERROR) | `valid=false` → エントリ消費 | なし |
| `dst_ip_prefix` が不正 IP prefix 文字列 | L376-381 | `"<key>: invalid destination IP prefix <e.what()>."` (LOG_ERROR) | `valid=false` → エントリ消費 | なし |
| `src_ip` が不正 IP prefix 文字列 | L407-412 | `"<key>: invalid source IP prefix <src_ip>."` (LOG_ERROR) | `valid=false` → エントリ消費 | なし |
| `term_type` が `P2P`/`P2MP`/`MP2MP` 以外 | L420 | `"<key>: invalid tunnel decap term type <value>."` (LOG_ERROR) | `valid=false` → エントリ消費 | なし |
| `subnet_type` が `vlan`/`vip` 以外 | L431 | `"<key>: invalid subnet type: <value>."` (LOG_ERROR) | `valid=false` → エントリ消費 | なし |
| 未知フィールド名 | L438 | `"<key>: unknown decap term table attribute '<field>'"` (LOG_ERROR) | `valid=false` → エントリ消費 | なし |
| subnet decap tunnel への term が `MP2MP` 以外 | L447-449 | `"<key>: only MP2MP tunnel decap term is allowed for subnet decap tunnel."` (LOG_ERROR) | `valid=false` → エントリ消費 | なし |
| `subnet_type` あり かつ `term_type` が `MP2MP` 以外 | L451-453 | `"<key>: only MP2MP is allowed for subnet decap term."` (LOG_ERROR) | `valid=false` → エントリ消費 | なし |
| `term_type==P2P` かつ `src_ip` 未設定 | L456-460 | `"<key>: no source IP is provided."` (LOG_ERROR) | `valid=false` → エントリ消費 | なし |
| `term_type==MP2MP` (non-subnet) かつ `src_ip` 未設定 | L461-464 | `"<key>: no source IP is provided."` (LOG_ERROR) | `valid=false` → エントリ消費 | なし |
| subnet decap 有効 + subnet term で `src_ip`(IPv4) 未設定 | L484 | `"<key>: source IP is not configured for subnet decap term, ignored."` (LOG_ERROR) | エントリ消費 (永続スキップ) | なし |
| subnet decap 有効 + subnet term で `src_ip_v6` 未設定 | L497 | `"<key>: source IPv6 is not configured for subnet decap term, ignored."` (LOG_ERROR) | エントリ消費 (永続スキップ) | なし |
| subnet decap 無効 (`subnetDecapConfig.enable==false`) + subnet term | L506 | `"<key>: subnet decap is disabled, ignored."` (LOG_ERROR) | エントリ消費 (永続スキップ) | なし |
| 親トンネルが未存在 (tunnel_exists==false) | L521 | `"<key>: tunnel doesn't exist, added to unhandled list."` (LOG_NOTICE) | `unhandledDecapTerms` に保留。親トンネル作成後に `processUnhandledDecapTunnelTerms()` で自動フラッシュ | **自動リトライ** |
| `addDecapTunnelTermEntry()` 失敗（SAI エラー） | L515 | `"<key>: failed to add tunnel decap term to ASIC_DB."` (LOG_ERROR) | エントリ消費。SAI エラー詳細は syncd ログ参照 | なし |
| term entry が既に存在 | `addDecapTunnelTermEntry()` L915 | `"Tunnel decap term entry <dst_ip> already exists."` (LOG_NOTICE) | 二重 SET は `true` 返却で成功扱い（重複無視） | — |

## DEL 失敗経路

| 失敗条件 | 検出箇所 | ログメッセージ | 結果 | リトライ |
|---------|---------|--------------|------|--------|
| 親トンネルが存在しない (tunnel_exists==false) | `doDecapTunnelTermTask()` L540 | `"Tunnel for decap term <key> doesn't exist, removed from unhandled list."` (LOG_NOTICE) | `unhandledDecapTerms` から削除。ASIC_DB 操作なし | なし |
| SAI `remove_tunnel_term_table_entry()` 失敗 | `removeDecapTunnelTermEntry()` L1251 | `"Failed to remove tunnel table entry: <oid>"` (LOG_ERROR) | `handleSaiRemoveStatus()` 経由。`task_need_retry` の場合はキュー残留リトライ | 条件次第 |
| DEL 対象 term entry が orchagent キャッシュに存在しない | `removeDecapTunnelTermEntry()` L1243 | `"Tunnel decap term entry <dst_ip> does not exist."` (LOG_ERROR) | `false` 返却 → DEL 失敗 | なし |

## 設計上の注意点

- **term 無効化は永続スキップ**: キー/フィールド不正・subnet decap 無効などの `valid=false` はエントリを消費して再キューイングしない。修正するには正しい値で再 SET が必要。
- **subnet decap 未設定の競合**: `SUBNET_DECAP` で `enable` が後から変更された場合、既にスキップされた term はキューに残っていないため **自動再処理されない**。SUBNET_DECAP 変更後に term を再 SET する必要がある。
- **親トンネル不在は唯一の自動リトライ**: 他の失敗条件はすべてエントリ消費（恒久スキップ）。親トンネル不在のみ `unhandledDecapTerms` を経由して自動回復する。
- **SAI create 失敗のリトライ**: `addDecapTunnelTermEntry()` の SAI `create_tunnel_term_table_entry()` 失敗は `handleSaiCreateStatus()` で `task_need_retry` に変換されうるが、`doDecapTunnelTermTask()` では成功扱い（LOG_ERROR + continue）でエントリを消費するため、実際にはリトライされない。
