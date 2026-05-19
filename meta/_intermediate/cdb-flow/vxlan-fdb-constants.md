# VXLAN_FDB_TABLE ハードコード定数 (Phase E)

## ソース
- sonic-swss/fdbsyncd/fdbsync.h (master)
- sonic-swss/fdbsyncd/fdbsync.cpp (master)
- sonic-swss/orchagent/fdborch.h (master)
- sonic-swss-common/common/schema.h (master)

## テーブル名定数 (schema.h)

```c
// sonic-swss-common/common/schema.h:87-88
#define APP_VXLAN_FDB_TABLE_NAME          "VXLAN_FDB_TABLE"
#define APP_VXLAN_REMOTE_VNI_TABLE_NAME   "VXLAN_REMOTE_VNI_TABLE"
```

APP_DB に書き込まれるテーブル名は `#define` で固定されており、設定で変更不可。

## ブリッジインタフェース名プレフィックス (fdbsync.cpp)

```c
// sonic-swss/fdbsyncd/fdbsync.cpp:22
#define VXLAN_BR_IF_NAME_PREFIX    "Brvxlan"
```

fdbsyncd が VXLAN ブリッジを識別するためのプレフィックス。`isVxlanIntf` 判定に使用。

## warm-restart タイマー (fdbsync.h)

```c
// sonic-swss/fdbsyncd/fdbsync.h:15
#define DEFAULT_FDBSYNC_WARMSTART_TIMER 120
```

warm-restart 時に APP_DB への書き込みをバッファリングする秒数。この期間中は reconcile が完了せず古いエントリが残存する可能性がある。設定で変更不可。

## FDB エントリ種別文字列 (ハードコード)

| 値 | 意味 | コード根拠 |
|----|------|-----------|
| `"dynamic"` | EVPN 動的学習 MAC（`NUD_NOARP` フラグなし） | `fdbsync.cpp:801` |
| `"static"` | 静的 MAC（`NUD_NOARP` フラグあり） | `fdbsync.cpp:797` |

これら 2 値のみが `type` フィールドとして有効。orchagent の `fdborch.cpp:770` は受信側でも `"dynamic"` をデフォルト初期化する。

## FDB Origin 列挙値 (fdborch.h)

```c
// sonic-swss/orchagent/fdborch.h:10-14
FDB_ORIGIN_INVALID = 0,
FDB_ORIGIN_LEARN = 1,
FDB_ORIGIN_PROVISIONED = 2,
FDB_ORIGIN_VXLAN_ADVERTIZED = 4,
FDB_ORIGIN_MCLAG_ADVERTIZED = 8
```

`APP_VXLAN_FDB_TABLE_NAME` から来るエントリは必ず `FDB_ORIGIN_VXLAN_ADVERTIZED = 4` が設定される（`fdborch.cpp:719-722`）。この値は設定で変更不可。
