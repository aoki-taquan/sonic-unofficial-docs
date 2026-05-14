# MIRROR_SESSION — Phase 6/7/8 中間ファイル

生成日: 2026-05-14 (batch cdb_batch_3)

<!-- derivation -->
## Phase 6: 自動派生代入スキャン

### minigraph.py — MIRROR_SESSION 派生

`minigraph.py` の MIRROR_SESSION 生成は **コメントアウト済み** (L2709-L2721)。

```
# L2709: # mirror_sessions = {}
# L2719: #   mirror_sessions['everflow...'] = {"dst_ip": dst, "src_ip": lo_addr}
# L2721: # results['MIRROR_SESSION'] = mirror_sessions
```

現行 minigraph.py は MIRROR_SESSION を自動生成しない。手動 config_db.json / CLI が必要。

### config_samples.py / db_migrator.py / init_cfg.json.j2 — 該当なし

**結論**: Phase 6 派生なし — MIRROR_SESSION はすべて明示的 CLI 設定。

<!-- /derivation -->

<!-- derivation -->
## Phase 7: 条件付き manager/orch 登録

### orchdaemon.cpp — MirrorOrch 登録

`orchdaemon.cpp:406`:
```cpp
gMirrorOrch = new MirrorOrch(stateDbMirrorSession, confDbMirrorSession,
    gPortsOrch, gRouteOrch, gNeighOrch, gFdbOrch, gPolicerOrch, gSwitchOrch);
```

`m_orchList` への追加: `orchdaemon.cpp:568` — **常時**。条件付き登録なし。

<!-- /derivation -->

<!-- handler-branching -->
## Phase 8: manager メソッド内 early return / dispatch

### mirrororch.cpp — doTask 分岐

主要 early return パターン:

| 条件 | 場所 | 戻り値 |
|------|------|--------|
| MIRROR_SESSION エントリ不存在 | L217 | `return false` |
| ポート解決失敗 | L231 | `return false` |
| ネクストホップ解決失敗 | L245 | `return false` |
| SAI ミラーセッション作成失敗 | L280 | `return false` |
| ERSPAN 用 IP ルート未解決 | L285 | `return false` |

SET path: `addMirrorEntry()` → nexthop/port 解決 → SAI session 作成。
DEL path: `removeMirrorEntry()` → SAI session 削除 → 関連 ACL rule を無効化。

<!-- /handler-branching -->
