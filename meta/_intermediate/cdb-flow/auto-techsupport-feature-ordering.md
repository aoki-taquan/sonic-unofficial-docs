# AUTO_TECHSUPPORT_FEATURE — Phase B 書込み順依存スキャンノート

対象テーブル: `AUTO_TECHSUPPORT_FEATURE`
Consumer / Writer:
- `sonic-utilities/scripts/coredump_gen_handler.py` (一発実行 handler、kernel `core_pattern` 経由)
- `sonic-utilities/scripts/techsupport_cleanup.py` (`generate_dump` の cleanup フック)
- `sonic-utilities/sonic_package_manager/service_creator/feature.py` (パッケージ install 時 writer)

スキャン範囲:
- `coredump_gen_handler.py` 1-82 行 全行精読
- `techsupport_cleanup.py` 1-59 行 全行精読
- `feature.py` register / register_auto_ts / infer_auto_ts_capability (60-200 行)

---

## 検出した順序依存・タイミング依存

### 1. `AUTO_TECHSUPPORT|GLOBAL.state` が `AUTO_TECHSUPPORT_FEATURE.<feat>.state` より**強制先行**で評価される

- `CriticalProcCoreDumpHandle.handle_core_dump_creation_event()` (`coredump_gen_handler.py:46-58`) は **最初に GLOBAL.state を読む** (47 行) → `"enabled"` でなければ syslog NOTICE を出力して即 return。
- FEATURE.state (55 行) は **GLOBAL.state が `"enabled"` のときだけ評価**される。
- **順序依存**: GLOBAL.state を `disabled` のまま FEATURE.state を `enabled` に書いても、handler は GLOBAL 段階で抜けて FEATURE エントリは事実上 dead config。逆に GLOBAL.state を先に `enabled` にしてから FEATURE を `disabled` で追加することで「全体は ON だが特定 feature だけ抑止する」中間状態は意図通り機能する。
- 同じく `handle_coredump_cleanup()` (14-33 行) も GLOBAL.state を先評価 → 不在/disabled で core dump cleanup スキップ。FEATURE 側は cleanup 経路では参照されない。
- evidence: `sonic-utilities/scripts/coredump_gen_handler.py:17,47,55`

### 2. `FEATURE` テーブルのコンテナ名 ↔ `AUTO_TECHSUPPORT_FEATURE` キーの先行関係

- `FEATURE_KEY = FEATURE.format(self.container)` (54 行) で key を組み立てて HGET。`self.container` は `trim_masic_suffix(self.container)` (52 行) で masic suffix (`swss0`/`syncd1` 等) を削った後の値。
- **順序依存**: `AUTO_TECHSUPPORT_FEATURE|<feat>` エントリは、対応する `FEATURE|<feat>` エントリより**先に**書かれていても handler 動作上問題はない (handler は FEATURE テーブル本体を直接参照しない)。ただし `feature.py:register()` の install 時シーケンスは `conn.set_entry(FEATURE, name, new_cfg)` (80 行) → `register_auto_ts(name)` (82 行) の順で書く。`AUTO_TECHSUPPORT_FEATURE` は **FEATURE 書き込み後**に追加される設計上の不変条件。
- evidence: `coredump_gen_handler.py:52-54`; `feature.py:80-83`

### 3. パッケージ install 時の `AUTO_TECHSUPPORT|GLOBAL` 先行必須 (capability 判定)

- `register_auto_ts()` (`feature.py:178-196`) は `infer_auto_ts_capability(init_cfg_conn)` (182 行) を呼び、`AUTO_TECHSUPPORT|GLOBAL` を `init_cfg.json` から読む。
- GLOBAL エントリが**不在**または `state` が空の場合、`(False, "disabled")` が返り、`AUTO_TECHSUPPORT_FEATURE` エントリ自体が**作成されない** (185-186 行: `Skip adding AUTO_TECHSUPPORT_FEATURE table because no AUTO_TECHSUPPORT|GLOBAL entry is found`)。
- **順序依存 (install)**: `sonic-package-manager install <pkg>` 実行時点で `init_cfg.json` に `AUTO_TECHSUPPORT|GLOBAL` セクションが含まれていなければ、その feature の `AUTO_TECHSUPPORT_FEATURE|<feat>` エントリは生成されない。後から CLI で GLOBAL を追加しても**自動補完されない** (手動 `config auto-techsupport-feature add <feat>` が必要)。
- 通常運用では `init_cfg.json.j2` が GLOBAL ブロックを必ず注入するため発生しないが、カスタム image build で GLOBAL を削るとサイレントに feature override が無効化される。
- evidence: `sonic-utilities/sonic_package_manager/service_creator/feature.py:159-197`

### 4. container (docker) start → kernel `core_pattern` パイプ起動 → handler の遅延起動

- handler は常駐プロセスではなく、kernel `core_pattern=|/usr/local/bin/coredump-compress %e %t %p %P` 経由で**プロセスクラッシュ発生時にのみ** `setsid python3 coredump_gen_handler.py &` が起動する (`sonic-buildimage/files/image_config/sysctl/90-sonic.conf:45`)。
- `verify_recent_file_creation()` (`coredump_gen_handler.py:73-75`) は `TIME_BUF=20` 秒以内に作成された core ファイルでなければ "Spurious Invocation" として即 return。
- **順序依存**: container start 直後 (= FEATURE state が `enabled` に遷移する瞬間) より**前**に発生した古い core dump は handler のスコープ外。CONFIG_DB の `AUTO_TECHSUPPORT_FEATURE` 書き込みは container start とは**完全に独立**で、container が起動していなくても CONFIG_DB エントリは保持される。
- **container 再起動と handler の整合**: `featured` / `hostcfgd` が FEATURE state 変化を検知して docker start を呼んでも、その docker 内で発生する core dump は kernel `core_pattern` 経由なので handler 起動順序は OS 側に委ねられる。AUTO_TECHSUPPORT_FEATURE エントリは container start 前でも後でも参照可能。
- evidence: `coredump_gen_handler.py:73-75`; `auto_techsupport_helper.py:69` (`TIME_BUF=20`); `sonic-buildimage/files/image_config/sysctl/90-sonic.conf:45`

### 5. `rate_limit_interval` 評価は GLOBAL → FEATURE の二段順序評価

- `invoke_ts_command_rate_limited()` (60 行で呼ばれる) は GLOBAL の `rate_limit_interval` と FEATURE の `rate_limit_interval` を **両方** HGET する (`auto_techsupport_helper.py:300-338`)。GLOBAL の cool-off が満たされていなければ FEATURE 側の cool-off は評価されない (GLOBAL が先)。
- **順序依存**: GLOBAL.rate_limit_interval を `0` (= 無効) にしてから FEATURE.rate_limit_interval を強い制限 (例 3600 秒) に設定しても、GLOBAL 段階で素通りするケースがある。一方 GLOBAL=600, FEATURE=0 (無効) と書くと、当該 feature だけ rate-limit が外れて core dump 連発時に techsupport 暴走する危険。
- evidence: `coredump_gen_handler.py:60`; `auto_techsupport_helper.py:300-338`

### 6. `STATE_DB:AUTO_TECHSUPPORT_DUMP_INFO` への前回 dump timestamp 記録は**handler 完了後** (非同期更新)

- rate-limit 判定は `STATE_DB:AUTO_TECHSUPPORT_DUMP_INFO|<feat>` の前回 dump timestamp と現在時刻の差で行う (`auto_techsupport_helper.py:TS_MAP=AUTO_TECHSUPPORT_DUMP_INFO`)。
- timestamp 書き込みは `generate_dump` 完了後に `auto_techsupport_helper.py` が STATE_DB へ HSET。**CONFIG_DB.AUTO_TECHSUPPORT_FEATURE を変更しても STATE_DB の前回 dump 履歴は変わらない**。
- **順序依存**: `rate_limit_interval` を runtime で短縮した直後の core dump は、STATE_DB に残る古い (長い周期で記録された) timestamp で評価されるため、変更後すぐには新しい cool-off が効かないケースがある。CLI で `sonic-db-cli STATE_DB del 'AUTO_TECHSUPPORT_DUMP_INFO|<feat>'` を打つことで強制リセット可能。
- evidence: `auto_techsupport_helper.py:60`(`TS_MAP`), 300-338

### 7. `techsupport_cleanup.py` は `AUTO_TECHSUPPORT_FEATURE` を**参照しない** (順序依存なし、ただし設計上の非対称)

- `techsupport_cleanup.py:21-44` は `AUTO_TECHSUPPORT|GLOBAL.state` と `AUTO_TECHSUPPORT|GLOBAL.max_techsupport_limit` のみ評価。FEATURE 単位の cleanup 制御は存在しない。
- **順序依存なし**だが、FEATURE.state を `enabled` のまま GLOBAL.state を `disabled` にすると、生成済み techsupport tarball の cleanup も停止する (tarball が溜まり続ける) 副作用がある。
- evidence: `techsupport_cleanup.py:27-44`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `AUTO_TECHSUPPORT\|GLOBAL.state` → `AUTO_TECHSUPPORT_FEATURE.<feat>.state` | **強制先行** (handler 内の早期 return) | 設計上の仕様。GLOBAL を先に `enabled` にしてから FEATURE を整える |
| 2 | `FEATURE\|<feat>` 書き込み → `AUTO_TECHSUPPORT_FEATURE\|<feat>` 書き込み | install 時に `feature.py:register()` が保証 | runtime CLI ではこの順序は緩い (handler は FEATURE テーブル本体を見ない) |
| 3 | `AUTO_TECHSUPPORT\|GLOBAL` 存在 → install 時の `AUTO_TECHSUPPORT_FEATURE` 自動生成 | **強制先行** (install 一発、後追い不可) | 手動 CLI `config auto-techsupport-feature add` |
| 4 | container start → kernel `core_pattern` 経由 handler 起動 | プロセス外順序 (OS 側) | `TIME_BUF=20s` で古い core を弾く |
| 5 | GLOBAL.rate_limit_interval → FEATURE.rate_limit_interval (二段評価) | 同期順 (GLOBAL が先) | GLOBAL=0 で FEATURE 制限が無効化される点に注意 |
| 6 | CONFIG_DB 変更 → STATE_DB の前回 dump timestamp | 非同期 (handler 完了後) | `sonic-db-cli STATE_DB del AUTO_TECHSUPPORT_DUMP_INFO\|<feat>` で強制リセット |
| 7 | GLOBAL.state → tarball cleanup (FEATURE 非参照) | 順序依存なし (非対称) | 仕様。FEATURE 単位の cleanup 制御は不在 |

---

## キーパースペクティブ

- AUTO_TECHSUPPORT_FEATURE は**常駐 subscriber を持たない pull-on-event 型テーブル**であり、CONFIG_DB 書込時刻と handler 評価時刻が完全に分離している。**ほとんどの「順序依存」はトランザクショナルではなく eventual** (次の core dump 発生時に最新値が HGET される)。
- 強制先行の核心は **GLOBAL → FEATURE の二段ゲート** (#1, #5)。FEATURE エントリだけを操作しても GLOBAL が gate を閉じていれば動作しない。
- install 時の `AUTO_TECHSUPPORT_FEATURE` 自動生成は **GLOBAL の image build 時静的設定** に依存しており、ベースイメージのカスタマイズで暗黙に欠落するリスクがある (#3)。
- `techsupport_cleanup.py` は AUTO_TECHSUPPORT_FEATURE を完全に無視する設計で、cleanup と invocation の責任分界が GLOBAL/FEATURE で非対称 (#7)。
