# FIPS 値依存挙動分析

## boolean フィールド

### enable (boolean)
- `false` (デフォルト): 通常 OpenSSL モジュールを使用
- `true`: FIPS-validated module をロード。grub パラメータ変更のため次回 reboot 後に有効化

### enforce (boolean)
- `false` (デフォルト): 非準拠操作を許容
- `true`: 非 FIPS アルゴリズム使用をエラー化。enable=true との組み合わせが前提

## 結論
boolean フィールドのみ。厳密な enum なし。値依存挙動は enable/enforce の組み合わせ。
