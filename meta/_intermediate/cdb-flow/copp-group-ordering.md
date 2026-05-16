# COPP_GROUP — Phase B 書込み順依存分析

中間ファイル。最終成果は `docs/reference/config-db/copp-group.md` の `<!-- ordering -->` ブロックに反映済み。

## 分析対象ソース

- `sonic-swss/cfgmgr/coppmgr.cpp` (コンストラクタ L296-422, `doCoppGroupTask` L840-925)
- `sonic-swss/orchagent/copporch.cpp` (`processCoppTrapGroup` L720-872)

## 書込み順依存の要点

### 1. init 時の処理順序（コンストラクタ内）

```
parseInitFile()               # copp.json をパース → m_coppGroupInitCfg / m_coppTrapInitCfg
mergeConfig(trap_cfg)         # COPP_TRAP を先にマージ → m_coppTrapConfMap / m_coppTrapIdTrapGroupMap を構築
mergeConfig(group_cfg)        # COPP_GROUP をマージ — trap_group → trap_ids の逆引き MAP が必要
```

**COPP_TRAP が COPP_GROUP より先に処理される**。`mergeConfig` の呼出し順 (L334 → L372) で確定。
COPP_GROUP の `checkTrapGroupPending()` は `m_coppTrapIdTrapGroupMap`（COPP_TRAP 処理で構築）を参照するため、
COPP_GROUP が先に来ると pending 判定が誤る。

### 2. ランタイム更新時の順序依存

`doCoppGroupTask` (SET) — L855-860:
```cpp
if (g_copp_init_set.find(key) != g_copp_init_set.end())
{
    g_copp_init_set.erase(key);
    it = consumer.m_toSync.erase(it);
    continue;  // 初回 CONFIG_DB 通知を無視（init時に設定済みのため）
}
```

init 時に `g_copp_init_set` に登録された key は、最初の CONFIG_DB SET イベントを読み飛ばす。
これにより **COPP_GROUP を CONFIG_DB に書く前に COPP_TRAP が存在していないと trap_ids が空になる** 可能性がある。

### 3. COPP_TRAP → COPP_GROUP の参照方向

- `COPP_TRAP` は `trap_group` フィールドで COPP_GROUP を参照する（FK 方向: TRAP → GROUP）
- `coppmgr` は COPP_TRAP を処理して trap_ids を trap_group に紐付け、
  その後 COPP_GROUP を処理して `APPL_DB COPP_TABLE` に `trap_ids` を付加して書き込む

依存方向:
```
COPP_GROUP (親) ← COPP_TRAP.trap_group (子が参照)
書込み順序: COPP_GROUP を先に CONFIG_DB に書く → COPP_TRAP を書く
```

ただし **coppmgr の APPL_DB への最終書き込みは COPP_GROUP ベース**（trap_ids を付加）なので、
COPP_TRAP が存在しない状態で COPP_GROUP を APPL_DB へ書いても `trap_ids` が空になるだけで
エラーにはならない（feature pending 扱いになる）。

### 4. DEL 時の依存

COPP_GROUP DEL 時: `coppmgr` は `checkTrapGroupPending()` を確認し、
pending でなければ `m_appCoppTable.del(key)` を呼ぶ。

**COPP_TRAP を先に削除しないと COPP_GROUP が pending 状態になり APPL_DB から削除されない**。

削除順序: COPP_TRAP を先に削除 → COPP_GROUP を削除

### 5. `default` グループの保護

`copporch.cpp` L861-864: `op == DEL_COMMAND` かつ `trap_group_name == "default"` → `task_ignore`。
`default` グループは CONFIG_DB からの DEL を無視する。運用上 `default` を削除しようとしても
APPL_DB / SAI 側には反映されない。

## まとめ（書込み順依存テーブル）

| 操作 | 必須順序 | 違反時の結果 |
|------|---------|------------|
| 初期設定（init）| COPP_TRAP → COPP_GROUP（coppmgr 内部で自動） | — (coppmgr が保証) |
| CONFIG_DB 新規追加 | COPP_GROUP を先に書いてもよい（trap_ids 空で APPL_DB 反映） | trap_ids が空のまま — feature pending |
| CONFIG_DB 完全有効化 | COPP_GROUP → COPP_TRAP の順で書く | COPP_TRAP なしでは trap_ids が紐かない |
| CONFIG_DB 削除 | COPP_TRAP を先に削除 → COPP_GROUP 削除 | COPP_GROUP DEL が pending 状態のまま残る |
| `default` グループ削除 | 削除不可（orchagent が拒否） | task_ignore — SAI に反映されない |

## evidence

- `coppmgr.cpp` L334 `mergeConfig(m_coppTrapInitCfg, ...)` — TRAP 先処理
- `coppmgr.cpp` L372 `mergeConfig(m_coppGroupInitCfg, ...)` — GROUP 後処理
- `coppmgr.cpp` L383 `checkTrapGroupPending(i.first)` — GROUP 処理時に TRAP MAP を参照
- `coppmgr.cpp` L855-860 `g_copp_init_set` スキップロジック
- `copporch.cpp` L861-864 `default` グループ削除拒否
