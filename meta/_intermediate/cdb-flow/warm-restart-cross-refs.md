# WARM_RESTART 暗黙参照テーブル調査 (Phase C)

調査日: 2026-05-18
対象: `docs/reference/config-db/warm-restart.md`

---

## 暗黙参照マップ

### CONFIG_DB WARM_RESTART → 他テーブル

| 参照方向 | このテーブル | 相手テーブル / リソース | 条件 | evidence |
|---------|------------|----------------------|------|---------|
| WARM_RESTART → | `module=bgp` エントリ存在 | `STATE_DB WARM_RESTART_ENABLE_TABLE\|bgp` | `bgp.sh` の `check_warm_boot()` が STATE_DB の enable フラグを確認した場合のみ CONFIG_DB から `bgp_timer` を読む | `warm_restart.cpp:86-147`, `bgp.sh:9-27` |
| WARM_RESTART → | `module=teamd` エントリ存在 | `STATE_DB WARM_RESTART_ENABLE_TABLE\|teamd` | 同上。STATE_DB enable 確認後に `teamsyncd_timer` を読む | `warm_restart.cpp:86-147`, `teamd.sh:9-27` |
| WARM_RESTART → | `module=swss` エントリ存在 | `STATE_DB WARM_RESTART_ENABLE_TABLE\|swss` | 同上。`neighsyncd_timer` を読む | `warm_restart.cpp:86-147`, `swss.sh:9-27` |
| WARM_RESTART → | `bgp_eoiu=true` | `supervisord.conf.j2 (bgp_eoiu_marker)` | `bgp_eoiu` が true の場合のみ `bgp_eoiu_marker` プロセスが supervisord に登録される | `sonic-buildimage/dockers/docker-fpm-frr/.../supervisord.conf.j2:239` |

### 他テーブル → CONFIG_DB WARM_RESTART

| 参照方向 | 相手テーブル / リソース | このテーブルの参照対象 | 条件 | evidence |
|---------|----------------------|---------------------|------|---------|
| → WARM_RESTART | `STATE_DB WARM_RESTART_ENABLE_TABLE\|system` | - (enable 確認後に全 warm_restart timer を読む前提) | enable=true かつ restore_count > 0 の場合のみ warm start として扱う | `warm_restart.cpp:86-147` |
| → WARM_RESTART | `finalize-warmboot.sh` (fast-reboot 時) | `WARM_RESTART\|teamd` (DEL 操作) | `finalize_fast_reboot()` が `CONFIG_DB DEL "WARM_RESTART\|teamd"` を実行する | `finalize-warmboot.sh:175` |

### YANG leafref 依存

`sonic-warm-restart.yang` は自テーブル内の `must` 制約のみで、他テーブルへの leafref 参照を持たない。
依存関係は YANG データモデル上ではなくランタイムコードの実装に存在する。

---

## 参照コード

| ファイル | 関連箇所 |
|---------|---------|
| `sonic-swss-common/common/warm_restart.cpp` | `checkWarmStart()` L86-147 (STATE_DB 確認), `getWarmStartTimer()` L149-172 (CONFIG_DB 読取) |
| `sonic-buildimage/files/scripts/bgp.sh` | `check_warm_boot()` L9-27 (STATE_DB → warm start 判定) |
| `sonic-buildimage/files/image_config/warmboot-finalizer/finalize-warmboot.sh` | `finalize_fast_reboot()` L175 (CONFIG_DB DEL "WARM_RESTART|teamd") |
| `sonic-buildimage/dockers/docker-fpm-frr/.../supervisord.conf.j2` | L239 (`bgp_eoiu` 条件分岐 → `bgp_eoiu_marker` 登録) |
