# NEIGH テーブル Phase A — コード由来暗黙デフォルト調査メモ

調査日: 2026-05-14  
対象テーブル: CONFIG_DB `NEIGH`  
主要ソース:
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-neigh.yang` (rev 9ea932ec)
- `sonic-swss/cfgmgr/nbrmgr.cpp` (rev 43055961)
- `sonic-swss/cfgmgr/nbrmgrd.cpp`
- `sonic-swss/neighsyncd/neighsync.cpp`
- `sonic-swss/neighsyncd/restore_neighbors.py`
- `sonic-buildimage/src/sonic-config-engine/minigraph.py`

---

## テーブル概要

CONFIG_DB の `NEIGH` テーブルはスタティック隣接（Permanent neighbor）エントリを保持する。  
Consumer: `nbrmgrd` (`NbrMgr::doSetNeighTask`)。

key 形式: `NEIGH|<port>|<ip_address>`  
例: `NEIGH|Ethernet0|10.0.0.2`

---

## フィールド一覧と型

| フィールド | YANG 型 | YANG mandatory | 説明 |
|-----------|---------|---------------|------|
| `neigh`   | `yang:mac-address` | 任意 | 対向の MAC アドレス |
| `family`  | `string (IPv4\|IPV4\|IPv6\|IPV6)` | 任意 | IP ファミリ |

---

## 暗黙デフォルト・フォールバック詳細

### 1. `neigh` フィールド（MAC アドレス）

**YANG default**: なし（`default` 文なし）  
**実装挙動**:
- `doSetNeighTask` (nbrmgr.cpp:321–347): `field == "neigh"` のみを読む。他フィールドはすべて無視。
- MAC が空文字列 or フィールド未指定の場合: `MacAddress mac` はデフォルトコンストラクタ（ゼロ MAC `00:00:00:00:00:00`）で初期化される。
- `setNeighbor()` 内で `if (!mac)` (nbrmgr.cpp:175): MAC がゼロ／未設定なら `NUD_DELAY + NTF_USE` でカーネルに ARP 解決を要求する（`RTM_NEWNEIGH` に NTF_USE フラグ）。
- **Fallback**: `neigh` を省略または空文字 → カーネルが ARP/NDP で自動解決を試みる。エントリは `NUD_DELAY` 状態でカーネルに挿入される。
- 無効な MAC 文字列（`invalid_argument` 例外）: エントリはサイレントに drop (`it = consumer.m_toSync.erase(it)` nbrmgr.cpp:350–353)。エラーログあり、再試行なし。

**dead consumer 問題**: なし（DEL_COMMAND は `"Not yet implemented"` でログのみ、nbrmgr.cpp:375）。

### 2. `family` フィールド

**YANG default**: なし  
**実装挙動**:
- `doSetNeighTask` は `family` フィールドを**一切読まない**。ループで `field == "neigh"` のみ分岐し、他フィールドは無処理スキップ（nbrmgr.cpp:330–347）。
- IP ファミリ判定は `IpAddress ip(keys[1])` から `ip.isV4()` で行う（nbrmgr.cpp:325、setNeighbor:147/164）。
- **`family` は CONFIG_DB NEIGH に対しては dead field（Consumer が読まない）**。

> NOTE: APPL_DB の `NEIGH_TABLE` では `family` フィールドが `neighsyncd` (neighsync.cpp:172) によって書き込まれ、`restore_neighbors.py` (line:153) が必須チェックする。CONFIG_DB `NEIGH` テーブルの `family` は YANG に定義があるが実装上は無視される。

### 3. `port` キー部分 (alias)

**インターフェイス状態チェック**: `isIntfStateOk(alias)` → STATE_DB の `INTERFACE_TABLE` にエントリがなければ処理をスキップ（`it++` で再試行に回る、nbrmgr.cpp:357–361）。  
**Fallback**: インターフェイスが未準備の場合は永続リトライ。インターフェイスが存在しない port 名を指定した場合は netlink `RTM_NEWNEIGH` がカーネルに届いて `if_nametoindex()` が 0 を返し、netlink が失敗する（setNeighbor:145）。

---

## DEL_COMMAND の dead consumer（実装欠落）

`doSetNeighTask` の `DEL_COMMAND` ブランチ (nbrmgr.cpp:373–376):

```cpp
else if (op == DEL_COMMAND)
{
    SWSS_LOG_NOTICE("Not yet implemented, key '%s'", kfvKey(t).c_str());
}
```

CONFIG_DB `NEIGH` エントリを削除しても**カーネルの静的 neighbor エントリは削除されない**。  
カーネル側に `NUD_PERMANENT` で設定されたエントリは手動 `ip neigh del` か再起動まで残存する。

---

## 書き込み順依存・タイミング問題

1. `NEIGH` エントリより先にインターフェイスが STATE_DB に登録されている必要がある。未登録なら SELECT_TIMEOUT (1000ms) ごとにリトライ。
2. warm reboot 時: `nbrmgrd` 起動後に `isNeighRestoreDone()` フラグ（NEIGH_RESTORE_TABLE|Flags|restored = "true"）待ちで 120 秒タイムアウト（nbrmgrd.cpp:17, 54-61）。この間も NEIGH の処理は進む（warm start 制御はあくまで restore_neighbors.py 側）。

---

## ハードコード値

| 箇所 | 値 | 意味 |
|------|-----|------|
| `nbrmgrd.cpp:17` | `RESTORE_NEIGH_WAIT_TIME_OUT = 120` | warm reboot 時 neighbor restore 待ちタイムアウト(秒) |
| `nbrmgrd.cpp:18` | `RESTORE_NEIGH_WAIT_TIME_INT = 10` | ポーリング間隔(秒) |
| `nbrmgrd.cpp:24` | `SELECT_TIMEOUT = 1000` | select() タイムアウト(ms) |
| `setNeighbor` NUD_PERMANENT | MAC あり時の ndm_state | カーネルへ永続 neighbor として設定 |
| `setNeighbor` NUD_DELAY+NTF_USE | MAC なし時の ndm_state | カーネルへ ARP 解決トリガ |

---

## VoQ / switch_type 依存

`switch_type == "voq"` の場合のみ `NbrMgr` が `STATE_SYSTEM_NEIGH_TABLE_NAME` を追加購読し、`doStateSystemNeighTask` を実行してリモート neighbor をカーネルに挿入する（nbrmgr.cpp:78–84）。非 VoQ 環境では `STATE_SYSTEM_NEIGH` は無視される。

---

## minigraph.py の `family`-only NEIGH エントリ

FG-NHG (Fine-Grained ECMP) 構成時、minigraph.py (line 584) は `NEIGH` エントリを `{"family": "IPV4" or "IPV6"}` のみで生成する（`neigh` MAC フィールドなし）。  
nbrmgrd はこれを受け取ると `neigh` フィールドが存在しないため MAC = ゼロ MAC → `NUD_DELAY+NTF_USE` でカーネルに ARP 解決を要求する。意図的な挙動。

---

## まとめ（`<!-- defaults -->` ブロック用）

| フィールド | YANG default | 実装 fallback | 備考 |
|-----------|-------------|--------------|------|
| `neigh` | なし | MAC 省略→ゼロ MAC → ARP 解決要求; 無効 MAC → サイレント drop | 無効値は再試行なし |
| `family` | なし | Consumer が読まない（dead field） | APPL_DB 側では必須 |
| DEL_COMMAND | — | 未実装。カーネル neighbor は残存 | 既知の設計不足 |
