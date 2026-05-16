# ports-status Phase A 中間調査ノート

## 対象

STATE_DB `PORT_TABLE|<port>` に書き込まれるステータスフィールド。
CONFIG_DB `PORT` テーブルとは異なり、カーネル netlink / SAI oper 状態を反映する読み取り専用フィールド群。

## ソース精読結果

### 1. portsyncd/linksync.cpp (sonic-swss @ 4305596)

`LinkSync::onMsg()` が RTM_NEWLINK を受信すると以下 4 フィールドを `m_statePortTable.set()` で書き込む:

```cpp
FieldValueTuple("state", "ok")                            // 定数 "ok"
FieldValueTuple("netdev_oper_status", oper ? "up" : "down")  // IFF_RUNNING フラグ
FieldValueTuple("admin_status",       admin ? "up" : "down") // IFF_UP フラグ
FieldValueTuple("mtu", to_string(mtu))                    // rtnl_link_get_mtu()
```

RTM_DELLINK を受信すると `m_statePortTable.del(key)` でエントリ削除。

### 2. orchagent/portsorch.cpp (sonic-swss @ 4305596)

| フィールド | 書き込みメソッド | トリガー | デフォルト/fallback |
|-----------|---------------|---------|---------------------|
| `supported_speeds` | `initPortSupportedSpeeds()` L3172 | ポート作成初回（lazy init） | SAI から取得したカンマ区切り速度リスト（例: `"10000,25000,100000"`）。空なら空文字列 |
| `supported_fecs` | `initPortSupportedFecModes()` L3320 | `isFecModeSupported()` 初回呼び出し | 成功+空集合: `"N/A"`; 失敗(NOT_SUPPORTED): フィールド不在 |
| `host_tx_ready` | `initHostTxReadyState()` L2202 / `setHostTxReady()` L2274 | ポート作成時 / admin_status 変更時 | 既存エントリになければ `"false"` で初期化 |
| `speed` | `updateDbPortOperSpeed()` L9857 | oper-status UP 通知 / refreshPortStatus() | oper speed 0 なら `"N/A"` |
| `fec` | `updateDbPortOperFec()` L9870 | oper-status UP 通知 / refreshPortStatus() | SAI 未対応 / DOWN の場合は `"N/A"` |
| `link_training_status` | L4907 / `refreshPortStateLinkTraining()` L11380 | LT 設定変更 / oper-status 変化 | 条件不成立時 `"off"` |
| `rmt_adv_speeds` | `updatePortStateAutoNeg()` L11338 | auto-neg 状態変化 | admin DOWN または取得失敗で `"N/A"` |
| `phy_ctrl_unreliable_los` | L5200 | serdes.unreliable_los 設定変更 | `m_unreliable_los` の bool → `"true"`/`"false"` |
| `oper_status` | `updateDbPortOperStatus()` L9928 | oper-status 変化 | APP_DB `PORT_TABLE` に書く（STATE_DB ではない）|

**注意**: `oper_status` は `m_portTable->set()` (APP_DB) に書かれる。STATE_DB PORT_TABLE ではない。

### 3. デフォルト値まとめ

| フィールド | コード由来デフォルト | ソース |
|-----------|-------------------|--------|
| `state` | `"ok"` (定数) | linksync.cpp:196 |
| `netdev_oper_status` | `"up"` or `"down"` | linksync.cpp:201 (IFF_RUNNING) |
| `admin_status` | `"up"` or `"down"` | linksync.cpp:197 (IFF_UP) |
| `mtu` | カーネル mtu 値 (文字列) | linksync.cpp:198 |
| `host_tx_ready` | `"false"` (初期化時) | portsorch.cpp:2202 |
| `speed` | `"N/A"` (取得失敗/DOWN) | portsorch.cpp:9855 |
| `link_training_status` | `"off"` (LT 無効/条件不成立) | portsorch.cpp:11351 |
| `rmt_adv_speeds` | `"N/A"` (admin DOWN / 失敗) | portsorch.cpp:11327 |
| `supported_speeds` | SAI 取得値 (空なら空) | portsorch.cpp:3170 |
| `supported_fecs` | `"N/A"` (空集合) or 不在 (NOT_SUPPORTED) | portsorch.cpp:3292 |
| `phy_ctrl_unreliable_los` | `"false"` (通常デフォルト) | portsorch.cpp:5191-5200 |

### 4. hard=0 確認（暗黙デフォルト）

- `state`: コードが定数 `"ok"` を注入。エントリ存在 = ポートが kernel に認識済み。
- `host_tx_ready`: `initHostTxReadyState()` が既存エントリに `host_tx_ready` がなければ `"false"` を強制設定。YANG 定義なし。
- `link_training_status`: LT が off / 非サポート / admin DOWN の場合はコードが `"off"` を書く。
- `speed`: UP 時は SAI から取得、ゼロなら `"N/A"` を書く。

### 5. 検出した注意点

1. `admin_status` が STATE_DB と CONFIG_DB の両方に存在する（意味は同じだが書込み主体が異なる）。
2. `oper_status` は STATE_DB PORT_TABLE ではなく APP_DB PORT_TABLE に書かれる（portsorch.cpp:3930）。
3. RTM_DELLINK でエントリ全体が削除される。ポート削除後は STATE_DB に残らない。
4. `supported_speeds` は portsorch が lazy init で 1 回だけ書く。orchagent 再起動まで更新されない。
