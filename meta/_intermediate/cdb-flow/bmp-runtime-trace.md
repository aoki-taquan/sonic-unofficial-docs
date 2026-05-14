# BMP — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/bmp.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `bmpcfgd` (`sonic-bgpcfgd` パッケージ内) |
| 2. CFG→APPL 翻訳 | なし (FRR vtysh 経由で BMP 設定) |
| 3. APPL→SAI | なし (BMP は FRR の BGP モニタリングプロトコル、SAI 非経由) |
| 4. タイミング+副作用 | CONFIG_DB の `BMP` エントリ変化を検知後、FRR に BMP target station 設定を注入。BMP セッション確立は非同期。... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`bmpcfgd` (`sonic-bgpcfgd` パッケージ内) が CONFIG_DB の `BMP` テーブルを購読する。

`BMP` テーブルは BMP target server を定義。`bgpcfgd` と協調して動作。

### 段階 2 — CFG→APPL 翻訳

なし (FRR vtysh 経由で BMP 設定)

### 段階 3 — APPL→SAI

なし (BMP は FRR の BGP モニタリングプロトコル、SAI 非経由)

### 段階 4 — タイミングと副作用

**適用タイミング**: CONFIG_DB の `BMP` エントリ変化を検知後、FRR に BMP target station 設定を注入。BMP セッション確立は非同期。

**副作用**: BMP サーバへの監視データ送信が開始/停止。FRR BGP 動作への影響なし。
<!-- /runtime-trace -->
```
