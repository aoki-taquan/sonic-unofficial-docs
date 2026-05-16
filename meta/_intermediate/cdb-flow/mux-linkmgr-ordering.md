# MUX_LINKMGR — Phase B 書込み順依存スキャンノート

対象テーブル: `MUX_LINKMGR`
Consumer: `linkmgrd` (`sonic-linkmgrd/src/DbInterface.cpp`)
ソース: `sonic-swss/orchagent/muxorch.cpp`、`sonic-linkmgrd/src/DbInterface.cpp`
スキャン範囲: `processMuxLinkmgrConfigNotifiction()`、`handleSwssNotification()`、`handleMuxLinkmgrConfigNotifiction()`

---

## 検出した順序依存・タイミング依存

### 1. MUX_LINKMGR は linkmgrd が直接購読（orchagent 非経由）

- `DbInterface::handleSwssNotification()` (DbInterface.cpp:1820) は `CFG_MUX_LINKMGR_TABLE_NAME` を
  `swss::SubscriberStateTable` として CONFIG_DB から直接購読する。
- orchagent / MuxOrch は MUX_LINKMGR を処理しない。
- よって、MUX_LINKMGR の設定変更は orchagent の PortInitDone や SAI 完了を待たない。
- **順序依存なし（orchagent 側）**: TUNNEL / PEER_SWITCH / MUX_CABLE の準備状態とは独立して
  MUX_LINKMGR を書き込める。

### 2. MUX_CABLE より前に MUX_LINKMGR を書くことを推奨

- `processMuxLinkmgrConfigNotifiction()` (DbInterface.cpp:1120) は `LINK_PROBER` /
  `MUXLOGGER` / `TIMED_OSCILLATION` の 3 キーのみを分岐処理する。
- `interval_v4` / `interval_v6` / `positive_signal_count` / `negative_signal_count` などの
  プローバパラメータは `mMuxManagerPtr->setTimeoutIpv4_msec()` 等でランタイム中もいつでも反映される。
- ただし linkmgrd 起動**後**かつ MUX_CABLE エントリが届く**前**に MUX_LINKMGR を書いておくと、
  ポートごとのリンクプローバが初期化時に正しいパラメータで開始できる。
- **推奨順序**: MUX_LINKMGR → MUX_CABLE（厳密必須ではなく推奨。MUX_CABLE 処理後の
  notification でも即時反映される）

### 3. PEER_SWITCH → MUX_CABLE の順序依存（orchagent 側）

これは MUX_LINKMGR 自体の依存ではないが、同一 Dual-ToR 設定セットに密接に関連する:

- `MuxOrch::handleMuxCfg()` (muxorch.cpp:2271):
  ```cpp
  if (mux_peer_switch_.isZero())
  {
      SWSS_LOG_INFO("Mux Peer switch addr not yet configured, port '%s'", port_name.c_str());
      return false;
  }
  ```
  `mux_peer_switch_` が 0.0.0.0 のままだと MUX_CABLE エントリが `return false` でリトライ待機に入る。

- `MuxOrch::handlePeerSwitch()` (muxorch.cpp:2336):
  ```cpp
  IpAddresses dst_ips = decap_orch_->getDstIpAddresses(MUX_TUNNEL);
  if (!dst_ips.getSize())
  {
      SWSS_LOG_INFO("Mux tunnel not yet created for '%s' peer ip '%s'", ...);
      return false;
  }
  ```
  PEER_SWITCH を処理する際に MuxTunnel0 の dst IP が未設定なら PEER_SWITCH 処理自体が `return false`
  でリトライ待機する。

- **orchagent 側の必須順序**:
  `TUNNEL (MuxTunnel0 decap dst IP)` → `PEER_SWITCH SET` → `MUX_CABLE SET`

### 4. PEER_SWITCH DELETE の未実装（orchagent 側 discrepancy）

- `handlePeerSwitch()` の DEL パス (muxorch.cpp:2387):
  ```
  "Mux peer ip '%s' delete (Not Implemented), peer name '%s'"
  ```
  DEL が来ても `mux_peer_switch_` はリセットされない。PEER_SWITCH エントリ削除後も
  orchagent は旧 peer IP を保持し続け、MUX_CABLE の tunnel nexthop 計算に旧 IP が使われる。
- **運用注意**: PEER_SWITCH を変更する場合は orchagent の再起動が必要。

### 5. SERVICE_MGMT (kill_radv) は linkmgrd が処理しない

- `processMuxLinkmgrConfigNotifiction()` に `SERVICE_MGMT` キーの分岐がない (DbInterface.cpp:1120-1214)。
- YANG `default True` は YANG バリデーション側で機能するが、linkmgrd の runtime handler には届かない。
- **順序に影響なし**（linkmgrd は kill_radv を動的に読まないため、値変更のタイミングは無関係）。

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | MUX_LINKMGR は orchagent 非経由 — TUNNEL/PEER_SWITCH/MUX_CABLE と独立 | 独立（任意タイミングで書込み可） | linkmgrd は notification で即時反映 |
| 2 | MUX_LINKMGR を MUX_CABLE より先に書く | 推奨（初期プローバパラメータを正確に設定） | runtime notification でも反映されるが初期状態が不定になりうる |
| 3 | TUNNEL → PEER_SWITCH → MUX_CABLE（orchagent 側） | 必須（`return false` でリトライ待機） | orchagent の retry ループで自動回復するが設定完了まで MUX_CABLE が pending |
| 4 | PEER_SWITCH DEL 未実装 | orchagent が旧 IP を保持 | orchagent 再起動が必要 |
| 5 | SERVICE_MGMT (kill_radv) は linkmgrd runtime handler に届かない | 順序依存なし | YANG default 値のみ有効 |
