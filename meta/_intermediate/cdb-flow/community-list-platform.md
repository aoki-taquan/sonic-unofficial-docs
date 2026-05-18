# community-list (SNMP_COMMUNITY) — Phase H プラットフォーム差異スキャンノート

## スキャン対象ソース

- `sonic-buildimage/dockers/docker-snmp/snmpd.conf.j2`
- `sonic-buildimage/dockers/docker-snmp/snmp_yml_to_configdb.py`
- `sonic-buildimage/dockers/docker-snmp/start.sh`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-snmp.yang`

## 抽出結果

### 1. SNMP_COMMUNITY テーブル自体のプラットフォーム差異なし

`snmpd.conf.j2` の `SNMP_COMMUNITY` 処理ブロック (L48-64) に `is_multi_npu` / `namespace` / プラットフォーム判定条件なし。
`RO`/`RW` の TYPE 判定のみ。ASIC 種別・ベンダー・chassis 構成に依らず同一ロジックで展開される。

### 2. multi-asic 環境での agentAddress 差異（SNMP_COMMUNITY 外）

`snmpd.conf.j2` L16-34 はコメントに「multi-asic platform」の言及があり、`SNMP_AGENT_ADDRESS_CONFIG` テーブルが空の場合に `udp:161` / `udp6:161` にフォールバックする。SNMP_COMMUNITY の community 文字列処理には影響しない。multi-asic 環境でも各 namespace の CONFIG_DB ではなく host CONFIG_DB の `SNMP_COMMUNITY` を読む（`snmp_yml_to_configdb.py` は `ConfigDBConnector()` でデフォルト接続）。

### 3. snmp_yml_to_configdb.py の multi-asic 非対応

`snmp_yml_to_configdb.py` は `ConfigDBConnector()` を引数なしで呼ぶため、host の CONFIG_DB (DB 4) のみに接続する。`asic0`/`asic1` などの per-namespace CONFIG_DB への書き込みは行わない。SNMP_COMMUNITY は host 単位で管理されるため、multi-asic でも単一テーブルが全 ASIC 共用される。

### 4. VOQ chassis / supervisor 構成

`docker-snmp` は per-host コンテナであり、supervisor と各 line card で独立起動する。SNMP_COMMUNITY テーブルは各 host の CONFIG_DB に独立して存在する。chassis 全体を統一した community 管理機構はなく、各ノードで個別に設定が必要。

### 5. プラットフォーム固有 YANG / template 分岐なし

`sonic-snmp.yang` にプラットフォーム条件分岐なし。`snmpd.conf.j2` の SNMP_COMMUNITY ブロックにも `{% if platform %}` 等の条件なし（`platform` / `asic` / `chassis` / `vendor` をキーワードで grep して 0 ヒット）。

## 結論

`SNMP_COMMUNITY` テーブルの処理は ASIC 種別・multi-asic / VOQ chassis 構成・ベンダーに依らない。
プラットフォーム差は「影響なし」。
