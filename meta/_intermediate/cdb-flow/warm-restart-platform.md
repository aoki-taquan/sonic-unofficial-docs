# warm-restart-platform

## 調査対象

- `sonic-swss-common/common/warm_restart.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-buildimage/files/image_config/warmboot-finalizer/finalize-warmboot.sh`

## 結論

`WARM_RESTART` テーブル自体の読み書きロジック（`warm_restart.cpp`）はプラットフォーム非依存。
ASIC 種別・multi-asic・VOQ chassis に関する条件分岐は一切ない。

ただし `finalize-warmboot.sh` は multi-asic デバイスで **asic namespace ごとに並列 subshell** を起動し
各 namespace の DB への warm boot フラグ処理を行う（L270-291）。
また `finalize_global()` は `asic_type == mellanox` の場合のみ CPU frequency governor を復元する（L198-202）。
これらは `WARM_RESTART` テーブルの設定値を参照するわけではなく、
warm restart プロセスのインフラ層の差異にとどまる。

## VS / VPP

`warm_restart.cpp` は SAI を呼ばない。VS / VPP でも `hget()` / `hset()` は正常動作し、
各プロセスのタイマー値・enable フラグは通常通り読み取られる。
ただし VS ではデータプレーンが存在しないため warm restart の「再収束」の実動作に意味はない。

## multi-asic

`WarmStart::initialize()` は `DBConnector("CONFIG_DB", ...)` を名前指定で接続し、
namespace を明示的に指定しない（`warm_restart.cpp:51`）。
したがって各コンテナ（asic0, asic1 ...）内で実行された場合、
そのコンテナのデフォルト namespace の CONFIG_DB を参照する。
`WARM_RESTART` テーブルは各 asic-namespace CONFIG_DB に独立して存在し、
chassis-wide に同期する仕組みはない。
