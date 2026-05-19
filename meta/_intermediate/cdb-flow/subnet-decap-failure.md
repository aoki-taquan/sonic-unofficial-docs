# SUBNET_DECAP 失敗挙動調査 (Phase D)

## ソース
- `sonic-swss/orchagent/tunneldecaporch.cpp`

## 調査結果

### doSubnetDecapTask() 失敗パス

失敗制御は `valid` フラグで行われる。失敗時は即時破棄でリトライなし。

1. **src_ip + src_ip_v6 両方未設定**: L636-640 — `valid=false` → 破棄
2. **src_ip に IPv6**: L597-601 — `isV4()` 失敗 → `valid=false` → 破棄
3. **src_ip 形式不正**: L591-595 — `std::invalid_argument` → `valid=false` → 破棄
4. **src_ip_v6 に IPv4**: L617-621 — `isV4()` 真 → `valid=false` → 破棄
5. **src_ip_v6 形式不正**: L609-613 — `std::invalid_argument` → `valid=false` → 破棄
6. **未知フィールド**: L628-633 — `valid=false` → 破棄

### doDecapTunnelTermTask() subnet decap 関連失敗パス

- MP2MP 以外の term: L446-449 — 即時破棄
- subnet decap disabled: L504-508 — `erase(it)` 破棄
- src_ip 未設定: L482-486 — `erase(it)` 破棄
- src_ip_v6 未設定: L495-499 — `erase(it)` 破棄
- SAI 失敗: L513-516 — SWSS_LOG_ERROR のみ、破棄
- tunnel 未存在: L511 — `unhandledDecapTerms` キューへ、トンネル追加後に再処理

### STATE_DB / ERROR_TABLE

- STATE_DB への失敗ステータス書き込みなし
- ERROR_TABLE への書き込みなし
- 成功時のみ STATE_TUNNEL_DECAP_TABLE が更新される
