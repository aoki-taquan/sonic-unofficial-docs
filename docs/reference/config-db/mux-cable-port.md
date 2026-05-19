---
title: MUX_CABLE テーブル（per-port フィールド詳細）
description: "DualToR MUX_CABLE テーブルの per-port エントリ — ycabled と linkmgrd が読み取る各フィールドのコード由来デフォルトおよび暗黙 fallback を整理する。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-14
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-mux-cable.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-platform-daemons
    path: sonic-ycabled/ycable/ycable_utilities/y_cable_helper.py
    ref: master
  - repo: sonic-net/sonic-linkmgrd
    path: src/DbInterface.cpp
    ref: master
related:
  config_db:
    - MUX_CABLE
    - PEER_SWITCH
    - TUNNEL
  yang:
    - sonic-mux-cable
---

# MUX_CABLE テーブル（per-port フィールド詳細）

## 概要

`MUX_CABLE|<ifname>` は Dual-ToR 構成で各 server-facing port に紐付く mux cable の per-port 設定エントリ[^1]。
`linkmgrd` と `ycabled` (`sonic-ycabled`) が [CONFIG_DB](../../reference/glossary.md#term-config_db) の `MUX_CABLE` テーブルを購読し、
それぞれ `cable_type` / `state` / `soc_ipv4` などを読み取ってステートマシンと gRPC チャネルを制御する。

本ページは **コード由来のデフォルト・fallback 動作** に焦点を当てる。テーブル全体の概要は [`MUX_CABLE`](mux-cable.md) を参照。

## key 構造

```text
MUX_CABLE|<ifname>
```

`<ifname>` は `PORT.name` への leafref。

## フィールド

| フィールド | 型 | YANG default | 説明 |
|-----------|----|-------------|------|
| `cable_type` | enum `active-active`/`active-standby` | `active-standby` | ケーブル種別。ycabled と linkmgrd のステートマシン分岐を決定 |
| `state` | enum `auto`/`manual`/`detach`/`active`/`standby` | `auto` | MUX 動作モード。`auto` が自動 failover |
| `server_ipv4` | ipv4-prefix | — | サーバ IPv4 アドレス (orchagent が無条件参照するため実質 mandatory) |
| `server_ipv6` | ipv6-prefix | — | サーバ IPv6 アドレス (同上) |
| `soc_ipv4` | ipv4-prefix | — | SoC IPv4 (active-active 専用。ycabled の gRPC セットアップに必須) |
| `soc_ipv6` | ipv6-prefix | — | SoC IPv6 (active-active 専用。ycabled 未参照、linkmgrd は no-op) |
| `prober_type` | enum `hardware`/`software` | `software` | ICMP prober モード。ASIC 非対応時は silent に `software` 降格 |
| `neighbor_mode` | enum `prefix-route`/`host-route` | `host-route` | neighbor 経路モード。SAI 非対応 ASIC では silent に `host-route` 動作 |

## 購読者

- **ycabled** (`sonic-ycabled`): `y_cable_table_helper.py` が `swsscommon.Table(config_db, "MUX_CABLE")` で各 ASIC ごとに `port_tbl` を保持。
  `check_mux_cable_port_type()` が `cable_type` と `state` を参照してポートを active-active / active-standby に分類する。
- **linkmgrd**: `ConfigDBConnector` で `MUX_CABLE` を購読。`processPortCableType()` / `processProberType()` / `processSoCIpAddress()` で per-port 設定を反映。
- **orchagent** (`MuxOrch`): `CFG_MUX_CABLE_TABLE_NAME` を購読し SAI nexthop を操作。

<!-- defaults -->
## コード由来の暗黙デフォルト (Phase A)

<!-- evidence:
  sonic-platform-daemons/sonic-ycabled/ycable/ycable_utilities/y_cable_helper.py:295-320,660-718
  sonic-linkmgrd/src/DbInterface.cpp:827,880-881,910-946,968-1001
  sonic-swss/orchagent/muxorch.cpp:2206-2207,2240
  sonic-buildimage/src/sonic-yang-models/yang-models/sonic-mux-cable.yang
-->

| フィールド | YANG default | コード実装の fallback / 乖離 | 乖離種別 |
|-----------|-------------|---------------------------|---------|
| `cable_type` | `active-standby` | ycabled: 欠落時 `None` → else ブランチで `"active-standby"` 扱い (y_cable_helper.py:317); linkmgrd: `"active-standby"` 明示 fallback (DbInterface.cpp:827) | 乖離なし |
| `state` | `auto` | ycabled: `state` キー自体が存在しない場合 `(False, None)` を返しポートをスキップ (y_cable_helper.py:319); linkmgrd: 欠落で MUXLOGERROR + 処理続行 (DbInterface.cpp:996) | **キー欠落時のスキップ** |
| `soc_ipv4` | — (optional) | ycabled: `"state" in dict and "soc_ipv4" in dict` の二重条件 (y_cable_helper.py:672) — 欠落で gRPC セットアップ未実施; linkmgrd: 欠落 → no-op (DbInterface.cpp:922) | **active-active 時に実質 mandatory** |
| `soc_ipv6` | — (optional) | ycabled: 参照なし; linkmgrd: 欠落 → no-op | 乖離なし |
| `prober_type` | `software` | `hw_offload_capable=false` または欠落 → 強制 `"software"` (DbInterface.cpp:880-881) | プラットフォーム依存 silent 降格 |
| `server_ipv4` | — (optional) | orchagent: `getAttrIpPrefix("server_ipv4")` を無条件呼出し (muxorch.cpp:2206) — 欠落で `std::out_of_range` 例外 | **YANG optional vs 実装 mandatory** |
| `server_ipv6` | — (optional) | orchagent: 同上 (muxorch.cpp:2207) | **YANG optional vs 実装 mandatory** |
| `neighbor_mode` | `host-route` | SAI が `SAI_NEIGHBOR_ENTRY_ATTR_NO_HOST_ROUTE` 非対応 → silent に `host-route` 動作 (muxorch.cpp:2240) | プラットフォーム依存 silent 無視 |

### 注記

- **`cable_type` 欠落時の安全 fallback**: ycabled (`y_cable_helper.py:312-317`) は `cable_type == "active-active"` を明示チェックし、それ以外（`None` を含む）は `"active-standby"` として扱う。linkmgrd (`DbInterface.cpp:827`) も同様に `"active-standby"` を fallback として採用。YANG default と一致しており問題なし。
- **`state` キー欠落でのポートスキップ**: ycabled の `check_mux_cable_port_type()` は `"state" in mux_table_dict` チェックを行い、キーが存在しない場合 `(False, None)` を返す。呼出し元では `status=False` を受け取ると当該ポートへの gRPC チャネル設定を行わない。エントリ作成の直後など `state` が未書き込みの瞬間がある場合はポートが無視される。
- **`soc_ipv4` の active-active 時の実質 mandatory**: ycabled の gRPC チャネルセットアップ (`y_cable_helper.py:672`) は `"state" in dict and "soc_ipv4" in dict` を前提条件としており、`soc_ipv4` が欠落すると `cable_type=active-active` であっても gRPC セッションが確立されない。YANG は optional として定義しているが、active-active 構成では事実上必須。linkmgrd (`processSoCIpAddress`) は欠落時 no-op で graceful に処理する。
- **`prober_type = hardware` の silent 降格**: `SWITCH_CAPABILITY.ICMP_OFFLOAD_CAPABLE != "true"` の ASIC では、`hardware` と設定してもエラーなく `software` として動作する。ログ (`MUXLOGWARNING`) のみ出力。
- **`server_ipv4` / `server_ipv6` の実質 mandatory**: YANG は optional だが、orchagent の `handleMuxCfg` が `getAttrIpPrefix()` を無条件呼出しするため欠落で `std::out_of_range` 例外が発生し orchagent が異常終了する可能性がある。minigraph 経由では `lo_addr` から自動補完される。手動設定時は必須。

<!-- /defaults -->

<!-- ordering -->
## 書込み順依存 (Phase B)

<!-- evidence: sonic-swss/orchagent/muxorch.cpp handleMuxCfg:2202 / handlePeerSwitch:2336 / addOperation:2394; sonic-linkmgrd/src/DbInterface.cpp:1843-1849 -->

`MUX_CABLE|<port>` エントリの SAI 反映は `PEER_SWITCH` の設定完了と `MuxTunnel0` トンネルの存在に依存する。orchagent は `Orch2` フレームワーク経由で `MuxOrch::handleMuxCfg()` を呼び出す（`orch.cpp:1226` の `Orch2::doTask()` 経由）。

### 依存 1: PEER_SWITCH 先行必須（必須先行・自動回復あり）

```
PEER_SWITCH|<name>  SET (address_ipv4 確定)  先行
  ↓
MUX_CABLE|<port>  SET
```

`handleMuxCfg()` (`muxorch.cpp:2271`) は `mux_peer_switch_.isZero()` を確認する。`PEER_SWITCH` エントリが未設定の間は `SWSS_LOG_INFO("Mux Peer switch addr not yet configured")` → `return false` で `m_toSync` に保留し次のイベントループで再試行する。

**違反時**: `PEER_SWITCH` SET 完了後の次イベントループで自動的に処理される（自動回復あり）。

### 依存 2: TUNNEL MuxTunnel0 → PEER_SWITCH チェーン

```
APP_DB TUNNEL_DECAP_TABLE:MuxTunnel0  存在  先行
  ↓
PEER_SWITCH|<name>  SET
  ↓
MUX_CABLE|<port>  SET
```

`handlePeerSwitch()` (`muxorch.cpp:2348-2354`) は `decap_orch_->getDstIpAddresses(MUX_TUNNEL)` が空の場合 `return false` でリトライに戻す。`MuxTunnel0` トンネルが APP_DB に存在しなければ PEER_SWITCH 自体も処理できず、MUX_CABLE の処理も間接的にブロックされる。

**違反時**: `MuxTunnel0` 追加後の次イベントループで自動回復。

### 依存 3: server_ipv4 / server_ipv6 同一 SET_COMMAND 必須（自動回復なし）

`handleMuxCfg()` (`muxorch.cpp:2206-2207`) はフィールドリスト走査前に `getAttrIpPrefix("server_ipv4")` と `getAttrIpPrefix("server_ipv6")` を **無条件** で呼び出す。これらが欠落すると `std::out_of_range` 例外が発生し `addOperation()` の catch ブロック (`muxorch.cpp:2409`) で捕捉されエントリが erase される。

**違反時**: エントリ破棄（自動回復なし）。`server_ipv4` / `server_ipv6` は必ず同一 SET_COMMAND に含める。

### 依存 4: linkmgrd 起動時の初期読み込み順序

linkmgrd は起動時に以下の順序で `MUX_CABLE` テーブルを読み込む（`DbInterface.cpp:1846-1849`）:

```
getPortCableType()   # cable_type を全ポート読み込み
getProberType()      # prober_type を全ポート読み込み
getServerIpAddress() # server_ipv4 / server_ipv6 を全ポート読み込み
getSoCIpAddress()    # soc_ipv4 を全ポート読み込み
```

この順序は固定。初期読み込み中の MUX_CABLE 変更は Subscribe ループで後から処理される。

### 依存 5: neighbor_mode 変更の禁止（運用注意）

既存 mux ポートに対する `neighbor_mode` の変更は orchagent によって拒否される (`muxorch.cpp:2258-2266`)。`SWSS_LOG_ERROR("Neighbor mode change is not allowed")` が出力され `return false` でリトライに保留されるが、元の `neighbor_mode` が存在する限り永続的に失敗する。変更する場合はポートを `DEL` してから再 `SET` する必要がある。

<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照 — linkmgrd / orchagent が読み出す関連テーブル (Phase C)

`MUX_CABLE|<port>` エントリを処理するデーモンは、エントリ本体以外にも複数の CONFIG_DB / APPL_DB / STATE_DB テーブルを参照・監視する。

### linkmgrd 起動時一括読み込み (DbInterface.cpp:1843-1849)

linkmgrd の `run()` は `MUX_CABLE` フィールドを読む前に以下の 3 テーブルから前提情報を取得する。

| テーブル (CONFIG_DB) | 参照箇所 | 用途 | evidence |
|---------------------|---------|------|---------|
| `DEVICE_METADATA` (`localhost.mac`) | `getTorMacAddress()` | ToR の MAC アドレスを取得。MUX ステートマシンの ToR ID として使用 | DbInterface.cpp:589,594 |
| `VLAN` | `getVlanNames()` → `getVlanMacAddress()` | DualToR VLAN の MAC アドレスを取得 | DbInterface.cpp:609-613 |
| `LOOPBACK_INTERFACE` (`Loopback2|*` / `Loopback3|*`) | `getLoopbackInterfacesInfo()` | Loopback2/3 の IPv4 アドレスを linkmgrd の src/dst IP として使用 | DbInterface.cpp:742-746,671-694 |

### linkmgrd ランタイム subscribe (DbInterface.cpp:1819-1841)

`MUX_CABLE` 以外にイベントループで監視するテーブル。

| テーブル | DB | 用途 | evidence |
|---------|----|------|---------|
| `MUX_LINKMGR` | CONFIG_DB | Link Prober 設定 (`interval_v4` / `interval_v6` / `positive_signal_count` 等) の動的変更を受信 | DbInterface.cpp:1820,1887 |
| `BGP_DEVICE_GLOBAL` | CONFIG_DB | `tsa_enabled` フラグ変更を受信し TSA (Traffic Shift Away) モードへ遷移 | DbInterface.cpp:1822,1892 |
| `APP_PORT_TABLE` | APPL_DB | ポートのリンクアップ / ダウンを検知してステートマシンをトリガ | DbInterface.cpp:1827 |
| `APP_MUX_CABLE_RESPONSE_TABLE` | APPL_DB | ycabled からの mux 切替完了応答を受信 | DbInterface.cpp:1829 |
| `APP_FORWARDING_STATE_RESPONSE_TABLE` | APPL_DB | ycabled からの forwarding state 応答を受信 | DbInterface.cpp:1831 |
| `STATE_MUX_CABLE_TABLE` | STATE_DB | orchagent が書き込む mux state 変化を監視 | DbInterface.cpp:1833 |
| `STATE_ROUTE_TABLE` | STATE_DB | デフォルトルート存在 / 消失の通知を受信し Active/Standby 決定に利用 | DbInterface.cpp:1835 |
| `MUX_CABLE_INFO_TABLE` | STATE_DB | ピア ToR のリンクステータスを取得 | DbInterface.cpp:1837 |
| `STATE_PEER_HW_FORWARDING_STATE_TABLE` | STATE_DB | ピア ToR の admin forwarding state を取得 | DbInterface.cpp:1839 |
| `STATE_ICMP_ECHO_SESSION_TABLE` | STATE_DB | ICMP エコーセッション状態を受信 | DbInterface.cpp:1841 |

### orchagent (MuxOrch / MuxAclHandler) 側の暗黙参照 (muxorch.cpp)

| テーブル | DB | 用途 | evidence |
|---------|-----|------|---------|
| `PEER_SWITCH` | CONFIG_DB | ピア ToR の IPv4 (`address_ipv4`) を取得して nexthop 切替に使用。`MUX_CABLE` 処理の前提条件 (Phase B 参照) | muxorch.cpp:2190,2348-2354 |
| `SYSTEM_DEFAULTS` | CONFIG_DB | `mux_tunnel_egress_acl.status` を参照し MuxAclHandler が ingress/egress ACL どちらを適用するかを決定 | muxorch.cpp:1388-1390 |
| `STATE_MUX_CABLE_TABLE` | STATE_DB | SAI 反映後に orchagent が mux state を書き戻す (読み書き両方) | muxorch.cpp:2199 |

> `PEER_SWITCH` と `LOOPBACK_INTERFACE` は `MUX_CABLE|<port>` 処理開始前の前提条件でもある (Phase B 依存関係を参照)。

詳細スキャン手順と grep 結果は `meta/_intermediate/cdb-flow/mux-cable-port-cross-refs.md` を参照。
<!-- /cross-refs -->

## 関連 CONFIG_DB / YANG / CLI

- 上位ページ: [`MUX_CABLE`](mux-cable.md) — テーブル全体の概要・値依存挙動・Phase 6/7/8 分析
- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `PEER_SWITCH`、`TUNNEL` (DualToR の MuxTunnel0)
- 関連 CLI: `config muxcable mode`、`show mux status`、`show mux config`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-mux-cable`

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-mux-cable`](../yang/sonic-mux-cable.md)
- [CONFIG_DB: MUX_CABLE](mux-cable.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-mux-cable.yang` container `MUX_CABLE` / `MUX_CABLE_LIST`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-mux-cable.yang>

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: Dual-ToR と Mux 制御](../../topics/05-dual-tor/index.md)

<!-- /topics-back-ref -->

<!-- ops-hint -->
## 運用ヒント

### よくある落とし穴

- `cable_type=active-active` ポートで `soc_ipv4` を設定し忘れると、ycabled が gRPC チャネルを確立せず active-active 制御が機能しない。設定後 ycabled を再起動しても状態が復旧しない場合は CONFIG_DB エントリを確認する。
- `server_ipv4` / `server_ipv6` を省略すると orchagent が例外で落ちる可能性がある。minigraph 使用時は自動補完されるが、`sonic-db-cli CONFIG_DB hset 'MUX_CABLE|<port>' ...` で手動設定する際は両フィールドを必ず指定する。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB hgetall 'MUX_CABLE|Ethernet0'
show mux status
show mux config
```
<!-- /ops-hint -->
