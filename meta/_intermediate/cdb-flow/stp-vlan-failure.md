# STP_VLAN / STP_VLAN_PORT — 失敗挙動調査 (Phase D)

調査日: 2026-05-18
対象ファイル:
- sonic-swss/cfgmgr/stpmgr.cpp (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- sonic-swss/cfgmgr/stpmgrd.cpp

## 調査まとめ

### doStpVlanTask 失敗パス

1. stpGlobalTask/stpPortTask 未満足 → `return` (保留, 自動リトライ)
2. l2ProtoEnabled == L2_NONE → `it++` (保留)
3. isVlanStateOk 失敗 → `it++` (保留)
4. allocL2Instance() == -1 (インスタンス枯渇) → SWSS_LOG_ERROR + erase (リトライなし)
5. SET calloc 失敗 → SWSS_LOG_ERROR + `return` (全キュー保留)
6. DEL calloc 失敗 → SWSS_LOG_ERROR + `return` (全キュー保留)
7. sendMsgStpd calloc 失敗 → SWSS_LOG_ERROR + return -1 (呼び元無視, エントリ消費)
8. sendMsgStpd sendto 失敗 → SWSS_LOG_ERROR + return -1 (呼び元無視, エントリ消費)
14. stoi 例外 → 未キャッチ → stpmgrd プロセス終了

### doStpVlanPortTask 失敗パス

9. 全3フラグ未到達 → `return` (保留)
10. 無効キー形式 → SWSS_LOG_ERROR + erase
11. SET: l2ProtoEnabled/m_vlanInstMap 未設定 → `it++` (保留)
12. DEL: l2ProtoEnabled/m_vlanInstMap 未設定 → erase (ログなし)
13. isLagEmpty() → erase (ログなし)

## 証跡

- stpmgr.cpp:183-185 (ガード条件)
- stpmgr.cpp:210-215 (l2ProtoEnabled/isVlanStateOk)
- stpmgr.cpp:263-269 (allocL2Instance失敗)
- stpmgr.cpp:278-283 (calloc失敗)
- stpmgr.cpp:319-323 (DEL calloc失敗)
- stpmgr.cpp:333-336 (sendMsgStpd 戻り値無視)
- stpmgr.cpp:444-450 (VlanPort ガード)
- stpmgr.cpp:473-479 (キー形式エラー)
- stpmgr.cpp:483-503 (l2ProtoEnabled/m_vlanInstMap)
- stpmgr.cpp:505-511 (isLagEmpty)
- stpmgr.cpp:1218-1251 (sendMsgStpd 実装)
