# MCLAG_DOMAIN / MCLAG_INTERFACE / MCLAG_UNIQUE_IP — 暗黙参照調査 (Phase C)

生成日: 2026-05-16
対象ページ: `docs/reference/config-db/mclag-domain.md`
ソース: `sonic-swss/orchagent/mlagorch.cpp`

## 調査概要

`MCLAG_DOMAIN` / `MCLAG_INTERFACE` / `MCLAG_UNIQUE_IP` テーブルが暗黙的に参照する
（または参照される）周辺 CONFIG_DB / APPL_DB テーブルを `mlagorch.cpp` および関連ファイルから列挙した。

---

## A. MCLAG_DOMAIN が参照するテーブル（MCLAG_DOMAIN → X）

### A-1. PORT / PORTCHANNEL (CONFIG_DB)

- **経路**: `MCLAG_DOMAIN.peer_link` フィールドに PORT 名または PORTCHANNEL 名を文字列で保持する。
  `MlagOrch::doMlagDomainTask()` が `peer_link` を `addIslInterface(peer_link)` に渡し、
  ISL (Inter-Switch Link) として登録。YANG `sonic-mclag.yang:62-71` の `leafref` で
  `PORT.name` または `PORTCHANNEL.name` への参照が宣言されており、
  存在しないポート名は YANG バリデーションで拒否される。
- **証跡**: `mlagorch.cpp:85-93`, `sonic-mclag.yang:62-71`
- **影響**: `peer_link` に指定した PORT / PORTCHANNEL が存在しない場合は書込み拒否。
  `peer_link` が空の場合 `doMlagDomainTask()` はエントリを erase してスキップ（`:98-99`）。

### A-2. PORTCHANNEL (CONFIG_DB) — MCLAG_INTERFACE 経由

- **経路**: `MCLAG_INTERFACE.if_name` は YANG leafref で `PORTCHANNEL.name` を参照。
  `MlagOrch::doMlagInterfaceTask()` が `mlag_if_name` として PortChannel 名を受け取り
  `addMlagInterface(mlag_if_name)` を呼ぶ。
- **証跡**: `mlagorch.cpp:117-154`, `sonic-mclag.yang:115-116`
- **影響**: PORTCHANNEL が存在しないと YANG バリデーション拒否。
  orchagent 内では `m_mlagIntfs` セットに if_name を保持し、後段の FDB 処理で参照される。

---

## B. MCLAG_DOMAIN を参照するテーブル（X → MCLAG_DOMAIN）

### B-1. MCLAG_INTERFACE (CONFIG_DB)

- **経路**: `MCLAG_INTERFACE.domain_id` は YANG leafref で `MCLAG_DOMAIN.domain_id` を参照。
  MCLAG_DOMAIN が 0 件のとき MCLAG_INTERFACE の書込みは YANG バリデーション拒否。
- **証跡**: `sonic-mclag.yang:108-109`
- **影響**: MCLAG_DOMAIN の追加が MCLAG_INTERFACE より先行必須。

### B-2. MCLAG_UNIQUE_IP (CONFIG_DB)

- **経路**: YANG `must "count(MCLAG_DOMAIN_LIST/domain_id) != 0"` により MCLAG_DOMAIN が
  少なくとも 1 件存在しなければ書込み拒否。`MCLAG_UNIQUE_IP.if_name` は本来 `VLAN.name`
  への leafref が望ましいが libyang 制約で plain string になっている。
- **証跡**: `sonic-mclag.yang:132-134`, YANG コメント
- **影響**: VLAN_INTERFACE への参照は間接的にのみ存在。

---

## C. FDB テーブルへの暗黙参照

### C-1. FDB_TABLE (APPL_DB) — FDB フラッシュ抑止

- **経路**: `FdbOrch::updatePortOperState()` がポートの oper-down 時に FDB フラッシュを実行するが、
  `gMlagOrch->isMlagInterface(p.m_alias)` が true のポート（MCLAG_INTERFACE に登録済み
  PortChannel）は **フラッシュをスキップ** する。
  これは MCLAG ピア側が当該 PortChannel の FDB を保持し続けるため不要なフラッシュを防ぐ設計。
- **証跡**: `fdborch.cpp:1209-1212`
- **影響**: MCLAG_INTERFACE に登録された PortChannel が oper-down になっても FDB エントリは残存する。

### C-2. FDB_TABLE (APPL_DB) — MCLAG 広告 FDB の削除制御

- **経路**: `FdbOrch::removeFDBEntry()` で `origin == FDB_ORIGIN_MCLAG_ADVERTIZED` かつ
  `fdbData.origin == FDB_ORIGIN_LEARN` かつ ポートが oper-down かつ
  `gMlagOrch->isMlagInterface(port.m_alias)` が true のとき、
  削除 origin を `FDB_ORIGIN_LEARN` に書き換えてローカル MAC を削除する。
- **証跡**: `fdborch.cpp:1665-1670`
- **影響**: MCLAG ポートが down 時に限り MCLAG 広告 FDB をローカル学習扱いで削除する例外処理。

---

## D. NEIGHBOR / NEIGH テーブルへの参照

`mlagorch.cpp` では `NEIGHBOR` / `NEIGH` テーブルへの直接参照は存在しない。
隣接解決は `neighorch` が行い、MCLAG は `isMlagInterface()` / `isIslInterface()` で
PortChannel 状態を通知するに留まる。NEIGHBOR への暗黙参照はなし（スコープ外）。

---

## E. 暗黙参照のまとめ（cross-refs ブロック用）

```
MCLAG_DOMAIN.peer_link    → PORT / PORTCHANNEL  (ISL ポート解決、YANG leafref)
MCLAG_INTERFACE.if_name   → PORTCHANNEL          (MLAG member LAG、YANG leafref)
MCLAG_INTERFACE           ← MCLAG_DOMAIN.domain_id (leafref、DOMAIN 先行必須)
MCLAG_UNIQUE_IP           ← MCLAG_DOMAIN         (YANG must 制約)
MCLAG_INTERFACE (member)  →→ FDB_TABLE flush skip (fdborch.cpp:1209)
MCLAG_INTERFACE (member)  →→ FDB_TABLE del-origin override (fdborch.cpp:1665)
```

---

## F. 証跡ソース一覧

| ファイル | 行番号 | 内容 |
|---------|--------|------|
| `sonic-swss/orchagent/mlagorch.cpp` | 85-99 | `peer_link` 取得 → `addIslInterface()` |
| `sonic-swss/orchagent/mlagorch.cpp` | 117-154 | `doMlagInterfaceTask()` → `addMlagInterface()` |
| `sonic-swss/orchagent/mlagorch.cpp` | 156-172 | `addIslInterface()` — ISL 登録と observer 通知 |
| `sonic-swss/orchagent/mlagorch.cpp` | 192-214 | `addMlagInterface()` — m_mlagIntfs 管理 |
| `sonic-swss/orchagent/fdborch.cpp` | 1203-1213 | oper-down FDB フラッシュ抑止 (MLAG intf ガード) |
| `sonic-swss/orchagent/fdborch.cpp` | 1663-1672 | MCLAG 広告 FDB 削除 origin 書き換え |
| `sonic-buildimage/.../sonic-mclag.yang` | 62-71 | `peer_link` leafref → PORT / PORTCHANNEL |
| `sonic-buildimage/.../sonic-mclag.yang` | 108-116 | MCLAG_INTERFACE leafref → DOMAIN / PORTCHANNEL |
| `sonic-buildimage/.../sonic-mclag.yang` | 132-134 | MCLAG_UNIQUE_IP must DOMAIN 存在制約 |
