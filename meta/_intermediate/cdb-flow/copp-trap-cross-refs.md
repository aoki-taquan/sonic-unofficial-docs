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

## 4. DEVICE_METADATA テーブル (ビルド時間接参照)

### 参照箇所

`files/image_config/copp/copp_cfg.j2:37-43`

```jinja2
{% if DEVICE_METADATA is defined and DEVICE_METADATA['localhost'] is defined
   and DEVICE_METADATA['localhost']['type'] is defined
   and 'Mgmt' in DEVICE_METADATA['localhost']['type'] %}
    "cir":"300",
    "cbs":"300",
{% else %}
    "cir":"100",
    "cbs":"100",
{% endif %}
```

### 依存内容

| COPP_TRAP フィールド | 参照先テーブル | 参照先キー | 依存内容 | 参照箇所 |
|---|---|---|---|---|
| `trap_group` (間接、queue4_group3 指定時) | `DEVICE_METADATA` | `DEVICE_METADATA\|localhost` | `type` が `'Mgmt'` を含む場合、COPP_GROUP `queue4_group3` の policer cir/cbs が 300 pps になる（非 Mgmt は 100 pps）。COPP_TRAP がこのグループを参照すると間接的にレートが変わる | `copp_cfg.j2:37-43` |

### 特記事項

- この参照は sonic-cfggen による `copp_cfg.j2` 展開時（ビルド時または初回起動時）にのみ評価される。
- `CoppOrch` や `coppmgr` がランタイムで `DEVICE_METADATA` を直接読む処理はない。

---

## 5. SAI HOSTIF オブジェクト (ランタイム SAI 層)

### 参照箇所

- `copporch.cpp:661-678` — `createGenetlinkHostIf()`: COPP_GROUP が Genetlink 型の場合に
  `sai_hostif_api->create_hostif()` を呼び出して netdev ソケットを作成。
- `copporch.cpp:780-792` — `processCoppGroup()`: `sai_hostif_api->create_hostif_trap_group()` で
  SAI HOSTIF_TRAP_GROUP オブジェクトを生成。
- `copporch.cpp:516-523` — `processCoppTrap()`: trap_id ごとに `sai_create_hostif_trap()` を呼び出し。

### 依存内容

| COPP_TRAP フィールド | 参照先 | 依存内容 | 参照箇所 |
|---|---|---|---|
| `trap_ids` (SAI 適用時) | SAI HOSTIF_TRAP（非 CONFIG_DB） | `CoppOrch` が各 trap_id に対して `sai_create_hostif_trap()` を呼び出し SAI オブジェクトを生成。OID は `m_syncdTrapIds` にキャッシュ | `copporch.cpp:516-523` |
| `trap_group` (Genetlink 型) | SAI HOSTIF（非 CONFIG_DB） | COPP_GROUP が `genetlink` フィールドを持つ場合、`CoppOrch` が `create_hostif()` で netdev ソケットを生成し trap 受信チャネルとして登録 | `copporch.cpp:661-678` |

---

## 6. cross-refs ブロック (最終形)

```markdown
<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

`COPP_TRAP` エントリが処理される際に `coppmgr` / `CoppOrch` が暗黙的に参照する
他テーブルを示す。YANG の `leafref` として定義された `trap_group` に加え、
コードのみで表現された依存がある。

| 参照元フィールド | 参照先テーブル | 参照先キー形式 | 依存内容 | 証跡 |
|---|---|---|---|---|
| `trap_group` | COPP_GROUP | `COPP_GROUP\|<name>` | グループ未登録の場合 `coppmgr` は APPL_DB 書き込みを保留。`CoppOrch` は `task_need_retry` を返して再試行 | `coppmgr.cpp:62-79`, `copporch.cpp:584` |
| `trap_ids` (各 trap_id) | FEATURE | `FEATURE\|<feature-name>` | feature の `state=disabled` の場合、対応 trap_id を APPL_DB から除外（`always_enabled=false` のみ対象） | `coppmgr.cpp:173-191` |
| `always_enabled` | FEATURE | `FEATURE\|<feature-name>` | `true` の場合は feature state に関わらず常時インストール。未設定は `false` 扱い | `coppmgr.cpp:90` |
| `trap_group` (間接、queue4_group3 指定時) | DEVICE_METADATA | `DEVICE_METADATA\|localhost` | `copp_cfg.j2` が `DEVICE_METADATA.localhost.type` に `'Mgmt'` を含む場合、COPP_GROUP `queue4_group3` の policer cir/cbs を 300 pps に設定（通常は 100 pps）。ビルド時 sonic-cfggen 展開時のみ評価 | `copp_cfg.j2:37-43` |
| `trap_ids` (SAI 適用時) | SAI HOSTIF オブジェクト | SAI OID（非 CONFIG_DB） | `CoppOrch` が `sai_hostif_api->create_hostif_trap()` / `create_hostif_trap_group()` で SAI HOSTIF_TRAP・HOSTIF_TRAP_GROUP を生成。Genetlink 型では `create_hostif()` で netdev ソケットも作成 | `copporch.cpp:661-678`, `copporch.cpp:780-792` |
<!-- /cross-refs -->
```
