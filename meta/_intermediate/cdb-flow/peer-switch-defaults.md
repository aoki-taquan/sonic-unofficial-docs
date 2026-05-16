# PEER_SWITCH — Phase A: フィールド暗黙デフォルト調査

## 調査対象

- テーブル: `PEER_SWITCH`
- フィールド: `peer_switch` (key), `address_ipv4`
- 主要ソース:
  - `sonic-swss/orchagent/muxorch.cpp`
  - `sonic-swss/orchagent/muxorch.h` (line 340)
  - `sonic-swss/cfgmgr/tunnelmgr.cpp`
  - `sonic-buildimage/dockers/docker-orchagent/tunnel_packet_handler.py`
  - `sonic-buildimage/src/sonic-config-engine/minigraph.py`
  - `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-peer-switch.yang`
  - `sonic-swss/neighsyncd/neighsync.cpp`

---

## フィールド別 暗黙デフォルト・挙動調査

### 1. `peer_switch` (key フィールド)

- **型**: `stypes:hostname` (最大 63 文字、英数字とハイフン)
- **YANG default**: なし
- **コード由来デフォルト**: なし
- **暗黙挙動**:
  - minigraph.py: `data["PeerSwitch"]` から peer hostname を取得。Dual-ToR でない場合はエントリ自体が生成されない
  - `tunnel_packet_handler.py`: `config_db.get_keys("PEER_SWITCH")[0]` でキー取得。エントリが 0 件の場合 `IndexError` → `(None, None)` を返す → Dual-ToR 機能が無効扱い
  - `neighsync.cpp:69`: `peerSwitchKeys.size() > 0` で `is_dualtor` フラグを立てる。エントリ 0 件 → `is_dualtor = false` → link-local IPv4 neighbor をフィルタしない

### 2. `address_ipv4`

- **型**: `inet:ipv4-address`
- **YANG default**: なし (mandatory 相当 — YANG に `mandatory true` の明示はないが実質必須)
- **コード由来デフォルト**: なし
- **暗黙挙動**:
  - `muxorch.h:340`: `IpAddress mux_peer_switch_ = 0x0;` — MuxOrch 内部変数のゼロ初期化 (= 0.0.0.0)。PEER_SWITCH エントリが届くまではこのゼロ値が保持される
  - `muxorch.cpp:2271`: `mux_peer_switch_.isZero()` が true の場合 MUX_CABLE エントリ追加が `return false` でブロック。**書き込み順依存**: PEER_SWITCH → MUX_CABLE の順で投入しなければ MUX_CABLE エントリが pending に残る
  - `muxorch.cpp:2483`: `mux_peer_switch_.isZero()` が true の場合 `updateCachedNeighbors()` をスキップ。近隣更新がキャッシュに積み上がる
  - `tunnelmgr.cpp:127-131`: コンストラクタ起動時に PEER_SWITCH テーブルを **1 回だけ** 読み込み `m_peerIp` に格納。実行中の動的変更は `m_peerIp` に反映されない (再起動必要)
  - `tunnelmgr.cpp:252-261`: `m_peerIp` が空文字の場合 `configIpTunnel()` を呼ばず "Peer/Remote IP not configured" ログのみ
  - `tunnel_packet_handler.py:234`: `get_entry("PEER_SWITCH", peer_switch)["address_ipv4"]` — `address_ipv4` キーが存在しない場合 `KeyError` → `(None, None)` を返す → ICMP プローブ送信不可

---

## 検出された問題・注意点

### A. 書き込み順依存 (write-order dependency)

`muxorch.cpp:2271`: MUX_CABLE エントリ処理は `mux_peer_switch_` がゼロでない場合のみ進む。
つまり **PEER_SWITCH が先に CONFIG_DB に投入されていないと MUX_CABLE の処理が defer される**。
minigraph 生成時は `PEER_SWITCH` と `MUX_CABLE` が同一 JSON に含まれるが、orchagent の consumer キュー処理順によっては競合する可能性がある。

### B. dead consumer (ランタイム注入なし / 動的変更無効)

`tunnelmgr.cpp`: コンストラクタで 1 回読み込み後、`m_peerIp` は更新されない。PEER_SWITCH エントリを実行中に変更しても tunnelmgr には反映されない。**silent drop** の一形態。

### C. DELETE 未実装 (dead operation)

`muxorch.cpp:2387`: DEL_COMMAND ハンドラが "Not Implemented" ログを出力して `return true` のみ。`mux_peer_switch_` はゼロにリセットされない。エントリ削除後も orchagent は旧 peer IP を保持し続ける。実質的に **dead operation**。

### D. `mux_peer_switch_` ゼロ初期化ハードコード

`muxorch.h:340`: `IpAddress mux_peer_switch_ = 0x0;` — `0.0.0.0` にハードコード初期化。これは YANG スキーマに存在しない実装内部デフォルト。

### E. 多重 consumer の PEER_SWITCH 読み込み

| consumer | 読み込み時点 | 更新タイミング |
|---------|-----------|------------|
| `MuxOrch` (orchagent) | SET イベント到着時 | リアルタイム |
| `TunnelMgr` (tunnelmgrd) | コンストラクタ起動時のみ | 再起動のみ |
| `tunnel_packet_handler.py` | Pkt受信時都度 `get_entry()` | 都度読み込み |
| `NeighSync` (neighsyncd) | neighbor 通知受信時都度 `getKeys()` | 都度読み込み |

読み込み頻度がデーモンごとに異なる。tunnelmgrd のみ起動後の変更を無視する。

### F. YANG `mandatory` 欠如

`address_ipv4` に `mandatory true` が付いていない。YANG 的には省略可能だが、省略すると上記複数の consumer が `KeyError` / ゼロ IP で動作不全になる。YANG-実装 discrepancy (YANG は optional、実装は実質 mandatory)。

---

## サマリ表

| フィールド | YANG default | コード実装デフォルト | 注意点 |
|-----------|------------|-----------------|------|
| `peer_switch` (key) | なし | なし | エントリ 0 件で is_dualtor=false、link-local フィルタ無効化 |
| `address_ipv4` | なし | `0x0` (0.0.0.0) in MuxOrch | 書き込み順依存 / DELETE 未実装 / tunnelmgrd は起動時 1 回読み込みのみ |

---

## ソース証跡

| 事象 | ファイル | 行番号 |
|-----|---------|-------|
| `mux_peer_switch_ = 0x0` 初期化 | `sonic-swss/orchagent/muxorch.h` | 340 |
| `isZero()` で MUX_CABLE pending | `sonic-swss/orchagent/muxorch.cpp` | 2271-2274 |
| `isZero()` で cached neigh スキップ | `sonic-swss/orchagent/muxorch.cpp` | 2483-2487 |
| DELETE Not Implemented | `sonic-swss/orchagent/muxorch.cpp` | 2387-2389 |
| tunnelmgrd コンストラクタ 1 回読み | `sonic-swss/cfgmgr/tunnelmgr.cpp` | 115-131 |
| `m_peerIp` 空で tunnel 未設定 | `sonic-swss/cfgmgr/tunnelmgr.cpp` | 258-260 |
| `get_entry()["address_ipv4"]` KeyError | `dockers/docker-orchagent/tunnel_packet_handler.py` | 232-240 |
| `get_keys()[0]` IndexError (0 件) | `dockers/docker-orchagent/tunnel_packet_handler.py` | 221-226 |
| `is_dualtor` = keys > 0 | `sonic-swss/neighsyncd/neighsync.cpp` | 68-69 |
| peer_lo_addr なし → None | `sonic-buildimage/src/sonic-config-engine/minigraph.py` | 476 |
