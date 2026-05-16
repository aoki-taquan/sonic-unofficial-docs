# COPP_GROUP — Phase C: 暗黙参照テーブル分析 (cross-refs)

対象ドキュメント: `docs/reference/config-db/copp-group.md`
解析日: 2026-05-15
根拠ソース: `sonic-swss/orchagent/copporch.cpp`, `sonic-swss/cfgmgr/coppmgr.cpp`, `sonic-buildimage/files/image_config/copp/copp_cfg.j2`, `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-copp.yang`

---

## 目的

`COPP_GROUP` エントリが CONFIG_DB に書かれたとき、`coppmgr` / `CoppOrch` が**暗黙的に**
参照・依存する他テーブルのキー / フィールドを網羅する。YANG 定義に明示されていない、
コードのみで表現された依存を列挙し、`<!-- cross-refs -->` ブロックに変換する。

---

## 1. COPP_TRAP テーブル（逆参照 — COPP_GROUP を参照する側）

COPP_GROUP は他テーブルを直接参照しないが、`COPP_TRAP` テーブルの `trap_group` leafref が
COPP_GROUP を参照する。COPP_GROUP の削除・変更は COPP_TRAP の処理に影響する。

### 参照箇所

`CoppMgr::checkTrapGroupPending()` — `coppmgr.cpp:62-79`

```cpp
// COPP_TRAP の処理時に参照先 COPP_GROUP が存在するか確認
bool CoppMgr::checkTrapGroupPending(string trap_group_name)
{
    if (m_coppTrapGroupMap.find(trap_group_name) == m_coppTrapGroupMap.end())
        return true;  // COPP_GROUP 未登録 → COPP_TRAP 書き込み保留
    ...
}
```

`CoppOrch::processCoppTrap()` — `copporch.cpp:584`

```cpp
if (m_trap_group_map.find(trap_group) == m_trap_group_map.end())
{
    return task_need_retry;  // COPP_GROUP が SAI に未登録 → COPP_TRAP をリトライ
}
```

### 依存内容

| 参照方向 | フィールド | 参照先テーブル | 参照先キー | 依存内容 | 証跡 |
|---------|-----------|--------------|----------|---------|------|
| COPP_TRAP → COPP_GROUP | `trap_group` (COPP_TRAP 側) | `COPP_GROUP` | `COPP_GROUP\|<name>` | COPP_GROUP が SAI に登録されるまで COPP_TRAP の APPL_DB 書き込みが保留。DEL すると紐付く COPP_TRAP が pending 状態になる | `coppmgr.cpp:62-79`, `copporch.cpp:584` |

---

## 2. DEVICE_METADATA テーブル（ビルド時テンプレート経由の暗黙依存）

### 参照箇所

`files/image_config/copp/copp_cfg.j2` — L37-43

```jinja2
{# queue4_group3 の cir/cbs はデバイスタイプで分岐 #}
{% if DEVICE_METADATA['localhost']['type'] is defined and 'Mgmt' in DEVICE_METADATA['localhost']['type'] %}
    "cir": "300", "cbs": "300",
{% else %}
    "cir": "100", "cbs": "100",
{% endif %}
```

### 依存内容

| 参照元 | 参照先テーブル | 参照先キー | 依存フィールド | 依存内容 | 証跡 |
|--------|--------------|----------|--------------|---------|------|
| `COPP_GROUP\|queue4_group3` の cir/cbs 初期値 | `DEVICE_METADATA` | `DEVICE_METADATA\|localhost` | `type` | `type` に `'Mgmt'` を含む場合 `cir=cbs=300` pps、含まない場合 `cir=cbs=100` pps。`sonic-cfggen` によるビルド時テンプレート展開時に解決 | `copp_cfg.j2:37-43` |

### 特記事項

- この依存はビルド時（`sonic-cfggen` による `copp_cfg.j2` 展開時）に解決される。
- 実行時に `coppmgrd` が DEVICE_METADATA を直接参照するわけではなく、
  展開済みの `/etc/sonic/copp_cfg.json` の値がデフォルトとして機能する。
- `type` = `MgmtToRRouter` / `MgmtTsToR` 等が対象（`'Mgmt'` を含む型）。

---

## 3. FEATURE テーブル（間接依存 — genetlink / sflow 経由）

### 参照箇所

`CoppMgr::doFeatureTask()` — `coppmgr.cpp:90`

```cpp
// FEATURE テーブルの変化を購読し、feature state に応じて
// COPP_TRAP の trap_ids フィルタリングを再評価する
// → COPP_GROUP の trap_ids（APPL_DB 上）が間接的に変化する
```

`CoppMgr::isTrapIdDisabled()` — `coppmgr.cpp:173-191`

```cpp
bool CoppMgr::isTrapIdDisabled(string trap_id)
{
    // feature disabled → 対応 trap_id を APPL_DB から除外
    for (auto &feature : m_featureState)
    {
        if (feature.second == "disabled" && m_featureTrapIdMap[feature.first].count(trap_id))
            return true;
    }
    return false;
}
```

### 依存内容

| 参照元 | 参照先テーブル | 参照先キー | 依存内容 | 証跡 |
|--------|--------------|----------|---------|------|
| `COPP_GROUP` に紐付く `COPP_TRAP` の `trap_ids` (APPL_DB 上の `trap_ids` リスト) | `FEATURE` | `FEATURE\|<feature-name>` | feature `state=disabled` の場合、そのグループ宛ての trap_id が APPL_DB の `COPP_TABLE\|<group>` から除外される。`queue2_group1`（sflow/`sample_packet`）が典型例 | `coppmgr.cpp:173-191` |

### 特記事項

- COPP_GROUP は FEATURE を直接参照しない。依存は `COPP_TRAP` 経由の間接依存。
- `always_enabled=true` の trap（BGP・LLDP 等）はこの制限の対象外。
- sflow feature が disabled のとき `queue2_group1` の genetlink HostIf は作成されるが、
  `sample_packet` trap が APPL_DB から除外されるため実質的に無効となる。

---

## 4. copp_cfg.json / init_cfg（暗黙的な init 依存）

### 参照箇所

`CoppMgr::CoppMgr()` コンストラクタ — `coppmgr.cpp:20-60`

```cpp
// 起動時に /etc/sonic/copp_cfg.json を読み込み
// m_coppGroupInitCfg に COPP_GROUP 初期セットを保持
// ユーザーが DEL しても init cfg に存在するキーは自動復元される
```

`CoppMgr::doCoppGroupTask()` — `coppmgr.cpp:898-921`

```cpp
// DEL 後に init cfg の同名キーがあれば APPL_DB に再書き込み (自動復元)
```

### 依存内容

| 依存元 | 参照先 | 依存内容 | 証跡 |
|--------|--------|---------|------|
| `COPP_GROUP` (全エントリ) | `/etc/sonic/copp_cfg.json` (= `copp_cfg.j2` 展開物) | 起動時にデフォルトセットを読み込む。ユーザー DEL 後も init cfg に存在するキーは自動復元される（実質「DEL = init リセット」） | `coppmgr.cpp:898-921` |
| `COPP_GROUP\|default` (削除不可フラグ) | `CoppOrch` 内の `default_trap_group = "default"` 定数 | `default` グループへの DEL コマンドは `task_ignore` で拒否（ハードコード） | `copporch.cpp:861-864, copporch.cpp:184` |

---

## 5. cross-refs ブロック（最終形）

以下を `docs/reference/config-db/copp-group.md` の `<!-- glossary-links-injected -->` 直前（`<!-- constants -->` ブロック末尾の後）に挿入する。

```markdown
<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

`COPP_GROUP` エントリが処理される際に `coppmgr` / `CoppOrch` が暗黙的に関与する
他テーブルの依存関係を示す。COPP_GROUP 自体は他テーブルへの leafref を持たないが、
ビルド時テンプレートと逆方向の参照（COPP_TRAP → COPP_GROUP）が存在する。

| 依存方向 | 参照元フィールド / 参照元 | 参照先テーブル | 参照先キー形式 | 依存内容 | 証跡 |
|---------|------------------------|--------------|--------------|---------|------|
| 逆参照（被参照） | `COPP_TRAP.trap_group` | `COPP_GROUP`（本テーブル） | `COPP_GROUP\|<name>` | COPP_GROUP が SAI 未登録の場合、COPP_TRAP の APPL_DB 書き込みが保留される。COPP_GROUP を DEL すると紐付く COPP_TRAP が pending 状態になる | `coppmgr.cpp:62-79`, `copporch.cpp:584` |
| ビルド時依存 | `queue4_group3` の `cir`/`cbs` 初期値 | `DEVICE_METADATA` | `DEVICE_METADATA\|localhost` | `type` フィールドに `'Mgmt'` が含まれる場合 `cir=cbs=300` pps、それ以外は `100` pps。`sonic-cfggen` によるテンプレート展開時に解決（実行時依存なし） | `copp_cfg.j2:37-43` |
| 間接依存（COPP_TRAP 経由） | `COPP_GROUP` に属する `COPP_TRAP` の `trap_ids` | `FEATURE` | `FEATURE\|<feature-name>` | feature `state=disabled` の場合、そのグループ宛ての trap_id が APPL_DB `COPP_TABLE\|<group>` から除外される。`queue2_group1`（sflow/`sample_packet`）が典型例 | `coppmgr.cpp:173-191` |
| init 依存（自動復元） | `COPP_GROUP` (全エントリ) | `/etc/sonic/copp_cfg.json` | — | 起動時に init セットをロード。ユーザー DEL 後も init cfg に同名キーがあれば自動復元（実質「DEL = init リセット」）。`default` グループは DEL 自体が `task_ignore` で拒否 | `coppmgr.cpp:898-921`, `copporch.cpp:861-864` |

### 解決タイミング

- **COPP_TRAP → COPP_GROUP 依存**: COPP_TRAP の SET 処理時に即座に確認。未解決は
  保留キューで管理され、COPP_GROUP 登録後の `doTask()` 再実行で解消。
- **DEVICE_METADATA → cir/cbs**: ビルド時（`sonic-cfggen`）に解決済み。
  実行時の DEVICE_METADATA 変化は COPP_GROUP に影響しない。
- **FEATURE → trap_ids**: `doFeatureTask()` が FEATURE テーブルの変化を購読し、
  state 変更のたびに影響する COPP_TRAP の trap_ids を再評価・APPL_DB を更新。
  COPP_GROUP エントリ自体は変化しない（APPL_DB 上の `trap_ids` リストが変化する）。

### init_cfg 由来の暗黙初期化

`coppmgr` は起動時に `/etc/sonic/copp_cfg.json`（`files/image_config/copp/copp_cfg.j2` の展開物）を
読み込み、`COPP_GROUP` の初期セットを `m_coppGroupInitCfg` に保持する。
ユーザーが CONFIG_DB から DEL した場合も、init cfg に同名キーがあれば init 値で
自動復元される（実質「DEL = init リセット」）。`coppmgr.cpp:898-921`

- 既定グループ例: `default`、`queue4_group1`（BGP/LLDP）、`queue2_group1`（sflow/genetlink）
- `default` グループは `CoppOrch` 側でも削除を `task_ignore` で拒否する二重防護
<!-- /cross-refs -->
```
