---
title: 運用
area: topics
verification: meta
last_verified: 2026-05-10
sources: []
---

# 運用

機能章を読む上で必要な「SAI 失敗時の見方」「内部 dump の取り方」「health/system ready の解釈」をここに集める。機能固有の切り分け（BGP の neighbor down、ACL の install 失敗、L2 の port flap など）は各機能章の運用ページに任せ、ここは共通の観察ポイントを扱う。

## SAI 失敗を見るときの順番

1. syncd ログで `handleSai*Status` の失敗判定を確認する。fatal なら syncd は abort し、stack trace と dump が残る。
2. `ERROR_DB` に該当 object と SAI status code が出ているかを確認する。orchagent はここを購読して retry/再構成の判断材料にする。
3. 上位の APP（例: AclOrch、RouteOrch）でその object がどの CONFIG_DB エントリに対応するかを照合する。
4. 影響の出ている機能章の運用ページに戻り、機能固有の retry 規約や fallback 動作を確認する。

設計の詳細は [SAI 失敗ハンドリング（handleSai*Status virtual + ERROR_DB）](../../platform/hld-for-handling-sai-failures.md) と [Error Handling Framework（ERROR_DB / SAI 失敗の app への伝搬）](../../architecture/error-handling-framework-in-sonic.md) を読む。

## syncd dump と SAI 失敗時の自動採取

SAI 失敗は単発の状態ではなく、その時点の ASIC_DB と SAI 内部状態をセットで保全したいことが多い。syncd には `syncd_dump.sh` と SAI 通知（`SAI_REDIS_NOTIFY_SYNCD_INVOKE_DUMP`）を組み合わせ、失敗時に dump を自動採取する仕組みがある。crash を待たずに状態を残せるため、再現が困難な間欠失敗の原因切り分けに使える。

採取の仕掛けと出力場所は [SAI 失敗時の dump 取得](../../platform/dump-on-sai-failure.md) を読む。

## dump utility による DB 横断調査

機能の不具合切り分けでは、ある port や VRF に紐づく key が `CONFIG_DB`、`APPL_DB`、`STATE_DB`、`ASIC_DB` に同時に存在することを確認したい。dump utility は「モジュール（例: port、vrf）」を起点に複数 DB から関連 key を集約する CLI で、内部実装の経路を辿る作業を簡略化する。

使い方と拡張規約は [dump utility（モジュール単位で複数 DB から関連 key を集約する debug CLI）](../../internals/dump-utility-for-easy-debugging.md) を読む。

## debug framework

各 daemon は debug 情報の dump 関数を Debug Framework に登録し、`show techsupport` や障害時の自動採取から一括で取得できるようにする。assert 拡張により、想定外状態を「ログだけ残して動作継続」か「停止」かを切り替えやすくする。

詳細は [Debug Framework（コンポーネント dump 登録 / assert 拡張）](../../architecture/debug-framework-in-sonic.md) を読む。

## health-check と system ready

`docker exec ... monit` ベースの単発 probe ではなく、container 内で複数の検査結果を 1 つの readiness に集約することで、k8s 上の SONiC で正確な readiness を得る。これは container 単位の運用観察。全体起動状態は別途 `system ready`（sysmonitor）が、per-app の closest UP status を event 集約して判定する。

詳細は [コンテナ health-check（k8s readiness probe）](../../internals/why-need-health-check.md) と [System Ready（sysmonitor + per-app closest UP status の event 集約）](../../system/system-ready-hld.md) を読む。

## 関連ページ

- [SAI 失敗ハンドリング（handleSai*Status virtual + ERROR_DB）](../../platform/hld-for-handling-sai-failures.md)
- [Error Handling Framework（ERROR_DB / SAI 失敗の app への伝搬）](../../architecture/error-handling-framework-in-sonic.md)
- [SAI 失敗時の dump 取得（syncd_dump.sh / SAI_REDIS_NOTIFY_SYNCD_INVOKE_DUMP）](../../platform/dump-on-sai-failure.md)
- [dump utility（モジュール単位で複数 DB から関連 key を集約する debug CLI）](../../internals/dump-utility-for-easy-debugging.md)
- [Debug Framework（コンポーネント dump 登録 / assert 拡張）](../../architecture/debug-framework-in-sonic.md)
- [コンテナ health-check（k8s readiness probe）](../../internals/why-need-health-check.md)
- [System Ready（sysmonitor + per-app closest UP status の event 集約）](../../system/system-ready-hld.md)
