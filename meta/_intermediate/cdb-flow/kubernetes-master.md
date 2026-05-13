# CONFIG_DB 例外条件分析: KUBERNETES_MASTER

## Consumer

- `config kube` コマンド (`sonic-utilities/config/kube.py`): `KUBERNETES_MASTER|SERVER` を直接 `mod_entry()` で書く。
- `kubelet` / `kube-proxy` 管理スクリプト: CONFIG_DB の値を読んで kubelet 起動オプションを生成。

## 例外条件

### 1. ip フィールドの ValueError → デフォルト値またはエラー終了
- ソース: `config/kube.py` L39, L47
- `set()` 処理で `ValueError` をキャッチする。フィールドが数値変換できない場合は「Missing field. Set to default or given value」としてデフォルト値が設定される。
- 証拠: `except ValueError as e: ...  # Missing field. Set to default or given value`

### 2. ip がホスト名（FQDN）の場合 → DNS 解決失敗で kubelet 起動不可
- ソース: `config/kube.py` L9 (`KUBE_SERVER_TABLE_NAME = "KUBERNETES_MASTER"`)
- DNS が利用できない環境（起動早期）では hostname を IP として解決できず kubelet が接続失敗する。IP アドレス指定が推奨。

### 3. disable フィールドのデフォルト
- ソース: `config/kube.py` — `disable=false` がデフォルト。未設定時は false として扱われ、kubelet 接続が有効になる。

### 4. insecure フィールド: TLS 検証スキップ
- `insecure=true` では TLS 証明書検証が無効になる。YANG スキーマの `true`/`false` 文字列以外は拒否。CONFIG_DB に不正値が直書きされた場合の挙動は kubelet 実装依存。
