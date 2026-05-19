# gnmi-counter Phase E — ハードコード定数調査メモ

調査日: 2026-05-19
対象ページ: `docs/reference/config-db/gnmi-counter.md`
フェーズ: Phase E (ハードコード定数)

## 調査対象ソース

| ファイル | リポジトリ | 役割 |
|---------|-----------|------|
| `common_utils/shareMem.go` | sonic-net/sonic-gnmi | 共有メモリ IPC キー・サイズ・モード定数 |
| `common_utils/context.go` | sonic-net/sonic-gnmi | CounterType 列挙型・COUNTER_SIZE 番兵定数 |
| `gnmi_dump/gnmi_dump.go` | sonic-net/sonic-gnmi | gnmi_dump バイナリエントリポイント |

## 検出した定数一覧

### SysV 共有メモリ定数（shareMem.go）

| 定数名 | 値 | 宣言箇所 | 説明 |
|--------|-----|---------|------|
| `memKey` | `7749` | `shareMem.go:15` | SysV IPC キー。CONFIG_DB 非管理・固定値 |
| `memSize` | `1024` (バイト) | `shareMem.go:16` | 共有メモリ領域サイズ。`uint64 × 128` スロット分を確保 |
| `memMode` | `0x380` | `shareMem.go:17` | `shmget` flags: `O_RDWR \| IPC_CREAT` |

### カウンタ配列定数（context.go）

| 定数名 | 値 | 宣言箇所 | 説明 |
|--------|-----|---------|------|
| `COUNTER_SIZE` | `32` (iota 番兵) | `context.go:55` | `CounterType` 列挙の番兵。`globalCounters` 配列のサイズ、および `InitCounters`/`SetMemCounters` のループ上限に使用 |

`COUNTER_SIZE = 32` のとき実際に使用する共有メモリは `32 × 8 = 256` バイト（全 1024 バイトの 25%）。残り `768` バイトは空き（96 カウンタ分）。

### gnmi_dump の出力フォーマット定数

`gnmi_dump.go` は `fmt.Printf` でカウンタを出力する際、区切り文字として `---` を使用する（ハードコード）。

| 用途 | 値 | 宣言箇所 |
|------|----|---------|
| ヘッダ行 | `"Dump GNMI counters\n"` | `gnmi_dump.go:17` |
| カウンタ出力書式 | `"%s---%d\n"` (CounterType.String() と uint64 値) | `gnmi_dump.go:22` |
| エラー出力書式 | `"Error: Fail to read counters, syscall error, err: %v\n"` | `gnmi_dump.go:20` |

### 注記

- `memKey = 7749` は他の SysV IPC キーとの衝突を避けるための固定値であり、設定変更不可（再ビルド必要）。
- `COUNTER_SIZE` を変更した場合、`telemetryd` と `gnmi_dump` を**同時に**再ビルド・再デプロイしないと配列インデックスがずれ、カウンタの対応関係が壊れる。
- `gnmi_dump` の終了コードは常に `0`（エラー時も）。出力文字列に `"Error:"` を含むかで成否を判断する必要がある。
