# AUTO_TECHSUPPORT — Phase B 順序依存中間ファイル

生成日: 2026-05-16

対象ページ: `docs/reference/config-db/auto-techsupport.md`
主ソース: `coredump_gen_handler.py`, `coredump-compress`, `hostcfgd`

<!-- ordering -->
## Phase B: コア生成順序・systemd-coredump 設定・AUTO_TECHSUPPORT 連携の抽出

### 調査対象ソース

| ファイル | リポジトリ |
|---------|-----------|
| `scripts/coredump_gen_handler.py` | sonic-net/sonic-utilities |
| `scripts/coredump-compress` | sonic-net/sonic-utilities |
| `utilities_common/auto_techsupport_helper.py` | sonic-net/sonic-utilities |
| `files/image_config/sysctl/90-sonic.conf` | sonic-net/sonic-buildimage |

### 1. カーネル coredump パイプ設定

`sonic-buildimage/files/image_config/sysctl/90-sonic.conf` に以下が設定される:

```
kernel.core_pattern=|/usr/local/bin/coredump-compress %e %t %p %P
kernel.core_pipe_limit=16
```

- `%e`: 実行ファイル名
- `%t`: Unix タイムスタンプ
- `%p`: PID
- `%P`: グローバル PID (名前空間外)
- `core_pipe_limit=16`: 最大 16 プロセスのコアダンプを並列処理可能（カーネルはハンドラ完了まで `/proc/<pid>` を保持）

**systemd-coredump は使用しない**: `core_pattern` を独自パイプスクリプトに向けることで systemd-coredump を完全に回避。`/etc/systemd/coredump.conf` は参照されない。

### 2. coredump-compress の処理フロー

`sonic-utilities/scripts/coredump-compress`:

1. コマンドライン引数 (`%e %t %p`) からプレフィックスを構築
2. `/proc/<PID>/cgroup` から Docker コンテナ ID を抽出（`CONTAINER_ID`）
3. `/proc/<PID>/environ` から `NAMESPACE_ID` を取得してプレフィックスに付加（masic 対応）
4. 標準入力を `/var/core/<prefix>.core.gz` に gzip 圧縮して保存
5. `CONTAINER_ID` が判明した場合のみ `coredump_gen_handler.py` を非同期起動:
   ```bash
   setsid python3 /usr/local/bin/coredump_gen_handler.py ${PREFIX}core.gz ${CONTAINER_NAME} &
   ```

**非同期化の理由**: カーネルのパイプハンドラはタイムアウトが存在するため、techsupport 起動（数分かかる可能性）を同期で待てない。`setsid` + `&` でセッション分離して非同期実行する。

### 3. coredump_gen_handler.py の CONFIG_DB 参照順序

`sonic-utilities/scripts/coredump_gen_handler.py` の `handle_core_dump_creation_event()` および `handle_coredump_cleanup()`:

```
main()
  ├─ verify_recent_file_creation()  # ファイル作成が TIME_BUF(20秒)以内か確認
  ├─ CriticalProcCoreDumpHandle.handle_core_dump_creation_event()
  │    ├─ [L47] AUTO_TECHSUPPORT|GLOBAL state == "enabled" ?
  │    │         No → syslog NOTICE + return（auto_invoke_ts スキップ）
  │    ├─ [L52] trim_masic_suffix() で masic サフィックス除去
  │    ├─ [L55] AUTO_TECHSUPPORT_FEATURE|<container> state == "enabled" ?
  │    │         No → syslog NOTICE + return（techsupport 起動スキップ）
  │    └─ [L60] invoke_ts_command_rate_limited()
  │              ├─ rate_limit_interval チェック（STATE_DB 参照）
  │              ├─ available_mem_threshold / min_available_mem チェック
  │              └─ show techsupport 実行
  └─ handle_coredump_cleanup()       # techsupport 起動後に同期実行
       ├─ [L17] AUTO_TECHSUPPORT|GLOBAL state == "enabled" ?
       │         No → syslog NOTICE + return（cleanup スキップ）
       ├─ max_core_limit 取得（float 変換失敗時は 0.0 扱い）
       ├─ max_core_limit == 0 → cleanup スキップ
       └─ cleanup_process() → /var/core 内の古い *.core.gz を削除
```

### 4. AUTO_TECHSUPPORT 連携ポイント

| CONFIG_DB キー | フィールド | 参照タイミング | 参照元 |
|---------------|-----------|--------------|-------|
| `AUTO_TECHSUPPORT\|GLOBAL` | `state` | techsupport 起動判定（最初のガード） | `coredump_gen_handler.py:47` |
| `AUTO_TECHSUPPORT\|GLOBAL` | `state` | cleanup 実行判定 | `coredump_gen_handler.py:17` |
| `AUTO_TECHSUPPORT\|GLOBAL` | `max_core_limit` | /var/core 使用量上限 | `coredump_gen_handler.py:22` |
| `AUTO_TECHSUPPORT_FEATURE\|<c>` | `state` | feature 単位の起動判定 | `coredump_gen_handler.py:55` |
| `AUTO_TECHSUPPORT\|GLOBAL` | `rate_limit_interval` | 連続起動抑制 | `auto_techsupport_helper.py` |
| `AUTO_TECHSUPPORT\|GLOBAL` | `available_mem_threshold` | メモリ閾値チェック | `auto_techsupport_helper.py` |
| `AUTO_TECHSUPPORT\|GLOBAL` | `min_available_mem` | 最低空きメモリ確認 | `auto_techsupport_helper.py` |

### 5. hostcfgd との関係

`sonic-host-services/scripts/hostcfgd` はコアダンプ処理パイプラインには直接関与しない。`hostcfgd` は SSH/AAA/syslog などのホスト設定を扱い、`AUTO_TECHSUPPORT` テーブルの購読は `auto_techsupport_handler`（別サービス）が担当する。

### 6. 全体シーケンス図

```
クラッシュ発生（カーネル検知）
  │
  ▼
kernel.core_pattern=|coredump-compress %e %t %p %P
  │ (同期パイプ, core_pipe_limit=16 まで並列)
  ▼
coredump-compress
  ├─ /var/core/<prefix>.core.gz 保存
  └─ [コンテナプロセスの場合] setsid coredump_gen_handler.py & (非同期)
       │
       ▼
  coredump_gen_handler.py
       ├─ verify_recent_file_creation (20秒以内か)
       ├─ AUTO_TECHSUPPORT|GLOBAL.state == "enabled" ?
       ├─ AUTO_TECHSUPPORT_FEATURE|<container>.state == "enabled" ?
       ├─ rate_limit_interval チェック
       ├─ メモリ閾値チェック
       ├─ [条件通過] show techsupport → /var/dump/sonic_dump_*.tar.gz
       └─ handle_coredump_cleanup → /var/core 整理
```

### evidence リスト

- `sonic-buildimage/files/image_config/sysctl/90-sonic.conf:45,55`
- `sonic-utilities/scripts/coredump-compress:12-31`
- `sonic-utilities/scripts/coredump_gen_handler.py:14-78`
- `sonic-utilities/utilities_common/auto_techsupport_helper.py:33-71`

<!-- /ordering -->
