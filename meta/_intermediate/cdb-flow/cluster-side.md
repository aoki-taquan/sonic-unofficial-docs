# cluster フィールド — 副次 DB 書込調査 (Phase F)

## 調査対象

- `DEVICE_METADATA|localhost.cluster`
- `DEVICE_NEIGHBOR_METADATA|<device>.cluster`

書き込み元: `sonic-buildimage/src/sonic-config-engine/minigraph.py`

## 調査方法

`cluster` フィールドを消費するデーモン・テンプレートが存在しないことは Phase C (cross-refs) 調査で確認済み。
Phase F では「cluster フィールドの SET/DEL が他の DB エントリへの書き込みを引き起こすか」を追加調査。

```
grep -rn "cluster" sonic-buildimage/src/sonic-config-engine/
grep -rn "DEVICE_METADATA.*cluster\|cluster.*DEVICE_METADATA" sonic-swss/
grep -rn "DEVICE_NEIGHBOR_METADATA.*cluster\|cluster.*DEVICE_NEIGHBOR_METADATA" sonic-swss/
```

## 結果

### CONFIG_DB への書き込み

`minigraph.py` が `DEVICE_METADATA|localhost.cluster` および
`DEVICE_NEIGHBOR_METADATA|<device>.cluster` に値を書き込む。
これは PRIMARY 書き込みであり副次書き込みではない。

### APPL_DB

`portmgrd`・`neighsyncd`・`bgpcfgd` 等は `DEVICE_METADATA` / `DEVICE_NEIGHBOR_METADATA`
テーブル全体を subscribe するが `cluster` フィールドを参照しない
(`buffers_config.j2:83,209-210`、`qos_config.j2:107-116,150-151` は `type` フィールドのみ参照)。
→ APPL_DB への副次書き込みは**なし**。

### STATE_DB

`cluster` 値に依存する STATE_DB 書き込み経路なし。
→ STATE_DB への副次書き込みは**なし**。

### COUNTERS_DB / FLEX_COUNTER_DB / ASIC_DB

`cluster` フィールドは SAI レイヤと無関係。
→ これらへの副次書き込みは**なし**。

### まとめ

`cluster` フィールドは minigraph から CONFIG_DB への一方向書き込みのみ。
SET 後に他の DB / テーブルへの副次書き込みは発生しない。

Evidence:
- `sonic-buildimage/src/sonic-config-engine/minigraph.py:662-668,806-811,2170-2172`
- Phase C cross-refs 調査結果 (コードベース全体 grep でデーモン消費なし)
