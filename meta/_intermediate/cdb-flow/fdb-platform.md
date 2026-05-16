# fdb-platform.md — Phase H プラットフォーム差分抽出

ソース: `sonic-swss/orchagent/fdborch.cpp` (master)

## 1. SAI FDB サポート差（DIP トンネル vs SIP トンネル）

`fdborch.cpp:1308-1312` で `isDipTunnelsSupported()` の結果によって VXLAN FDB のエンドポイント IP 解決パスが分岐する。

```cpp
// fdborch.cpp:1308-1313
if (!tunnel_orch->isDipTunnelsSupported())
{
    end_point_ip = fdbData.remote_ip;
}
```

- **DIP トンネル対応プラットフォーム**: リモート VTEP ごとに個別トンネルポートを作成（`getTunnelPortName(remote_ip)`）。`SAI_FDB_ENTRY_ATTR_ENDPOINT_IP` は不要。VLAN メンバー識別に port のみを使用。
- **SIP トンネル対応プラットフォーム（DIP 非対応）**: 単一の SIP トンネルポートを共有。`end_point_ip = fdbData.remote_ip` で VLAN メンバー識別時に IP アドレスを付加。`SAI_FDB_ENTRY_ATTR_ENDPOINT_IP` を SAI FDB エントリに設定する（`fdborch.cpp:1467,1481`）。

さらに `fdborch.cpp:836-854` で doTask 内でも同様の分岐:

```cpp
if (tunnel_orch->isDipTunnelsSupported())
{
    port = tunnel_orch->getTunnelPortName(remote_ip);
}
else
{
    // SIP tunnel: use EVPN VTEP single tunnel port
    VxlanTunnel* sip_tunnel = evpn_nvo_orch->getEVPNVtep();
    port = tunnel_orch->getTunnelPortName(sip_tunnel->getSrcIP().to_string(), true);
}
```

## 2. MCLAG 連携差

MCLAG リモート MAC (`FDB_ORIGIN_MCLAG_ADVERTIZED`) は通常のプロビジョニング MAC と異なる SAI 属性で登録される。

### 2a. SAI_FDB_ENTRY_ATTR_TYPE の差

`fdborch.cpp:449-455`:
```cpp
if (fdbData.origin == FDB_ORIGIN_VXLAN_ADVERTIZED)
{
    attr.value.s32 = SAI_FDB_ENTRY_TYPE_STATIC;
}
else if (fdbData.origin == FDB_ORIGIN_MCLAG_ADVERTIZED)
{
    attr.value.s32 = (fdbData.type == "dynamic_local") ?
        SAI_FDB_ENTRY_TYPE_DYNAMIC : SAI_FDB_ENTRY_TYPE_STATIC;
}
else
{
    attr.value.s32 = (fdbData.type == "dynamic") ?
        SAI_FDB_ENTRY_TYPE_DYNAMIC : SAI_FDB_ENTRY_TYPE_STATIC;
}
```

MCLAG リモート MAC は `type` フィールドが `"dynamic_local"` の場合のみ `SAI_FDB_ENTRY_TYPE_DYNAMIC` となり、それ以外（`"dynamic"` を含む）は `SAI_FDB_ENTRY_TYPE_STATIC` として SAI に登録される。

### 2b. SAI_FDB_ENTRY_ATTR_ALLOW_MAC_MOVE の付加

`fdborch.cpp:461-465`:
```cpp
if (((fdbData.origin == FDB_ORIGIN_VXLAN_ADVERTIZED) ||
     (fdbData.origin == FDB_ORIGIN_MCLAG_ADVERTIZED))
        && (fdbData.type == "dynamic"))
{
    attr.id = SAI_FDB_ENTRY_ATTR_ALLOW_MAC_MOVE;
    attr.value.booldata = true;
    attrs.push_back(attr);
}
```

MCLAG/VXLAN のリモート dynamic MAC には `ALLOW_MAC_MOVE=true` が付与される。これにより、同一 MAC のローカル学習が発生しても SAI レベルで上書き移動が許可される。

### 2c. AGE イベントでの MCLAG MAC 保護

`fdborch.cpp:490-521`: MCLAG リモート MAC が AGE イベントを受け取った場合、通常の削除処理を行わず SAI FDB エントリを再作成する（`SAI_FDB_ENTRY_TYPE_STATIC` + `ALLOW_MAC_MOVE=true`）。これはローカル FDB ASIC の aging が MCLAG リモートエントリを誤削除しないようにするための保護。

### 2d. ローカル学習による MCLAG リモート → ローカル MAC 移動

`fdborch.cpp:332-384`: LEARN イベントで既存 MCLAG リモートエントリと同一 MAC が検出された場合、SAI FDB エントリを `SAI_FDB_ENTRY_TYPE_DYNAMIC` + 新ブリッジポートで更新。同時に STATE_DB の MCLAG FDB テーブルから当該エントリを削除（`m_mclagFdbStateTable.del(key)`）。

## 3. Warm-reboot リカバリ差

`fdborch.cpp:51-66` (`FdbOrch::bake()`):
```cpp
bool FdbOrch::bake()
{
    Orch::bake();
    auto consumer = dynamic_cast<Consumer *>(getExecutor(APP_FDB_TABLE_NAME));
    if (consumer == NULL)
    {
        SWSS_LOG_ERROR("No consumer %s in Orch", APP_FDB_TABLE_NAME);
        return false;
    }
    size_t refilled = consumer->refillToSync(&m_fdbStateTable);
    SWSS_LOG_NOTICE("Add warm input FDB State: %s, %zd", APP_FDB_TABLE_NAME, refilled);
    return true;
}
```

- Warm-reboot 時、`FdbOrch::bake()` が STATE_DB `FDB_TABLE` から FDB エントリを `m_toSync` キューに再投入（`refillToSync`）する。SAI に再プログラムする前に STATE_DB を正規ソースとして使用するため、ASIC FDB テーブルが残存していてもソフトウェアと一致させることができる。
- **プラットフォーム差**: `bake()` の挙動自体は共通だが、DIP トンネル対応 ASIC では warm-reboot 後に VXLAN FDB エントリのエンドポイント IP が不要（ポート名で一意識別）なのに対し、SIP トンネル ASIC では STATE_DB 復旧時にエンドポイント IP も保持されていることが必要。

## 4. まとめ（docs/reference/config-db/fdb.md への反映指針）

| 差分カテゴリ | 内容 | 追加箇所 |
|-------------|------|---------|
| SAI FDB サポート差 | DIP/SIP トンネル分岐による ENDPOINT_IP 属性の有無 | `<!-- platform -->` ブロック新設 |
| MCLAG 連携差 | ALLOW_MAC_MOVE 付加、AGE 保護、type マッピング差 | `<!-- platform -->` ブロック内 |
| warm-reboot リカバリ差 | bake() による STATE_DB からの FDB 再投入、SIP トンネル ASIC での IP 保持要件 | `<!-- platform -->` ブロック内 |
