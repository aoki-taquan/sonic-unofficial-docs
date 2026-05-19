# state-db-port — Phase E ハードコード定数調査ノート

調査対象:
- `sonic-swss/orchagent/portsorch.cpp`
- `sonic-swss/orchagent/portsorch.h`
- `sonic-swss/portsyncd/linksync.cpp`

調査日: 2026-05-19

## 検出した定数一覧

### portsorch.cpp / portsorch.h

| 定数 | 値 | 定義場所 | 用途 |
|------|-----|----------|------|
| `PORT_STATE_POLLING_SEC` | `5` | `portsorch.cpp:86` | `m_port_state_poller` の SelectableTimer 周期 [秒]。ポート oper 状態をポーリングで再確認する間隔 |
| `PORT_SPEED_LIST_DEFAULT_SIZE` | `16` | `portsorch.cpp:85` | `getPortSupportedSpeeds()` で SAI クエリ用の vector 初期サイズ。SAI が返す速度数が 16 超の場合は自動リサイズ |
| `MAX_MACSEC_SECTAG_SIZE` | `32` | `portsorch.h:28` | MACsec SecTAG ヘッダ分として MTU から差し引くバイト数。`setPortMtu()` で `mtu > 32` のとき SAI の MTU を `mtu - 32` で設定する (`portsorch.cpp:6757-6759`) |
| `"N/A"` | 文字列リテラル | `portsorch.cpp:9855, 9919, 3292` | speed/fec 取得失敗時のフォールバック文字列。フィールド不在ではなく文字列 `"N/A"` が書き込まれる |
| `"false"` | 文字列リテラル | `portsorch.cpp:2203, 2274` | `host_tx_ready` の初期値および admin DOWN / Gearbox 失敗時の値 |
| `"off"` | 文字列リテラル | `portsorch.cpp:11351` | `link_training_status` のローカル変数初期値（LT 無効時） |

### linksync.cpp

| 定数 | 値 | 定義場所 | 用途 |
|------|-----|----------|------|
| `"ok"` | 文字列リテラル | `linksync.cpp:196` | `state` フィールドの固定値。RTM_NEWLINK 受信時に必ず書き込まれ、他の値はコードに存在しない |
| `INTFS_PREFIX` | `"Ethernet"` | `linksync.cpp:30` | フロントパネルインタフェースの名前プレフィックス。RTM_NEWLINK の key マッチに使用 |

## 注意点

- `PORT_STATE_POLLING_SEC = 5` は CONFIG_DB から変更不可のハードコード値。SAI event-driven 通知（`refreshPortStatus()`）が失敗した際のフォールバックポーリング間隔として機能する
- `MAX_MACSEC_SECTAG_SIZE = 32` は MACsec の SecTAG サイズを定数化したもの。`state` フィールドには直接影響しないが、`mtu` フィールドの値が MACsec 有効環境では ASIC 実際設定値よりも 32 大きくなるという乖離を生む
- `"N/A"` は `speed` と `fec` 両方で使用されるが、文脈が異なる。`speed=0` は SAI 未取得、`fec` の `"N/A"` は SAI 未対応または変換失敗
