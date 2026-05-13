# KUBERNETES_MASTER 値依存挙動分析

## boolean フィールド

### disable (boolean string "true"/"false")
- `false` (デフォルト): K8s 統合有効。ctrmgrd が kubelet 設定を実施
- `true`: K8s 統合無効化。kubelet 接続を停止

### insecure (boolean string "true"/"false")
- `true` (デフォルト): CA 証明書取得時に HTTP を許可（TLS 検証なし）
- `false`: TLS 証明書検証あり（セキュアモード）
- その他: YANG バリデーションで reject

## ip フィールド
- IP アドレス: 推奨
- FQDN: DNS 解決失敗環境（起動早期）では kubelet 接続失敗リスク
- 数値変換不可文字列: ValueError をキャッチしてデフォルト値を設定（kube.py L39, L47）

## 結論
boolean: disable, insecure。厳密な enum なし。ip の型によって起動時挙動が異なる。
