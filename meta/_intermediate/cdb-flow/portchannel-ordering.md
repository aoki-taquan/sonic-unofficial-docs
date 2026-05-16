# PORTCHANNEL テーブル — Phase B: 書込み順依存調査メモ

調査日: 2026-05-15
対象: `docs/reference/config-db/portchannel.md`
証跡ソース: `teammgr.cpp` (sonic-swss), `portsorch.cpp` (sonic-swss), `minigraph.py` (sonic-buildimage)

---

## 1. 先行必須テーブル (SET 時)

### PORT が先行必須 (ハード依存)

- `teammgr.cpp:212-225` — `TeamMgr::addLag()` は `m_portsOrch->getPort(portName, port)` を呼び出してポートが APP_DB に存在するか確認する。ポートが未登録の場合 `task_need_retry` を返す。
- **結論**: LAG メンバとして追加する物理ポートは `PORT` テーブルに先行して登録されている必要がある。PORT が存在しない間は PORTCHANNEL_MEMBER の SET は保留される。
- 厳密に言えば PORTCHANNEL エントリ自体は PORT 存在前に書けるが、`addLag()` 呼出し中のポート存在チェックで retry になるためポート初期化後まで LAG 作成が保留される。

### PORT_CONFIG_DONE / allPortsReady が必須

- `portsorch.cpp:6513-6517` — orchagent は `allPortsReady()` が true になるまで LAG 関連処理を含むほぼ全 orch の SET をブロックする。
- **結論**: BootUp 時は portsyncd が CONFIG_DB|PORT を処理して PortConfigDone → PortInitDone が発行されるまで、PORTCHANNEL エントリの処理も保留される。

---

## 2. SET → SET 順 (フィールド適用順)

`TeamMgr::doLagTask()` (`teammgr.cpp:280-330`) でのフィールド適用順:

1. **addLag()** — SET の最初の処理。LAG が未作成の場合は teamd プロセスを起動し Linux bond デバイスを作成。
   - この時点で `min_links` / `fallback` / `fast_rate` が teamd conf に書き込まれる。
   - `addLag()` が `task_need_retry` を返した場合、後続フィールドは一切処理されない。
2. `admin_status` — `setLagAdminStatus()` を呼び出してカーネル LAG インタフェースの up/down を設定 (`teammgr.cpp:314`)。
3. `tpid` — `setLagTpid()` を呼び出して TPID を設定 (`teammgr.cpp:321-323`)。

### LAG 作成後に変更不可なフィールド

- `min_links`, `fallback`, `fast_rate` は **`addLag()` 呼出し時のみ** teamd conf ファイルに反映される。
- `teammgr.cpp:258-259` に明示コメント: "min_links and fallback attributes cannot be changed after the LAG is created."
- LAG 作成後にこれらフィールドを CONFIG_DB で更新しても teamd は変更を認識しない。反映には teamd プロセスの再起動 (`config portchannel del` → `add`) が必要。

---

## 3. DEL 順 (先に削除が必要なエントリ)

PORTCHANNEL エントリを DEL する前に以下を先に削除しないと `orchagent` / `teammgrd` がエラーを返す。

### 先行削除必須

1. **PORTCHANNEL_MEMBER** の全エントリ — `portsorch.cpp` `LagOrch::removeLag()` が `non-empty LAG` エラーを返す (`SWSS_LOG_ERROR: "Failed to remove non-empty LAG %s"`).
2. **PORTCHANNEL_INTERFACE** — LAG に L3 インタフェースが残っている場合、`ref_count > 0` のため SAI LAG DEL が拒否される (`"Failed to remove ref count %d LAG %s"`).
3. **VLAN_MEMBER** での LAG 所属 — LAG が VLAN に所属したまま DEL しようとすると `"Failed to remove LAG %s, it is still in VLAN"` エラー。

### DEL の正しい順序

```
1. VLAN_MEMBER DEL (LAG が VLAN メンバの場合)
2. PORTCHANNEL_INTERFACE DEL (L3 設定が存在する場合)
3. PORTCHANNEL_MEMBER DEL (全メンバポートを除外)
4. PORTCHANNEL DEL
```

teamd プロセス側では `TeamMgr::doLagTask()` が DEL を受信すると SIGTERM を送信して teamd を終了させ (`teammgr.cpp:339`)、Linux bond デバイスを削除する。

---

## 4. restart / warm-reboot 影響

### cold reboot / daemon restart

- teammgrd は stateless で再起動後に CONFIG_DB の PORTCHANNEL テーブルを再購読し全 LAG を再作成する。
- teamd プロセスが再起動されるため `min_links` / `fallback` / `fast_rate` が正しく再適用される。

### warm reboot

- `teammgr.cpp` warm reboot 対応: warm reboot 時は既存 teamd プロセスを維持し、APP_DB の `LAG_TABLE` と `LAG_MEMBER_TABLE` を reconcile する。
- warm reboot 中は CONFIG_DB への書き込みが処理保留になる。復元完了後に通常の subscribe 処理が再開される。
- warm reboot 後に `min_links` / `fallback` / `fast_rate` を変更したい場合は cold リスタートが必要。

---

## 5. boot order 依存 (起動時シーケンス)

```
[起動時]
minigraph.py / sonic-cfggen が CONFIG_DB|PORTCHANNEL を生成
  ↓
portsyncd 起動 → CONFIG_DB|PORT 全件読み → APP|PORT 書込み → PortConfigDone
  ↓
PortsOrch が PortConfigDone を受信 → SAI create_port() → PortInitDone
  ↓
allPortsReady() = true → LagOrch / TeamMgr がアンブロック
  ↓
TeamMgr が PORTCHANNEL SET を処理 → addLag() → teamd spawn → APP_DB|LAG_TABLE 書込み
  ↓
LagOrch が APP_DB|LAG_TABLE を読み → SAI create_lag() → LAG ready
  ↓
TeamMgr が PORTCHANNEL_MEMBER SET を処理 → addLagMember() → teamd にメンバ追加
  ↓
LagOrch が APP_DB|LAG_MEMBER_TABLE → SAI add_ports_to_lag()
```

---

## ソース証跡

| 知見 | ファイル | 行 |
|------|---------|-----|
| addLag() task_need_retry (ポート未存在) | `sonic-swss/cfgmgr/teammgr.cpp` | 212-225, 303-305 |
| min_links/fallback 変更不可コメント | `sonic-swss/cfgmgr/teammgr.cpp` | 258-259 |
| admin_status 適用 | `sonic-swss/cfgmgr/teammgr.cpp` | 314 |
| tpid 適用 | `sonic-swss/cfgmgr/teammgr.cpp` | 321-323 |
| DEL SIGTERM | `sonic-swss/cfgmgr/teammgr.cpp` | 339 |
| non-empty LAG エラー | `sonic-swss/orchagent/portsorch.cpp` | LagOrch::removeLag() |
| VLAN 所属 LAG エラー | `sonic-swss/orchagent/portsorch.cpp` | LagOrch::removeLag() |
| ref_count LAG エラー | `sonic-swss/orchagent/portsorch.cpp` | LagOrch::removeLag() |
| allPortsReady() ブロック | `sonic-swss/orchagent/portsorch.cpp` | 6513-6517 |
| minigraph.py PORTCHANNEL 生成 | `sonic-buildimage/src/sonic-config-engine/minigraph.py` | 2531, 2546 |
