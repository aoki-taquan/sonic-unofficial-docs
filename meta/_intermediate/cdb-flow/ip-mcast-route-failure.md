# IP マルチキャストルート (P4RT) — Phase D 失敗挙動スキャンノート

対象テーブル: `REPLICATION_IP_MULTICAST_TABLE` / `FIXED_IPV4_MULTICAST_TABLE` / `FIXED_IPV6_MULTICAST_TABLE`
Consumer: `L3MulticastManager` (orchagent p4orch/l3_multicast_manager.cpp)、`IpMulticastManager` (orchagent p4orch/ip_multicast_manager.cpp)
スキャン範囲: `orchagent/p4orch/ip_multicast_manager.cpp`、`orchagent/p4orch/l3_multicast_manager.cpp`

---

## 検出した失敗シナリオ

### IpMulticastManager — SET (CREATE) 時の失敗パターン

1. **デシリアライズ失敗** (`ip_multicast_manager.cpp:L127-135`)
   - APP_DB エントリのパース失敗 → `SWSS_LOG_ERROR` + `m_publisher->publish(..., status)` → バッチ中断
   - retry: なし（バッチ全体が中断）

2. **同一バッチ内での同一エントリ重複** (`ip_multicast_manager.cpp:L142-150`)
   - `SWSS_RC_INVALID_PARAM` + `SWSS_LOG_ERROR` → `m_publisher->publish` → バッチ中断

3. **バリデーション失敗** (`ip_multicast_manager.cpp:L154-163`)
   - `validateIpMulticastEntry()` が失敗した場合 (`SWSS_RC_NOT_FOUND` / `SWSS_RC_INVALID_PARAM` など)
   - `SWSS_LOG_ERROR` + `m_publisher->publish` → バッチ中断

4. **P4OidMapper で multicast group OID 未登録** (`ip_multicast_manager.cpp:L748-755`)
   - `SWSS_RC_NOT_FOUND` → バッチ失敗（バッチ内後続エントリは `SWSS_RC_NOT_EXECUTED`）

5. **SAI create_ipmc_entry 失敗** (`ip_multicast_manager.cpp:L761-764`)
   - SAI_STATUS_SUCCESS 以外 → バッチ失敗（後続エントリは `SWSS_RC_NOT_EXECUTED`）

6. **defaultRpfGroup 作成失敗** (`ip_multicast_manager.cpp:L661-665`, `L639-642`, `L612-615`)
   - 最初の IPMC エントリ追加前に RPF group / RIF / RPF group member が作成される
   - SAI 失敗時は `LOG_ERROR_AND_RETURN` で `ReturnCode(status)` を即返却

### IpMulticastManager — UPDATE 時の失敗パターン

7. **内部キャッシュに存在しないエントリの更新** (`ip_multicast_manager.cpp:L794-798`)
   - `SWSS_RC_INTERNAL` → バッチ失敗

8. **更新時 group OID 未登録** (`ip_multicast_manager.cpp:L817-820`)
   - `SWSS_RC_NOT_FOUND` → バッチ失敗

9. **SAI set_ipmc_entry_attribute 失敗** (`ip_multicast_manager.cpp:L827-830`)
   - SAI_STATUS_SUCCESS 以外 → バッチ失敗

### IpMulticastManager — DEL 時の失敗パターン

10. **内部キャッシュに存在しないエントリの削除** (`ip_multicast_manager.cpp:L866`)
    - `SWSS_RC_NOT_FOUND` → バッチ失敗

11. **SAI remove_ipmc_entry 失敗**
    - SAI_STATUS_SUCCESS 以外 → バッチ失敗

12. **deleteDefaultRpfGroup 失敗** (`ip_multicast_manager.cpp:L691-693`)
    - 全 IPMC エントリ削除後に内部 RPF group を削除する際の SAI 失敗
    - 失敗時は直前の IPMC エントリ削除が成功していても `LOG_ERROR_AND_RETURN`

### L3MulticastManager — SET 時の失敗パターン

13. **デシリアライズ失敗** (`l3_multicast_manager.cpp:L430`)
    - `SWSS_LOG_ERROR` + `m_publisher->publish` → バッチ中断

14. **replicas フィールド空** (`l3_multicast_manager.cpp:L991`)
    - `SWSS_RC_INVALID_PARAM` → バッチ失敗

15. **replica の router interface 未登録** (`l3_multicast_manager.cpp:L1003-1008`)
    - `SWSS_RC_NOT_FOUND` → バッチ失敗

## バッチセマンティクス

P4RT フレームワークの失敗モデルは**バッチ内一括適用**で、失敗発生時は残りのエントリに `SWSS_RC_NOT_EXECUTED` を付与して中断する (`ip_multicast_manager.cpp:L184-189`)。個別エントリの retry は存在しない。コントローラ (`p4rt-app`) が状態確認のうえ再送を担う。

## STATE_DB / ERROR_TABLE への影響

- いずれの失敗でも STATE_DB への書き込みはない（P4RT マネージャは STATE_DB を直接操作しない）
- 失敗は `m_publisher->publish()` で APP_P4RT_TABLE_NAME に返却コードとして書き戻される（P4RT ステータスとして読み取り可能）
- CONFIG_DB は本テーブルに対して無関係（Phase C 済み）
