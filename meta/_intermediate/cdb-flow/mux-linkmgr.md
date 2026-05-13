# CONFIG_DB 例外条件分析: MUX_LINKMGR

## Consumer

- `linkmgrd` (DualToR linkmgrd プロセス): `MUX_LINKMGR` テーブルの `LINK_PROBER`・`TIMED_OSCILLATION`・`MUXLOGGER`・`SERVICE_MGMT` コンテナを購読し、プロセス内部設定として適用。
- ソース: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-mux-linkmgr.yang`。

## 例外条件

### 1. interval_v4 / interval_v6 / positive_signal_count / negative_signal_count が 0 → YANG は uint32 を許可するが動作上問題
- ソース: `sonic-mux-linkmgr.yang` — これらのフィールドは `type uint32` で range 制約なし。0 を設定するとハートビートが送信されず、冗長性保護が機能しない。
- デフォルト: `interval_v4 = 100ms`, `interval_v6 = 1000ms`, `positive_signal_count = 1`, `negative_signal_count = 3`。

### 2. use_well_known_mac の不正値 → YANG が拒否
- ソース: `sonic-mux-linkmgr.yang` — `enum { enabled; disabled; }` のみ許可。

### 3. src_mac の不正値 → YANG が拒否
- ソース: `sonic-mux-linkmgr.yang` — `enum { ToRMac; VlanMac; }` のみ許可。

### 4. log_verbosity の不正値 → YANG が拒否
- ソース: `sonic-mux-linkmgr.yang` — `enum { trace; debug; info; error; fatal; }` のみ許可。

### 5. oscillation_enabled のデフォルト = true
- ソース: `sonic-mux-linkmgr.yang` — `default true`。TIMED_OSCILLATION コンテナが空の場合も `interval_sec = 300` で自動切替が有効。
- 無効化する場合は明示的に `oscillation_enabled = false` を設定する必要がある。

### 6. kill_radv のデフォルト = True
- ソース: `sonic-mux-linkmgr.yang` — `default True`。radv サービスは MUX 切替時にデフォルトで強制終了される。
