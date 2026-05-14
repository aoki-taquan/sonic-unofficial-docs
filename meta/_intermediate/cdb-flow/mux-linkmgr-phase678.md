# MUX_LINKMGR — Phase 6/7/8 中間ファイル

生成日: 2026-05-14 (batch cdb_batch_3)

<!-- derivation -->
## Phase 6: 自動派生代入スキャン

### 全ソース — 該当なし

minigraph.py / config_samples.py / db_migrator.py / init_cfg.json.j2 に MUX_LINKMGR への代入なし。MUX_LINKMGR は linkmgrd デーモンが実行時に STATE_DB へ書き込む。

init_cfg.json.j2 間接: `mux feature: subtype=='DualToR' → always_enabled` (linkmgrd コンテナ起動条件)。

**結論**: Phase 6 直接派生なし。

<!-- /derivation -->

<!-- derivation -->
## Phase 7: 条件付き manager/orch 登録

`sonic-linkmgrd` リポが MUX_LINKMGR を購読。`mux` feature が always_enabled かつ DualToR 環境のみ起動。orchdaemon 側は MUX_LINKMGR を直接購読しない。linkmgrd → STATE_DB → MuxOrch の経路。

<!-- /derivation -->

<!-- handler-branching -->
## Phase 8: manager メソッド内 early return / dispatch

### linkmgrd — dispatch

| 条件 | 処理 |
|------|------|
| `link_state` = `up` | MUX ステート機械を active 方向へ遷移 |
| `link_state` = `down` | standby 切替トリガー |
| プローブ応答なし | oscillation 検出カウンタ増加 |

orchagent 側では STATE_DB 経由で MuxOrch が反映。

<!-- /handler-branching -->
