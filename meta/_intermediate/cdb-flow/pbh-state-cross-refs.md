# pbh-state — Phase C: 暗黙参照テーブル

調査日: 2026-05-18
調査対象: sonic-swss/orchagent/pbh/pbhcap.cpp, orchdaemon.cpp, sonic-utilities/config/plugins/pbh.py

## 書き込み側 (PbhCapabilities) の参照先

`PBH_CAPABILITIES` テーブルは `PbhCapabilities::writePbhVendorCapabilitiesToDb()` が起動時 1 回のみ書き込む。
書き込まれるフィールド値はすべてコードにハードコードされており、CONFIG_DB / APPL_DB の任意エントリへの依存はない。

### 実際の依存関係

| 参照先リソース | 参照方向 | 条件 | evidence |
|--------------|---------|------|---------|
| `STATE_DB` 接続 (`PbhCapabilities::stateDb`) | 書き込み先 DB | 必須。static メンバとして orchdaemon 起動最初期に確立 | `pbhcap.cpp:288` |
| `ASIC_VENDOR` 環境変数 | env var 読み取り → ベンダー分岐 | 任意。未設定時は `GENERIC` platform へ fallback | `pbhcap.cpp:314–329` |
| CONFIG_DB `PBH_TABLE` / `PBH_RULE` / `PBH_HASH` / `PBH_HASH_FIELD` | **なし** | `PBH_CAPABILITIES` の値はコード固定値のみ。CONFIG_DB エントリは参照しない | `pbhcap.cpp:107–124`（全フィールド値はコンストラクタで直書き） |
| APPL_DB | **なし** | 同上 | — |
| SAI / ASIC | **なし** | SAI クエリなし。ベンダー判別は env var のみ | `pbhcap.cpp:310–334` |

## 読み取り側 (sonic-utilities) の参照先

`config pbh` コマンドは `pbh_capabilities_query(db, key)` で `STATE_DB.PBH_CAPABILITIES|<key>` を hgetall する。

| 参照先リソース | 参照方向 | 使用箇所 |
|--------------|---------|---------|
| `STATE_DB PBH_CAPABILITIES\|table` | 読み取り | `config pbh table add/update/del` (`pbh.py:1351`) |
| `STATE_DB PBH_CAPABILITIES\|rule` | 読み取り | `config pbh rule add/update/del` (`pbh.py:1090,1218`) |
| `STATE_DB PBH_CAPABILITIES\|hash` | 読み取り | `config pbh hash add/update/del` (`pbh.py:781`) |
| `STATE_DB PBH_CAPABILITIES\|hash-field` | 読み取り | `config pbh hash-field add/update/del` (`pbh.py:670`) |

## まとめ

`PBH_CAPABILITIES` は CONFIG_DB / APPL_DB / SAI への依存を持たない唯一の STATE_DB テーブルに近い存在で、
書き込み値は `ASIC_VENDOR` env var とコードハードコード定数のみに依存する。
読み取り側の `config pbh` コマンドが orchagent 起動前に実行された場合、STATE_DB にキーが存在しないため
`pbh_capabilities_query()` が空 dict を返し、capability 検証がエラーになる。
