# STATIC_NAT — Phase C 暗黙参照テーブル調査メモ

slug: nat-static  
phase: C (cross-refs)  
調査日: 2026-05-18  
調査元: sonic-swss/cfgmgr/natmgr.cpp

## 参照パス整理

`doStaticNatTask()` は SET を受け付けてキャッシュ (`m_staticNatEntry`) に格納し、`addStaticNatEntry()` を呼ぶ。
`addStaticNatEntry()` 内で以下の暗黙参照が発生する:

1. **NAT_GLOBAL (管理変数 `natAdminMode`)**: `isNatEnabled()` が `natAdminMode == ENABLED` のみ true。`doNatGlobalTask()` が `NAT_GLOBAL|Values.admin_mode` を受信し `natAdminMode` を更新する。YANG leafref なし。

2. **STATE_DB:STATE_INTERFACE_TABLE**: `doNatIpInterfaceTask()` が `INTERFACE|<port>|<prefix>` を受信する前に `isIntfStateOk()` で `m_stateInterfaceTable.get()` を確認。ready でなければ `it++; continue` でリトライ。

3. **INTERFACE (m_natIpInterfaceInfo)**: `getIpEnabledIntf()` が `m_natIpInterfaceInfo` を走査し global_ip がいずれかのサブネットに含まれるか確認。DNAT エントリのみ必須。`doNatIpInterfaceTask()` が `INTERFACE|<port>|<ip/prefix>` SET で `m_natIpInterfaceInfo[port]` を更新。

4. **STATIC_NAPT (m_staticNaptEntry)**: `isMatchesWithStaticNapt()` が `m_staticNaptEntry` を走査し global_ip の重複をチェック。重複時は APPL_DB 反映なし (return)。YANG leafref なし。

5. **NAT_POOL (m_natPoolInfo) [doStaticNatTask 内]**: `doStaticNatTask()` の SET ハンドラが `m_natPoolInfo` を走査して global_ip が NAT_POOL の IP 範囲と重複しないか確認。重複時は erase。

6. **STATIC_NAT 同士 (Twice NAT; m_staticNatEntry)**: `addStaticTwiceNatEntry()` が `m_staticNatEntry` 全体を走査し、`twice_nat_id` が一致する SNAT+DNAT ペアを探して APPL_DB に書く。2 エントリが揃うまで双方のキャッシュに pending 保持。

7. **NAT_BINDINGS + NAT_POOL (m_natBindingInfo, m_natPoolInfo; Twice NAT バインディング)**: `addStaticTwiceNatEntry()` は `m_staticNatEntry` の Twice NAT ペア探索に失敗した場合、さらに `m_natBindingInfo` + `m_natPoolInfo` を走査して SNAT ダイナミックバインディングとのペア接続を試みる (natmgr.cpp:2210-2263)。
