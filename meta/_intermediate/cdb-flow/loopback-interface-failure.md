# LOOPBACK_INTERFACE — Phase D 失敗挙動調査ノート

調査日: 2026-05-16
調査対象:
- sonic-swss/cfgmgr/intfmgr.cpp
- sonic-swss/orchagent/intfsorch.cpp

---

## 1. intfmgr.cpp — addLoopbackIntf 失敗

```cpp
// intfmgr.cpp:196-207
void IntfMgr::addLoopbackIntf(const string &alias)
{
    cmd << IP_CMD << " link add " << alias << " mtu " << LOOPBACK_DEFAULT_MTU_STR << " type dummy";
    int ret = swss::exec(cmd.str(), res);
    if (ret)
    {
        SWSS_LOG_ERROR("Command '%s' failed with rc %d", cmd.str().c_str(), ret);
    }
}
```

**挙動**: `ip link add` が失敗しても例外を投げず SWSS_LOG_ERROR のみ。
処理は継続するが Loopback デバイスは OS に存在しない状態になる。
`m_loopbackIntfList.insert(alias)` はその後も実行されるため、以後の SET は「既登録」とみなされ `addLoopbackIntf` が再呼び出しされない（`intfmgr.cpp:854-858`）。

## 2. intfmgr.cpp — delLoopbackIntf 失敗

```cpp
// intfmgr.cpp:209-220
void IntfMgr::delLoopbackIntf(const string &alias)
{
    cmd << IP_CMD << " link del " << alias;
    int ret = swss::exec(cmd.str(), res);
    if (ret)
    {
        SWSS_LOG_ERROR("Command '%s' failed with rc %d", cmd.str().c_str(), ret);
    }
}
```

**挙動**: `ip link del` 失敗は SWSS_LOG_ERROR のみ。
OS の dummy デバイスが残存したまま CONFIG_DB エントリは消える（不整合状態）。
再起動時の `flushLoopbackIntfs()` で残存デバイスを発見・削除するが、
その間の IP アドレス設定は OS 上に留まる可能性がある。

## 3. intfmgr.cpp — admin_status 不正値

```cpp
// intfmgr.cpp:865-868
else if (adminStatus != "up" && adminStatus != "down")
{
    SWSS_LOG_WARN("Got incorrect value for admin_status as %s for intf %s, defaulting as up", ...);
    adminStatus = "up";
}
```

**挙動**: `"up"` / `"down"` 以外の値は WARN ログを出力して `"up"` にフォールバック。
設定は失敗せず、誤った値が `up` として扱われる。

## 4. intfmgr.cpp — setIntfAdminStatus 例外 (runtime_error)

```cpp
// intfmgr.cpp:879-882
catch (const std::runtime_error &e)
{
    SWSS_LOG_WARN("Lo interface ip link set admin status %s failure. Runtime error: %s", adminStatus.c_str(), e.what());
}
```

**挙動**: `ip link set <name> up/down` が runtime_error を throw した場合、
SWSS_LOG_WARN のみで処理継続。admin_status は CONFIG_DB に記録されるが
OS の実際の状態は変わっていない可能性がある。

## 5. intfmgr.cpp — VRF 変更拒否 (isIntfChangeVrf)

```cpp
// intfmgr.cpp:846-849
if (isIntfChangeVrf(alias, vrf_name))
{
    SWSS_LOG_ERROR("%s can not change to %s directly, skipping", alias.c_str(), vrf_name.c_str());
    return true;  // true = 処理済みとして event を消費
}
```

**挙動**: 既バインドの VRF から別 VRF への直接変更は SWSS_LOG_ERROR で拒否。
イベントは消費されるため再試行は発生しない（サイレント失敗）。
VRF を切り替えるには vrf_name 削除 → 再設定の 2 ステップが必要。

## 6. intfmgr.cpp — VRF 未 ready 時スキップ

```cpp
// intfmgr.cpp:839-842
if (!isIntfStateOk(vrf_name))
{
    SWSS_LOG_DEBUG("VRF is not ready, skipping %s", vrf_name.c_str());
    return false;  // false = キューに残す（再試行）
}
```

**挙動**: `vrf_name` 指定時に STATE_VRF_TABLE に対象 VRF が存在しなければ
SWSS_LOG_DEBUG でスキップ（エラーではない）。VRF 完了後に自動リトライされる。

## 7. orchagent/intfsorch.cpp — SAI RIF 作成失敗

```cpp
// intfsorch.cpp:1296-1304
sai_status_t status = sai_router_intfs_api->create_router_interface(...);
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to create router interface %s, rv:%d", port.m_alias.c_str(), status);
    if (handleSaiCreateStatus(SAI_API_ROUTER_INTERFACE, status) != task_success)
    {
        throw runtime_error("Failed to create router interface.");
    }
}
```

**挙動**: SAI `create_router_interface` が SAI_STATUS_SUCCESS 以外を返すと
SWSS_LOG_ERROR + `handleSaiCreateStatus` で判定。
`task_success` でなければ `runtime_error` を throw → orchestration フレームワーク
がキャッチして当該タスクをリトライキューに戻す。

## 8. orchagent/intfsorch.cpp — loopback_action 不正値

```cpp
// intfsorch.cpp:1162
SWSS_LOG_WARN("Unsupported loopback action [%s]", actionStr.c_str());
return false;
```

**挙動**: `loopback_action` が `"drop"` / `"forward"` 以外の場合、SWSS_LOG_WARN のみ。
SAI 属性は設定されずデフォルト（SAI 実装依存）が維持される。

## 9. orchagent/intfsorch.cpp — RIF 削除・参照カウント非 0

```cpp
// intfsorch.cpp:1327-1330
if (m_syncdIntfses[port.m_alias].ref_count > 0)
{
    SWSS_LOG_NOTICE("Router interface %s is still referenced with ref count %d", ...);
    return false;
}
```

**挙動**: 他オブジェクト（ネクストホップ等）が RIF を参照中の場合、削除を拒否して
SWSS_LOG_NOTICE を出力。DEL イベントはリトライキューに残り、参照が解放されるまで
自動で再試行される。

## 10. intfmgr.cpp — DEL 時に IP が残存

```cpp
// intfsorch.cpp:1053-1064
if (!ip_prefix_in_key)
{
    if (m_syncdIntfses[alias].ip_addresses.size() == 0)
    {
        // 削除実行
    }
    else
    {
        it++;  // IP が残存 → スキップ（リトライ）
        continue;
    }
}
```

**挙動**: 属性ロウ DEL 時に IP プレフィクスロウが残存していると、
DEL はキューに保留されてリトライされる。ログは出力されない（サイレントリトライ）。

---

## まとめ表

| 障害シナリオ | 処理コンポーネント | ログレベル | 自動リトライ | 副作用 |
|------------|-----------------|-----------|-------------|--------|
| `ip link add` 失敗 | intfmgrd | ERROR | なし | OS に dummy デバイスなし、m_loopbackIntfList は登録済み → 再作成不可 |
| `ip link del` 失敗 | intfmgrd | ERROR | なし | OS に dummy デバイス残存、CONFIG_DB は消去済み |
| `admin_status` 不正値 | intfmgrd | WARN | — | `"up"` にフォールバック（サイレント矯正） |
| `ip link set up/down` 例外 | intfmgrd | WARN | なし | OS と CONFIG_DB の admin 状態が乖離 |
| VRF 変更（直接） | intfmgrd | ERROR | なし | 変更が無視される（イベントは消費） |
| VRF 未 ready | intfmgrd | DEBUG | あり（VRF 完了後） | 設定保留 |
| SAI RIF 作成失敗 | orchagent IntfsOrch | ERROR | あり（task_success 非時） | runtime_error throw → フレームワーク再試行 |
| loopback_action 不正値 | orchagent IntfsOrch | WARN | なし | デフォルト action 維持 |
| RIF 削除・参照残存 | orchagent IntfsOrch | NOTICE | あり（自動） | 参照解放まで RIF 存続 |
| 属性ロウ DEL・IP 残存 | orchagent IntfsOrch | なし | あり（自動） | IP 削除まで DEL 保留 |
