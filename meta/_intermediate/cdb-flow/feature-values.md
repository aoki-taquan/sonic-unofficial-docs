# FEATURE フィールド値分析

## enum / string フィールド

### `state` (string: enabled/disabled/always_enabled/always_disabled)
- `enabled` → featured daemon が systemd unit を enable + start
- `disabled` → systemd unit を disable + stop
- `always_enabled` → featured が state を `always_enabled` とみなし、ユーザーからの `disabled` への変更を無効化（featured:248-256）
- `always_disabled` → ユーザーからの `enabled` への変更を無効化
- `None` / 未設定 → `always_enabled` と同等に扱う（featured:248）
- YANG 上は非制約 string だが、featured が上記 4 値以外を受け取った場合は挙動未定義

### `auto_restart` (string: enabled/disabled)
- `enabled` → docker が crash した場合に systemd が自動再起動
- `disabled` → crash 時に手動復旧が必要

### `delayed` (string: True/False)
- `True` → ポート初期化完了 / warm-fast boot 完了 / タイムアウトのいずれかを待ってから起動（featured:163-184）
- `False` (デフォルト) → システム起動直後に起動

### `set_owner` (string: kube/local)
- `kube` → Kubernetes が container イメージ管理。KUBERNETES_MASTER テーブルの接続先 k8s cluster を使う
- `local` (デフォルト) → ローカル docker image で管理

### `has_global_scope` / `has_per_asic_scope` / `has_per_dpu_scope`
- `True` → 対応スコープでインスタンスを起動。`DEVICE_RUNTIME_METADATA['ETHERNET_PORTS_PRESENT']` 等を条件に init_cfg.json.j2 で決定
- `False` → 対応スコープのインスタンスなし

### `check_up_status` (boolean_type)
- `true` → system_health サービスが対象 feature の up 状態を監視（ヘルスチェック対象）
- `false` (デフォルト) → system_health の監視対象外

### `support_syslog_rate_limit` (boolean_type)
- `true` → SYSLOG_CONFIG_FEATURE テーブルでサービス単位の rate limit を設定可能
- `false` (デフォルト) → サービス単位の rate limit なし（グローバル設定のみ）

## cross-cutting
- `state = always_enabled` / `always_disabled` はオーバーライド保護付き: cached_state が always_* の場合は enabled/disabled 遷移しか許可しない（featured:258-260）
- `delayed = True` かつ warm/fast boot の場合は boot 完了後に即 enable（featured:171-172）
- `has_per_asic_scope = True` かつ `ETHERNET_PORTS_PRESENT = False`（supervisor module 等）→ per-asic インスタンス不要として `False` に上書き
