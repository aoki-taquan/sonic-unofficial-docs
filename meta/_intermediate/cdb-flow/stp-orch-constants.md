# stp-orch — Phase E ハードコード定数 調査メモ

ソース: `orchagent/stporch.h`, `orchagent/stporch.cpp`
ref: 4305596156d70e9797e8a881b3d19b46de0bce0d

## マクロ定数 (stporch.h)

| マクロ | 値 | 用途 |
|---|---|---|
| `STP_INVALID_INSTANCE` | `0xFFFF` | stp_instance フィールド欠落時の番兵値。`doStpTask()` で SET 処理スキップ判定に使用 |
| `APP_STP_INST_PORT_FLUSH_TABLE_NAME` | `"STP_INST_PORT_FLUSH_TABLE"` | APPL_DB テーブル名文字列 |

## 数値 enum: stp_state (stporch.h:11-19)

| enum 値 | 数値 | 意味 |
|---|---|---|
| `STP_STATE_DISABLED` | 0 | ポート無効 |
| `STP_STATE_BLOCKING` | 1 | ブロッキング |
| `STP_STATE_LISTENING` | 2 | リスニング |
| `STP_STATE_LEARNING` | 3 | ラーニング |
| `STP_STATE_FORWARDING` | 4 | フォワーディング |
| `STP_STATE_INVALID` | 5 | 番兵値: state フィールド欠落または不正値時 |

## SAI 初期値ハードコード (stporch.cpp:245)

STP ポート作成時の初期 SAI 状態: `SAI_STP_PORT_STATE_BLOCKING` (ハードコード)

## off-by-one 定数 (stporch.cpp:605)

`m_maxStpInstance = (sai_uint16_t)max_stp_instances - 1`
STATE_DB へは `max_stp_instances - 1` を書き込む。SAI の `MAX_STP_INSTANCE` から最終インデックスへの変換 (意図的 off-by-one)。
