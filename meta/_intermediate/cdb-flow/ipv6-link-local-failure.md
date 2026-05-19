# ipv6-link-local — Phase D 失敗挙動スキャンノート

対象フィールド: `INTERFACE|<name>.ipv6_use_link_local_only` / `PORTCHANNEL_INTERFACE|<name>` / `VLAN_INTERFACE|<name>`
Consumer: `intfmgrd` (sonic-swss cfgmgr/intfmgr.cpp)、`neighsyncd` (sonic-swss neighsyncd/neighsync.cpp)
スキャン範囲: `cfgmgr/intfmgr.cpp`、`neighsyncd/neighsync.cpp`

---

## 検出した失敗シナリオ

### 1. インターフェース未 ready — SET を silent skip して再キュー

`intfmgr.cpp:832-837` で `isIntfStateOk()` が `false` を返すと `return false` (再キュー) する。
`ipv6_use_link_local_only` フィールドを含む CONFIG_DB SET は APP_DB に転送されず、インターフェースが STATE_DB に登録されるまで自動待機する。
エラーログレベルは `SWSS_LOG_DEBUG` のみで、デフォルトログ設定では不可視。

### 2. VRF 未 ready — 同様に silent skip

`intfmgr.cpp:839-843` で VRF が `STATE_VRF_TABLE` に未登録の場合も `return false` で再キュー。
VRF バインドインターフェースの `ipv6_use_link_local_only` は VRF 作成完了まで反映されない。

### 3. `delIpv6LinkLocalNeigh()` — `ip neigh del` 失敗を無視

`disable` 時に呼ばれる `delIpv6LinkLocalNeigh()` は `swss::exec()` の戻り値をチェックしない (`intfmgr.cpp:712-740`)。
`ip neigh del` コマンドが失敗した場合でも `SWSS_LOG_INFO` ログのみ出力し、APP_DB `NEIGH_TABLE` のエントリ削除を再試行しない。
カーネルの近傍エントリが残存してもコード上は成功扱いになる。

### 4. `neighsyncd` の CONFIG_DB 参照失敗 — link-local neigh を silent drop

`isLinkLocalEnabled()` (`neighsync.cpp:193-243`) は CONFIG_DB テーブルの `.get()` が失敗した場合（エントリ不在・DB 接続障害等）に `false` を返し、link-local neigh の ADD を無視する。
エラーレベルは `SWSS_LOG_INFO` のみ。CONFIG_DB が一時的に応答しない場合、link-local neigh の学習が黙って停止する。

### 5. サポートされないインターフェース種別 — silent drop

`isLinkLocalEnabled()` で `Ethernet` / `Vlan` / `PortChannel` 以外のプレフィクス（`eth0`、`lo`、`docker0` 等）は即 `false` 返却 (`neighsync.cpp:221-226`)。
これらのインターフェースに `ipv6_use_link_local_only=enable` を設定してもランタイムでは完全に無視され、エラーも出ない。
