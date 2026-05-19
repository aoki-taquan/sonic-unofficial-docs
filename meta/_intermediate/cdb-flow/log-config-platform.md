# LOGGER — Phase H プラットフォーム差異 調査証跡

## 調査対象ソース

- `sonic-swss-common/common/logger.cpp` (全行)
- `sonic-swss-common/common/loglevel.cpp` (全行)
- `sonic-utilities/config/syslog.py` L665-698

## logger.cpp / loglevel.cpp — プラットフォーム分岐なし

`Logger::linkToDbWithOutput()` および `Logger::settingThread()` は `DBConnector db("CONFIG_DB", 0)` でデフォルト namespace の CONFIG_DB に直接接続する。`platform` / `asic` / `chassis` / `namespace` / `hwsku` / `vendor` に基づく条件分岐は一切存在しない (全行精読確認)。

`swssloglevel` (`loglevel.cpp:129`) も同様に `DBConnector config_db("CONFIG_DB", 0)` を使用し、namespace オプションを持たない。

## multi-asic 構成

`swssloglevel` は namespace 引数を持たない C++ バイナリである。multi-asic 構成では各 ASIC コンテナ (`asic0`, `asic1`, ...) 内で個別にデーモンが動作し、それぞれのコンテナ内の `swssloglevel` がそのコンテナの CONFIG_DB を参照する。ホストから asic コンテナを横断して一括設定する CLI は `config syslog level` に限られる。

`config syslog level` (`syslog.py:665-698`) は `--namespace` オプションを受け付け、`multi_asic.get_asic_id_from_name(namespace)` でコンテナ名にサフィックスを付与して正しい `cfgdb_clients[namespace]` を選択する (L676-678)。

| ツール | namespace 対応 | 根拠 |
|--------|---------------|------|
| `swssloglevel` (C++) | **なし** — デフォルト namespace のみ | `loglevel.cpp:129` |
| `config syslog level` (Python CLI) | **あり** — `--namespace` オプション | `syslog.py:661-678` |

## SAI コンポーネント (`SAI_API_*`)

`syncd` は各 ASIC コンテナ内で 1 プロセスとして動作する。`SAI_API_*` の LOGGER エントリは各コンテナの CONFIG_DB に独立して存在し、`swssloglevel -s` もコンテナ内で実行する必要がある。ASIC ベンダーによって `SAI_API_*` のコンポーネント名一覧が異なる可能性があるが、logger.cpp / loglevel.cpp 側の処理ロジック自体は共通。

## SmartSwitch / VOQ Chassis

`logger.cpp` / `loglevel.cpp` に SmartSwitch / VOQ Chassis 固有の分岐なし。DPU コンテナでも同一の `Logger` ライブラリが使用されるが、CONFIG_DB 接続先はそれぞれのコンテナ内のデフォルト namespace に固定される。

## 結論

`LOGGER` テーブルの読み書きロジック (`logger.cpp`, `loglevel.cpp`) にプラットフォーム差異はない。multi-asic 環境では `swssloglevel` はコンテナ内で個別実行が必要であり、`config syslog level --namespace` CLI のみがホストから namespace 横断操作を提供する。
