---
title: 運用
description: "運用 — 機能章を読む上で必要な「SAI 失敗時の見方」「内部 dump の取り方」「health/system ready の解釈」をここに集める。"
area: topics
verification: meta
last_verified: 2026-05-11
sources: []
---

# 運用

機能章を読む上で必要な「SAI 失敗時の見方」「内部 dump の取り方」「health/system ready の解釈」をここに集める。機能固有の切り分け（BGP の neighbor down、ACL の install 失敗、L2 の port flap など）は各機能章の運用ページに任せ、ここは共通の観察ポイントを扱う。

## DB 一覧（番号）

最初に頭に入れておくと迷わない。

| n | DB 名 | 役割 |
| --- | --- | --- |
| 0 | APPL_DB | orchagent への入力（fpmsyncd、teamsyncd、portsyncd、p4rt-app など） |
| 1 | ASIC_DB | orchagent → syncd / SAI への出力。`ASIC_STATE:*` |
| 2 | COUNTERS_DB | flex counter |
| 4 | CONFIG_DB | ユーザ設定の真実 |
| 6 | STATE_DB | 各 daemon の状態（PORT_TABLE、INTERFACE_TABLE 等） |
| 13 | ERROR_DB | SAI 失敗の app 通知 |
| 14 | APPL_STATE_DB | APPL_DB に書いた結果（成功 / 失敗） |

```
admin@sonic:~$ redis-cli -n 4 KEYS "*" | wc -l
admin@sonic:~$ redis-cli -n 1 KEYS "ASIC_STATE:*" | head
admin@sonic:~$ redis-cli -n 6 KEYS "PORT_TABLE|*" | head
```

## SAI 失敗を見るときの順番

1. **syncd ログ** で `handleSai*Status` の失敗判定を確認する。fatal なら syncd は abort し、stack trace と dump が残る。

   ```
   admin@sonic:~$ docker exec syncd supervisorctl tail syncd \
     | grep -E "SAI_STATUS|handleSai"
   admin@sonic:~$ ls /var/log/syncd*.log
   ```

2. **ERROR_DB** に該当 object と SAI status code が出ているかを確認する。orchagent はここを購読して retry / 再構成の判断材料にする。

   ```
   admin@sonic:~$ redis-cli -n 13 KEYS "ERROR_*"
   admin@sonic:~$ redis-cli -n 13 HGETALL "ERROR_ROUTE_ENTRY|10.0.0.0/24"
   1) "operation"
   2) "create"
   3) "rc"
   4) "SAI_STATUS_TABLE_FULL"
   ```

3. **上位 APP** （例: AclOrch、RouteOrch）でその object がどの CONFIG_DB エントリに対応するかを照合する。`docker exec swss supervisorctl tail orchagent` で `<Orch名>` を grep。
4. **影響の出ている機能章の運用ページ** に戻り、機能固有の retry 規約や fallback 動作を確認する。

設計の詳細は [SAI 失敗ハンドリング（handleSai*Status virtual + ERROR_DB）](../../platform/hld-for-handling-sai-failures.md) と [Error Handling Framework（ERROR_DB / SAI 失敗の app への伝搬）](../../architecture/error-handling-framework-in-sonic.md) を読む。

### 代表的な SAI status code と一次切り分け

| status | 典型原因 | 一次対処 |
| --- | --- | --- |
| `SAI_STATUS_TABLE_FULL` | CRM 枯渇（route、ACL、neighbor 等） | `crm show resources` でテーブル特定、scale を下げる / threshold を設定 |
| `SAI_STATUS_NOT_SUPPORTED` | ASIC が attribute / object を非対応 | platform 章 / SAI vendor 対応表を確認、機能無効化 |
| `SAI_STATUS_INVALID_PARAMETER` | orchagent が誤った attribute を渡した可能性 | orchagent ログで attribute 名特定、PR / issue 起票 |
| `SAI_STATUS_ITEM_ALREADY_EXISTS` | 同じ key の重複 install | warm boot 直後に多発するなら抑止、それ以外は orchagent の reconcile を疑う |
| `SAI_STATUS_OBJECT_IN_USE` | 削除順序の誤り（依存先がまだ参照中） | orchagent の destroy 順を確認、retry で消えるか観察 |

## syncd dump と SAI 失敗時の自動採取

SAI 失敗は単発の状態ではなく、その時点の ASIC_DB と SAI 内部状態をセットで保全したいことが多い。syncd には `syncd_dump.sh` と SAI 通知（`SAI_REDIS_NOTIFY_SYNCD_INVOKE_DUMP`）を組み合わせ、失敗時に dump を自動採取する仕組みがある。crash を待たずに状態を残せるため、再現が困難な間欠失敗の原因切り分けに使える。

手動採取の例:

```
admin@sonic:~$ sudo docker exec syncd syncd_dump.sh
admin@sonic:~$ ls /var/log/syncd/
sairedis.rec.gz  asic_db.json  saidump.txt
```

採取の仕掛けと出力場所は [SAI 失敗時の dump 取得](../../platform/dump-on-sai-failure.md) を読む。

## dump utility による DB 横断調査

機能の不具合切り分けでは、ある port や VRF に紐づく key が `CONFIG_DB`、`APPL_DB`、`STATE_DB`、`ASIC_DB` に同時に存在することを確認したい。dump utility は「モジュール（例: port、vrf）」を起点に複数 DB から関連 key を集約する CLI で、内部実装の経路を辿る作業を簡略化する。

```
admin@sonic:~$ sonic-db-dump -n CONFIG_DB -k "PORT|Ethernet0" -y
admin@sonic:~$ dump state port Ethernet0
admin@sonic:~$ dump state vlan Vlan1000
```

使い方と拡張規約は [dump utility（モジュール単位で複数 DB から関連 key を集約する debug CLI）](../../internals/dump-utility-for-easy-debugging.md) を読む。

## debug framework

各 daemon は debug 情報の dump 関数を Debug Framework に登録し、`show techsupport` や障害時の自動採取から一括で取得できるようにする。assert 拡張により、想定外状態を「ログだけ残して動作継続」か「停止」かを切り替えやすくする。

```
admin@sonic:~$ sudo show techsupport --since "1 hour ago"
admin@sonic:~$ ls /var/dump/
sonic_dump_<hostname>_<timestamp>.tar.gz
```

techsupport を解凍すると、各 docker の `supervisor` ログ、redis 全 DB の snapshot、`syncd_dump.sh` の出力、syslog、journal、kernel dmesg がまとまっている。

詳細は [Debug Framework（コンポーネント dump 登録 / assert 拡張）](../../architecture/debug-framework-in-sonic.md) を読む。

## health-check と system ready

`docker exec ... monit` ベースの単発 probe ではなく、container 内で複数の検査結果を 1 つの readiness に集約することで、k8s 上の SONiC で正確な readiness を得る。これは container 単位の運用観察。全体起動状態は別途 `system ready`（sysmonitor）が、per-app の closest UP status を event 集約して判定する。

```
admin@sonic:~$ show system-health summary
admin@sonic:~$ show system-health monitor-list
admin@sonic:~$ sudo systemctl status sonic.target
admin@sonic:~$ docker exec swss /usr/local/bin/container_checker
```

`system not ready` で長時間止まる場合の入口:

- どの per-app が UP でないか: `show system-health detail` で UP していない service を特定。
- service の起動失敗: `journalctl -u <svc>.service`、`docker logs <container>`。
- monit が NG: `docker exec <container> monit summary`。

詳細は [コンテナ health-check（k8s readiness probe）](../../internals/why-need-health-check.md) と [System Ready（sysmonitor + per-app closest UP status の event 集約）](../../system/system-ready-hld.md) を読む。

## ログの場所まとめ

| 経路 | ログ | grep キーワード |
| --- | --- | --- |
| orchagent | `docker exec swss supervisorctl tail orchagent` | `<Orch名>`、`SAI_STATUS`、`SWSS_RC_` |
| syncd | `docker exec syncd supervisorctl tail syncd` | `handleSai`、`SAI_STATUS`、`SAI_OBJECT_TYPE_*` |
| sairedis 記録 | `/var/log/syncd/sairedis.rec` | 全 SAI op が trace される（再現に有用） |
| sysmonitor | `/var/log/syslog` | `sysmonitor`、`system_ready` |
| monit | `docker exec <container> monit summary` | NG service |
| swss / sub-daemons | `docker exec swss supervisorctl tail <daemon>` | `fpmsyncd`、`portsyncd`、`teamsyncd` 等 |

## sairedis.rec の使い方

`/var/log/syncd/sairedis.rec` は syncd が SAI に投げた全 op を時系列で記録するファイルで、原因不明の SAI 失敗を再現するうえで最強の手掛かりになる。

```
admin@sonic:~$ docker exec syncd ls -lh /var/log/syncd/sairedis.rec*
admin@sonic:~$ docker exec syncd tail -50 /var/log/syncd/sairedis.rec
```

行頭の `c|`（create）、`s|`（set）、`r|`（remove）、`g|`（get response）、`n|`（notification）を読めば、orchagent から SAI への呼び出しと、SAI が返した OID / status が辿れる。`saidump` と組み合わせて、失敗直前のオブジェクト群を再構築する用途にも使える。

## orchagent の event loop が詰まったとき

オペレーション全般が遅い・反映されないときは、orchagent の event queue が詰まっているケースを疑う。

```
admin@sonic:~$ docker exec swss top -bn1 -p $(pidof orchagent)
admin@sonic:~$ docker exec swss supervisorctl tail orchagent | grep -i "queue"
admin@sonic:~$ redis-cli -n 0 LLEN "_*"
```

- CPU が貼り付いている: 設定流入が多すぎる、無限 retry に陥っている可能性。`ERROR_DB` を見る。
- queue 長が増えている: APPL_DB の subscribe を捌けていない。orchagent の単一スレッド設計上、SAI 呼び出しが遅いと全部詰まる。

並列性の改善は orchagent 周辺の internals ドキュメント群を参照する。

## 関連ページ

- [SAI 失敗ハンドリング（handleSai*Status virtual + ERROR_DB）](../../platform/hld-for-handling-sai-failures.md)
- [Error Handling Framework（ERROR_DB / SAI 失敗の app への伝搬）](../../architecture/error-handling-framework-in-sonic.md)
- [SAI 失敗時の dump 取得（syncd_dump.sh / SAI_REDIS_NOTIFY_SYNCD_INVOKE_DUMP）](../../platform/dump-on-sai-failure.md)
- [dump utility（モジュール単位で複数 DB から関連 key を集約する debug CLI）](../../internals/dump-utility-for-easy-debugging.md)
- [Debug Framework（コンポーネント dump 登録 / assert 拡張）](../../architecture/debug-framework-in-sonic.md)
- [コンテナ health-check（k8s readiness probe）](../../internals/why-need-health-check.md)
- [System Ready（sysmonitor + per-app closest UP status の event 集約）](../../system/system-ready-hld.md)
- [Build / Packaging 章](../19-build-packaging/index.md)（FEATURE / hostcfgd との関係）
- [SRv6 / MPLS 章](../17-srv6-mpls/operations.md)（SAI 失敗の実例）
