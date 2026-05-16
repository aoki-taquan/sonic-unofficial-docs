# DEVICE_METADATA — ハードコード定数調査 (Phase E)

## 調査方針

`docs/reference/config-db/device-metadata.md` に関係するすべての consumer スクリプト・Jinja テンプレート・C++ ソースを対象に、
「`DEVICE_METADATA` フィールドの値に基づいて分岐する処理で用いられる起動タイマー・retry カウント・threshold 定数」を grep + 全行精読で列挙する。

---

## 発見した定数一覧

### 1. orchagent バッチサイズ (switch_type 依存)

| 定数 | 値 | 条件 | 用途 | source |
|------|-----|------|------|--------|
| `-b` batch_size | `128` | `switch_type == 'chassis-packet'` | orchagent メッセージキューの pop バッチサイズ。リンク通知を高速処理 | `docker-orchagent/orchagent.sh:26` |
| `-b` batch_size | `65536` | `switch_type == 'dpu'` | DPU の高ボリュームオブジェクト処理向け大容量バッチ | `docker-orchagent/orchagent.sh:29` |
| `-b` batch_size | `1024` | その他 (デフォルト) | 通常スイッチ向け標準バッチサイズ | `docker-orchagent/orchagent.sh:32` |

### 2. orchagent ZMQ bulk limit (switch_type == 'dpu')

| 定数 | 値 | 条件 | 用途 | source |
|------|-----|------|------|--------|
| `-k` bulk_size | `65536` | `switch_type == 'dpu'` | ZMQ synchronous mode の最大 bulk limit | `docker-orchagent/orchagent.sh:39` |

### 3. SAI create_switch タイムアウト (switch_type 依存)

`SAI_REDIS_DEFAULT_SYNC_OPERATION_RESPONSE_TIMEOUT = 60,000 ms (60 秒)` を基準に、switch_type によって倍率を変える。

| 定数 | 値 | 条件 | 用途 | source |
|------|-----|------|------|--------|
| `SAI_REDIS_DEFAULT_SYNC_OPERATION_RESPONSE_TIMEOUT` | `60,000 ms` | 基準値 | SAI redis sync 操作のデフォルトタイムアウト | `sonic-sairedis/lib/sairedis.h:46` |
| create_switch timeout | `5 × 60,000 = 300,000 ms` | `switch_type IN ['voq','chassis-packet','dpu']` | 多数のフロントパネルポート/システムポート初期化のための延長待機 | `sonic-swss/orchagent/main.cpp:822` |
| create_switch timeout | `10 × 60,000 = 600,000 ms` | `switch_type == 'fabric'` | Fabric スイッチ初期化の更に長い待機 | `sonic-swss/orchagent/main.cpp:825` |
| create_switch timeout | `60,000 ms` | その他 (デフォルト) | 通常スイッチのデフォルト待機 | `sonic-swss/orchagent/main.cpp:829` |

### 4. orchagent heartbeat interval

| 定数 | 値 | 条件 | 用途 | source |
|------|-----|------|------|--------|
| `HEART_BEAT_INTERVAL_MSECS_DEFAULT` | `10,000 ms` | デフォルト | orchagent heartbeat 送信間隔 | `sonic-swss/orchagent/main.cpp:75` |

`-I` CLI オプションで上書き可能。

### 5. BGP graceful-restart タイマー (constants.yml, type='ToRRouter')

| 定数 | 値 | 条件 | 用途 | source |
|------|-----|------|------|--------|
| `constants.bgp.graceful_restart.restart_time` | `240` 秒 | `type == 'ToRRouter'` かつ `graceful_restart.enabled == true` | FRR BGP graceful-restart タイマー | `constants.yml:24; bgpd.main.conf.j2:119` |
| `constants.bgp.graceful_restart.select_defer_time` | `45` 秒 (Jinja fallback) | 同上、constants.yml に未定義のため Jinja `default(45)` が適用 | BGP best-path 選択遅延タイマー | `bgpd.main.conf.j2:122` |

### 6. BGP coalesce-time (subtype='DualToR')

| 定数 | 値 | 条件 | 用途 | source |
|------|-----|------|------|--------|
| `coalesce-time` | `10,000` ms | `subtype == 'DualToR'` | BGP ルート集約タイマー (mux 切替時のルート収束遅延短縮) | `bgpd.main.conf.j2:111` |

### 7. BMP 接続タイマー (frr_bmp feature 有効時)

BMP は DEVICE_METADATA の feature 設定に依存して有効化されるが、タイマー値は固定ハードコード。

| 定数 | 値 | 条件 | 用途 | source |
|------|-----|------|------|--------|
| `bmp stats interval` | `1,000` ms | `FEATURE.frr_bmp.state == 'enabled'` または `FEATURE.bmp.state == 'enabled'` | BMP 統計送信間隔 | `bgpd.main.conf.j2:133` |
| `bmp connect port` | `5000` | 同上 | ローカル BMP コレクター接続先ポート | `bgpd.main.conf.j2:136` |
| `bmp connect min-retry` | `10,000` ms | 同上 | BMP 接続リトライ最小間隔 | `bgpd.main.conf.j2:136` |
| `bmp connect max-retry` | `15,000` ms | 同上 | BMP 接続リトライ最大間隔 | `bgpd.main.conf.j2:136` |
| `bmp mirror buffer-limit` | `4,294,967,214` bytes | 同上 | BMP ミラーバッファ上限 (≒ 4 GiB) | `bgpd.main.conf.j2:130` |

### 8. teamd retry count (default_bgp_status 依存)

`teamd_increase_retry_count.py` は `DEVICE_METADATA.default_bgp_status` を読んで PortChannel BootUp 動作を制御する。

| 定数 | 値 | 条件 | 用途 | source |
|------|-----|------|------|--------|
| `DEFAULT_RETRY_COUNT` | `3` | 通常 / リセットパケット時 | LACPDU の actor/partner retry_count フィールド値 | `sonic-utilities/scripts/teamd_increase_retry_count.py:31` |
| `EXTENDED_RETRY_COUNT` | `5` | `defaultBgpStatus == True` かつ 新バージョン対向時 | BGP up 状態で retry を延ばし PortChannel 安定化を待つ | `sonic-utilities/scripts/teamd_increase_retry_count.py:32,215` |
| LACPDU 送信 sleep | `15` 秒 | retry count 変更パケット送信ループ | LACPDU ブロードキャスト間隔 | `sonic-utilities/scripts/teamd_increase_retry_count.py:225,327` |
| peer 処理待ち sleep | `2` 秒 | リセットパケット送信前 | 対向デバイスの処理完了待機 | `sonic-utilities/scripts/teamd_increase_retry_count.py:297` |
| LACP sniff timeout | `30` 秒 | sniffer 起動時 | LACPDU キャプチャ待機タイムアウト | `sonic-utilities/scripts/teamd_increase_retry_count.py:99` |

### 9. fpmsyncd warm-restart タイマー (suppress-fib-pending 依存)

`suppress-fib-pending` フィールドを有効にした場合に影響する FPM フラッシュ・warm-restart タイマー。

| 定数 | 値 | 条件 | 用途 | source |
|------|-----|------|------|--------|
| `DEFAULT_ROUTING_RESTART_INTERVAL` | `120` 秒 | warm-restart 有効時 | FRR routing stack の warm-restart 完了待機タイマー | `sonic-swss/fpmsyncd/fpmsyncd.cpp:46` |
| `DEFAULT_EOIU_HOLD_INTERVAL` | `3` 秒 | warm-restart + EOIU 検出時 | EOIU フラグ検出後 reconciliation 開始前の hold タイマー | `sonic-swss/fpmsyncd/fpmsyncd.cpp:51` |
| `FLUSH_TIMEOUT` | `500` ms | 常時 | fpmsyncd route flush 間隔の上限 | `sonic-swss/fpmsyncd/fpmsyncd.cpp:25` |
| `SMALL_TRAFFIC` | `500` (ルート数閾値) | 常時 | `remaining < 500` のとき即時 flush するトラフィック量閾値 | `sonic-swss/fpmsyncd/fpmsyncd.cpp:28` |
| `FPM_MAX_MSG_LEN` | `16,384` bytes | 常時 | FPM メッセージバッファ最大長 | `sonic-swss/fpmsyncd/fpm/fpm.h:95` |

### 10. bgpcfgd FRR daemon 起動待機

| 定数 | 値 | 条件 | 用途 | source |
|------|-----|------|------|--------|
| `wait_for_daemons seconds` | `20` 秒 | bgpcfgd 起動時 | FRR daemons が vtysh に接続するまでの最大待機時間 | `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py:47` |

### 11. bfdmon リトライ / ポーリング (switch_type='dpu' で BFD スキップ)

`bfdmon.py` は `switch_type != 'dpu'` のとき起動する。

| 定数 | 値 | 条件 | 用途 | source |
|------|-----|------|------|--------|
| `MAX_RETRY_ATTEMPTS` | `3` | vtysh コマンド失敗時 | BFD セッション情報取得のリトライ上限 | `sonic-buildimage/src/sonic-bgpcfgd/bfdmon/bfdmon.py:21` |
| `SLEEP_TIME` | `2` 秒 | BFD ポーリングループ | 各 BFD チェック間の待機時間 | `sonic-buildimage/src/sonic-bgpcfgd/bfdmon/bfdmon.py:151` |

### 12. ECMP hash_seed (type 別固定値)

switch.json.j2 で `DEVICE_METADATA.type` に応じて SAI `ecmp_hash_seed` / `lag_hash_seed` に設定される固定値。
multi-ASIC では `namespace_id` をオフセットとして加算する (`hash_seed + namespace_id`)。

| type | hash_seed | ecmp_hash_offset | lag_hash_offset | ordered_ecmp | source |
|------|-----------|-----------------|----------------|-------------|--------|
| `ToRRouter` | `0` | `0` | `0` | `false` | `switch.json.j2:9` |
| `LeafRouter` | `10` | `10` | `10` | `true` | `switch.json.j2:11-13` |
| `SpineRouter` | `25` | `0` | `0` | `false` | `switch.json.j2:15` |
| `FabricSpineRouter` | `40` | `0` | `0` | `false` | `switch.json.j2:16-17` |
| `UpperSpineRouter` | `50` | `0` | `0` | `false` | `switch.json.j2:18-19` |
| `LowerRegionalHub` | `60` | `0` | `0` | `false` | `switch.json.j2:20-21` |
| `FabricRegionalHub` | `70` | `0` | `0` | `false` | `switch.json.j2:22-23` |
| `UpperRegionalHub` | `80` | `0` | `0` | `false` | `switch.json.j2:24-25` |

---

### 13. SwitchOrch ポーリング定数 (switchorch.cpp / switchorch.h)

`SwitchOrch` (`sonic-swss/orchagent/switchorch.cpp`) に定義された固定ポーリング間隔・重複排除ウィンドウ。`DEVICE_METADATA` の `switch_type`/`type` 値に依存しない共通定数だが、`SwitchOrch` は `DEVICE_METADATA` の主要 consumer (SAI スイッチ初期化・カウンタ管理) であるため記録する。

| 定数名 | 値 | 用途 | source |
|--------|-----|------|--------|
| `SWITCH_STAT_COUNTER_POLLING_INTERVAL_MS` | `60,000` ms | SWITCH_STAT カウンタ (dropped_trim / tx_trim) の FlexCounter ポーリング間隔 | `sonic-swss/orchagent/switchorch.cpp:32,157` |
| `DEFAULT_ASIC_SENSORS_POLLER_INTERVAL` | `60` 秒 | ASIC 温度センサーポーリング初期値 (`ASIC_SENSORS_POLLER_INTERVAL` で上書き可) | `sonic-swss/orchagent/switchorch.h:12; switchorch.cpp:154` |
| `ASIC_SDK_HEALTH_EVENT_ELIMINATE_INTERVAL` | `3,600` 秒 | ASIC SDK health event の重複排除ウィンドウ (同一 severity × category を 1 時間内に重複送信しない) | `sonic-swss/orchagent/switchorch.h:29` |

### 14. `switch_type` 有効 enum 値と既定値

`orchagent/main.cpp` の `getCfgSwitchType()` 関数がバリデーションする値のリスト。

| 値 | 既定 | SAI マッピング | source |
|----|------|--------------|--------|
| `switch` | ◎ (未設定時 fallback) | `SAI_SWITCH_TYPE_NPU` | `sonic-swss/orchagent/main.cpp:251,264` |
| `voq` | — | `SAI_SWITCH_TYPE_VOQ` | `sonic-swss/orchagent/main.cpp:698` |
| `fabric` | — | `SAI_SWITCH_TYPE_FABRIC` | `sonic-swss/orchagent/main.cpp:742` |
| `chassis-packet` | — | `SAI_SWITCH_TYPE_NPU` (multi-ASIC chassis) | `sonic-swss/orchagent/main.cpp:260` |
| `dpu` | — | `SAI_SWITCH_TYPE_NPU` (ZMQ 強制) | `sonic-swss/orchagent/main.cpp:260` |

### 15. `hostname` 既定値

| コンテキスト | 既定値 | source |
|------------|--------|--------|
| `generate_sample_config()` / `config_db.json` 初期生成 | `"sonic"` | `sonic-buildimage/src/sonic-config-engine/config_samples.py:50,154` |
| `migrate_config_db_to_new_schema()`（`hostname` 不在時のみ挿入） | `"sonic"` | `sonic-buildimage/src/sonic-config-engine/config_samples.py:219-220` |
| orchagent VoQ モード（`switch_type=voq`） | 必須フィールド扱い → 欠如時にエラー終了 | `sonic-swss/orchagent/main.cpp:337-347` |

### 16. `buffer_model` enum 値と `dynamic_buffer_model` フラグ

`sonic-swss/cfgmgr/buffermgr.cpp:390-406` が `buffer_model` を読み取り内部フラグを設定する。

| 値 | `dynamic_buffer_model` | 挙動 | source |
|----|----------------------|------|--------|
| `dynamic` | `true` | BUFFER_POOL / BUFFER_PROFILE の APPL_DB 転写をスキップ (dynamic buffer manager が SAI を直接制御) | `sonic-swss/cfgmgr/buffermgr.cpp:392-394,476` |
| `traditional` またはその他 / 未設定 | `false` | BUFFER_POOL / BUFFER_PROFILE を APPL_DB へ転写 | `sonic-swss/cfgmgr/buffermgr.cpp:397-406` |

---

## 定数分類サマリ

| 分類 | 定数数 | 依存フィールド |
|------|--------|--------------|
| orchagent バッチ/bulk サイズ | 4 | `switch_type` |
| SAI create_switch タイムアウト | 4 | `switch_type` |
| BGP タイマー (graceful-restart/coalesce) | 3 | `type`, `subtype`, `constants.yml` |
| BMP 接続タイマー | 5 | `FEATURE.frr_bmp/bmp` (DEVICE_METADATA 間接) |
| teamd retry/sleep | 5 | `default_bgp_status` |
| fpmsyncd warm-restart/flush | 5 | `suppress-fib-pending` (間接) |
| bgpcfgd startup | 1 | 常時 |
| bfdmon retry/poll | 2 | `switch_type != 'dpu'` |
| ECMP hash_seed | 8 × 3 = 24 値 | `type` |
| orchagent heartbeat | 1 | `HEARTBEAT` テーブル (DEVICE_METADATA 間接) |
| SwitchOrch ポーリング/重複排除 | 3 | 常時 (switchorch.cpp) |
| `switch_type` enum 定義 | 5 値 | `switch_type` |
| `hostname` 既定値 | 1 | `hostname` |
| `buffer_model` enum 定義 | 2 値 | `buffer_model` |

**合計: 約 63 個の数値定数・enum 値** を DEVICE_METADATA フィールドに関連する consumer コードから確認。

---

## 補足: constants.yml の DEVICE_METADATA 関連値

`/files/image_config/constants/constants.yml` より DEVICE_METADATA consumer が参照する値のうち、上記以外のもの:

| key | 値 | 用途 |
|-----|-----|------|
| `bgp.maximum_paths.ipv4` | `514` | IPv4 ECMP 最大パス数 |
| `bgp.maximum_paths.ipv6` | `514` | IPv6 ECMP 最大パス数 |
| `bgp.route_do_not_send_appdb_tag` | `202` | SpineRouter+UpstreamLC BGP route-map tag |
| `bgp.route_eligible_for_fallback_to_default_tag` | `203` | VoQ/UpstreamLC BGP route-map tag |
| `bgp.internal_fallback_community` | `22222:22222` | SpineRouter+UpstreamLC BGP community |
| `bgp.hide_internal_community` | `55555:55555` | FabricSpineRouter 等 HIDE_INTERNAL route-map |
| `bgp.traffic_shift_community` | `12345:12345` | TSA/TSB route-map community |
| `bgp.internal_community` | `11111:11111` | internal BGP community |
