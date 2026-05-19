# MCLAG_INTERFACE ハードコード定数調査 (Phase E)

調査日: 2026-05-19

## 調査対象ファイル

- `sonic-swss/mclagsyncd/mclaglink.h` (sha: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/mclagsyncd/mclag.h` (sha: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-utilities/config/mclag.py` (sha: a3e5b4c9fb7a95e213d08f8761e6c94f02a18b41)

## 発見した定数

### mclaglink.h

```c
#define MAX_L_PORT_NAME 20

struct mclag_iface_cfg_info {
    int op_type;
    int domain_id;
    char mclag_iface[MAX_L_PORT_NAME];  // if_name 転送上限 19 バイト（null 込み 20）
};
```

- MCLAG_INTERFACE の `if_name` (PortChannel 名) は `mclag_iface_cfg_info.mclag_iface[]` に格納されて iccpd に転送される
- `MAX_L_PORT_NAME = 20` のため、実効上限は 19 バイト

### mclag.h

```c
#define MCLAG_MAX_SEND_MSG_LEN 4096
#define MCLAG_PROTO_VERSION 1
#define MCLAG_DEFAULT_PORT 2626
```

- `MCLAG_MAX_SEND_MSG_LEN = 4096`: 送信バッファ上限。1 バッチに詰め込める `mclag_iface_cfg_info` 数は `4096 / sizeof(mclag_iface_cfg_info)` で決まる
- `MCLAG_PROTO_VERSION = 1`: IPC プロトコルバージョン固定

### config/mclag.py (CLI)

```python
CFG_PORTCHANNEL_PREFIX = "PortChannel"
CFG_PORTCHANNEL_PREFIX_LEN = 11
CFG_PORTCHANNEL_MAX_VAL = 9999
CFG_PORTCHANNEL_NAME_TOTAL_LEN_MAX = 15
```

- `if_name` に設定できる PortChannel 名: `PortChannel0` 〜 `PortChannel9999`（CLI 強制）
- `if_type = "PortChannel"` は固定値として書き込まれる（`config/mclag.py:293`）
- `MlagOrch` は `if_type` を参照しない（プレースホルダ）

## 影響範囲

1. `MAX_L_PORT_NAME = 20` により、カスタム PortChannel 名が 19 バイトを超えると無言切り捨て
2. 通常の命名規則 (`PortChannelXXXX`, 最大 15 文字) では問題なし
3. `MCLAG_MAX_SEND_MSG_LEN = 4096` は大量 MCLAG_INTERFACE 一括送信時のバッチサイズに影響
