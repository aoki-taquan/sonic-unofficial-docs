# KDUMP 値依存挙動分析

## boolean フィールド

### enabled (boolean)
- `true`: kdump 有効化。grub パラメータ変更 → 次回 reboot 後に有効化
- `false`: kdump 無効化

### remote (boolean)
- `true`: SSH 経由リモートダンプ転送。ssh_string / ssh_path が必要
- `false`: ローカル保存のみ

## 数値/文字列フィールド

### memory (string)
- `512M-2G:64M,2G-:128M` 形式: 範囲指定（例: 512M〜2G のメモリなら 64M 確保）
- 絶対値形式（例: `512M`）: 固定値
- 小さすぎる値: kdump kernel 起動失敗（コード上バリデーションなし）

### num_dumps (uint8 1..9)
- 1〜9: 保持する core file 数
- 0 以下: CLI 下限チェックなし → hostcfgd が kdump-config にそのまま渡す（動作実装依存）

## 結論
boolean: enabled, remote。文字列: memory（書式注意）。enum なし。
