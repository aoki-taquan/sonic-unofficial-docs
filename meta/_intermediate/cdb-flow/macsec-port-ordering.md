# macsec-port — Phase B: 順序依存・起動順

## 調査対象

- `sonic-swss/cfgmgr/macsecmgr.cpp` — `MACsecMgr::enableMACsec()`, `isPortStateOk()`, `removeProfile()`
- `sonic-swss/orchagent/macsecorch.cpp` — `MACsecOrch::createMACsecPort()`, `createMACsecSC()`, `createMACsecSA()`

## 前提条件チェーン (enableMACsec)

`PORT|<ifname>.macsec` の SET イベントで `enableMACsec()` が呼ばれる際、以下の 2 条件が揃うまで `task_need_retry` を返し続ける。

1. **MACSEC_PROFILE が先にロードされていること**
   - `m_profiles.find(profile_name) == m_profiles.end()` → `task_need_retry`
   - `loadProfile()` (MACSEC_PROFILE SET) が完了して初めて有効
   - 証跡: `cfgmgr/macsecmgr.cpp:488-495`

2. **PORT が STATE_DB で ready であること**
   - `isPortStateOk(port_name)` → `STATE_PORT_TABLE_NAME` から `state == "ok"` かつ `netdev_oper_status == "up"` を確認
   - 未達の場合 `task_need_retry`
   - 証跡: `cfgmgr/macsecmgr.cpp:500-503`, `614-631`

## プロファイル変更時の順序

既に MACsec が有効なポートに別プロファイルを設定した場合:
1. `disableMACsec()` (旧プロファイル解除・wpa_supplicant 停止)
2. `enableMACsec()` (新プロファイルで再起動)
- 証跡: `cfgmgr/macsecmgr.cpp:519-527`

## プロファイル削除の順序ロック

`removeProfile()` は参照中ポートが 1 つでも残っている間は `task_need_retry` を返し削除を拒否する。
すべてのポートで `disableMACsec()` が完了してから削除が成立する。
- 証跡: `cfgmgr/macsecmgr.cpp:452-466`

## SAI MACsec オブジェクト作成順 (macsecorch)

`MACsecOrch` が SAI オブジェクトを作成する順序:

```
1. MACsec Switch Object (initMACsecObject)  ← スイッチ単位で 1 回
2. MACsec Port Object (createMACsecPort)    ← PORT ごと
3. MACsec SC Object (createMACsecSC)        ← SC ごと
4. MACsec SA Object (createMACsecSA)        ← SA ごと
```

前段オブジェクトが未作成の場合は `task_need_retry` で待機。
