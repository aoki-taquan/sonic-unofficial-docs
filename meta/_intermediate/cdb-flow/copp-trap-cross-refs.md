# COPP_TRAP — Phase C: 暗黙参照テーブル分析 (cross-refs)

対象ドキュメント: `docs/reference/config-db/copp-trap.md`
解析日: 2026-05-15
根拠ソース: `sonic-swss/orchagent/copporch.cpp`, `sonic-swss/cfgmgr/coppmgr.cpp`, `sonic-buildimage/files/image_config/copp/copp_cfg.j2`

---

## 目的

`COPP_TRAP` エントリが CONFIG_DB に書かれたとき、`coppmgr` / `CoppOrch` が**暗黙的に**
参照・依存する他テーブルのキー / フィールドを網羅する。YANG `leafref` として定義された
`trap_group` 以外の、コードのみで表現された依存を列挙し、`<!-- cross-refs -->` ブロックに変換する。

---

## 1. COPP_GROUP テーブル (明示 leafref + 実装依存)

### 参照箇所

`CoppMgr::checkTrapGroupPending()` — `coppmgr.cpp:62-79`

```cpp
bool CoppMgr::checkTrapGroupPending(string trap_group_name)
{
    // 参照先 COPP_GROUP が CONFIG_DB 上に存在しないか、
    // または copymgr がまだ処理していない場合に true を返す
    if (m_coppTrapGroupMap.find(trap_group_name) == m_coppTrapGroupMap.end())
        return true;
    ...
}
```

`CoppOrch::processCoppTrap()` — `copporch.cpp:584`

```cpp
if (m_trap_group_map.find(trap_group) == m_trap_group_map.end())
{
    return task_need_retry;  // COPP_GROUP が未登録 → リトライ
}
```

### 依存内容

| COPP_TRAP フィールド | 参照先テーブル | 参照先キー | 依存内容 | 参照箇所 |
|---|---|---|---|---|
| `trap_group` | `COPP_GROUP` | `COPP_GROUP\|<name>` | グループ未作成の場合 APPL_DB 書き込みを保留。CoppOrch は `task_need_retry` を返す | `coppmgr.cpp:62-79`, `copporch.cpp:584` |

### 特記事項

- YANG で `leafref` として定義されているが、copymgr / CoppOrch レベルでも二重に存在確認が行われる。
- `copp_cfg.j2` は `COPP_GROUP` と `COPP_TRAP` を同一 JSON ファイルに定義し、
  `sonic-cfggen` が一括で CONFIG_DB に流し込むため通常は順序問題が起きない。
- 手動 `sonic-db-cli SET` で `COPP_TRAP` を書く場合は `COPP_GROUP` を先行書き込みする必要がある。

---

## 2. FEATURE テーブル (暗黙参照)

### 参照箇所

`CoppMgr::isTrapIdDisabled()` — `coppmgr.cpp:173-191`

```cpp
bool CoppMgr::isTrapIdDisabled(string trap_id)
{
    // trap_id が所属する feature が FEATURE テーブルで disabled なら true
    for (auto &feature : m_featureState)
    {
        if (feature.second == "disabled" && m_featureTrapIdMap[feature.first].count(trap_id))
            return true;
    }
    return false;
}
```

`CoppMgr::doFeatureTask()` — `coppmgr.cpp:90`

```cpp
// FEATURE テーブルの変化を購読し、state 変更に応じて COPP_TRAP を再評価する
```

### 依存内容

| COPP_TRAP フィールド | 参照先テーブル | 参照先キー | 依存内容 | 参照箇所 |
|---|---|---|---|---|
| `trap_ids` (各 trap_id) | `FEATURE` | `FEATURE\|<feature-name>` | feature の `state` が `disabled` の場合、対応する trap_id を APPL_DB から除外。`always_enabled=false` の trap のみ対象 | `coppmgr.cpp:173-191` |
| `always_enabled` | `FEATURE` | `FEATURE\|<feature-name>` | `true` の場合は feature の state に関わらず常時インストール。`false`/未設定は feature state に従う | `coppmgr.cpp:90, L183` |

### 特記事項

- `trap_id` → `feature` のマッピングは `m_featureTrapIdMap` に保持される。
  このマップは `copp_cfg.j2` / `copp_cfg.json` の `COPP_TRAP` エントリを起動時に読み込んで構築。
- YANG 定義には `FEATURE` への leafref はない。コードのみで表現された依存。
- FEATURE テーブルの `state` は `enabled` / `disabled` / `always_disabled` の3値をとる
  (`sonic-feature.yang` 定義)。`coppmgr` は `disabled` を検出して `isTrapIdDisabled()=true` を返す。

---

## 3. init_cfg / copp_cfg.j2 由来のデフォルト (書き込み入り口の暗黙依存)

### 参照箇所

`CoppMgr::CoppMgr()` コンストラクタ — `coppmgr.cpp:20-60`

```cpp
// 起動時に /etc/sonic/copp_cfg.json を読み込み m_coppTrapInitCfg に保持
// この init cfg は COPP_TRAP エントリのデフォルト値として機能し、
// ユーザーが DEL しても自動復元される
```

### 依存内容

| 依存元 | 参照先 | 依存内容 |
|---|---|---|
| `COPP_TRAP` (全エントリ) | `/etc/sonic/copp_cfg.json` (= `copp_cfg.j2` 展開物) | 起動時にデフォルトセットを読み込む。ユーザー DEL 後も init 値が残存するキーは自動復元される (`coppmgr.cpp:773-805`) |
| `COPP_TRAP` の `trap_group` 値 | `COPP_GROUP` (init cfg 内で同時定義) | `copp_cfg.j2` 内で `COPP_GROUP.queue4_group1` 等を参照。ビルド時テンプレート生成時に整合性を保証 |

---

## 4. cross-refs ブロック (最終形)

以下を `docs/reference/config-db/copp-trap.md` の `<!-- glossary-links-injected -->` 直前に挿入する。

```markdown
<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

`COPP_TRAP` エントリが処理される際に `coppmgr` / `CoppOrch` が暗黙的に参照する
他テーブルを示す。YANG の `leafref` として定義された `trap_group` に加え、
コードのみで表現された依存がある。

| 参照元フィールド | 参照先テーブル | 参照先キー形式 | 依存内容 | 証跡 |
|---|---|---|---|---|
| `trap_group` | `COPP_GROUP` | `COPP_GROUP\|<name>` | グループ未登録の場合 `coppmgr` は APPL_DB 書き込みを保留。`CoppOrch` は `task_need_retry` を返して再試行 | `coppmgr.cpp:62-79`, `copporch.cpp:584` |
| `trap_ids` (各 trap_id) | `FEATURE` | `FEATURE\|<feature-name>` | feature の `state=disabled` の場合、対応 trap_id を APPL_DB から除外（`always_enabled=false` のみ対象） | `coppmgr.cpp:173-191` |
| `always_enabled` | `FEATURE` | `FEATURE\|<feature-name>` | `true` の場合は feature state に関わらず常時インストール。未設定は `false` 扱い | `coppmgr.cpp:90` |

### 解決タイミング

- **COPP_GROUP**: SET 処理時に即座に参照確認。未解決は保留キューで管理され、
  GROUP 登録後に `doFeatureTask` / `doTask` 再実行で解消する。
- **FEATURE**: `doFeatureTask()` が FEATURE テーブルの変化を購読し、
  state 変更のたびに影響する COPP_TRAP を再評価・再書き込みする。

### init_cfg 由来の暗黙初期化

`coppmgr` は起動時に `/etc/sonic/copp_cfg.json`（`files/image_config/copp/copp_cfg.j2` の展開物）を
読み込み、`COPP_TRAP` と `COPP_GROUP` の初期セットを `m_coppTrapInitCfg` / `m_coppGroupInitCfg` に
保持する。ユーザーが CONFIG_DB から DEL した場合も、init cfg に同名キーがあれば init 値で
自動復元される（実質「DEL = init リセット」）。`coppmgr.cpp:773-805`

- 既定エントリ例: `bgp` → `trap_ids: bgp,bgpv6` / `trap_group: queue4_group1`
- `always_enabled=true` の例: `lacp`, `arp`, `udld`, `ip2me`, `neighbor_miss`
<!-- /cross-refs -->
```
