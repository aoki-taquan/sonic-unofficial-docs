# BFD_SESSION — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-swss/orchagent/bfdorch.cpp`
- `sonic-swss/orchagent/bfdorch.h`

---

## 発見された定数一覧

### bfdorch.cpp — `#define` マクロ定数

| 定数名 | 値 | 用途 | ソース |
|--------|----|------|--------|
| `BFD_SESSION_DEFAULT_TX_INTERVAL` | `1000` (ms) | `tx_interval` フィールド未指定時のデフォルト送信間隔 | `bfdorch.cpp:15` |
| `BFD_SESSION_DEFAULT_RX_INTERVAL` | `1000` (ms) | `rx_interval` フィールド未指定時のデフォルト最小受信間隔 | `bfdorch.cpp:16` |
| `BFD_SESSION_DEFAULT_DETECT_MULTIPLIER` | `10` | `multiplier` フィールド未指定時のデフォルト検知乗数 (hardware BFD 経路) | `bfdorch.cpp:17` |
| `BFD_SESSION_DEFAULT_TOS` | `192` (0xC0) | `tos` フィールド未指定時のデフォルト。DSCP 48 (EF) << 2 \| ECN 0 | `bfdorch.cpp:18-19` |
| `BFD_SESSION_MILLISECOND_TO_MICROSECOND` | `1000` | ms → μs 変換係数。SAI `SAI_BFD_SESSION_ATTR_MIN_TX` / `MIN_RX` 投入時に `tx_interval × 1000`、`rx_interval × 1000` で適用 | `bfdorch.cpp:20, 452, 457` |
| `BFD_SRCPORTINIT` | `49152` | BFD UDP 送信元ポート範囲下限 (IANA dynamic/ephemeral 範囲開始) | `bfdorch.cpp:21` |
| `BFD_SRCPORTMAX` | `65536` | BFD UDP 送信元ポート範囲上限 (排他、実際の最大値は 65535) | `bfdorch.cpp:22` |
| `NUM_BFD_SRCPORT_RETRIES` | `3` | UDP 送信元ポート衝突時の自動 retry 回数。`retry_create_bfd_session()` で消費 | `bfdorch.cpp:23, 596` |

### bfdorch.cpp — `type` 文字列 ⇄ SAI enum マップ (双方向)

#### `session_type_map` (CONFIG_DB 文字列 → SAI enum)

| key (文字列) | value (SAI enum) | 用途 |
|--------------|------------------|------|
| `"demand_active"` | `SAI_BFD_SESSION_TYPE_DEMAND_ACTIVE` | CONFIG_DB の `type` フィールドからの parse |
| `"demand_passive"` | `SAI_BFD_SESSION_TYPE_DEMAND_PASSIVE` | 同上 |
| `"async_active"` | `SAI_BFD_SESSION_TYPE_ASYNC_ACTIVE` | 同上 (既定) |
| `"async_passive"` | `SAI_BFD_SESSION_TYPE_ASYNC_PASSIVE` | 同上 |

ソース: `bfdorch.cpp:33-39`

#### `session_type_lookup` (SAI enum → 文字列、逆引き)

| key (SAI enum) | value (文字列) | 用途 |
|---------------|---------------|------|
| `SAI_BFD_SESSION_TYPE_DEMAND_ACTIVE` | `"demand_active"` | STATE_DB `BFD_SESSION_TABLE.type` 書き戻し |
| `SAI_BFD_SESSION_TYPE_DEMAND_PASSIVE` | `"demand_passive"` | 同上 |
| `SAI_BFD_SESSION_TYPE_ASYNC_ACTIVE` | `"async_active"` | 同上 |
| `SAI_BFD_SESSION_TYPE_ASYNC_PASSIVE` | `"async_passive"` | 同上 |

ソース: `bfdorch.cpp:41-47`

### bfdorch.cpp — `session_state_lookup` (SAI session state → 文字列)

| key (SAI enum) | value (文字列) | 用途 |
|---------------|----------------|------|
| `SAI_BFD_SESSION_STATE_ADMIN_DOWN` | `"Admin_Down"` | STATE_DB の `state` フィールドへ書き戻し |
| `SAI_BFD_SESSION_STATE_DOWN` | `"Down"` | 同上 (初期値・通知欠落時) |
| `SAI_BFD_SESSION_STATE_INIT` | `"Init"` | 同上 |
| `SAI_BFD_SESSION_STATE_UP` | `"Up"` | 同上 |

ソース: `bfdorch.cpp:49-55`

### bfdorch.cpp — `create_bfd_session()` 内のリテラル既定値・暗黙定数

| 位置 | 識別子 / リテラル | 値 | 用途 |
|------|------------------|----|------|
| L340 | `bfd_session_type` 初期値 | `SAI_BFD_SESSION_TYPE_ASYNC_ACTIVE` | `type` 未指定時のフォールバック (`async_active`) |
| L341 | `encapsulation_type` 初期値 | `SAI_BFD_ENCAPSULATION_TYPE_NONE` | 常に NONE 固定。`bfdorch.cpp` 内に enum を変える分岐なし |
| L345 | `multiplier` 初期値 | `BFD_SESSION_DEFAULT_DETECT_MULTIPLIER` (`10`) | 同上 |
| L346 | `tos` 初期値 | `BFD_SESSION_DEFAULT_TOS` (`192`) | 同上 |
| L347 | `multihop` 初期値 | `false` | 同上 |
| L431 | `SAI_BFD_SESSION_ATTR_REMOTE_DISCRIMINATOR` 値 | `0` | 常に 0 で投入 (peer 検出後に SAI 内部で更新される想定) |
| L439 | `SAI_BFD_SESSION_ATTR_IPHDR_VERSION` 値 | `4` または `6` (リテラル) | `src_ip.isV4() ? 4 : 6` で確定 |
| L506 | `SAI_BFD_SESSION_ATTR_HW_LOOKUP_VALID` 値 | `false` (リテラル) | `interface != "default"` のみセット (hw lookup 無効) |
| L562 | 初期 `state` 出力値 | `session_state_lookup.at(SAI_BFD_SESSION_STATE_DOWN)` (`"Down"`) | セッション作成直後の STATE_DB 初期 state |

### bfdorch.cpp — SAI 属性 ID 一覧 (`create_bfd_session` で投入)

`bfdorch.cpp:415-541` で常時セットされる SAI 属性。すべて SAI 標準識別子で、bfdorch 側にエイリアス定義はない。

| SAI 属性 ID | 投入条件 | データ型 |
|-------------|----------|----------|
| `SAI_BFD_SESSION_ATTR_TYPE` | 常時 | `s32` (enum) |
| `SAI_BFD_SESSION_ATTR_LOCAL_DISCRIMINATOR` | 常時 (`bfd_gen_id()` で生成) | `u32` |
| `SAI_BFD_SESSION_ATTR_UDP_SRC_PORT` | 常時 (`bfd_src_port()` で `49152..65535` から選択) | `u32` |
| `SAI_BFD_SESSION_ATTR_REMOTE_DISCRIMINATOR` | 常時 (固定 `0`) | `u32` |
| `SAI_BFD_SESSION_ATTR_BFD_ENCAPSULATION_TYPE` | 常時 (固定 `NONE`) | `s32` (enum) |
| `SAI_BFD_SESSION_ATTR_IPHDR_VERSION` | 常時 (`4` or `6`) | `u8` |
| `SAI_BFD_SESSION_ATTR_SRC_IP_ADDRESS` | 常時 | `ipaddr` |
| `SAI_BFD_SESSION_ATTR_DST_IP_ADDRESS` | 常時 | `ipaddr` |
| `SAI_BFD_SESSION_ATTR_MIN_TX` | 常時 (`tx_interval × 1000` μs) | `u32` |
| `SAI_BFD_SESSION_ATTR_MIN_RX` | 常時 (`rx_interval × 1000` μs) | `u32` |
| `SAI_BFD_SESSION_ATTR_MULTIPLIER` | 常時 | `u8` |
| `SAI_BFD_SESSION_ATTR_TOS` | 常時 | `u8` |
| `SAI_BFD_SESSION_ATTR_MULTIHOP` | `multihop == true` のみ | `booldata` |
| `SAI_BFD_SESSION_ATTR_HW_LOOKUP_VALID` | `interface != "default"` のみ (値 `false`) | `booldata` |
| `SAI_BFD_SESSION_ATTR_PORT` | `interface != "default"` のみ | `oid` |
| `SAI_BFD_SESSION_ATTR_SRC_MAC_ADDRESS` | `interface != "default"` のみ | `mac` |
| `SAI_BFD_SESSION_ATTR_DST_MAC_ADDRESS` | `interface != "default"` のみ | `mac` |
| `SAI_BFD_SESSION_ATTR_VIRTUAL_ROUTER` | `interface == "default"` のみ (`gVirtualRouterId` or VRF id) | `oid` |

### bfdorch.cpp — その他の文字列リテラル

| リテラル | 用途 | ソース |
|----------|------|--------|
| `"default"` | VRF 名・interface 名のセンチネル。VRF=`"default"` は `gVirtualRouterId` を使用、interface=`"default"` は hardware lookup 有効 (`HW_LOOKUP_VALID=true` 既定で SAI 属性自体セットしない) | `bfdorch.cpp:498, 521, 534` |
| state DB key 区切り | `":"` (SAI BFD session 用 STATE_DB key の組立) | `createStateDBKey()` (`bfdorch.cpp:95+`), `get_state_db_key()` (`bfdorch.cpp:636+`) |

---

## 備考

- **`tx_interval` / `rx_interval` の単位**: CONFIG_DB / APPL_DB ではミリ秒 (ms)、SAI 投入時はマイクロ秒 (μs)。変換係数は `BFD_SESSION_MILLISECOND_TO_MICROSECOND = 1000` 固定。FRR (software BFD) では ms をそのまま渡すため、bgpcfgd `BfdMgr` 経路ではこの変換が発生しない。
- **`BFD_SRCPORTMAX = 65536` の半開区間表現**: `bfd_src_port()` は `[BFD_SRCPORTINIT, BFD_SRCPORTMAX)` の半開区間で乱数選択する想定で、実効最大値は `65535`。
- **`multiplier` のデフォルトは経路で異なる**: hardware BFD では `10` (`BFD_SESSION_DEFAULT_DETECT_MULTIPLIER`)、software BFD (bgpcfgd/BfdMgr) では `3` (`managers_bfd.py:13`)。`bfdorch.cpp` 内では `10` のみ参照。
- **`SAI_BFD_ENCAPSULATION_TYPE_NONE` 固定**: IP-in-IP 等の他のカプセル化は `bfdorch.cpp` では選択肢に存在しない。将来 SAI 側で対応が広がっても CONFIG_DB から指定する方法はない。
- **type マップは双方向**: `session_type_map` (parse 用) と `session_type_lookup` (STATE_DB 書き戻し用) を別 const map として保持する設計。enum とリテラル文字列が 1:1 で対応するため、片方の追加変更時はもう一方も同時更新する必要がある。
