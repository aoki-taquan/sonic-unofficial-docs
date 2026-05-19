# hardware-side-effects.md — Phase F 調査証跡

## 調査概要

- 対象テーブル: `HARDWARE|ACCESS_LIST` (CONFIG_DB)
- 調査日: 2026-05-19
- 調査目的: `HARDWARE` テーブルへの書込みに起因する副次 DB 書込（STATE_DB / COUNTERS_DB / FLEX_COUNTER_DB / ASIC_DB 等）の有無を確認する

## grep 結果

### sonic-swss/orchagent/

```
$ grep -rn "HARDWARE\|COUNTER_MODE\|LOOKUP_MODE\|TCAM_SHARING" sonic-swss/orchagent/aclorch.cpp
→ 0 件

$ grep -rn "HARDWARE\|COUNTER_MODE\|LOOKUP_MODE\|TCAM_SHARING" sonic-swss/orchagent/
→ 0 件（portschema.h の PORT_LEARN_MODE_HARDWARE 等は HARDWARE テーブルと無関係）
```

### sonic-utilities/

```
$ grep -rn "HARDWARE" sonic-utilities/
→ 0 件（CLI コマンドなし）
```

### sonic-gnmi/（本番コード）

```
$ grep -rn "HARDWARE\|COUNTER_MODE\|LOOKUP_MODE" sonic-gnmi/gnmi_server/ sonic-gnmi/translib/
→ 0 件（testdata/db_dump.json のみ出現）
```

### sonic-mgmt-common/tools/test/dbinit.py

```python
db_hmset(ConfigDB, "HARDWARE|ACCESS_LIST", {
    "COUNTER_MODE": "per-rule",
    "LOOKUP_MODE":  "optimized",
})
```
テスト初期化のみ。本番 transformer コードでの参照は community リポジトリ内に未確認。

## 結論

`HARDWARE|ACCESS_LIST` は community SONiC コードパスにおいて dead consumer テーブルである。
書込みに起因して STATE_DB / COUNTERS_DB / FLEX_COUNTER_DB / ASIC_DB / APPL_DB いずれへも
副次書込は発生しない。Phase F の副次書込テーブルは全行「なし」。
