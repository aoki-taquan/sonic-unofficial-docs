# VLAN — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-swss/cfgmgr/vlanmgr.cpp`
- `sonic-swss/orchagent/portsorch.cpp`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vlan.yang`

---

## 発見された定数一覧

### vlanmgr.cpp (#define)

| 定数名 | 値 | 用途 |
|--------|-----|------|
| `DOT1Q_BRIDGE_NAME` | `"Bridge"` | Linux dot1q ブリッジデバイス名（固定） |
| `VLAN_PREFIX` | `"Vlan"` | VLAN インタフェース名プレフィクス |
| `LAG_PREFIX` | `"PortChannel"` | LAG インタフェース名プレフィクス |
| `DEFAULT_VLAN_ID` | `"1"` | Bridge 初期化時に削除する IEEE 802.1Q デフォルト VLAN |
| `DEFAULT_MTU_STR` | `"9100"` | MTU 省略時に APP_DB へ注入するデフォルト値（バイト） |
| `VLAN_HLEN` | `4` | IEEE 802.1Q VLAN ヘッダ長（バイト）— 定義のみ、コード中未参照 |

### portsorch.cpp (#define)

| 定数名 | 値 | 用途 |
|--------|-----|------|
| `DEFAULT_SYSTEM_PORT_MTU` | `9100` | システムポートデフォルト MTU（ポートオブジェクト初期化時に使用） |
| `DEFAULT_VLAN_ID` | `1` (int) | デフォルト VLAN ID（vlanmgr.cpp の文字列版とは別定義） |
| `MAX_VALID_VLAN_ID` | `4094` | サブインタフェース VLAN ID 上限チェック用 |
| `VLAN_PREFIX` | `"Vlan"` | VLAN エイリアス生成に使用 |

### SAI デフォルト (portsorch.cpp:7409-7410)

| 属性 | デフォルト値 | 備考 |
|------|-------------|------|
| `uuc_flood_type` | `SAI_VLAN_FLOOD_CONTROL_TYPE_ALL` | create_vlan 時の初期 UUC flooding 制御型 |
| `bc_flood_type` | `SAI_VLAN_FLOOD_CONTROL_TYPE_ALL` | create_vlan 時の初期 BC flooding 制御型 |

### YANG モデル制約 (sonic-vlan.yang)

| 対象 | 制約 | 値 |
|------|------|-----|
| `VLAN.name` | pattern | `Vlan(409[0-5]|40[0-8][0-9]|[1-3][0-9]{3}|[1-9][0-9]{2}|[1-9][0-9]|[2-9])` |
| `VLAN.vlanid` | range | `2..4094` |
| `VLAN.description` | length | `1..255` |
| `VLAN.mtu` | range | `1..9216` |
| `VLAN_INTERFACE.nat_zone` | range | `0..3`（デフォルト `0`） |
| `VLAN_INTERFACE.mpls` | enum | `enable` / `disable`（デフォルト `disable`） |

---

## タイミング・sleep 定数

- **タイマー・sleep なし**: vlanmgr.cpp に明示的な sleep / usleep / タイムアウト定数は存在しない。
- **retry 判断**: member port/LAG が未 ready の場合のみ retry あり（タイムアウト値なし、次 select サイクルで再試行）。
- **warm-restart**: replayDone フラグで制御。明示的な待機定数なし。

---

## 特記事項

1. **`DEFAULT_MTU_STR = "9100"` の二重定義**: vlanmgr.cpp (文字列) と portsorch.cpp (`DEFAULT_SYSTEM_PORT_MTU = 9100` int) で独立に定義されており、参照箇所も異なる。
2. **`VLAN_HLEN = 4`**: vlanmgr.cpp で定義されているが、同ファイル内で未使用（dead define）。IEEE 802.1Q ヘッダ長 4 バイトを表す意図だが参照なし。
3. **`DEFAULT_VLAN_ID = "1"` (文字列)**: Bridge 初期化時に `bridge vlan del vid 1 dev Bridge self` を実行するためのリテラル。IEEE 802.1Q デフォルト VLAN 1 をブリッジから削除する標準手順。
4. **SAI flooding デフォルト**: `SAI_VLAN_FLOOD_CONTROL_TYPE_ALL` は create_vlan 時の初期値。プラットフォーム SAI によって後から上書き可能。
5. **YANG mtu 上限 9216**: Jumbo frame 最大値として定義。コードの `DEFAULT_MTU_STR = "9100"` はこの範囲内。

---

## 出典

- `sonic-swss/cfgmgr/vlanmgr.cpp` lines 15-20, 96, 139, 357, 424, 428
- `sonic-swss/orchagent/portsorch.cpp` lines 79-82, 2016, 7409-7410
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vlan.yang` lines 105, 219, 225, 239, 257
