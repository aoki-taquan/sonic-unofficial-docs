# community-set — Phase D 失敗挙動スキャンノート

ソース: `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`

## 抽出した失敗ケース

### 1. 不正 community 値 → FRR コマンド拒否 + LOG_ERR

- 場所: `g_run_command()` L47-63 / `run_command()` L763-766
- `community_member` に不正値が含まれると FRR bgpd が vtysh コマンドを拒否する
- `g_run_command` は returncode != 0 を検知し `syslog.LOG_ERR 'failed running FRR command: <cmd>'` を出力
- `break` により当該キーの残コマンドはスキップ、再試行なし
- CONFIG_DB の値は残留、FRR と乖離

### 2. vtysh 接続失敗 → LOG_ERR + drop

- 場所: `BgpdClientMgr` L161, L192-195, L208-216, L222, L259, L264, L269, L356, L358, L360, L362, L364
- ソケット書き込み失敗・タイムアウト・デーモン未接続などで LOG_ERR を出力
- 再接続ロジックなし、処理 drop
- community-list が FRR 側に未反映のまま残る

### 3. 重複名エントリの silent overwrite

- 場所: `hdl_com_set()` L988-990
- 同一 `<name>` の COMMUNITY_SET が存在し `is_configurable()` が True の場合、自動で `no bgp community-list` を発行してから新規投入
- 警告・エラーなし、先行エントリが無通知で上書きされる

### 4. is_configurable() 失敗時の DEL スキップ

- 場所: `CommunityList.is_configurable()` L1580-1582 / `hdl_com_set()` L989-990
- 3 フィールド（set_type, match_action, community_member）が不完全な状態で OP_DELETE が来た場合
- `is_configurable()` = False → `no bgp community-list` が発行されない
- FRR 側に古い community-list が残留、エラーなし

### 5. 汎用例外 → LOG_ERR + drop

- 場所: `ExtConfigDBConnector.sub_msg_handler()` L1532-1534
- `except Exception as e: syslog.LOG_ERR ... ; logging.exception(e)`
- 当該更新を drop して次へ進む、再試行なし

## 中間ファイルの位置

詳細ブロックは `docs/reference/config-db/community-set.md` の `<!-- failure -->` / `<!-- /failure -->` を参照。
