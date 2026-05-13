# CONFIG_DB 例外条件分析: FLEX_COUNTER_TABLE

## Consumer

- `flexcounterorch` (`sonic-swss/orchagent/flexcounterorch.cpp`): orchagent が `FLEX_COUNTER_TABLE` を subscribe し、各カウンタグループの enable/disable・polling interval・bulk chunk サイズを syncd へ設定する。
- `counterpoll` (sonic-utilities): CLI から CONFIG_DB を書くフロントエンド。

## 例外条件

### 1. 未知グループ名 → エラーログ + スキップ
- ソース: `flexcounterorch.cpp` L561
- `BUFFER_QUEUE` / `BUFFER_PG` の key 形式が不正な場合 `SWSS_LOG_ERROR("Invalid BUFFER_QUEUE key: [%s]", ...)` → エントリをスキップ。
- 証拠: `SWSS_LOG_ERROR("Invalid BUFFER_QUEUE key: [%s]", portQueueKey.c_str())`

### 2. queue/PG インデックスが非整数 → invalid_argument キャッチ + エラーログ
- ソース: `flexcounterorch.cpp` L599, L661
- queue インデックス・PG インデックスが `stoi()` で変換失敗すると `std::invalid_argument` をキャッチして `SWSS_LOG_ERROR` → そのポートのカウンタ設定は適用されない。

### 3. FLEX_COUNTER_STATUS デフォルト=disable
- ソース: `flexcounterorch.cpp` L227（コメント）
- 「counters are disabled for polling by default」。`FLEX_COUNTER_TABLE` エントリが存在しない場合や `FLEX_COUNTER_STATUS=disable` 時はカウンタ収集が行われない。

### 4. create_only_config_db_buffers 読み取りエラー
- ソース: `flexcounterorch.cpp` L124
- `create_only_config_db_buffers` フラグ取得失敗時に `SWSS_LOG_ERROR("System error reading create_only_config_db_buffers: %s", e.what())` → バッファカウンタ関連設定がデフォルト動作になる可能性がある。

### 5. POLL_INTERVAL の下限なし・CPU 負荷リスク
- ソース: コード上に下限バリデーションなし。`counterpoll` CLI のみで間接的に制限。极端に短い interval（例: 100ms）は orchagent と syncd の CPU を圧迫するが、コード上では拒否されない。
