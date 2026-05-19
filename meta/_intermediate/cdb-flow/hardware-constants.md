# HARDWARE テーブル — ハードコード定数調査証跡 (Phase E)

調査日: 2026-05-19  
調査対象リポジトリ: sonic-net/sonic-swss、sonic-net/sonic-gnmi、sonic-net/sonic-mgmt-common

## 調査コマンド

```bash
grep -rn "COUNTER_MODE\|LOOKUP_MODE\|TCAM_SHARING\|HARDWARE.*ACCESS_LIST" \
  sonic-swss/orchagent/ sonic-swss/cfgmgr/ sonic-swss/fpmsyncd/
# → 0 件

grep -rn "per-rule\|PER-RULE\|optimized\|advanced\|LEGACY" \
  sonic-swss/orchagent/aclorch.cpp sonic-swss/orchagent/aclorch.h
# → HARDWARE テーブルフィールドとしての参照 0 件
#   （ACL_TABLE の processing とは別）

grep -n "HARDWARE\|COUNTER_MODE\|LOOKUP_MODE" \
  sonic-mgmt-common/tools/test/dbinit.py
# → L88-90: db_hmset(ConfigDB, "HARDWARE|ACCESS_LIST", {...})
#   テスト用初期化スクリプトのみ

grep -n "HARDWARE" sonic-gnmi/testdata/db_dump.json
# → L5426: "HARDWARE|ACCESS_LIST": {"TCAM_SHARING@":"","COUNTER_MODE":"per-rule","LOOKUP_MODE":"advanced"}
# → L7101: "HARDWARE_TABLE|ACCESS_LIST": {"LOOKUP_MODE":"LEGACY","COUNTER_MODE":"PER-RULE"}
```

## 結論

community SONiC (sonic-swss) コードベースには `HARDWARE|ACCESS_LIST` のフィールド値を参照・処理する
コードは存在しない。したがってハードコード定数（enum マップ、有効値リスト、パスリテラル等）も
orchagent には存在しない。

観測された値文字列はすべてテストデータ (sonic-gnmi testdata / sonic-mgmt-common dbinit) にのみ出現しており、
正式な有効値集合として定義するソースコードは community リポジトリ内には確認できない。
