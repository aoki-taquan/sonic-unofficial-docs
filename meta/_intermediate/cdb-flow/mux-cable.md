# CONFIG_DB 例外条件分析: MUX_CABLE

## Consumer

- `linkmgrd` (DualToR linkmgrd プロセス): `MUX_CABLE` テーブルを購読し、mux ケーブルのモード切替・監視制御を行う。
- ソース: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-mux-cable.yang`。

## 例外条件

### 1. cable_type の不正値 → YANG が拒否
- ソース: `sonic-mux-cable.yang` — `cable_type` は `enum { active-active; active-standby; }` のみ許可。デフォルト `active-standby`。

### 2. prober_type の不正値 → YANG が拒否
- ソース: `sonic-mux-cable.yang` — `prober_type` は `enum { hardware; software; }` のみ。デフォルト `software`。

### 3. neighbor_mode の不正値 → YANG が拒否
- ソース: `sonic-mux-cable.yang` — `neighbor_mode` は `enum { prefix-route; host-route; }` のみ。デフォルト `host-route`。

### 4. state の不正値 → YANG が拒否
- ソース: `sonic-mux-cable.yang` — `state` は `enum { auto; manual; detach; active; standby; }` のみ。デフォルト `auto`。
- `auto` モードではリンクプローバの判断で自動切替。`manual` は手動切替固定。

### 5. server_ipv4 の形式不正 → YANG が拒否
- ソース: `sonic-mux-cable.yang` — `type inet:ipv4-prefix`。不正な IPv4 プレフィックスは YANG バリデーションで拒否。

### 6. MUX_CABLE エントリがない場合の linkmgrd 動作
- ポート設定がない場合、linkmgrd は当該インターフェースに対して mux 管理を行わない。
