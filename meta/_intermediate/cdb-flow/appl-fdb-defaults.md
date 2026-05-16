# APPL_DB FDB_TABLE フィールドのコード由来デフォルト (Phase A)

調査対象: `docs/reference/config-db/appl-fdb.md`

## ソース

- `sonic-swss/orchagent/fdborch.cpp` — APPL_DB FDB_TABLE consumer (FdbOrch)
- `sonic-swss/orchagent/fdborch.h` — FdbData 構造体定義
- `sonic-swss/cfgmgr/vlanmgr.cpp` — PAC/802.1X 経由の FDB_TABLE producer
- `sonic-swss-common/common/schema.h` — `APP_FDB_TABLE_NAME "FDB_TABLE"` 定義

sha: master branch (2026-05 時点)

---

## テーブル概要

`APPL_DB` の `FDB_TABLE` は動的学習 MAC エントリと静的プロビジョニング MAC エントリの両方を保持する。

- **書き込み元**: `fdbsyncd` (kernel netlink → 動的学習), `swssconfig` (JSON 手動投入), VlanMgr (PAC/802.1X)
- **読み取り元 (consumer)**: `orchagent` の `FdbOrch`
- **key 形式**: `FDB_TABLE:Vlan<id>:<MAC>` (例: `FDB_TABLE:Vlan100:00:11:22:33:44:55`)

---

## フィールド一覧と初期値

`fdborch.cpp` L769-L775 の consumer 側初期値:

| フィールド | C++ 初期値 | 必須 | 有効値 | 備考 |
|-----------|-----------|------|--------|------|
| `port` | `""` (空文字列) | 実質必須 | ポート名文字列 | 空のまま通過するとエントリ登録失敗 |
| `type` | `"dynamic"` | - | `"dynamic"` / `"static"` / `"dynamic_local"` | フィールド不在時は `"dynamic"` と解釈 |
| `discard` | `"false"` | - | `"true"` / `"false"` | PAC/802.1X 使用。`"true"` で当該 MAC を破棄 |

VXLAN 起源エントリ (`APP_VXLAN_FDB_TABLE_NAME`) 限定の追加フィールド:

| フィールド | C++ 初期値 | 有効値 | 備考 |
|-----------|-----------|--------|------|
| `remote_vtep` | `""` | IP アドレス文字列 | VXLAN リモートトンネル終端点 IP |
| `esi` | `""` | ESI 文字列 | EVPN Ethernet Segment Identifier |
| `vni` | `0` | uint32 | VXLAN Network Identifier |

---

## consumer 側初期化コード

`fdborch.cpp:769-775`:

```cpp
string port = "";
string type = "dynamic";
string remote_ip = "";
string esi = "";
unsigned int vni = 0;
string sticky = "";
string discard = "false";
```

フィールドが APPL_DB に存在する場合のみ上書きされる。よって:
- `type` フィールド不在 → `"dynamic"` (FDB_ORIGIN_PROVISIONED 扱い)
- `discard` フィールド不在 → `"false"`
- `port` フィールド不在 → `""` → エントリ登録失敗

---

## type assert チェック

`fdborch.cpp:830`:

```cpp
assert(type == "dynamic" || type == "dynamic_local" || type == "static");
```

無効な `type` 値はプロセスクラッシュを引き起こす。

---

## SAI 型マッピング

| `type` 値 | `origin` | SAI FDB Entry Type |
|-----------|----------|-------------------|
| `"dynamic"` | LEARN / PROVISIONED | `SAI_FDB_ENTRY_TYPE_DYNAMIC` |
| `"static"` | PROVISIONED | `SAI_FDB_ENTRY_TYPE_STATIC` |
| `"dynamic_local"` | MCLAG_ADVERTIZED | `SAI_FDB_ENTRY_TYPE_DYNAMIC`（aging 有効化目的） |
| `"static"` | VXLAN_ADVERTIZED / MCLAG_ADVERTIZED | `SAI_FDB_ENTRY_TYPE_STATIC` |

---

## PAC/VlanMgr 側 producer デフォルト

`vlanmgr.cpp:806`:

```cpp
string port, discard = "false", type = "static";
```

PAC 経由では `type` デフォルト値が `"static"` となる点に注意（orchagent 側とは逆）。

---

## 書き込み経路別まとめ

| 書き込み元 | type デフォルト | discard デフォルト | 備考 |
|-----------|----------------|-------------------|------|
| `fdbsyncd` (動的学習) | `"dynamic"` | なし | kernel netlink → APPL_DB 直書き |
| `swssconfig` (手動) | `"dynamic"` | なし | JSON 内 type 指定推奨 |
| VlanMgr / PAC | `"static"` | `"false"` | 802.1X 認証後 |
| VXLAN FDB Table | `"dynamic"` | なし | `APP_VXLAN_FDB_TABLE_NAME` 経由 |
