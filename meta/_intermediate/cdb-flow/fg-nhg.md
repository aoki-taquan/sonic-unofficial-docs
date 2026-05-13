# CONFIG_DB 例外条件分析: FG_NHG / FG_NHG_PREFIX / FG_NHG_MEMBER

## Consumer

- `fgnhgorch` (`sonic-swss/orchagent/fgnhgorch.cpp`): orchagent が `FG_NHG`・`FG_NHG_PREFIX`・`FG_NHG_MEMBER` の 3 テーブルを subscribe。`doTask()` → `doTaskFgNhg()` / `doTaskFgNhgPrefix()` / `doTaskFgNhgMember()` に振り分け。

## 例外条件

### 1. match_mode が不正値 → route-based にフォールバック
- ソース: `fgnhgorch.cpp` L1705
- `match_mode` が `nexthop-based` でも `prefix-based` でもない値を受けると `SWSS_LOG_WARN` を出して `route-based` として扱う。エントリは拒否されず処理継続。
- 証拠: `SWSS_LOG_WARN("Received unsupported match_mode %s, defaulted to route-based", ...)`

### 2. match_mode==prefix-based かつ max_next_hops==0 → エラーログ・処理継続
- ソース: `fgnhgorch.cpp` L1716-1719
- `prefix_based` で `max_next_hops` が 0（未設定）の場合 `SWSS_LOG_ERROR` を出すが処理はリターンしない。SAI グループが誤動作する可能性がある。
- 証拠: `SWSS_LOG_ERROR("Received match_mode==prefix_based with max_next_hops 0, not a supported combination")`

### 3. bucket_size==0 → エラーログ・エントリ破棄
- ソース: `fgnhgorch.cpp` L1722-1726
- `bucket_size` が 0 の場合は `SWSS_LOG_ERROR` を出して `return true`（処理済みとして再試行なし）。

### 4. FG_NHG エントリ重複 → warn + ignore
- ソース: `fgnhgorch.cpp` L1730
- 既存 `fg_nhg_name` に SET が来ると `SWSS_LOG_WARN("FG_NHG %s already exists, ignoring", ...)` → 更新されない。削除して再設定が必要。

### 5. FG_NHG_PREFIX DEL で prefix 未存在 → info ログ + 正常終了
- ソース: `fgnhgorch.cpp` L1895
- `DEL` 時に prefix が存在しない場合 `SWSS_LOG_INFO("FG_NHG prefix doesn't exists, ignore")` → `return true`（エラー扱いにならない）。

### 6. FG_NHG_MEMBER を prefix-based グループに追加 → エラーログ・破棄
- ソース: `fgnhgorch.cpp` L2010-2015
- `prefix-based` グループに `FG_NHG_MEMBER` を投入すると `SWSS_LOG_ERROR("Received FG_NHG member for prefix-based match_mode, not a supported operation")` → `return true`。

### 7. FG_NHG エントリ未受信時の MEMBER → 処理延期
- ソース: `fgnhgorch.cpp` L2005
- 親 `FG_NHG` が未だ存在しない場合 `SWSS_LOG_INFO("FG_NHG entry not received yet, continue")` → `return false`（Consumer キューに残り再試行）。

### 8. max_next_hops 超過ネクストホップ → スキップ
- ソース: `fgnhgorch.cpp` L1365
- prefix-based モードで nh 数が `max_next_hops` を超えると `SWSS_LOG_WARN("Next-hop %s exceeds max_next_hops %d for prefix %s, skipping", ...)` → 超過分は無視。

### 9. 一部 FG nh を持つルートで非 FG nh が混在 → 非 FG ECMP にデグレード
- ソース: `fgnhgorch.cpp` L1224
- FG グループに属さない NH が混在するルートは `SWSS_LOG_WARN` を出し、ルート全体を通常 ECMP として扱う。
