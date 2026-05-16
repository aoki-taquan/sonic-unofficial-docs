# BFD_SESSION テーブル 暗黙参照スキャン (Phase C)

`docs/reference/config-db/bfd-session.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソースは:

- `sonic-net/sonic-swss/orchagent/bfdorch.cpp` (`BfdOrch::doTask` / `create_bfd_session` / `BgpGlobalStateOrch`)
- `sonic-net/sonic-buildimage/src/sonic-bgpcfgd/staticroutebfd/main.py` (`StaticRouteBfd`)
- `sonic-net/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bfd.py` (`BfdMgr`)

`BFD_SESSION` は YANG schema を持たず subscribe/leafref 経由の明示参照を宣言しないが、`bfdorch` が SAI 投入時に他 CONFIG_DB テーブル由来のオブジェクト ID / 状態を直接参照する。本資料ではこれら **コード経路ベースの暗黙参照** を列挙する。

## スキャン手順

```bash
# 1. bfdorch.cpp が直接参照する gPortsOrch / VRFOrch / BgpGlobalStateOrch
grep -nE 'gPortsOrch|VRFOrch|getVRFid|BgpGlobalStateOrch|getSoftwareBfd|getTsaState' \
    .cache/sonic-sources/sonic-swss/orchagent/bfdorch.cpp

# 2. staticroutebfd から STATIC_ROUTE → BFD_SESSION_TABLE への書込み経路
grep -nE 'STATIC_ROUTE|BFD_SESSION_TABLE|subscribe' \
    .cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/staticroutebfd/main.py

# 3. BfdMgr (software BFD) の購読対象
grep -nE 'subscribe|SOFTWARE_BFD|STATE_DB' \
    .cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bfd.py
```

## 検出された暗黙参照テーブル

### CONFIG_DB レベル

| 参照先テーブル | 参照タイミング | 用途 | 方向 | evidence |
|---|---|---|---|---|
| `PORT` (`PORT|<alias>`) | `create_bfd_session()` で `interface != "default"` のとき | `gPortsOrch->getPort(alias, port)` で `Port::m_port_id` と `Port::m_mac` を取得し、SAI `BFD_SESSION_ATTR_PORT` / `SRC_MAC_ADDRESS` を埋める | 入力依存 (BFD_SESSION → PORT) | `bfdorch.cpp:482-515` |
| `VRF` (`VRF|<name>`) | `create_bfd_session()` で `vrf != "default"` かつ `interface == "default"` のとき | `VRFOrch::getVRFid(vrf_name)` で SAI virtual_router OID を取得し、`BFD_SESSION_ATTR_VIRTUAL_ROUTER` に投入 | 入力依存 | `bfdorch.cpp:530-541` |
| `BGP_DEVICE_GLOBAL` (`STATE` の `tsa_enabled` / `use_software_bfd`) | `doTask()` 毎周回 + TSA state change 通知時 | `BgpGlobalStateOrch::getSoftwareBfd()` / `getTsaState()` で経路 (hw/sw) と TSA shutdown 挙動を決定 | 制御依存 | `bfdorch.cpp:114-138, 683-748` |
| `STATIC_ROUTE` (`STATIC_ROUTE|<vrf>|<prefix>`) | `staticroutebfd` プロセスが CONFIG_DB を subscribe し、対応する BFD セッションを APPL_DB `BFD_SESSION_TABLE` に push | static route の BFD 監視ピアごとに APPL_DB `BFD_SESSION_TABLE` を書き込む (`tx_interval=50` / `rx_interval=50`) | **逆方向** (STATIC_ROUTE → BFD_SESSION) | `staticroutebfd/main.py:23-24, 118-120, 283-288, 366-559, 720-730` |

> 上記は **bfdorch が CONFIG_DB を直接 subscribe する** わけではない。`PORT` / `VRF` は orchagent 内 in-memory state (gPortsOrch / VRFOrch) 経由、`BGP_DEVICE_GLOBAL` は `BgpGlobalStateOrch` 経由で参照される。

### STATE_DB / APPL_DB レベル

| 参照先 | 役割 | 経路 | evidence |
|---|---|---|---|
| `STATE_DB.SOFTWARE_BFD_SESSION_TABLE` | `use_software_bfd=true` の場合の中継。`bfdorch` が CONFIG_DB から転記し、`bgpcfgd/BfdMgr` が読み出して FRR bfdd に投入 | bfdorch (write) → BfdMgr (read/subscribe) | `bfdorch.cpp:114-138` / `managers_bfd.py` 全般 |
| `APPL_DB.BFD_SESSION_TABLE` | hardware BFD の SAI 投入直前段。`orchagent` 内の APPL_DB 経路 + `staticroutebfd` の ProducerStateTable | `staticroutebfd` (producer) → `bfdorch` (subscriber) | `staticroutebfd/main.py:118-120` / `bfdorch.cpp` consumer 経路 |
| `STATE_DB.BFD_SESSION_TABLE` | hardware BFD の状態通知 (`UP` / `DOWN`)。SAI notification handler が更新 | bfdorch (write) → staticroutebfd `bfd_state_set_handler` (read/subscribe) | `bfdorch.cpp:274-302` / `staticroutebfd/main.py:296-300, 641-710` |

### 直接参照されない隣接テーブル (範囲外)

- **`INTERFACE` / `PORTCHANNEL_INTERFACE` / `LOOPBACK_INTERFACE`**: `bfdorch.cpp` は IP アドレスの所属を確認しない。`local_addr` の妥当性検証は SAI 実装側に委ねる。`staticroutebfd` は `INTERFACE` / `PORTCHANNEL_INTERFACE` を subscribe するが、`bfdorch` 自身は触らない (`staticroutebfd/main.py:718-730`)
- **`ROUTE_TABLE` / `STATIC_ROUTE`**: `bfdorch` が直接読むことはない。`STATIC_ROUTE` は `staticroutebfd` を経由した**間接的な書込み源** であり、`bfdorch` から見ると APPL_DB に到達した時点で他の BFD セッションと区別はない
- **`BGP_NEIGHBOR` / `BGP_PEER_RANGE`**: BGP プロトコル側で BFD を有効化する設定はこれらにあるが、`BFD_SESSION` テーブル自体への投入は `bgpcfgd` / FRR が行うため bfdorch のスコープ外
- **`DEVICE_METADATA` / `SWITCH`**: `gSwitchId` / `gVirtualRouterId` は SwitchOrch 起動時に確定済みのグローバル変数として参照される (`bfdorch.cpp:27, 533`)。CONFIG_DB の `DEVICE_METADATA` を bfdorch が直接読むことはない

## まとめ — `bfd-session.md` Phase C 記載対象

| カテゴリ | 対象 | 種別 |
|---|---|---|
| 入力依存 (CONFIG_DB) | `PORT` (`alias`) / `VRF` (`vrf_name`) | gPortsOrch / VRFOrch 経由 |
| 制御依存 (CONFIG_DB) | `BGP_DEVICE_GLOBAL` (`STATE.tsa_enabled` / `STATE.use_software_bfd`) | BgpGlobalStateOrch 経由 |
| 逆方向書込み (CONFIG_DB) | `STATIC_ROUTE` | staticroutebfd が `BFD_SESSION_TABLE` を生成 |
| 状態経路 (STATE_DB / APPL_DB) | `SOFTWARE_BFD_SESSION_TABLE` / `BFD_SESSION_TABLE` (state) | 経路別の中継 / 通知 |
| 範囲外 | `INTERFACE` / `BGP_NEIGHBOR` / `ROUTE_TABLE` / `DEVICE_METADATA` | bfdorch から直接参照なし |

## 検証コマンド

```bash
grep -nE 'gPortsOrch|VRFOrch|getVRFid|BgpGlobalStateOrch' \
    .cache/sonic-sources/sonic-swss/orchagent/bfdorch.cpp

grep -nE 'STATIC_ROUTE|BFD_SESSION_TABLE' \
    .cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/staticroutebfd/main.py

# 実機での確認
sonic-db-cli APPL_DB keys 'BFD_SESSION_TABLE:*'
sonic-db-cli STATE_DB keys 'SOFTWARE_BFD_SESSION_TABLE|*'
sonic-db-cli STATE_DB keys 'BFD_SESSION_TABLE|*'
```

このスキャン結果から派生して `docs/reference/config-db/bfd-session.md` の `<!-- cross-refs -->` ブロックを生成する。
