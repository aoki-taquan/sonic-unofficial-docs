# FEATURE テーブル — 副次 DB 書込 (Phase F)

## 調査対象

- ソース: `sonic-host-services/scripts/featured`
- 調査日: 2026-05-16

## 副次 DB 書込の全貌

`featured` が CONFIG_DB の `FEATURE` テーブルを変更するとき、**3 種類の副次 DB 書込**が発生する。

---

## 1. STATE_DB への FEATURE 状態書込

### 書込先

```
STATE_DB  FEATURE|<feature_name>  state  <enabled|disabled|failed>
```

### 書込トリガーと経路

`FeatureHandler.set_feature_state(feature, state)` (`featured:585-590`) が次のタイミングで呼ばれる:

| タイミング | state 値 | コード箇所 |
|-----------|---------|-----------|
| `enable_feature()` 正常完了 | `"enabled"` | `featured:513` |
| `disable_feature()` 正常完了 | `"disabled"` | `featured:547` |
| `enable_feature()` / `disable_feature()` でコマンド失敗 | `"failed"` | `featured:510, 544` |
| `sync_feature_scope()` で scope 変更時に stop/disable/mask 失敗 | `"failed"` | `featured:344` |

### multi-asic での書込拡散

`set_feature_state` は主 namespace の `Table(state_db_conn, FEATURE_TBL)` に加え、各 namespace ごとの `self.ns_feature_state_tbl[ns]` にも同値を書き込む (`featured:588-590`)。

### 確認コマンド

```bash
sonic-db-cli STATE_DB hgetall 'FEATURE|bgp'
# 出力例: {"state": "enabled"}
```

---

## 2. CONFIG_DB への FEATURE フィールド書き戻し（resync 系）

`featured` は特定条件下で CONFIG_DB の FEATURE テーブルに自ら書き戻す。これは「副次書込」として扱う必要がある。

### 2a. resync_feature_state — state フィールド書き戻し

```
CONFIG_DB  FEATURE|<name>  state  <rendered_value>
```

条件: `feature.state` (rendered) と CONFIG_DB 上の現値が異なり、かつ:
- `feature.state` が `always_enabled` / `always_disabled` である、または
- 現 DB 値が Jinja2 テンプレート文字列である

(`featured:550-572`)

multi-asic では各 namespace の CONFIG_DB にも同値を書き込む。

### 2b. sync_feature_delay_state — delayed フィールド書き戻し

```
CONFIG_DB  FEATURE|<name>  delayed  <True|False>
```

条件: manifest 由来の `feature.delayed` と CONFIG_DB 現値が不一致 (`featured:574-583`)。

### 2c. sync_feature_scope — has_per_asic_scope / has_global_scope 書き戻し

```
CONFIG_DB  FEATURE|<name>  has_per_asic_scope  <True|False>
CONFIG_DB  FEATURE|<name>  has_global_scope    <True|False>
```

`_conditional_update_scope()` が実際の値と異なる場合のみ `mod_entry` を呼ぶ (`featured:289-355`)。multi-asic では各 namespace の CONFIG_DB にも書き込む。

---

## 3. Kubernetes 管理切替に伴う副次効果（set_owner = kube）

**注意**: 現行 `featured` スクリプト (`sonic-host-services/scripts/featured`) には `set_owner` / `kube` / `KUBE` / `KUBERNETES` のコードパスは**存在しない**。

調査結果:
- `grep -n "kube\|set_owner" featured` → 0 件
- `set_owner = "kube"` は FEATURE テーブルのフィールドとして定義されているが (`sonic-feature.yang`), featured スクリプトによる処理はない
- test_vectors.py に `"set_owner": "kube"` が多数登場するが、これは FEATURE テーブルの fixture 値であり、featured の kube 制御コードのテストではない

**結論**: `kube_global` override や Kubernetes 切替の実装は `featured` ではなく別のデーモン（`hostcfgd` の KubeHandler や sonic-kubernetes 関連コンポーネント）が担う。`sonic-host-services/src/sonic-host-services/` 内の `featured` スクリプトでの副次書込対象は STATE_DB と CONFIG_DB (resync) のみ。

---

## systemd unit ファイルへの副次書込

CONFIG_DB の FEATURE 変更に連動して **ファイルシステム上の systemd 設定ファイルも副次的に変更**される。

### 書込先ファイル

```
/etc/systemd/system/<feature_name>.service.d/auto_restart.conf
```

multi-asic では各 ASIC インスタンス分も生成:
```
/etc/systemd/system/<feature_name>@<asic_id>.service.d/auto_restart.conf
```

### 内容

```ini
[Service]
Restart=always   # auto_restart=enabled の場合
```
または
```ini
[Service]
Restart=no       # auto_restart=disabled または SpineRouter の syncd/gbsyncd
```

### 書込タイミング

`update_systemd_config(feature_config)` (`featured:357-406`) が呼ばれるのは:
1. `sync_state_field()` (起動時全エントリ処理) — `featured:236`
2. `handler()` で `auto_restart` が変化したとき — `featured:205-209`

書込後に `systemctl daemon-reload` を実行して設定を反映する (`featured:403`)。

### SpineRouter 特例

`DEVICE_METADATA.localhost.type == 'SpineRouter'` のとき、`syncd` / `gbsyncd` は CONFIG_DB の `auto_restart` 値を無視して `Restart=no` を強制書込する (`featured:374-378`)。

---

## Evidence

- `sonic-host-services/scripts/featured:357-406` — `update_systemd_config`
- `sonic-host-services/scripts/featured:508-513` — `enable_feature` → `set_feature_state`
- `sonic-host-services/scripts/featured:540-547` — `disable_feature` → `set_feature_state`
- `sonic-host-services/scripts/featured:585-590` — `set_feature_state` (STATE_DB write)
- `sonic-host-services/scripts/featured:550-572` — `resync_feature_state` (CONFIG_DB write-back)
- `sonic-host-services/scripts/featured:574-583` — `sync_feature_delay_state` (CONFIG_DB write-back)
- `sonic-host-services/scripts/featured:289-355` — `sync_feature_scope` / `_conditional_update_scope`
