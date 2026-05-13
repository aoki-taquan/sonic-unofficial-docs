# Mermaid Syntax Report

ユーザーがブラウザで「Syntax error in text, mermaid version 11.15.0」を確認したため、
`docs/**/*.md` 内の全 mermaid block を mermaid 公式パーサ (`mermaid.parse`) で検査し、
構文エラーを一括修正した。

## 検査方式

- ローカルに mermaid + jsdom + dompurify を install して `meta/scripts/mermaid_parse.mjs`
  経由で `mermaid.parse()` を全 block に通した
- CI には軽量な静的ヒューリスティック (`meta/scripts/check_mermaid_syntax.py`) を組み込み、
  代表的なパターンが新規 PR で混入したら検出できるようにした
- mermaid npm パッケージが揃っている環境 (`MERMAID_NODE_MODULES` env 設定) では
  チェッカは自動的に full parser を呼ぶ

## 修正前の集計

- 対象 md (mermaid 含む): 717
- mermaid block 総数: 887
- パーサで error を出した block 数: **129**
- 影響ファイル数: 125

### 種別 (パーサ出力の `Expecting ...` トークンで分類)

| 種別 | 件数 |
|------|------|
| `parse:SQE` (`]` 期待) — flowchart `[label]` 内に裸の括弧 | 83 |
| lexical (字句エラー) — 不正な記号列 | 31 |
| `parse:CYLINDEREND` — `[(label)]` cylinder 内に特殊文字 | 7 |
| `parse:SEMI` — subgraph title に括弧、edge label の引用漏れ | 5 |
| その他 (`AMP`, `LINK`, `()`) | 3 |

## 主な修正パターン

1. **flowchart `node[label]` 内に裸の `(` `)` `|` `<` `>` `&` `/`**
   - 例: `A[client tool\n(gnmi_get / gnmi_set)]` → `A["client tool\n(gnmi_get / gnmi_set)"]`
2. **cylinder `[(label)]` の label に `|` や特殊文字**
   - 例: `ST1[(STATE_DB\nCOPP_TRAP_CAPABILITY_TABLE|traps)]` → `ST1[("STATE_DB\nCOPP_TRAP_CAPABILITY_TABLE|traps")]`
3. **`subgraph TITLE` の TITLE に括弧**
   - 例: `subgraph Linux Host (global namespace)` → `subgraph SG_1["Linux Host (global namespace)"]`
4. **`subgraph ID[(label)]` のように shape 構文を subgraph に書いている**
   - 例: `subgraph CFG[(CONFIG_DB)]` → `subgraph CFG["CONFIG_DB"]`
5. **edge label `-->|text|` 内の括弧**
   - 例: `-->|flex counter\n(rifcounter group)|` → `-->|"flex counter\n(rifcounter group)"|`
6. **異常矢印 / dotted / thick の typo**
   - `Peer((Router)) ==|trunk: Vlan10/20/30| Eth` → `Peer((Router)) ==>|"trunk: Vlan10/20/30"| Eth`
   - `Eth -. dot1q .100 .- Sub` → `Eth -.->|"dot1q .100"| Sub`
7. **label 内の生 `"`**
   - 例: `ND[netdev\n"send_to_ingress"]` → `ND["netdev\nsend_to_ingress"]`
8. **sequenceDiagram のメッセージ内の `;`** (mermaid 11.x で別ステートメントと解釈)
   - `;` → `,` に置換

## 自動修正スクリプト

- `meta/scripts/fix_mermaid_syntax.py`
  - flowchart label / cylinder / subgraph title / subgraph shape / edge label を
    必要に応じて `"..."` で quote する
  - `--apply` で実際に書き込み、`--only-paths FILE` で対象を絞れる
- 残った 6 件のエッジケースは手動修正 (パターン 6-8)

## 修正後

- mermaid block 総数: 887
- パーサで error を出した block 数: **0**
- 修正対象ファイル: 125 (528 行差分)
- 静的チェッカ (`check_mermaid_syntax.py`) issue 数: 0

## CI 統合

`.github/workflows/ci.yml` の `lint` ジョブに静的チェッカを追加 (informational; 落とさない):

```yaml
- name: mermaid block syntax check (informational)
  run: python3 meta/scripts/check_mermaid_syntax.py --check || true
```

mermaid npm を入れた環境で full parser を回したい場合:

```sh
npm install --no-save mermaid jsdom dompurify
MERMAID_NODE_MODULES=$PWD/node_modules \
  python3 meta/scripts/check_mermaid_syntax.py --check
```
