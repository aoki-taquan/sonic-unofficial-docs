# bmp — Phase F 副次 DB 書込スキャンノート

## 調査対象

- `sonic-buildimage/src/sonic-bmpcfgd/bmpcfgd/bmpcfgd.py`
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/` (全 .py)

## 結果サマリ

| DB | 書込有無 | 根拠 |
|----|---------|------|
| BMP_STATE_DB | **あり（削除のみ）** | `reset_bmp_table()` が `delete_all_by_pattern` を 3 回呼ぶ |
| STATE_DB | **なし** | bmpcfgd.py 全行で `STATE_DB` / `APPL_DB` への接続・書込ゼロ |
| COUNTERS_DB | **なし** | 同上、`COUNTERS_DB` への参照ゼロ |

## BMP_STATE_DB 書込の詳細

### `reset_bmp_table()` — L61-65

```python
def reset_bmp_table(self):
    self.state_db_conn.delete_all_by_pattern(BMP_STATE_DB, 'BGP_NEIGHBOR*')
    self.state_db_conn.delete_all_by_pattern(BMP_STATE_DB, 'BGP_RIB_IN_TABLE*')
    self.state_db_conn.delete_all_by_pattern(BMP_STATE_DB, 'BGP_RIB_OUT_TABLE*')
```

- **トリガー**: `load()` または `cfg_handler()` が呼ばれるたびに無条件実行
- **操作種別**: delete（書込ではなく削除）
- **対象パターン**:
  - `BGP_NEIGHBOR*` — openbmpd が書き込む BGP neighbor 状態テーブル
  - `BGP_RIB_IN_TABLE*` — openbmpd が書き込む Adj-RIB-In テーブル
  - `BGP_RIB_OUT_TABLE*` — openbmpd が書き込む Adj-RIB-Out テーブル
- **目的**: openbmpd 再起動前にステール状態を除去し、再起動後に新鮮な状態で再構築させる

### openbmpd による BMP_STATE_DB 書込（間接）

`bmpcfgd` 自身は直接 BMP_STATE_DB にデータを **書き込まない**。
書込は `openbmpd` プロセスが行う（`supervisorctl start openbmpd` 後に非同期）。
`bmpcfgd` の役割は「設定変更時にテーブルをクリアしてから openbmpd を再起動する」制御のみ。

## frrcfgd.py / bgpcfgd/ との関係

- `frrcfgd.py`: "bmp" / "BMP" の文字列ゼロヒット。BMP は frrcfgd 非経由。
- `bgpcfgd/managers_*.py`: BMP 関連コードなし。`bgpcfgd` は BGP ピア設定を FRR vtysh に注入するが、BMP exporter 制御は行わない。

## 結論

`BMP` テーブルの変更に伴う副次 DB 書込は **BMP_STATE_DB への削除操作のみ**。
`STATE_DB`・`COUNTERS_DB` への書込は実装されていない。FRR vtysh には `frrcfgd` ではなく、FRR BMP テンプレート（`bgpd.main.conf.j2`）が初期設定を行い、openbmpd との接続は自律動作する。
