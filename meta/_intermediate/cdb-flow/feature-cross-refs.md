# FEATURE — Phase C 暗黙参照 (cross-refs)

対象ページ: `docs/reference/config-db/feature.md`
生成日: 2026-05-15

---

## 暗黙的参照関係の洗い出し

### FEATURE → 他テーブルへの暗黙依存

| 参照元フィールド | 参照先テーブル | 条件 / 根拠 |
|---|---|---|
| `set_owner = "kube"` | `KUBERNETES_MASTER` | Kubernetes sidecar 管理に切り替わるとき、`KUBERNETES_MASTER` の接続先 k8s cluster 情報を参照。`featured` が k8s API を呼ぶ前提条件として KUBERNETES_MASTER が有効である必要がある (`featured:375-380`) |
| `support_syslog_rate_limit = "true"` | `SYSLOG_CONFIG_FEATURE` | `true` のとき `containercfgd` が `SYSLOG_CONFIG_FEATURE|<feature>` エントリを参照してコンテナ内 rsyslog を再設定。FEATURE のフラグが入口、SYSLOG_CONFIG_FEATURE が実設定値 (`containercfgd.py:108-148`) |
| `check_up_status = "true"` | `DEVICE_METADATA` (暗黙) | `system_health` が feature up 監視を行うとき、装置全体の health policy は `DEVICE_METADATA.localhost.type` に依存する可能性がある |
| `state` / `has_global_scope` / `has_per_asic_scope` | `DEVICE_METADATA` | init_cfg.json.j2 が `DEVICE_METADATA.localhost.type` / `subtype` を読んで `FEATURE.<name>.state` を決定 (ビルド時派生。`init_cfg.json.j2:76-90`) |

### 他テーブル → FEATURE への暗黙依存

| 参照元テーブル | 参照フィールド | 根拠 |
|---|---|---|
| `SYSLOG_CONFIG_FEATURE` | key `<service>` が `FEATURE_LIST.name` の leafref | `SYSLOG_CONFIG_FEATURE` のキーは必ず `FEATURE` テーブルに登録済みの feature 名でなければならない (`sonic-feature.yang` leafref) |
| `AUTO_TECHSUPPORT_FEATURE` | key `<feature_name>` が `FEATURE.name` に対応 | `AUTO_TECHSUPPORT_FEATURE` のキーは FEATURE テーブルの feature 名を参照 (YANG leafref 未実装だが運用上の依存あり) |
| `KUBERNETES_MASTER` | `set_owner = "kube"` な FEATURE から参照される | FEATURE の `set_owner` が `kube` の場合に KUBERNETES_MASTER が有効である必要あり |
| `DEVICE_METADATA` | `localhost.type` / `subtype` から FEATURE.state を派生 | init_cfg.json.j2 でビルド時に `FEATURE.<name>.state` が決定される |

### CLI 参照

| CLI グループ | 参照テーブル | ページ |
|---|---|---|
| `config feature state` / `config feature autorestart` | `FEATURE` | `docs/reference/cli/show-feature.md` |
| `show feature status` / `show feature config` | `FEATURE` (読み取り) | `docs/reference/cli/show-feature.md` |

### YANG 参照

| YANG モジュール | 関係 |
|---|---|
| `sonic-feature` | `FEATURE_LIST` container を定義。全フィールドのスキーマ根拠 |
| `sonic-syslog` | `SYSLOG_CONFIG_FEATURE` が `FEATURE_LIST.name` を leafref |

---

## cross-refs ブロック (docs/reference/config-db/feature.md に挿入)

```markdown
<!-- cross-refs -->
## 暗黙参照マップ

| 参照方向 | このテーブル | 相手テーブル / ページ | 条件 |
|---------|------------|---------------------|------|
| FEATURE → | `set_owner = "kube"` | [`KUBERNETES_MASTER`](./kubernetes-master.md) | k8s 管理切替え時。featured が k8s API 呼び出し前に KUBERNETES_MASTER の接続情報を参照 |
| FEATURE → | `support_syslog_rate_limit = "true"` | [`SYSLOG_CONFIG_FEATURE`](./syslog-config-feature.md) | containercfgd が SYSLOG_CONFIG_FEATURE の rate-limit 値を読んでコンテナ内 rsyslog を再設定 |
| FEATURE → | `state` / `has_*_scope` (ビルド時) | [`DEVICE_METADATA`](./device-metadata.md) | init_cfg.json.j2 が `localhost.type` / `subtype` を条件に state を決定 |
| → FEATURE | `SYSLOG_CONFIG_FEATURE.<service>` | [`SYSLOG_CONFIG_FEATURE`](./syslog-config-feature.md) | key が FEATURE_LIST.name を leafref — 未登録 feature は設定不可 |
| → FEATURE | `AUTO_TECHSUPPORT_FEATURE.<feature_name>` | [`AUTO_TECHSUPPORT_FEATURE`](./auto-techsupport-feature.md) | key が FEATURE.name に対応 (YANG leafref 未実装、運用上の依存) |
| CLI | `config/show feature` | [`show feature`](../cli/show-feature.md) | FEATURE テーブルの読み書き CLI |
| YANG | `FEATURE_LIST` | [`sonic-feature`](../yang/sonic-feature.md) | 全フィールドのスキーマ定義 |

<!-- /cross-refs -->
```
