# syslog-config Phase A: 暗黙デフォルト調査

## 調査対象

`SYSLOG_CONFIG`（シングルトン `GLOBAL`）の全フィールドについて、コード由来の暗黙デフォルトを抽出する。

## ソース読解経路

1. `src/sonic-yang-models/yang-models/sonic-syslog.yang` — YANG 宣言上の `default`
2. `files/image_config/rsyslog/rsyslog.conf.j2` — ホスト側 rsyslog テンプレート fallback 精読
3. `files/image_config/rsyslog/rsyslog-container.conf.j2` — docker 内 rsyslog テンプレートの fallback 精読（`SYSLOG_CONFIG_FEATURE` 経由だが local fallback として観測対象）
4. `src/sonic-containercfgd/containercfgd/containercfgd.py` — `SyslogHandler.update_syslog_config()` 全行精読
5. `sonic-host-services/scripts/hostcfgd` — `RSyslogCfg` クラス精読（YANG 解釈後の処理）

## フィールド別デフォルト調査結果

### `rate_limit_interval`

- **YANG**: `default` 宣言なし（`syslog-rate-limit-interval` typedef `uint32 (0..2147483647)`）
- **ホスト側 (`rsyslog.conf.j2` L17, L22)**: `gconf.get('rate_limit_interval')` で取得し、`is not none` でガード。**フィールド未設定の場合、`SysSock.RateLimit.Interval=...` 属性自体が rsyslog `imuxsock` モジュールロード行から完全に省略される**
- **暗黙デフォルト（ホスト）**: **rsyslog 内部デフォルト（`imuxsock` の `SysSock.RateLimit.Interval` の出荷時値 = `0` 秒 = rate limit 無効）**
- **種別**: silent drop（フィールド省略時は rsyslog ディレクティブ非出力）

### `rate_limit_burst`

- **YANG**: `default` 宣言なし（`syslog-rate-limit-burst` typedef `uint32 (0..2147483647)`）
- **ホスト側 (`rsyslog.conf.j2` L18, L22)**: `gconf.get('rate_limit_burst')` で取得し、`is not none` でガード。同上、未設定なら `SysSock.RateLimit.Burst=...` 属性が省略される
- **暗黙デフォルト（ホスト）**: rsyslog 内部デフォルト（`imuxsock` 出荷時 `SysSock.RateLimit.Burst` ≈ `200` 件、ただし上記 Interval=0 と組み合わせで実効無効）
- **種別**: silent drop

### `format`

- **YANG**: `default standard` 宣言あり（`sonic-syslog.yang` L175）
- **ホスト側 (`rsyslog.conf.j2` L51)**: `gconf.get('format', 'standard')` でテンプレート側にも fallback `'standard'`
- **暗黙デフォルト**: **`standard`**（YANG default + テンプレート fallback の二重防御）
- **種別**: YANG default + ハードコードフォールバック（テンプレート）
- **効果**: 各 remote server の出力 template が `SONiCForwardFormat`（または `SONiCForwardFormatWithOsVersion`）。`format='welf'` のときのみ `WelfRemoteFormat` に切替

### `welf_firewall_name`

- **YANG**: `default` 宣言なし、`must "(../format != 'standard')"` 制約あり
- **ホスト側 (`rsyslog.conf.j2` L52)**: `gconf.get('welf_firewall_name', hostname)` — **未設定時はホスト名にフォールバック**
- **暗黙デフォルト**: **`hostname`**（Jinja2 テンプレート変数 `hostname`、`sonic-cfggen` が DEVICE_METADATA から注入）
- **種別**: ハードコードフォールバック（テンプレート）
- **補足**: YANG の `must` 制約上 `format='standard'` のままで `welf_firewall_name` を設定すると拒否されるが、`format='welf'` で `welf_firewall_name` を未指定にした場合はテンプレートが `hostname` を WELF タグ `fw="..."` として埋め込む

### `severity`

- **YANG**: `default notice` 宣言あり（`sonic-syslog.yang` L186）
- **ホスト側 (`rsyslog.conf.j2` L92)**: per-server severity が未設定のとき `gconf.get('severity', '*')` — `SYSLOG_CONFIG.GLOBAL.severity` 参照、さらに未設定なら `'*'`（rsyslog の全 severity）
- **暗黙デフォルト**: **`notice`**（YANG default。テンプレートは `SYSLOG_CONFIG` 自体が空のときの最終 fallback として `'*'` を持つ）
- **種別**: YANG default + 経路依存 fallback
- **discrepancy**: `SYSLOG_CONFIG.GLOBAL` 行が CONFIG_DB に存在しない場合（minigraph で未生成・db_migrator 未到達）、テンプレートは `gconf={}` となり per-server severity fallback が `'*'` になる。これは YANG 検証を通っていないため YANG default `notice` が適用されない

## ローカル fallback / 派生先

### `SYSLOG_CONFIG_FEATURE` への伝播（コンテナ側 local fallback）

- `rsyslog-container.conf.j2` L27: `SysSock.RateLimit.Interval="{{ rate_limit_interval|default('300') }}" SysSock.RateLimit.Burst="{{ rate_limit_burst|default('20000') }}"`
- container 別 `SYSLOG_CONFIG_FEATURE[container_name]` が無い／部分指定の場合、**`300`/`20000`** がハードコードで適用される
- ただし `containercfgd` (`containercfgd.py` L143-144) は `SyslogHandler.update_syslog_config()` 段で `data.get(..., '0')` を渡すため、データが空 dict でないが該当 field 未設定の場合は **テンプレート側で `'0'` が `{{ ... | default('300') }}` を素通り**し `'0'` が出力される（`default()` は値が undefined のときのみ発動）
- 結果として:
  - エントリ自体が無い (`data is None` or empty) → 一旦 `'0'/'0'` でテンプレート呼び出し → 値が `'0'` で defined のため default 発動せず `'0'/'0'` 出力（rate limit 無効）
  - 該当 service の SYSLOG_CONFIG_FEATURE 行はあるが field 欠落 → 同上 `'0'` 経由
  - 該当 service が `SYSLOG_CONFIG_FEATURE` テーブルから完全に欠落（sonic-cfggen 単独呼出時のみ） → テンプレートの `default('300')` / `default('20000')` 発動
- **SYSLOG_CONFIG（GLOBAL）はコンテナ側 rsyslog では参照されない**（テンプレートは `SYSLOG_CONFIG_FEATURE` のみ参照）

## 追加検出事項

### キャッシュ比較による reload スキップ

`RSyslogCfg.update_rsyslog_config()` (`hostcfgd` L1715-1743):

- `(self.cache.get('config', {}) != rsyslog_config or self.cache.get('servers', {}) != rsyslog_servers)` が False なら `systemctl restart rsyslog-config` を呼ばない
- `systemctl restart rsyslog-config` 失敗時はキャッシュ更新せず即 return → 次回の CONFIG_DB 変更で再試行

### `SYSLOG_CONFIG` テーブル全欠落時のホスト側挙動

`rsyslog.conf.j2` L16: `gconf = (SYSLOG_CONFIG | d({})).get('GLOBAL', {})` — テーブル自体が無くても `gconf={}` で安全。すべての field が「未指定」扱いになり、上述の各 fallback パスに乗る

### YANG default と CONFIG_DB 実体の乖離

- `format` `default standard`、`severity` `default notice` は YANG 検証通過時のみ自動付与
- `db_migrator` / `minigraph` / 直接 redis-cli 書き込みでは YANG 検証をバイパスするため、`SYSLOG_CONFIG|GLOBAL` 行が存在しても `format`/`severity` field が物理的に欠落する可能性がある
- その場合の最終出力は「ホストテンプレート fallback」に従う:
  - `format` → `'standard'`（テンプレート L51）
  - `severity`（per-server fallback として参照されるとき）→ `'*'`（テンプレート L92）

## evidence

- `sonic-syslog.yang`: sonic-buildimage `src/sonic-yang-models/yang-models/sonic-syslog.yang` L156-191 @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
- `rsyslog.conf.j2`: sonic-buildimage `files/image_config/rsyslog/rsyslog.conf.j2` L16-22, L51-52, L92 @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
- `rsyslog-container.conf.j2`: sonic-buildimage `files/image_config/rsyslog/rsyslog-container.conf.j2` L16-27 @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
- `containercfgd.py`: sonic-buildimage `src/sonic-containercfgd/containercfgd/containercfgd.py` L98-160 @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
- `hostcfgd`: sonic-host-services `scripts/hostcfgd` L1695-1743 @ `c5bbbe8b07b96f078fa4b761316627404b01bd04`
