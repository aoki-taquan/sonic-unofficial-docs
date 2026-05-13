# CONFIG_DB 例外条件分析: LOOPBACK_INTERFACE

## Consumer

- `intfmgr` (`sonic-swss/cfgmgr/intfmgr.cpp`): `LOOPBACK_INTERFACE` テーブルを subscribe し、Linux dummy デバイスとして Loopback を作成、IP アドレスを付与する。

## 例外条件

### 1. L3 enable 行なしの IP 行 → デバイス未作成のまま IP 付与失敗
- ソース: `intfmgr.cpp` L696 (`LOOPBACK_PREFIX = "Loopback"`)
- Loopback インターフェースは `LOOPBACK_INTERFACE|LoopbackN`（フィールドなし）のエントリが来た時に dummy デバイスを作成する。IP アドレス行（`LOOPBACK_INTERFACE|LoopbackN|ip/prefix`）のみ投入した場合はデバイスが存在しないため `ip addr add` が失敗する。

### 2. デフォルト MTU は 65536
- ソース: `intfmgr.cpp` L28 (`LOOPBACK_DEFAULT_MTU_STR "65536"`)
- `ip link add <name> mtu 65536 type dummy` で作成。MTU フィールドが CONFIG_DB に設定されていない場合は常に 65536 が使用される。明示的に小さい MTU を設定しても L3 enable 行の再入力タイミングで上書きされる可能性がある。

### 3. ip link set admin_status 失敗 → warn（処理継続）
- ソース: `intfmgr.cpp` L881
- Loopback の admin_status 変更が `RuntimeError` で失敗した場合 `SWSS_LOG_WARN("Lo interface ip link set admin status %s failure. Runtime error: %s", ...)` → warn のみで続行。Loopback の admin_status は実 NW 影響なしだが BGP next-hop 計算に影響する場合がある。

### 4. ip link del 失敗 → エラーログ
- ソース: `intfmgr.cpp` L260
- `DEL` 操作で `ip link del` コマンドが失敗した場合 `SWSS_LOG_ERROR("Command '%s' failed with rc %d", ...)` → dummy デバイスが OS に残存するが CONFIG_DB からはエントリが消える（不整合状態）。

### 5. 既存 Loopback 名とのリスト管理
- ソース: `intfmgr.cpp` L854, L857
- `m_loopbackIntfList` で作成済みリストを管理。同名 Loopback に SET が再入力された場合は `find` で既存確認後スキップ。削除済みの Loopback への IP 追加は、L3 enable 行を再設定しないと反映されない。
