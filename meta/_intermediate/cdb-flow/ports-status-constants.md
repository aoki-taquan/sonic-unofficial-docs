# ports-status Phase E — ハードコード定数調査ノート

対象: `STATE_DB PORT_TABLE` — 書込み主体: `portsyncd/linksync` / `PortsOrch`

## 調査ソース

- `sonic-swss/portsyncd/linksync.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/portsorch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## 検出した定数一覧

### linksync.cpp 由来

| 定数 | 値 | 行 | 用途 |
|------|----|----|------|
| `state` フィールド値 | `"ok"` (文字列リテラル) | linksync.cpp:196 | RTM_NEWLINK 受信時に無条件で書き込む固定値 |
| `admin_status` 値 | `"up"` / `"down"` | linksync.cpp:197 | `flags & IFF_UP` の bool を文字列化する二値定数 |
| `netdev_oper_status` 値 | `"up"` / `"down"` | linksync.cpp:201 | `flags & IFF_RUNNING` の bool を文字列化する二値定数 |

### portsorch.cpp 由来

| 定数 | 値 | 行 | 用途 |
|------|----|----|------|
| `speed` フォールバック | `"N/A"` | 9855 | `speed == 0` または SAI 取得失敗時のフォールバック文字列 |
| `fec` フォールバック | `"N/A"` | updateDbPortOperFec | FEC 取得失敗時のフォールバック文字列 |
| `supported_fecs` 空値 | `"N/A"` | 3292 | FEC モードセットが空の場合に push するシングルエントリ文字列 |
| `host_tx_ready` 初期値 | `"false"` | 2202 | initHostTxReadyState() — STATE_DB にフィールドが存在しない場合の初期書き込み値 |
| `host_tx_ready` 失敗値 | `"false"` | 2236, 2248 | SAI 失敗 / admin DOWN 時のフォールバック値 |
| `host_tx_ready` 成功値 | `"true"` | 2256 | admin UP + SAI 成功 + CMIS 非対応時の書き込み値 |
| `link_training_status` デフォルト | `"off"` | 11351 | LT 無効 / admin DOWN / `m_cap_lt==0` 時の初期値 |
| `link_training_status` 中間状態 | `"on"` | 11362 | LT 有効だが SAI RX status 取得失敗時の値 |
| `link_training_status` 訓練完了 | `"trained"` | link_training_rx_status_map:191 | `SAI_PORT_LINK_TRAINING_RX_STATUS_TRAINED` の文字列化定数 |
| `link_training_status` 未訓練 | `"not_trained"` | link_training_rx_status_map:190 | `SAI_PORT_LINK_TRAINING_RX_STATUS_NOT_TRAINED` の文字列化定数 |
| `link_training_failure` 値群 | `"none"`, `"frame_lock"`, `"snr_low"`, `"timeout"` | link_training_failure_map:181-185 | 各 SAI 失敗ステータスの文字列マッピング定数 |
| `rmt_adv_speeds` フォールバック | `"N/A"` | 11327 | admin DOWN または `getPortAdvSpeeds()` 失敗時 |
| `phy_ctrl_unreliable_los` 値 | `"true"` / `"false"` | 5200 | `p.m_unreliable_los` を `"true"/"false"` 文字列で直接 hset |

## 定数の出所（SAI 列挙値マッピング）

`link_training_failure_map` と `link_training_rx_status_map` は `portsorch.cpp` ファイルスコープの
`static map<...>` として定義されており、外部設定や YANG で変更不可のハードコード定数。

```cpp
// portsorch.cpp:180-192
static map<sai_port_link_training_failure_status_t, string> link_training_failure_map =
{
    { SAI_PORT_LINK_TRAINING_FAILURE_STATUS_NO_ERROR, "none" },
    { SAI_PORT_LINK_TRAINING_FAILURE_STATUS_FRAME_LOCK_ERROR, "frame_lock"},
    { SAI_PORT_LINK_TRAINING_FAILURE_STATUS_SNR_LOWER_THRESHOLD, "snr_low"},
    { SAI_PORT_LINK_TRAINING_FAILURE_STATUS_TIME_OUT, "timeout"}
};

static map<sai_port_link_training_rx_status_t, string> link_training_rx_status_map =
{
    { SAI_PORT_LINK_TRAINING_RX_STATUS_NOT_TRAINED, "not_trained" },
    { SAI_PORT_LINK_TRAINING_RX_STATUS_TRAINED, "trained"}
};
```

## 結論

- `state="ok"` は定義によりただ 1 つの値しか存在しない設計定数
- `"N/A"` は複数フィールドで共通のフォールバック文字列リテラルとして使われる
- `link_training_status` の値セットは SAI 列挙型を文字列化したハードコードマップから生成される
- これらの定数は YANG スキーマ (`sonic-port.yang`) に列挙型として定義されていない（STATE_DB フィールドのため）
