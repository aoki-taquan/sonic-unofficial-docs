# TUNNEL_DECAP_TABLE — Phase B: 書込み順依存調査

ソース: `sonic-swss/orchagent/tunneldecaporch.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
       `sonic-swss/cfgmgr/tunnelmgr.cpp` (同 SHA)

---

## 1. allPortsReady() ゲート (orchagent 側)

`TunnelDecapOrch::doTask()` L55-57 にて `gPortsOrch->allPortsReady()` が false の間は即 return する。
ports 初期化完了前に TUNNEL_DECAP_TABLE / TUNNEL_DECAP_TERM_TABLE エントリが APPL_DB に届いても、
Consumer キューに留まり処理されない。`allPortsReady()` が true になった最初の doTask() 呼び出し時にまとめて処理される。

## 2. TUNNEL_DECAP_TABLE → TUNNEL_DECAP_TERM_TABLE の依存

tunneldecaporch.cpp L513, L1486-1511:

- `TUNNEL_DECAP_TERM_TABLE` エントリが、対応するトンネル本体 (`TUNNEL_DECAP_TABLE`) よりも先に届いた場合:
  - `tunnel_exists` が false → `addUnhandledDecapTunnelTerm()` に蓄積 (L526 "tunnel doesn't exist, added to unhandled list.")
  - トンネル本体の `addDecapTunnel()` 成功後、`processUnhandledDecapTunnelTerms()` (L309) が一括処理
- トンネル本体が先に作成済みの場合: term エントリは即時 `addDecapTunnelTermEntry()` される (L513)
- **推奨順序**: `TUNNEL_DECAP_TABLE` SET → `TUNNEL_DECAP_TERM_TABLE` SET

## 3. CONFIG_DB(TUNNEL) → APPL_DB(TUNNEL_DECAP_TABLE) 投影順序 (tunnelmgr 側)

tunnelmgr.cpp `doTunnelTask()` L263-293:

- `tunnelmgrd` は CONFIG_DB の `TUNNEL` テーブルを購読し、APPL_DB の `APP_TUNNEL_DECAP_TABLE` と `APP_TUNNEL_DECAP_TERM_TABLE` に同時書き込む。
- CONFIG_DB `TUNNEL` エントリが存在しない限り APPL_DB への投影は発生しない。
  **依存チェーン**: `CONFIG_DB TUNNEL` → (tunnelmgrd) → `APPL_DB TUNNEL_DECAP_TABLE` → (tunneldecaporch) → SAI

## 4. Loopback3 依存 (tunnelmgr 側)

tunnelmgr.cpp `doLpbkIntfTask()` L337-348:

- `tunnelmgrd` は `LOOPBACK_INTERFACE` テーブルの `Loopback3` エントリが存在しない場合、
  トンネル IF への IP アドレス付与をスキップ（警告ログのみ）。
- `Loopback3` IP が後から設定された場合は `m_tunnelCache` 内の未処理エントリに対して
  `cmdIpTunnelIfAddress()` が遅延実行される。
- **推奨順序**: `LOOPBACK_INTERFACE|Loopback3` 設定 → `TUNNEL` エントリ設定

## 5. DEL 操作順序

- `TUNNEL_DECAP_TABLE` を DEL する前に `TUNNEL_DECAP_TERM_TABLE` を DEL することが必要。
  トンネル本体の DEL 時、term が残存していると SAI リソースがリークする可能性がある
  (tunneldecaporch は tunnel DEL 時に term を自動削除しない: `removeDecapTunnel()` は term 削除を別途行う設計)。
- DEL 順序: `TUNNEL_DECAP_TERM_TABLE` DEL → `TUNNEL_DECAP_TABLE` DEL

## 6. warm-restart 影響

- `tunnelmgrd` は warm-restart に対応 (`finalizeWarmReboot()` / `replayDone` フラグ, L419-425)。
  warm-restart 時は `m_tunnelReplay` に収録済みのトンネルへの APPL_DB 再書き込みをスキップし、
  orchagent のクラッシュを防ぐ (L263-272)。
- `tunneldecaporch` 自体は warm-restart 非対応 (`onWarmBootEnd()` 未実装)。
  cold restart 後は CONFIG_DB replay により APPL_DB 再投影 → 自動再構築。

## 7. まとめ: 推奨書込み順序

```
1. LOOPBACK_INTERFACE|Loopback3 (CONFIG_DB) — IP付与のため
2. CONFIG_DB TUNNEL SET          — tunnelmgrd が APPL_DB へ投影
3. APPL_DB TUNNEL_DECAP_TABLE SET (自動) — tunnelmgrd が書く
4. APPL_DB TUNNEL_DECAP_TERM_TABLE SET (自動) — tunnelmgrd が書く、または手動注入時は3の後
5. DEL時: TUNNEL_DECAP_TERM_TABLE DEL → TUNNEL_DECAP_TABLE DEL の順
```

---

*生成日: 2026-05-15*
