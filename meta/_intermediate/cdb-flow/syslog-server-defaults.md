# syslog-server Phase A: 暗黙デフォルト調査

## 調査対象

`SYSLOG_SERVER` テーブル全フィールドのコード由来暗黙デフォルト。

## ソース読解経路

1. `sonic-syslog.yang` — YANG 宣言上のデフォルト確認
2. `scripts/hostcfgd` (sonic-host-services) — `RSyslogCfg` クラス全行精読
3. `files/image_config/rsyslog/rsyslog.conf.j2` (sonic-buildimage) — テンプレート内 fallback 全行精読
4. `files/image_config/rsyslog/rsyslog-config.sh` — テンプレート変数注入経路確認

## フィールド別デフォルト調査結果

### `port`

- **YANG**: `default` 宣言なし（`inet:port-number` 型のみ）
- **テンプレート (`rsyslog.conf.j2` L89)**: `conf.get('port', 514)`
- **暗黙デフォルト**: **514**
- **種別**: ハードコードフォールバック（Jinja2 テンプレート）
- **discrepancy**: なし（docs の「典型値: port: 514」と一致）

### `protocol`

- **YANG**: `default` 宣言なし（`rsyslog-protocol` 型 enum tcp/udp のみ）
- **テンプレート (`rsyslog.conf.j2` L90)**: `conf.get('protocol', 'udp')`
- **暗黙デフォルト**: **`udp`**
- **種別**: ハードコードフォールバック（Jinja2 テンプレート）
- **rsyslog への出力**: `Protocol="udp"` → rsyslog が UDP 514 番で転送

### `vrf`

- **YANG**: `default` 宣言なし（union leafref / enum default/mgmt のみ）
- **テンプレート (`rsyslog.conf.j2` L91)**: `conf.get('vrf', 'default')`
- **暗黙デフォルト**: **`default`**
- **種別**: ハードコードフォールバック（Jinja2 テンプレート）
- **効果**: `device = vrf if vrf != '' and vrf != 'default'` → `vrf='default'` のとき `device=False` → rsyslog の `Device=` オプション付与なし

### `severity`

- **YANG**: per-server `severity` leaf に `default` 宣言なし
- **テンプレート (`rsyslog.conf.j2` L92)**: `conf.get('severity', gconf.get('severity', '*'))`
  - まず per-server フィールド確認 → なければ `SYSLOG_CONFIG.GLOBAL.severity` を参照
  - `SYSLOG_CONFIG.GLOBAL.severity` の YANG default = `notice`
  - `SYSLOG_CONFIG` テーブル自体が存在しない場合は最終フォールバック `'*'`（全 severity）
- **暗黙デフォルト**: 3段階カスケード:
  1. per-server `severity` フィールドが設定されていれば使用
  2. `SYSLOG_CONFIG|GLOBAL.severity`（YANG default `notice`）にフォールバック
  3. `SYSLOG_CONFIG` 未設定なら `'*'`（rsyslog の all-severity 構文）
- **種別**: 経路依存フォールバック + YANG-実装 discrepancy
- **discrepancy**: YANG は per-server `severity` に `default none` を設定していないが、テンプレートは GLOBAL severity（`notice`）を暗黙継承するため、per-server が未設定でも `*` ではなく `notice` が使われる（`SYSLOG_CONFIG.GLOBAL` が存在する場合）

### `source`

- **YANG**: `default` 宣言なし、optional leaf
- **テンプレート (`rsyslog.conf.j2` L88, L111-113)**: `source = conf.get('source')` → `None` のとき `if source:` ブロックをスキップ → `Address=` オプション付与なし
- **暗黙デフォルト**: **省略（rsyslog がカーネルのルーティングテーブルに従ってソース IP を自動選択）**
- **種別**: silent drop（フィールド省略時は該当 rsyslog オプション非出力）
- **補足**: `source` が `eth0` の IP と一致する場合、`device='eth0'` を空文字にクリアするロジックあり（L113）

### `filter` / `filter_regex`

- **YANG**: 双方とも `default` 宣言なし、optional leaf
- **テンプレート (`rsyslog.conf.j2` L120-121)**:
  ```jinja
  {% if filter %}
  :msg, {{ fmodifier }}ereregex, "{{ regex | ... }}"
  {% endif %}
  ```
- **暗黙デフォルト**: `filter` 未設定時はフィルタ行を出力しない（全メッセージ転送）
- **種別**: silent drop（フィルタなし状態が暗黙デフォルト）
- **`fmodifier`**: `filter == 'exclude'` のとき `!`、それ以外（`include`）は `''`（L96）

## 追加検出事項

### VRF + source の組み合わせ依存挙動

テンプレート L113: `source` フィールドが設定されている場合、`device = device if device != 'eth0' else ''`

- `vrf='mgmt'` かつ `source=<eth0 IP>` の組み合わせ: `device=''` にクリアされるため mgmt VRF バインドが無効化される
- 書込み順依存ではなく値依存（組み合わせ依存）
- docs の「vrf: mgmt で source を data-plane IP にすると syslog が出ない」と整合するが、eth0 IP 指定時は mgmt VRF Device が消える点はより精細な条件

### action オプション固定値

テンプレート L124（ハードコード）:
- `action.resumeRetryCount="60"`: 接続失敗時の再試行回数 60 回固定
- `queue.type="LinkedList"`: キュータイプ固定
- `queue.size="20000"`: キューサイズ 20000 固定

これら 3 値は CONFIG_DB から設定不可能（YANG にフィールドなし、テンプレートハードコード）。

### rsyslog 再起動スキップロジック（rsyslog-config.sh）

`rsyslog-config.sh` L62: config が前回と同一なら `systemctl restart rsyslog` をスキップし `SIGHUP` のみ送信。
`RSyslogCfg.update_rsyslog_config()` にも同様のキャッシュ比較がある（L1725-1726）。
→ 二重のデュプリケーション抑制あり。変更なしの場合はサービス再起動コストが発生しない。

## evidence

- `rsyslog.conf.j2`: sonic-buildimage `files/image_config/rsyslog/rsyslog.conf.j2` L84-125
- `hostcfgd` RSyslogCfg: sonic-host-services `scripts/hostcfgd` L1695-1743
- `rsyslog-config.sh`: sonic-buildimage `files/image_config/rsyslog/rsyslog-config.sh` L58-73
- YANG: `src/sonic-yang-models/yang-models/sonic-syslog.yang` L100-149
