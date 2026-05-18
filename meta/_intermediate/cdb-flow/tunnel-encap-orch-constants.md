# VxlanTunnelOrch encap 処理詳細 — Phase E ハードコード定数スキャンノート

対象ページ: `docs/reference/config-db/tunnel-encap-orch.md`
対象コード: `orchagent/vxlanorch.h`, `orchagent/vxlanorch.cpp`
スキャン日: 2026-05-18
スキャン範囲: `vxlanorch.h` 全 #define / 定数宣言、`vxlanorch.cpp` の固定値 SAI 属性設定箇所

---

## 検出したハードコード定数

### SAI トンネル属性の固定値

| 定数 / 値 | SAI 属性 | コード箇所 | 備考 |
|-----------|---------|---------|------|
| `SAI_TUNNEL_TYPE_VXLAN` | `SAI_TUNNEL_ATTR_TYPE` | `vxlanorch.cpp:304` | トンネルタイプは常に VXLAN。CONFIG_DB フィールドなし |
| `SAI_TUNNEL_PEER_MODE_P2MP` | `SAI_TUNNEL_ATTR_PEER_MODE` | `vxlanorch.cpp:368` | CLI 作成トンネル (`TNL_CREATION_SRC_CLI`) 固定 |
| `SAI_TUNNEL_PEER_MODE_P2P` | `SAI_TUNNEL_ATTR_PEER_MODE` | `vxlanorch.cpp:359` | EVPN DIP トンネル (`TNL_CREATION_SRC_EVPN`) 固定 |
| `SAI_TUNNEL_TTL_MODE_PIPE_MODEL` | `SAI_TUNNEL_ATTR_ENCAP_TTL_MODE` | `vxlanorch.cpp:388` | `encap_ttl != 0` 時の自動設定。フィールドで選択不可 |
| `gUnderlayIfId` | `SAI_TUNNEL_ATTR_UNDERLAY_INTERFACE` | `vxlanorch.cpp:307-309` | グローバル underlay RIF 固定 |

### 数値定数

| 定数名 | 値 | 定義 | 用途 |
|--------|----|------|------|
| `DEFAULT_TUNNEL_ENCAP_TTL` | `255` | `vxlanorch.h:49` | createTunnelHw() デフォルト引数 |
| `MAX_VNI_ID` | `16777215` | `vxlanorch.h:48` | VNI 上限 (2^24 − 1)。超過は恒久エラー |
| `MIN_VLAN_ID` | `1` | `vxlanorch.h:45` | VLAN 下限 |
| `MAX_VLAN_ID` | `4095` | `vxlanorch.h:46` | VLAN 上限 |

### FlexCounter 定数

| 定数名 | 値 | 定義 | 用途 |
|--------|----|------|------|
| `TUNNEL_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"TUNNEL_STAT_COUNTER"` | `vxlanorch.h:39` | カウンタグループ名 |
| `TUNNEL_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | `10000` | `vxlanorch.h:40` | ポーリング間隔 ms（10秒固定） |
| `FLEX_COUNTER_UPD_INTERVAL` | `1` | `vxlanorch.cpp:36` | 更新タイマー秒数（1秒固定） |

### mapper モード定数 (tunnel_map_use_t)

コードで用途が固定されており CONFIG_DB フィールドによる選択不可:
- `TUNNEL_MAP_USE_DEDICATED_ENCAP_DECAP`: L3VNI / Bridge VNI (`vxlanorch.cpp:2067`)
- `TUNNEL_MAP_USE_COMMON_ENCAP_DECAP`: EVPN DIP トンネル (`vxlanorch.cpp:1169`)
- `TUNNEL_MAP_USE_DECAP_ONLY`: VLAN MAP 特定ケース

---

## ページ反映方針

- `<!-- failure -->` ブロックの直後、「関連 CONFIG_DB / YANG / CLI」の直前に `<!-- constants -->` ブロックを挿入。
- SAI 属性固定値テーブル + 数値定数テーブル + FlexCounter 定数テーブル + mapper モード説明を含める。
