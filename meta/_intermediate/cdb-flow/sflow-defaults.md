# SFLOW Phase A — コード由来の暗黙デフォルト調査

調査日: 2026-05-14
対象ファイル: `docs/reference/config-db/sflow.md`
ソース:
- `sonic-swss/cfgmgr/sflowmgr.cpp` / `sflowmgr.h`
- `sonic-swss/orchagent/sfloworch.cpp`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-sflow.yang`
- `sonic-utilities/config/main.py`

---

## 検出一覧

### 1. SflowMgr コンストラクタのハードコードデフォルト (sflowmgr.cpp:13-22)

```cpp
SflowMgr::SflowMgr(...) {
    m_intfAllConf = true;   // 全ポートへのグローバル設定適用 = ON
    m_gEnable = false;       // グローバル admin_state 内部表現 = false
    m_gDirection = "rx";     // グローバル sample_direction 内部表現 = "rx"
    m_intfAllDir = "rx";     // SFLOW_SESSION|all の direction 内部表現 = "rx"
}
```

- `m_intfAllConf = true` は CONFIG_DB に対応するフィールドがない。SFLOW_SESSION|all エントリが存在しないときのデフォルト動作を制御する。SFLOW_SESSION|all が SET されると `enable` の値に追随し、DEL されると `true` に戻る (sflowmgr.cpp:563)。
- `m_gEnable = false` は YANG `SFLOW.global.admin_state default "down"` と整合。
- `m_gDirection = "rx"` は YANG `SFLOW.global.sample_direction default "rx"` と整合。
- `m_intfAllDir = "rx"` は YANG `SFLOW_SESSION.sample_direction default "rx"` と整合。

### 2. `SFLOW_SESSION` per-port の `admin_state` 暗黙デフォルト (sflowmgr.cpp:362-368)

```cpp
if (!admin_present)
{
    if (m_sflowPortConfMap[alias].admin == "")
    {
        /* By default admin state is enabled if not set explicitly */
        m_sflowPortConfMap[alias].admin = "up";
    }
    ...
}
```

- YANG には `default up` が明示されている (`sonic-sflow.yang:121`)。
- コード側でも `admin == ""` のとき `"up"` を注入する。YANG と一致。

### 3. `SFLOW_SESSION` per-port の `sample_direction` 暗黙デフォルト (sflowmgr.cpp:372-382)

```cpp
if (!dir_present)
{
    if (m_sflowPortConfMap[alias].dir == "")
    {
        /* By default direction is set to global, if not set explicitly */
        m_sflowPortConfMap[alias].dir = m_gDirection;
    }
    ...
}
```

- **YANG との乖離**: YANG `SFLOW_SESSION.sample_direction default "rx"` は固定値だが、実装は `m_gDirection`（グローバル設定の現在値）を参照する。グローバル direction が `"tx"` または `"both"` に変更されている状態で per-port エントリを新規作成すると、YANG default `"rx"` ではなくグローバル値が採用される。
- これは **書込み順依存乖離** および **YANG-実装 discrepancy**。

### 4. `sample_rate` の暗黙デフォルト = ポート速度由来 (sflowmgr.cpp:385-401)

```cpp
string SflowMgr::findSamplingRate(const string& alias)
{
    string oper_speed = m_sflowPortConfMap[alias].oper_speed;
    string cfg_speed = m_sflowPortConfMap[alias].speed;
    if (!oper_speed.empty() && oper_speed != NA_SPEED)
    {
        return oper_speed;
    }
    return cfg_speed;
}
```

- `sample_rate` は YANG では `mandatory false`（デフォルトなし）かつ `must "../port != 'all'"` 制約付き。
- 実装では、per-port セッションに `sample_rate` が指定されない場合、`findSamplingRate()` を呼び出し **ポートの oper_speed（なければ cfg_speed）をそのまま sample_rate として使用**する。
- これは **ハードコードではなく速度由来動的デフォルト**。1G ポート → rate=1000, 10G ポート → rate=10000 相当の数値（ただし速度文字列がそのまま渡るため uint32 変換はオーケストレータ側で行われる）。
- `ERROR_SPEED = "error"` を返す場合（ポートが port map に未登録）は rate=0 として sfloworch 側でセッション作成をスキップ (sfloworch.cpp:411-415)。

### 5. `SFLOW_SESSION` の per-port `sample_rate` 削除時のリセット (sflowmgr.cpp:344-358)

```cpp
if (!rate_present)
{
    if (m_sflowPortConfMap[alias].rate == "" ||
        m_sflowPortConfMap[alias].local_rate_cfg)
    {
        m_sflowPortConfMap[alias].rate = findSamplingRate(alias);
    }
    m_sflowPortConfMap[alias].local_rate_cfg = false;
    ...
}
```

- CLI で `config sflow interface sample-rate <ifname> default` を実行すると CONFIG_DB から `sample_rate` フィールドが削除される。
- 削除後は `findSamplingRate()` によりポート速度に戻る（速度由来デフォルトへの自動フォールバック）。

### 6. `sflowGetGlobalInfo()` の admin_state 注入 (sflowmgr.cpp:275-285)

```cpp
void SflowMgr::sflowGetGlobalInfo(vector<FieldValueTuple> &fvs, const string& alias, const string& dir)
{
    FieldValueTuple fv1("admin_state", "up");   // ハードコード "up"
    fvs.push_back(fv1);
    ...
}
```

- `m_intfAllConf = true`（SFLOW_SESSION|all が設定されていない）状態でポートが追加されると、APP_SFLOW_SESSION_TABLE に `admin_state = "up"` がハードコード注入される。
- CONFIG_DB の SFLOW_SESSION に `admin_state` フィールドが存在しない場合でも `"up"` として扱われる。

### 7. `sflowHandleSessionAll` の admin_state フォールバック (sflowmgr.cpp:231-234)

```cpp
/* Use global admin state if there is not a local one */
if (!it.second.local_admin_cfg) {
    FieldValueTuple fv1("admin_state", "up");
    fvs.push_back(fv1);
}
```

- per-port に `local_admin_cfg = false` の場合、グローバル `admin_state` 値ではなく **ハードコード `"up"`** が注入される。グローバルが `"down"` でも（そもそも `m_gEnable == false` なら sflowHandleSessionAll 自体が呼ばれない設計だが）この注入は注意が必要。

### 8. `SflowOrch` の `dir` 初期値 (sfloworch.cpp:387)

```cpp
string dir = "rx";
```

- APP_DB から `sample_direction` フィールドが欠落している場合、orch 側でも `"rx"` をデフォルトとして使用。YANG と一致。

### 9. `SflowOrch::m_sflowStatus` 初期値 (sfloworch.cpp:17-18)

```cpp
SflowOrch::SflowOrch(...) {
    m_sflowStatus = false;
}
```

- APP_SFLOW_TABLE に SET が来るまで、sfloworch は全セッション SET を無視する (`if (!m_sflowStatus) return;` — sfloworch.cpp:389-391)。
- **書込み順依存**: SFLOW_SESSION_TABLE に per-port エントリが先に届き、SFLOW_TABLE が後から届く場合、orch は per-port 設定を処理しない。再処理（retrigger）機構が必要だが、実装上は `Consumer::drain()` の再入りに依存。

### 10. `SFLOW_COLLECTOR.collector_port` YANG デフォルト (sonic-sflow.yang:81-83)

```yang
leaf collector_port {
    type inet:port-number;
    default 6343;
    ...
}
```

- YANG 明示デフォルト。実装側での上書きなし（sflowmgrd は hsflowd 設定ファイルを生成する際に DB の値をそのまま使う）。

### 11. `SFLOW.global.polling_interval` YANG デフォルト (sonic-sflow.yang:162-164)

```yang
leaf polling_interval {
    default 20;
    ...
}
```

- YANG 明示デフォルト 20 秒。実装でのオーバーライドなし。

### 12. `agent_id` 欠落時のサイレントスキップ

- sflowmgrd が hsflowd 設定ファイルを生成する際、`agent_id` フィールドが CONFIG_DB に存在しない場合は agent IP 行を生成しない（hsflowd のデフォルト動作に委ねる）。
- エラーログなし → **silent drop** パターン。hsflowd は独自の agent IP 選択ロジックを使う可能性がある。

---

## サマリテーブル

| フィールド | テーブル | YANGデフォルト | 実装デフォルト | 乖離/備考 |
|-----------|---------|--------------|--------------|-----------|
| `admin_state` | SFLOW | `down` | `m_gEnable=false`（一致） | 一致 |
| `polling_interval` | SFLOW | `20` | YANG値を使用（実装オーバーライドなし） | 一致 |
| `sample_direction` | SFLOW | `rx` | `m_gDirection="rx"`（一致） | 一致 |
| `agent_id` | SFLOW | なし | 欠落時サイレントスキップ | silent drop |
| `admin_state` | SFLOW_SESSION | `up` | 欠落時 `"up"` 注入（一致） | 一致 |
| `sample_rate` | SFLOW_SESSION | なし | ポート oper_speed → cfg_speed 動的デフォルト | 速度由来動的 |
| `sample_direction` | SFLOW_SESSION | `rx` | **欠落時 `m_gDirection`（グローバル値）を参照** | **YANG-実装 discrepancy** |
| `collector_port` | SFLOW_COLLECTOR | `6343` | YANG値を使用 | 一致 |
| `collector_vrf` | SFLOW_COLLECTOR | なし | 欠落時はデフォルトVRF扱い | 一致 |
| `m_intfAllConf` | (内部状態) | - | `true`（CONFIG_DBにフィールドなし） | SFLOW_SESSION|all DEL で true に戻る |

---

## 主要 discrepancy

### D1: SFLOW_SESSION.sample_direction の書込み順依存乖離

- **YANG**: `default "rx"` (固定)
- **実装**: フィールド欠落時は `m_gDirection`（グローバルの現在値）を使う
- **影響**: グローバル direction が `"tx"` や `"both"` の状態で per-port セッションを作成すると YANG default とは異なる値が APP_DB に書き込まれる
- **コード証跡**: `sflowmgr.cpp:374-378`

### D2: `m_intfAllConf` の CONFIG_DB 不可視状態

- SFLOW_SESSION|all エントリが存在しない間は `m_intfAllConf = true`（全ポートに暗黙的グローバル設定を適用）
- この内部状態は CONFIG_DB / YANG に対応するフィールドがない → ランタイム限定の暗黙デフォルト
- SFLOW_SESSION|all を SET すると明示的に制御可能になる

### D3: SflowOrch の書込み順依存

- APP_SFLOW_TABLE（グローバル状態）が APP_SFLOW_SESSION_TABLE より後に届く場合、per-port SET が全て無視される
- `m_sflowStatus = false` がデフォルトのため、グローバル有効化前の SESSION SET は捨てられる
