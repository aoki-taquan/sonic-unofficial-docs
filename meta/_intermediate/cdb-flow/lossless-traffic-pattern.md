# CONFIG_DB 例外条件分析: LOSSLESS_TRAFFIC_PATTERN

## Consumer

- `buffermgrdyn` (`sonic-swss/cfgmgr/buffermgrdyn.cpp`): dynamic buffer 計算モードでのみ `LOSSLESS_TRAFFIC_PATTERN` を参照する。静的バッファモード（`buffermgr.cpp`）は参照しない。
- `db_migrator.py` (`sonic-utilities/scripts/db_migrator.py`): DB バージョン移行時にデフォルトエントリ (`LOSSLESS_TRAFFIC_PATTERN|AZURE`) を挿入する。

## 例外条件

### 1. dynamic モード以外では参照されない
- ソース: `buffermgrdyn.cpp` — `buffermgr.cpp`（静的モード）はこのテーブルを subscribe しない。
- `config main.py` L918 で `LOSSLESS_TRAFFIC_PATTERN` はリセット対象として認識されているが、静的バッファモード時に変更しても headroom 計算に影響しない。

### 2. mtu 値と実 MTU 乖離 → headroom 過小/過大
- ソース: `buffermgrdyn.cpp` L2263「if mtu isn't configured, take the default value」
- `mtu` フィールドが CONFIG_DB に存在しない場合はコードが mtu デフォルト値を使用する。実際の MTU と異なる値が設定されると PFC headroom が過小（パケットロス）または過大（バッファ浪費）になる。

### 3. db_migrator によるデフォルト挿入（AZURE エントリ）
- ソース: `db_migrator.py` L345, L414
- DB migration 時に `LOSSLESS_TRAFFIC_PATTERN|AZURE: {mtu: '1024', small_packet_percentage: '100'}` が自動挿入される。これは Mellanox 向け初期値であり、他プラットフォームには不適切な場合がある。
- 既存エントリがある場合は上書きしない（`append_item_method` は存在チェックする）。

### 4. small_packet_percentage の範囲検証なし
- コード上で 0〜100 の範囲バリデーションが明示的にない。100 を超える値が CONFIG_DB に書かれると headroom 計算式が異常値を返す可能性がある。YANG スキーマのバリデーションに依存。

### 5. buffer_pool 未設定時は skip
- ソース: `buffermgrdyn.cpp` L684
- 「No shared buffer pool configured, skip calculating shared buffer pool size」— 先行依存テーブルが欠けている場合はサイレントスキップ。
