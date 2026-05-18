# voq-inband-interface Phase E — ハードコード定数調査

## 調査対象
- `sonic-swss/cfgmgr/intfmgr.cpp`
- `sonic-swss/cfgmgr/intfmgrd.cpp`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-voq-inband-interface.yang`

## 検出定数

### intfmgr.cpp — VOQ 固有定数

| 定数 / マジック値 | 値 | 定義場所 | 意味 |
|------------------|-----|----------|------|
| IPv6 metric (VOQ 専用) | `256` | `intfmgr.cpp:105` | `switch_type=="voq"` のとき IPv6 アドレス追加コマンドに `metric 256` を付与。カーネルのデフォルト connected route metric (256) と一致させ、eBGP / iBGP inband 経路を同一 ECMP グループに収めるため |
| IPv6 broadcast 付与閾値 | prefixLen `< 127` | `intfmgr.cpp:108` | `/127` 以上では broadcast オプションなしで `ip -6 address add` を実行 |

### intfmgrd.cpp — ループタイムアウト

| 定数 | 値 | 定義場所 | 意味 |
|------|----|----------|------|
| `SELECT_TIMEOUT` | `1000` ms | `intfmgrd.cpp:17` | メインループの `s.select()` タイムアウト。設定反映の最大遅延は 1 秒 |

### sonic-voq-inband-interface.yang — パターン / 列挙制約

| 制約 | 値 | 定義場所 | 意味 |
|------|----|----------|------|
| `name` パターン | `"Ethernet-IB[0-9]+"` | `sonic-voq-inband-interface.yang:32` | インバンド IF 名の YANG pattern 制約。違反は YANG バリデーションで reject |
| `inband_type` パターン | `"port\|Port"` | `sonic-voq-inband-interface.yang:38` | インバンドタイプの許容値。2 値のみ |
| `inband_type` デフォルト | `"port"` | `sonic-voq-inband-interface.yang` | YANG `default` 指定値 |
