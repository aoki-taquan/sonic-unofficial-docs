# INTERFACE テーブル — Phase D 失敗挙動分析

> 調査対象: `sonic-swss/orchagent/intfsorch.cpp`, `sonic-swss/cfgmgr/intfmgr.cpp`
> 調査日: 2026-05-16

## 失敗挙動一覧

### 1. PORT 未解決 → it++ / retry (intfmgrd + IntfsOrch)

**intfmgrd 側 (cfgmgr/intfmgr.cpp L833-836)**:
- `isIntfStateOk(alias)` が false（STATE_DB の `STATE_PORT_TABLE` に `state=ok` が未登録）
- `SWSS_LOG_DEBUG("Interface is not ready, skipping %s", alias.c_str())`
- `return false` → Consumer の `m_toSync` に残留、次ループで再試行

**IntfsOrch 側 (orchagent/intfsorch.cpp L905-924)**:
- `gPortsOrch->getPort(alias, port)` が false かつ非サブインタフェース
- `it++; continue` → `m_toSync` に残留、再試行
- PORT が PortsOrch に登録されるまで処理不可

### 2. VRF 未解決 → it++ / retry (intfmgrd + IntfsOrch)

**intfmgrd 側 (cfgmgr/intfmgr.cpp L839-842)**:
- `vrf_name` 指定時に `isIntfStateOk(vrf_name)` が false（VRF STATE_DB 未 ready）
- `SWSS_LOG_DEBUG("VRF is not ready, skipping %s", vrf_name.c_str())`
- `return false` → retry

**IntfsOrch 側 (orchagent/intfsorch.cpp L826-829)**:
- `m_vrfOrch->isVRFexists(vrf_name)` が false
- `it++; continue` → retry（VRF オブジェクトが orchagent 内に生成されるまで）

**VRF 直接変更 (cfgmgr/intfmgr.cpp L846-849)**:
- 既に VRF バインド済みのまま別 VRF を指定すると `isIntfChangeVrf()` が true
- `SWSS_LOG_ERROR("%s can not change to %s directly, skipping", alias.c_str(), vrf_name.c_str())`
- エントリはキューから除去（`m_toSync.erase`）→ 設定は適用されない

**VRF 変更時 IP 付きエラー (orchagent/intfsorch.cpp L860)**:
- Loopback 系で VRF 変更時に IP アドレスが残存している場合
- `SWSS_LOG_ERROR("Failed to set interface '%s' to VRF ID '%d' because it has IP addresses associated with it.")`

### 3. IP format 不正 / silent drop

**IPv4 link-local アドレスの silent drop (cfgmgr/intfmgr.cpp L1132)**:
- `ip_prefix.isV4() == true` かつ `getAddrScope() == LINK_SCOPE`（169.254.x.x）
- APP_DB への書き込みをスキップ（ログなし）→ orchagent / SAI に届かない
- IPv4 link-local はサポート対象外

**IP プレフィクス重複 / オーバーラップ (orchagent/intfsorch.cpp L571-580)**:
- 同 VRF 内の既存プレフィクスとサブネットが重複する場合
- `SWSS_LOG_NOTICE("Router interface %s IP %s overlaps with %s.", ...)`
- `setIntf` が `return false` → `m_toSync` に残留（重複エントリ削除まで retry）

**`mac_addr` 不正 (orchagent/intfsorch.cpp L740)**:
- MAC アドレスパースに例外 → `SWSS_LOG_ERROR("Invalid mac argument %s to %s()", ...)`
- `continue` → エントリは消去（設定スキップ）

**`nat_zone` 不正値 (orchagent/intfsorch.cpp L756)**:
- `SWSS_LOG_ERROR("Invalid argument %s for nat zone", value.c_str())`
- `continue` → エントリは消去（nat_zone 設定スキップ）

### 4. kernel netlink / ip コマンド失敗

**IP アドレス追加コマンド失敗 (cfgmgr/intfmgr.cpp L130)**:
- `ip address add/del` (`setIntfIp`) がゼロ以外の return code
- IPv6 の場合: `SWSS_LOG_NOTICE("Failed to assign IPv6 on interface %s ... trying to enable IPv6 and retry")` → `enableIpv6Flag()` を試みて再実行
- `enableIpv6Flag()` も失敗: `SWSS_LOG_ERROR("Failed to enable IPv6 on interface %s")` → return（エントリ自体は消去）
- IPv4 失敗: `SWSS_LOG_ERROR("Command '%s' failed with rc %d")` → return

**MTU 設定コマンド失敗 (cfgmgr/intfmgr.cpp L455)**:
- `ip link set mtu` が失敗
- `SWSS_LOG_WARN("Setting mtu to %s netdev failed with cmd:%s, rc:%d, error:%s", ...)`
- warn のみで処理継続。MTU は旧値のまま

**admin_status 設定コマンド失敗 (cfgmgr/intfmgr.cpp L501)**:
- `ip link set <alias> up/down` が失敗
- `SWSS_LOG_WARN("Setting admin_status to %s netdev failed with cmd:%s, rc:%d, error:%s", ...)`

**SAI router interface 作成失敗 (orchagent/intfsorch.cpp L1297-1303)**:
- `sai_router_intfs_api->create_router_interface()` が `SAI_STATUS_SUCCESS` 以外
- `SWSS_LOG_ERROR("Failed to create router interface %s, rv:%d", ...)`
- `handleSaiCreateStatus` が `task_success` 以外 → `throw runtime_error("Failed to create router interface.")` → orchagent が abort

## retry メカニズム

- `intfmgrd` の main ループはタイムアウト 1000 ms で `Select::select()` を呼ぶ
- `doIntfGeneralTask` / `doIntfAddrTask` が `false` を返した場合、エントリは `m_toSync` に残留
- タイムアウト時に `doTask()` が再実行され、残留エントリが再処理される
- PORT / VRF が ready になると STATE_DB 通知でキューが再試行される
