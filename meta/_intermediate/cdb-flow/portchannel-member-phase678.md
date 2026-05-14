# PORTCHANNEL_MEMBER — Phase 6/7/8 中間ファイル

生成日: 2026-05-14 (batch cdb_batch_4)

<!-- derivation -->
## Phase 6: 自動派生代入スキャン

### minigraph.py — PORTCHANNEL_MEMBER 自動生成

```
# minigraph.py:2547
results['PORTCHANNEL_MEMBER'] = pc_members
```

`pc_members` は minigraph XML の `<PortChannel>` 内 `<member>` タグから自動生成。各メンバーポートに空のフィールド辞書 `{}` を割り当て。

### db_migrator.py / config_samples.py / init_cfg.json.j2 — 該当なし

<!-- /derivation -->

<!-- derivation -->
## Phase 7: 条件付き manager/orch 登録

TeamMgr (teammgr.cpp) が PORTCHANNEL_MEMBER を購読し `teamd` にメンバーポートを追加/削除。常時起動、条件付き登録なし。

<!-- /derivation -->

<!-- handler-branching -->
## Phase 8: manager メソッド内 early return / dispatch

### teammgr.cpp — PORTCHANNEL_MEMBER ハンドラ分岐

| 操作 | 処理 |
|------|------|
| SET | `addPortChannelMember()` → `teamd ctl port add` |
| DEL | `removePortChannelMember()` → `teamd ctl port remove` |

early return:
- PortChannel 未作成 → `task_need_retry`
- ポートが他 PortChannel に所属中 → `task_invalid_entry`
- teamd コマンド失敗 → `task_failed`

<!-- /handler-branching -->
