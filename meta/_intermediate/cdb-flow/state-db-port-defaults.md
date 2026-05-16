# STATE_DB PORT_TABLE — Phase A コード由来デフォルト調査

作成日: 2026-05-14
対象ページ: docs/reference/config-db/state-db-port.md

## 書き込み主体一覧

STATE_DB の `PORT_TABLE` (STATE_PORT_TABLE_NAME) に書き込む処理は主に 2 箇所:

1. **`portsyncd/linksync.cpp`**: カーネル netlink (RTM_NEWLINK) を受信して書き込む
2. **`orchagent/portsorch.cpp`**: SAI 経由で取得した oper 値を書き込む

## linksync.cpp が書き込むフィールド

ソース: `sonic-net/sonic-swss portsyncd/linksync.cpp` @ 4305596

`LinkSync::onMsg()` (linksync.cpp:111) → RTM_NEWLINK かつ APPL_DB PORT_TABLE に該当エントリが存在する場合:

```cpp
FieldValueTuple tuple("state", "ok");
FieldValueTuple admin_status("admin_status", (admin ? "up" : "down"));
FieldValueTuple port_mtu("mtu", to_string(mtu));
FieldValueTuple op("netdev_oper_status", oper ? "up" : "down");
// 4 フィールドをまとめて set
m_statePortTable.set(key, vector);
```

RTM_DELLINK 時は `m_statePortTable.del(key)` でエントリ全削除。

| フィールド | コード由来デフォルト | 根拠 |
|-----------|-------------------|------|
| `state` | `"ok"` (固定値) | linksync.cpp:197 — RTM_NEWLINK かつポート存在時は必ず `"ok"` を書く |
| `admin_status` | カーネル IFF_UP フラグ由来。起動直後は `"down"` が多い | linksync.cpp:130,197 — `flags & IFF_UP` が 0 なら `"down"` |
| `mtu` | カーネル rtnl_link_get_mtu() 由来。プラットフォームデフォルト MTU | linksync.cpp:139,199 — カーネルの netdev MTU をそのまま文字列化 |
| `netdev_oper_status` | カーネル IFF_RUNNING フラグ由来。起動直後は `"down"` が多い | linksync.cpp:131,201 — `flags & IFF_RUNNING` が 0 なら `"down"` |

## portsorch.cpp が書き込むフィールド

ソース: `sonic-net/sonic-swss orchagent/portsorch.cpp` @ 4305596

### `supported_speeds`

`initPortSupportedSpeeds()` (portsorch.cpp:3159):
- SAI_PORT_ATTR_SUPPORTED_SPEEDS を取得してカンマ区切り文字列で書き込む
- 取得失敗 (NOT_SUPPORTED/NOT_IMPLEMENTED): `supported_speeds` フィールド不在
- 取得成功・空集合: 空文字列 `""` (CSV join の結果)
- 取得成功・非空: `"1000,10000,40000,100000"` 形式

| フィールド | コード由来デフォルト | 根拠 |
|-----------|-------------------|------|
| `supported_speeds` | (フィールド不在) または空文字列 | portsorch.cpp:3155,3170 — SAI 失敗時は clear() して join → 空文字 |

### `supported_fecs`

→ 既存ページ `fec-state.md` で詳細カバー済み。

### `speed` (oper speed)

`updateDbPortOperSpeed()` (portsorch.cpp:9850):
```cpp
string speedStr = speed != 0 ? to_string(speed) : "N/A";
tuples.emplace_back(std::make_pair("speed", speedStr));
m_portStateTable.set(port.m_alias, tuples);
```
- ポート UP 時: SAI_PORT_ATTR_OPER_SPEED 取得成功 → 数値文字列 (例 `"100000"`)
- ポート UP 時: 取得失敗 → `"N/A"` (portsorch.cpp:9916: speed=0 で呼ぶ)
- ポート DOWN 時: 書き込み自体が行われない (stale 残留)

| フィールド | コード由来デフォルト | 根拠 |
|-----------|-------------------|------|
| `speed` | `"N/A"` | portsorch.cpp:9855 — speed=0 のとき `"N/A"` 固定 |

### `fec` および `supported_fecs`

→ 既存 `fec-state.md` にて詳細記載済み。state-db-port.md では概要のみ。

### `host_tx_ready`

`initHostTxReadyState()` (portsorch.cpp:2181):
- ポート初期化時: フィールドが存在しない場合 `setHostTxReady(port, "false")` を呼ぶ → `"false"` で初期化
- 実際の更新: admin DOWN / gearbox 失敗 → `"false"`; admin UP + gearbox OK → `"true"`
- CMIS module ASIC sync が有効な場合は orchagent が直接 host_tx_ready を制御せず、SAI コールバックで決まる

| フィールド | コード由来デフォルト | 根拠 |
|-----------|-------------------|------|
| `host_tx_ready` | `"false"` | portsorch.cpp:2202 — initHostTxReadyState で未設定時に `"false"` 書き込み |

### `rmt_adv_speeds`

`refreshPortStateAutoNeg()` (portsorch.cpp:~11315):
- autoneg が有効 + admin UP: SAI から remote advertised speeds 取得 → 成功すれば CSV
- admin DOWN または取得失敗: `"N/A"` を書き込み
- autoneg が無効に変更された場合: `hdel` でフィールド削除 (portsorch.cpp:4862)

| フィールド | コード由来デフォルト | 根拠 |
|-----------|-------------------|------|
| `rmt_adv_speeds` | `"N/A"` または (フィールド不在) | portsorch.cpp:11327,11334 — admin DOWN 時は `"N/A"`、autoneg OFF 時は hdel |

### `link_training_status`

`refreshPortStateLinkTraining()` (portsorch.cpp:11342):
- LT 有効 + admin UP: SAI rx_status から判定
- それ以外: `"off"` を書き込み

| フィールド | コード由来デフォルト | 根拠 |
|-----------|-------------------|------|
| `link_training_status` | `"off"` | portsorch.cpp:11351 — 初期値は `"off"` |

### `phy_ctrl_unreliable_los`

- serdes unreliable LOS 設定時: `"true"` または `"false"` を書き込む
- portsorch.cpp:5200: `p.m_unreliable_los ? "true":"false"`

| フィールド | コード由来デフォルト | 根拠 |
|-----------|-------------------|------|
| `phy_ctrl_unreliable_los` | `"false"` | portsorch.cpp:5191 — 設定失敗時は `m_unreliable_los = false` |

## 特記事項

- `state` フィールドは RTM_NEWLINK で固定 `"ok"` のみ。`"error"` 等の値はコードに存在しない
- `admin_status` は CONFIG_DB PORT.admin_status ではなくカーネル IFF_UP フラグ由来 (独立して動く)
- `mtu` も同様にカーネル netdev MTU 由来。CONFIG_DB PORT.mtu とは独立
- ポートが存在しないとき（RTM_DELLINK）はエントリ全体が削除される
- DPU switch type では netdev が driver loading 時点で存在するため、通常の Ethernet port とは初期化タイミングが異なる (linksync.cpp:74-77)
