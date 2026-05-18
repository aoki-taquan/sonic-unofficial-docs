# SWITCH_HASH — Phase C 暗黙テーブル参照スキャンノート

対象テーブル: `SWITCH_HASH`
Consumer: `orchagent` / `SwitchOrch` (`sonic-swss/orchagent/switchorch.cpp`)
スキャン範囲: `doCfgSwitchHashTableTask()`, `setSwitchHash()`, `setSwitchHashFieldListSai()`, `setSwitchHashAlgorithmSai()`, `querySwitchHashDefaults()`, `getSwitchHashOidSai()` 全行精読

---

## YANG 明示 leafref

`sonic-hash.yang` の `SWITCH_HASH.GLOBAL` コンテナには他テーブルへの `leafref` が**ない**。
フィールドはすべて自己完結した enum (`hash-field`) / enum (`hash-algorithm`) で定義される。
`ordered-by user` 修飾子でリスト順を保持するが、他テーブルを参照しない。

## 暗黙参照スキャン結果

### SAI hash オブジェクト OID（ASIC 内部）

`SwitchOrch` コンストラクタ (`switchorch.cpp:169`) が呼ぶ `querySwitchHashDefaults()` (`switchorch.cpp:2030-2043`) は SAI から `SAI_SWITCH_ATTR_ECMP_HASH` / `SAI_SWITCH_ATTR_LAG_HASH` の OID を取得して `m_switchHashDefaults` にキャッシュする。この OID は ASIC が管理するオブジェクトであり、CONFIG_DB テーブルではない。

### 参照なしの理由

`doCfgSwitchHashTableTask()` は Consumer からフィールドを読み取り、`swHlpr.parseSwHash()` → `setSwitchHash()` を呼ぶ。この一連の処理で他の CONFIG_DB テーブル（`PORT` / `PORTCHANNEL` / `VRF` / `INTERFACE` / `FG_NHG` 等）を検索・参照する箇所はない。

`FG_NHG`（Fine-Grained ECMP）は `FgNhgOrch` が独自に管理し、`SWITCH_HASH` とは無関係の経路で SAI に設定する。`SwitchOrch` は `FgNhgOrch` を直接参照しない。

## スキャン結論

SWITCH_HASH テーブルは CONFIG_DB 上の暗黙参照を**一切持たない**。
YANG 明示 leafref も暗黙コード参照も存在しない。
