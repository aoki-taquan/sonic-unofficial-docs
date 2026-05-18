# cbf-nhg Phase D — 失敗挙動 調査ノート

## 調査対象

- `sonic-swss/orchagent/cbf/cbfnhgorch.cpp` (全行)
- `sonic-swss/orchagent/cbf/cbfnhgorch.h`

## SET 操作の失敗分岐

### allPortsReady() ガード (L42-44)
早期 return。m_toSync に全タスク滞留。ログなし。

### getMembers() バリデーション失敗 (L82-90)
- 空 members: SWSS_LOG_ERROR + erase（破棄、retry なし）
- 重複 members: SWSS_LOG_ERROR + erase（破棄、retry なし）

### NHG 上限チェック (L100-103)
`gRouteOrch->getNhgCount() + NhgBase::getSyncedCount() >= gRouteOrch->getMaxNhgCount()` が真の場合
SWSS_LOG_WARN + success=false → it++（保留）

### CbfNhg::sync() 失敗パス (L287-375)
- selection_map 未登録: L319-325 → SWSS_LOG_ERROR + return false
- selection_map の最大 NH index >= members 数: L327-331 → SWSS_LOG_ERROR + return false
- SAI create_next_hop_group 失敗: L341-345 → SWSS_LOG_ERROR + return false
- syncMembers() 失敗: L369-373 → SWSS_LOG_ERROR + return false

### 一時 NHG 含む sync 成功後 (L116-119)
`cbf_nhg->hasTemps()` が true → success=false → it++（保留）
NHG は m_syncdNextHopGroups に登録済み。次ループで update() 経路。

## DEL 操作の失敗分岐

### 後続 SET あり (L152-155)
success=true で DEL をスキップ → erase。後続 SET が update として処理。

### 存在しない NHG の DEL (L157-163)
SWSS_LOG_WARN + success=true → erase（冪等成功）

### 参照カウント > 0 (L165-170)
SWSS_LOG_WARN("Skipping removal ... which is still referenced") + success=false → it++（保留）

### SAI remove 失敗
CbfNhg::remove() / removeMembers() が false → success=false → it++（保留）

## ERROR_TABLE
書き込みなし。CBF NHG は STATE_DB ステータスを持たない。

## 調査日
2026-05-18
