# nvgre-tunnel — Phase D failure 調査ノート

## 調査対象

- `sonic-swss/orchagent/nvgreorch.cpp` (全行精読)

## 主要な失敗パス

### SET NVGRE_TUNNEL の失敗

1. 重複 SET: `isTunnelExists()` が true → WARN + `return true` (消費完了、再投入なし) `nvgreorch.cpp:357-361`
2. SAI create_tunnel_map 失敗: `throw std::runtime_error("Can't create the NVGRE tunnel map object")` `nvgreorch.cpp:106`
3. SAI create_tunnel 失敗: `throw std::runtime_error("Can't create the NVGRE tunnel object")` `nvgreorch.cpp:190`
4. SAI create_tunnel_termination 失敗: `throw std::runtime_error("Can't create a tunnel term table object")` `nvgreorch.cpp:253`
   - catch なし → orchagent abort → systemd 再起動

### DEL NVGRE_TUNNEL の失敗

5. 存在しない tunnel DEL: ERROR ログ + `return true` `nvgreorch.cpp:374-378`
6. SAI remove 失敗: `removeNvgreTunnel()` 内で catch + SWSS_LOG_ERROR → エラー消費 `nvgreorch.cpp:325-327`

### SET NVGRE_TUNNEL_MAP の失敗 (重要: return true = 永続廃棄)

7. 親トンネル未登録: WARN + `return true` (永続廃棄) `nvgreorch.cpp:473-474`
8. 重複 MAP: WARN + `return true` `nvgreorch.cpp:482-483`
9. VLAN 未登録: WARN + `return true` (永続廃棄) `nvgreorch.cpp:491-492`
10. VSID 範囲外: WARN + `return true` `nvgreorch.cpp:498-499`
11. SAI create_tunnel_map_entry 失敗: throw → orchagent abort `nvgreorch.cpp:438`

### DEL NVGRE_TUNNEL_MAP の失敗

12. 親トンネル存在しない: WARN + `return true` `nvgreorch.cpp:565-566`
13. MAP エントリ存在しない: WARN + `return true` `nvgreorch.cpp:571-573`
14. SAI remove_tunnel_map_entry 失敗: catch + SWSS_LOG_ERROR → `false` → delOperation が `return true` `nvgreorch.cpp:527,539-543`

## キー設計特性

- `return true` = 消費完了 = リトライなし (Orch2 契約)
- `return false` = キュー再投入 = リトライあり (NvgreTunnelMapOrch の delOperation で使われていない)
- SAI ADD 失敗は catch なし → abort → 自己回復
- SAI DEL 失敗は catch あり → エラー消費 → SAI オブジェクト孤立リスク
