# CONFIG_DB 例外条件分析: COMMUNITY_SET

## Consumer

- `frrcfgd` (`frrcfgd.py`): `COMMUNITY_SET` を subscribe し、Jinja2 テンプレート `bgpd.conf.db.comm_list.j2` で FRR vtysh コマンドに変換して bgpd に送信。

## 例外条件

### 1. 必須フィールド欠如 → エントリ全体スキップ (テンプレート条件)
- ソース: `bgpd.conf.db.comm_list.j2` L9
- `set_type`, `match_action`, `community_member` の 3 フィールドが揃っていない場合、テンプレートがそのエントリを **無視**して FRR コマンドを生成しない (`{% if 'set_type' in cm_val and 'match_action' in cm_val and 'community_member' in cm_val %}`)。エラーログなし。

### 2. match_action が `all` でも `any` でもない → FRR 設定なし (暗黙 skip)
- ソース: `bgpd.conf.db.comm_list.j2` L11, L16
- `match_action` が `all` / `any` 以外の場合、テンプレートはどちらの分岐にも入らず FRR bgp community-list コマンドが生成されない。

### 3. vtysh コマンド失敗 → ignore_fail=False 時ログ
- ソース: `frrcfgd.py` L47-60
- `g_run_command()` で vtysh が非ゼロ終了した場合、`ignore_fail=False` (デフォルト) であれば syslog に LOG_ERR を出力。エントリの再試行は行われない (FRR 側との整合性欠如が残る可能性)。

### 4. frrcfgd 起動時のエラー → catch + LOG_ERR + continue
- ソース: `frrcfgd.py` L1533-1534
- 全テーブルハンドラ共通: `Exception` が発生した場合 `LOG_ERR('[bgp cfgd] Failed handling config DB update with exception:' + str(e))` して次のエントリへ。処理はドロップ。
