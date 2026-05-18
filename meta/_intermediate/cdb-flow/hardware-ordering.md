# hardware-ordering.md — Phase B 調査ノート

## 対象テーブル
CONFIG_DB `HARDWARE|ACCESS_LIST`

## 調査方針
community sonic-swss 全体で HARDWARE テーブルの consumer（ProducerTable::set 呼び出し、
ConsumerStateTable 購読、SubscriberStateTable 購読のいずれか）を探索した。

## grep 結果サマリ

```
sonic-swss$ grep -rn "HARDWARE" orchagent/ cfgmgr/ fpmsyncd/ --include="*.cpp" --include="*.h"
# → 0 hits (HARDWARE_ACCESS_BUS など SAI 定数を除く)
sonic-swss$ grep -rn "COUNTER_MODE\|LOOKUP_MODE\|TCAM_SHARING\|ACCESS_LIST" orchagent/ cfgmgr/ fpmsyncd/
# → 0 hits
```

**結論: community orchagent / cfgmgr は HARDWARE テーブルを購読しない。**
書込み順依存は community コードパスでは発生しない。

## 書込み経路の確認

sonic-gnmi/testdata/db_dump.json — テスト用初期 DB スナップショット。
sonic-mgmt-common/tools/test/dbinit.py — db_hmset で直書き（読み出し側の初期化ツール）。

どちらも「テスト用の初期データ投入」であり、runtime の書き込み経路ではない。

## ベンダー路（Dell translib）

Dell SONIC の sonic-mgmt-common transformer 層（GET/SET path for ACL hardware-mode）が
HARDWARE テーブルを読み書きするとされるが、該当コードは community リポジトリには含まれない。
順序依存の詳細は community SONiC の範囲外。

## Phase B 記述方針

- 「consumer 不在のため書込み順依存なし」を明記
- `ACL_TABLE` / `ACL_RULE` との関係：HARDWARE テーブルは AclOrch に届かないため、
  ACL_TABLE / ACL_RULE への反映順序は存在しない
- `HARDWARE_TABLE|ACCESS_LIST`（アンダースコア版）との関係：同一エントリの異名と推定、
  どちらを書いても community orchagent は無視
