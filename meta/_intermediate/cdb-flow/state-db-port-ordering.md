# STATE_DB PORT_TABLE — Phase B 書込み順依存スキャンノート

対象ページ: `docs/reference/config-db/state-db-port.md`
対象テーブル: `STATE_DB PORT_TABLE|Ethernet*`
Producer:
  - `portsyncd` (linksync.cpp)
  - `PortsOrch` (portsorch.cpp)
スキャン範囲:
  - `LinkSync::LinkSync()` / `LinkSync::onMsg()` — 全行精読
  - `PortsOrch::initPortSupportedSpeeds()` / `initPortSupportedFecModes()`
  - `PortsOrch::initHostTxReadyState()` / `setHostTxReady()` / `setPortAdminStatus()`
  - `PortsOrch::updateDbPortOperSpeed()` / `updateDbPortOperFec()`
  - `PortsOrch::doPortTask()` 内の初期化シーケンス (portsorch.cpp:5494-5495, 6460-6462)
  - `PortsOrch::refreshPortStatus()` (portsorch.cpp:9850-9930)

---

## 検出した順序依存・タイミング依存

### 1. APP_DB `PORT_TABLE` が先に存在しないと STATE_DB への書き込みがスキップされる

- `LinkSync::onMsg()` は RTM_NEWLINK 受信時に `m_portTable.get(key, temp)` で APP_DB `PORT_TABLE` にキーが存在するかを確認する (linksync.cpp:193)。
- **APP_DB に未登録のポート名**（非 front-panel インタフェース、起動シーケンス中でまだ orchagent が APP_DB を書いていないポート）に対しては STATE_DB への書き込みが行われず、`g_portSet` にキーが残留する。
- **順序依存（強制）**: portsyncd が STATE_DB に `state=ok` を書けるのは、orchagent が APP_DB `PORT_TABLE` にポートエントリを書き込んだ後。起動シーケンス中は APP_DB 書き込みが先行するまで STATE_DB エントリは不在。
- evidence: `linksync.cpp:192-207`

### 2. 非 warm-reboot 時: 起動直後に既存インタフェースを DOWN → RTM_NEWLINK 再送でリカバリ

- `LinkSync::LinkSync()` コンストラクタは非 warm-reboot 時に `ip link set Ethernet* down` を全フロントパネルポートに実行し (linksync.cpp:96-107)、`m_ifindexOldNameMap` にインデックスを記録する。
- これにより起動前の古い STATE_DB 値は RTM_NEWLINK が再送されるまで**上書きされない**中間状態が発生する。
- **順序依存**: 起動後の最初の RTM_NEWLINK 受信 → STATE_DB 書き込みの間に、consumer が旧値を読む可能性がある。
- evidence: `linksync.cpp:44-108`, `linksync.cpp:172-177`（旧インタフェース無視ガード）

### 3. `portsyncd` 書き込みフィールドは 1 回の `set()` でアトミックに更新される

- RTM_NEWLINK 受信時、`state` / `admin_status` / `mtu` / `netdev_oper_status` の 4 フィールドが **1 回の `m_statePortTable.set()` 呼び出し**でまとめて書かれる (linksync.cpp:200-205)。
- 個別フィールドの書き込みは行われない（`hset` ではなく `set`）。
- **順序依存なし**（4 フィールドは atomic set）: ただし RTM_NEWLINK が複数回来る場合は上書きが繰り返される。
- evidence: `linksync.cpp:199-205`

### 4. `PortsOrch` の `supported_speeds` / `supported_fecs` は `initPortSupportedFecModes()` で初期化、以後は変化しない

- `initPortSupportedSpeeds()` / `initPortSupportedFecModes()` はポート初期化の完了直後（`doPortTask` シーケンス内の最後、portsorch.cpp:6460-6462）に呼ばれる。
- 一度 SAI クエリに成功すると `m_portSupportedSpeeds[port_id]` / `m_portSupportedFecModes[port_id]` にキャッシュされ、以後 `initPortSupportedSpeeds` は **即 return** する（portsorch.cpp:3163-3164）。
- **順序依存**: `supported_speeds` / `supported_fecs` が STATE_DB に書かれるのは、PortsOrch がポートの SAI オブジェクト作成・serdes 設定・admin 状態設定を完了した後。起動直後は一時的に不在になる。
- evidence: `portsorch.cpp:3159-3172` / `portsorch.cpp:6460`

### 5. `host_tx_ready` は serdes 設定 → admin_status 設定 の順序に紐付いて書き込まれる

- `doPortTask` の初期化フェーズ: serdes 設定完了後 `initHostTxReadyState()` で `"false"` を初期書き込み (portsorch.cpp:5494-5495)。
- `setPortAdminStatus()` 内での順序:
  1. admin DOWN の場合: SAI set の**前**に `setHostTxReady("false")` を書く (portsorch.cpp:2220-2222)
  2. SAI set 失敗時: `setHostTxReady("false")` を書く (portsorch.cpp:2232-2235)
  3. admin UP + Gearbox OK + SAI 成功の場合: SAI set 成功**後**に `setHostTxReady("true")` を書く (portsorch.cpp:2257)
- **順序依存（強制）**: `host_tx_ready = "true"` は SAI admin set 成功後にしか書かれない。SAI が失敗している間は `"false"` のまま。
- **CMIS 例外**: `m_cmisModuleAsicSyncSupported = true` の場合、`setPortAdminStatus()` 内の `setHostTxReady()` 呼び出しはスキップされ、SAI コールバック `on_port_host_tx_ready` 経由で更新される（portsorch.cpp:977）。

- evidence: `portsorch.cpp:2215-2275`, `portsorch.cpp:5494-5495`

### 6. `speed` / `fec` は oper UP 通知後にのみ更新される（DOWN 時は stale 残留）

- `refreshPortStatus()` (portsorch.cpp:9895-9930) はポート oper UP 確認後にのみ `updateDbPortOperSpeed()` / `updateDbPortOperFec()` を呼ぶ。
- ポートが oper DOWN になっても、speed / fec の STATE_DB フィールドは**削除も更新もされない**（最後の UP 時の値が残留）。
- **順序依存（非対称）**: speed / fec は UP → DOWN 遷移でフィールドが古くなる一方向の依存。consumer は `netdev_oper_status != "up"` のときこれらの値を信頼しないこと。
- evidence: `portsorch.cpp:9905-9930`

### 7. `rmt_adv_speeds` は autoneg 設定変更に紐付いて書き込まれる（CONFIG_DB 依存）

- autoneg が ON に設定された場合のみ `rmt_adv_speeds` が `hset` で書かれる (portsorch.cpp:11338)。
- autoneg が OFF に設定された場合は `hdel` でフィールドが削除される (portsorch.cpp:4862)。
- **順序依存（CONFIG_DB 依存）**: `CONFIG_DB PORT.autoneg` の書き込みイベント駆動。autoneg の ON/OFF 切り替えのたびに書き込み/削除が切り替わる。

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | APP_DB `PORT_TABLE` の存在 → `portsyncd` の STATE_DB 書き込み許可 | **強制先行** | orchagent APP_DB 書き込み完了まで STATE_DB エントリは不在 |
| 2 | 起動時 `ip link set down` → RTM_NEWLINK 再受信 → STATE_DB 更新 | 起動シーケンス依存 | 旧インタフェースからの RTM は無視ガードで除外 |
| 3 | `portsyncd` 4 フィールドの atomic set | 同一 RTM_NEWLINK イベント内で原子的 | 順序依存なし |
| 4 | PortsOrch ポート初期化完了 → `supported_speeds` / `supported_fecs` 書き込み | **強制先行**（serdes 設定後） | 起動直後は不在。SAI キャッシュ後は変化しない |
| 5 | SAI admin set 成功 → `host_tx_ready = "true"` | **強制先行**（SAI 成功必須） | CMIS 環境は SAI コールバック経由 |
| 6 | oper UP → speed / fec 更新 | oper UP 依存（DOWN 時 stale 残留） | consumer は `netdev_oper_status` で補正 |
| 7 | `CONFIG_DB PORT.autoneg` 変更 → `rmt_adv_speeds` 書き込み/削除 | CONFIG_DB イベント依存 | autoneg OFF で自動 hdel |

---

## ページ反映方針

- `<!-- ordering -->` ブロックをフィールド別詳細（`### link_training_status` セクション）の直後、`<!-- defaults -->` ブロックの前に挿入する。
- サマリ表 + 主要制約（依存 #1 / #5 / #6）を含める。
- 既存の `<!-- defaults -->` / `<!-- cdb-mermaid -->` ブロックは変更しない。
