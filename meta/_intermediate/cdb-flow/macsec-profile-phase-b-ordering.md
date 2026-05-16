# MACSEC_PROFILE — Phase B 順序依存中間ファイル

生成日: 2026-05-16 (Task F Phase B)

<!-- ordering -->
## Phase B: 順序依存・起動順スキャン

### ソースファイル

- `sonic-swss/cfgmgr/macsecmgr.cpp`
- `sonic-swss/orchagent/macsecorch.cpp`

---

### 1. PORT 先行条件 (macsecmgr.cpp L487–504)

`MACsecMgr::enableMACsec()` 内で PORT.macsec が設定されたとき、以下 2 つの前提条件を順番に確認する:

```cpp
// L487–496: MACSEC_PROFILE の存在確認
auto itr = m_profiles.find(profile_name);
if (itr == m_profiles.end())
{
    SWSS_LOG_DEBUG(
        "The MACsec profile '%s' for the port '%s' isn't ready",
        profile_name.c_str(),
        port_name.c_str());
    return task_need_retry;
}

// L499–504: PORT が STATE_DB で ready かどうか確認
if (!isPortStateOk(port_name))
{
    SWSS_LOG_DEBUG("The port '%s' isn't ready", port_name.c_str());
    return task_need_retry;
}
```

`isPortStateOk()` (L615–633) は `STATE_PORT_TABLE_NAME` を検索し、`state == "ok"` かつ `netdev_oper_status == "up"` を要求する。

**依存順序**: `MACSEC_PROFILE 登録 → STATE PORT ready → enableMACsec 実行`

---

### 2. wpa_supplicant 起動順 (macsecmgr.cpp L635–678)

```cpp
pid_t wpa_supplicant_pid = fork();
if (wpa_supplicant_pid == 0)
{
    exit(execl(WPA_SUPPLICANT_CMD, WPA_SUPPLICANT_CMD,
               "-s", "-D", "macsec_sonic", "-g", sock.c_str(), NULL));
}
else if (wpa_supplicant_pid > 0)
{
    // Wait wpa_supplicant ready
    bool wpa_supplicant_loading = false;
    auto retry_time = RETRY_TIME;
    while(!wpa_supplicant_loading && retry_time > 0)
    {
        try
        {
            wpa_cli_exec(sock, "", "", "status");
            wpa_supplicant_loading = true;
        }
        catch(const std::runtime_error&)
        {
            retry_time--;
        }
    }
    if (!wpa_supplicant_loading)
    {
        stopWPASupplicant(wpa_supplicant_pid);
        wpa_supplicant_pid = 0;
        SWSS_LOG_WARN("Cannot connect to wpa_supplicant.");
    }
}
```

`fork()` 後にソケットへのポーリング（`wpa_cli_exec status`）で応答確認。応答後に `configureMACsec()` を呼び出す。

**依存順序**: `fork() → ソケット応答待ち (RETRY_TIME 回) → configureMACsec()`

---

### 3. SAI macsec_sa 作成順 (macsecorch.cpp)

#### 3a. Port レベル (L960–996)

```cpp
// Switch Object 初期化（スイッチ単位で 1 回）
if (!initMACsecObject(*ctx.get_switch_id())) { return task_failed; }

// MACsec Port Object 作成（PORT ごと）
if (ctx.get_macsec_port() == nullptr)
{
    if (!createMACsecPort(...)) { return task_failed; }
}
```

#### 3b. SC レベル (L1887–1909)

```cpp
if (ctx.get_macsec_sc() == nullptr)
{
    if (!createMACsecSC(...)) { return task_failed; }
}
```

SC が未作成の場合は `task_failed`。taskUpdateEgressSA / taskUpdateIngressSA は SC 未作成時に `task_need_retry` を返す (L1106–1107)。

#### 3c. SA レベル (L2247–2251)

```cpp
if (ctx.get_macsec_sc() == nullptr)
{
    SWSS_LOG_INFO("The MACsec SC %s hasn't been created at the port %s.", ...);
    return task_need_retry;
}
```

#### 3d. 最初の SA 作成時の ACL 切り替え (L2328–2342)

```cpp
// If this SA is the first SA
// change the ACL entry action from packet action to MACsec flow
if (ctx.get_macsec_port()->m_enable && sc->m_sa_ids.empty())
{
    if (!setMACsecFlowActive(sc->m_entry_id, sc->m_flow_id, true))
    {
        return task_failed;
    }
}
```

SA 削除で 0 件になると逆に "packet action" へ戻す (L2419–2427)。

#### 3e. Ingress SA のトリガ型制御 (L1153–1208)

```cpp
// active = true → createMACsecSA (Ingress)
if (active) { return createMACsecSA(port_sci_an, sa_attr, SAI_MACSEC_DIRECTION_INGRESS); }
// active = false → deleteMACsecSA (Ingress)
```

Egress SA は `encoding_an` フィールドが SC の `m_encoding_an` と一致する AN のみ作成し、不一致は `task_need_retry` (L1109–1136)。

---

### まとめ: 全体的な順序依存チェーン

```
[CONFIG_DB] MACSEC_PROFILE|<name> 存在
  ↓ (必須: task_need_retry)
[STATE_DB]  PORT|<port> state=ok + netdev_oper_status=up
  ↓ (必須: task_need_retry)
[macsecmgrd] wpa_supplicant fork() + ソケット待ち
  ↓ (必須: ポーリング成功)
[macsecmgrd] configureMACsec() → wpa_cli でインターフェース設定
  ↓ (APPL_DB 経由)
[MACsecOrch] SAI MACsec Switch Object (initMACsecObject)
  ↓
[MACsecOrch] SAI MACsec Port Object (createMACsecPort)
  ↓
[MACsecOrch] SAI MACsec SC Object (createMACsecSC)
  ↓
[MACsecOrch] SAI MACsec SA Object (createMACsecSA)
  ↓ (最初の SA 作成時のみ)
[MACsecOrch] ACL エントリ: packet action → MACsec flow
```

<!-- /ordering -->
