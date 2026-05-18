# VLAN_INTERFACE テーブル — 失敗挙動調査メモ (Phase D)

調査日: 2026-05-18  
調査対象:
- `sonic-swss/cfgmgr/intfmgr.cpp`
- `sonic-swss/orchagent/intfsorch.cpp`

---

## 1. intfmgrd 側の失敗シナリオ

### 前提チェック失敗 → サイレントリトライ

| 失敗条件 | ログ | 自動リトライ | コード根拠 |
|---------|------|------------|-----------|
| VLAN が STATE_VLAN_TABLE に未登録（`isIntfStateOk()` false） | `SWSS_LOG_DEBUG("Interface is not ready, skipping %s")` | あり（VLAN ready 後） | `intfmgr.cpp:833-836` |
| `vrf_name` 指定時に STATE_VRF_TABLE に VRF 未登録 | `SWSS_LOG_DEBUG("VRF is not ready, skipping %s")` | あり（VRF ready 後） | `intfmgr.cpp:839-842` |
| VRF 変更（既バインド VRF から別 VRF への直接変更） | `SWSS_LOG_ERROR("%s can not change to %s directly, skipping")` | **なし**（イベント消費して拒否） | `intfmgr.cpp:846-849` |

### フィールド値不正 → ERROR ログ + `return false`（タスク消費）

| フィールド | 不正値の例 | ログ | 自動リトライ |
|-----------|---------|------|------------|
| `mpls` | `"enable"` / `"disable"` 以外 | `SWSS_LOG_ERROR("MPLS state is invalid: \"%s\"")` | **なし** |
| `grat_arp` | `"enabled"` / `"disabled"` 以外 | `SWSS_LOG_ERROR("GARP state is invalid: \"%s\"")` | **なし** |
| `proxy_arp` | `"enabled"` / `"disabled"` 以外 | `SWSS_LOG_ERROR("Proxy ARP state is invalid: \"%s\"")` | **なし** |

`return false` はこのパスでは**タスクを消費**しない（`doIntfGeneralTask` が false を返すと `m_toSync` にキューが残る）。しかし不正値の場合は実際には `SWSS_LOG_ERROR` を出してから false を返しているため、次サイクルでも同じエラーが繰り返される。

### カーネルコマンド失敗 → EXEC_WITH_ERROR_THROW

`setIntfGratArp()` / `setIntfProxyArp()` 内部の `/proc/sys/net/ipv4/conf/<IF>/` への書込みが失敗した場合、`EXEC_WITH_ERROR_THROW` が例外を throw する。`doIntfGeneralTask()` はこれを catch せず、`swss::exec` の失敗で ERROR ログが出る（`intfmgr.cpp:130`）。

```cpp
// intfmgr.cpp:130
SWSS_LOG_ERROR("Command '%s' failed with rc %d", cmd.str().c_str(), ret);
```

### IP アドレス追加失敗

`doIntfAddrTask()` で `isIntfStateOk(alias)` または `isIntfCreated(alias)` が false の場合（属性ロウ未処理）はリトライキューに積まれる（`intfmgr.cpp:1115-1118`）。  
`setIntfIp(alias, "add", ip_prefix)` 内の `ip address add` コマンド失敗は `SWSS_LOG_ERROR` 後 `return false`。

---

## 2. orchagent IntfsOrch 側の失敗シナリオ

### SAI RIF 作成失敗

```cpp
// intfsorch.cpp:1296-1304
sai_status_t status = sai_router_intfs_api->create_router_interface(...);
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to create router interface %s, rv:%d", ...);
    if (handleSaiCreateStatus(SAI_API_ROUTER_INTERFACE, status) != task_success)
    {
        throw runtime_error("Failed to create router interface.");
    }
}
```

`throw runtime_error` はフレームワークが catch してタスクをリトライキューに戻す（リトライあり）。

### SAI RIF 削除失敗（参照カウント非 0）

`removeRouterIntfs()` で `m_syncdIntfses[alias].ref_count > 0` の場合（ネクストホップ等が RIF を参照中）、`return false` → オーケストレータがリトライ（`intfsorch.cpp:1327-1330`）。

```
SWSS_LOG_NOTICE("Router interface %s is still referenced with ref count %d")
```

### SAI RIF 削除コマンド失敗

```cpp
// intfsorch.cpp:1353-1358
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to remove router interface for port %s, rv:%d", ...);
    if (handleSaiRemoveStatus(...) != task_success)
    {
        throw runtime_error("Failed to remove router interface.");
    }
}
```

### SAI 属性 SET 失敗

`setIntfMtu()` / `setIntfMac()` / `setIntfNatZoneId()` 等の各関数で SAI SET 失敗は `SWSS_LOG_ERROR` + `handleSaiSetStatus()` を呼ぶ。`task_need_retry` 判定されるとタスクがキューに残る。

---

## 3. まとめ表

| 障害シナリオ | コンポーネント | ログレベル | 自動リトライ | 主な副作用 |
|------------|--------------|-----------|------------|-----------|
| VLAN 未 ready (STATE_VLAN_TABLE 未登録) | intfmgrd | DEBUG | あり | サイレントキュー保留。VLAN が処理された後に自動再試行 |
| VRF 未 ready (STATE_VRF_TABLE 未登録) | intfmgrd | DEBUG | あり | サイレントキュー保留 |
| VRF 直接変更 | intfmgrd | ERROR | **なし** | イベント消費・拒否。CONFIG_DB 値は変わるが実態は旧 VRF のまま |
| `mpls` 不正値 | intfmgrd | ERROR | **なし** | intfmgrd タスク消費。sysctl 未設定のまま |
| `grat_arp` 不正値 | intfmgrd | ERROR | **なし** | `/proc/sys/…/arp_accept` 未変更のまま |
| `proxy_arp` 不正値 | intfmgrd | ERROR | **なし** | `/proc/sys/…/proxy_arp` 未変更のまま |
| `ip address add` 失敗（カーネルエラー） | intfmgrd | ERROR | あり（次サイクル） | STATE_DB 未書込み。orchagent への通知なし |
| 属性ロウ未処理で IP ロウ投入 | intfmgrd | DEBUG | あり | `isIntfCreated()` false → キュー保留 |
| SAI `create_router_interface` 失敗 | orchagent IntfsOrch | ERROR | あり（framework） | `throw runtime_error` → フレームワークリトライ |
| SAI RIF 削除時 ref_count > 0 | orchagent IntfsOrch | NOTICE | あり（自動） | 参照解放まで DEL 保留 |
| SAI `remove_router_interface` 失敗 | orchagent IntfsOrch | ERROR | あり（framework） | `throw runtime_error` → フレームワークリトライ |
| SAI SET 失敗 (MTU/MAC/NAT zone 等) | orchagent IntfsOrch | ERROR | 条件付き | `handleSaiSetStatus()` 判定による |

---

## 4. ポイント

- **VRF 直接変更は拒否されるがイベントが消費される**。`config interface vrf bind <IF> <new-VRF>` を既存バインド IF に実行すると ERROR ログが出るだけで実態は変わらない。回避策は `vrf unbind` → `vrf bind` の 2 ステップ（`intfmgr.cpp:846-849`）。
- **不正フィールド値（`grat_arp`/`proxy_arp`/`mpls`）はリトライされない**。設定を正しい値に修正してから再 SET する必要がある。
- **SAI 側の失敗はフレームワーク再試行あり**。orchagent は `handleSaiCreateStatus` / `handleSaiSetStatus` で retry / success / failure を判定し、リトライ可能なものはキューに戻す。
- **DEL 保留はログなし**（VLAN_INTERFACE 属性ロウ DEL 時に IP アドレスが残っている場合 `getIntfIpCount(alias) > 0` で `return false` — サイレント保留）。
