# TUNNEL 例外条件調査メモ

ソース: `sonic-swss/cfgmgr/tunnelmgr.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## 抽出した例外条件

1. **Peer IP 未設定時はトンネル未作成** — `PEER_SWITCH` テーブルから取得した `m_peerIp` が空の場合、
   `"Peer/Remote IP not configured"` を LOG_NOTICE してトンネル設定をスキップする。
   APPL_DB への書き込みは行われない。Peer IP が設定された後に再処理される。

2. **存在しないトンネルの DEL** — キャッシュ（`m_tunnelCache`）に存在しないトンネルを DEL しようとすると
   `"Tunnel <name> not found"` を LOG_ERROR して `return true`（エラーとして扱わず消費する）。

3. **IPINIP 以外のタイプは APPL_DB 書き込みなし** — `tunnel_type` が `IPINIP` 以外の場合、
   トンネルキャッシュには追加されるが APPL_DB の `TUNNEL_DECAP_TABLE` / `TUNNEL_DECAP_TERM_TABLE`
   には書き込まれない（orchagent への通知が行われない）。

4. **Warm reboot 時の重複作成防止** — `m_tunnelReplay` にエントリが存在する場合（ウォームリブート時）は
   APPL_DB への書き込みをスキップする。これは orchagent のクラッシュを防ぐための安全策。

5. **`src_ip` の有無で decap term タイプが変わる** — `src_ip` が空の場合は `P2MP` タイプの decap term を作成し、
   `src_ip` がある場合は `P2P` タイプを作成する。
   誤って空のまま SET すると P2MP 設定になり、意図しないワイルドカード decap が発生する。

6. **`configIpTunnel()` 失敗** — カーネルの `ip tunnel add` コマンド実行に失敗すると
   `return false` となりタスクキューに戻される（リトライ）。
