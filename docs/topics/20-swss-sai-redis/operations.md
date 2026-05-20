---
title: 運用
description: 運用 — 機能章を読む上で必要な「SAI 失敗時の見方」「内部 dump の取り方」「health/system ready の解釈」をここに集める。
area: topics
verification: meta
last_verified: 2026-05-11
sources: []
related:
  cli:
  - show techsupport
  - config vrf
  - show acl
  - config acl
  - config bgp
  - show bgp
  config_db:
  - CRM
  - VRF
  - ACL_RULE
  - ACL_TABLE
  - BGP_NEIGHBOR
  - BGP_GLOBALS
  - BGP_PEER_GROUP_AF
  yang:
  - sonic-bgp-global
  - sonic-bgp-neighbor
  - sonic-crm
  - sonic-vrf
  - sonic-bgp-bbr
  - sonic-bgp-peerrange
  - sonic-bgp-device-global
---

# 運用

機能章を読む上で必要な「[SAI](../../reference/glossary.md#term-sai) 失敗時の見方」「内部 dump の取り方」「health/system ready の解釈」をここに集める。機能固有の切り分け（[BGP](../../reference/glossary.md#term-bgp) の neighbor down、[ACL](../../reference/glossary.md#term-acl) の install 失敗、L2 の port flap など）は各機能章の運用ページに任せ、ここは共通の観察ポイントを扱う。

## DB 一覧（番号）

最初に頭に入れておくと迷わない。

| n | DB 名 | 役割 |
| --- | --- | --- |
| 0 | [APPL_DB](../../reference/glossary.md#term-appl_db) | [orchagent](../../reference/glossary.md#term-orchagent) への入力（[fpmsyncd](../../reference/glossary.md#term-fpmsyncd)、teamsyncd、[portsyncd](../../reference/glossary.md#term-portsyncd)、p4rt-app など） |
| 1 | [ASIC_DB](../../reference/glossary.md#term-asic_db) | orchagent → [syncd](../../reference/glossary.md#term-syncd) / SAI への出力。`ASIC_STATE:*` |
| 2 | [COUNTERS_DB](../../reference/glossary.md#term-counters_db) | flex counter |
| 4 | [CONFIG_DB](../../reference/glossary.md#term-config_db) | ユーザ設定の真実 |
| 6 | [STATE_DB](../../reference/glossary.md#term-state_db) | 各 daemon の状態（PORT_TABLE、INTERFACE_TABLE 等） |
| 13 | ERROR_DB | SAI 失敗の app 通知 |
| 14 | APPL_STATE_DB | APPL_DB に書いた結果（成功 / 失敗） |

```bash
admin@sonic:~$ redis-cli -n 4 KEYS "*" | wc -l
admin@sonic:~$ redis-cli -n 1 KEYS "ASIC_STATE:*" | head
admin@sonic:~$ redis-cli -n 6 KEYS "PORT_TABLE|*" | head
```

## SAI 失敗を見るときの順番

1. **syncd ログ** で `handleSai*Status` の失敗判定を確認する。fatal なら syncd は abort し、stack trace と dump が残る。

   ```bash
   admin@sonic:~$ docker exec syncd supervisorctl tail syncd \
     | grep -E "SAI_STATUS|handleSai"
   admin@sonic:~$ ls /var/log/syncd*.log
   ```

2. **ERROR_DB** に該当 object と SAI status code が出ているかを確認する。orchagent はここを購読して retry / 再構成の判断材料にする。

   ```bash
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
| `SAI_STATUS_TABLE_FULL` | [CRM](../../reference/glossary.md#term-crm) 枯渇（route、ACL、neighbor 等） | `crm show resources` でテーブル特定、scale を下げる / threshold を設定 |
| `SAI_STATUS_NOT_SUPPORTED` | ASIC が attribute / object を非対応 | platform 章 / SAI vendor 対応表を確認、機能無効化 |
| `SAI_STATUS_INVALID_PARAMETER` | orchagent が誤った attribute を渡した可能性 | orchagent ログで attribute 名特定、PR / issue 起票 |
| `SAI_STATUS_ITEM_ALREADY_EXISTS` | 同じ key の重複 install | warm boot 直後に多発するなら抑止、それ以外は orchagent の reconcile を疑う |
| `SAI_STATUS_OBJECT_IN_USE` | 削除順序の誤り（依存先がまだ参照中） | orchagent の destroy 順を確認、retry で消えるか観察 |

## syncd dump と SAI 失敗時の自動採取

SAI 失敗は単発の状態ではなく、その時点の ASIC_DB と SAI 内部状態をセットで保全したいことが多い。syncd には `syncd_dump.sh` と SAI 通知（`SAI_REDIS_NOTIFY_SYNCD_INVOKE_DUMP`）を組み合わせ、失敗時に dump を自動採取する仕組みがある。crash を待たずに状態を残せるため、再現が困難な間欠失敗の原因切り分けに使える。

手動採取の例:

```bash
admin@sonic:~$ sudo docker exec syncd syncd_dump.sh
admin@sonic:~$ ls /var/log/syncd/
sairedis.rec.gz  asic_db.json  saidump.txt
```

採取の仕掛けと出力場所は [SAI 失敗時の dump 取得](../../platform/dump-on-sai-failure.md) を読む。

## dump utility による DB 横断調査

機能の不具合切り分けでは、ある port や [VRF](../../reference/glossary.md#term-vrf) に紐づく key が `CONFIG_DB`、`APPL_DB`、`STATE_DB`、`ASIC_DB` に同時に存在することを確認したい。dump utility は「モジュール（例: port、vrf）」を起点に複数 DB から関連 key を集約する CLI で、内部実装の経路を辿る作業を簡略化する。

```text
admin@sonic:~$ sonic-db-dump -n CONFIG_DB -k "PORT|Ethernet0" -y
admin@sonic:~$ dump state port Ethernet0
admin@sonic:~$ dump state vlan Vlan1000
```

使い方と拡張規約は [dump utility（モジュール単位で複数 DB から関連 key を集約する debug CLI）](../../internals/dump-utility-for-easy-debugging.md) を読む。

## debug framework

各 daemon は debug 情報の dump 関数を Debug Framework に登録し、`show techsupport` や障害時の自動採取から一括で取得できるようにする。assert 拡張により、想定外状態を「ログだけ残して動作継続」か「停止」かを切り替えやすくする。

```bash
admin@sonic:~$ sudo show techsupport --since "1 hour ago"
admin@sonic:~$ ls /var/dump/
sonic_dump_<hostname>_<timestamp>.tar.gz
```

techsupport を解凍すると、各 docker の `supervisor` ログ、redis 全 DB の snapshot、`syncd_dump.sh` の出力、syslog、journal、kernel dmesg がまとまっている。

詳細は [Debug Framework（コンポーネント dump 登録 / assert 拡張）](../../architecture/debug-framework-in-sonic.md) を読む。

## health-check と system ready

`docker exec ... monit` ベースの単発 probe ではなく、container 内で複数の検査結果を 1 つの readiness に集約することで、k8s 上の SONiC で正確な readiness を得る。これは container 単位の運用観察。全体起動状態は別途 `system ready`（sysmonitor）が、per-app の closest UP status を event 集約して判定する。

```bash
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

```bash
admin@sonic:~$ docker exec syncd ls -lh /var/log/syncd/sairedis.rec*
admin@sonic:~$ docker exec syncd tail -50 /var/log/syncd/sairedis.rec
```

行頭の `c|`（create）、`s|`（set）、`r|`（remove）、`g|`（get response）、`n|`（notification）を読めば、orchagent から SAI への呼び出しと、SAI が返した OID / status が辿れる。`saidump` と組み合わせて、失敗直前のオブジェクト群を再構築する用途にも使える。

## orchagent の event loop が詰まったとき

オペレーション全般が遅い・反映されないときは、orchagent の event queue が詰まっているケースを疑う。

```bash
admin@sonic:~$ docker exec swss top -bn1 -p $(pidof orchagent)
admin@sonic:~$ docker exec swss supervisorctl tail orchagent | grep -i "queue"
admin@sonic:~$ redis-cli -n 0 LLEN "_*"
```

- CPU が貼り付いている: 設定流入が多すぎる、無限 retry に陥っている可能性。`ERROR_DB` を見る。
- queue 長が増えている: APPL_DB の subscribe を捌けていない。orchagent の単一スレッド設計上、SAI 呼び出しが遅いと全部詰まる。

並列性の改善は orchagent 周辺の internals ドキュメント群を参照する。

## saidump のスケール限界

`saidump` は ASIC_DB の全 key を [Redis](../../reference/glossary.md#term-redis) の Lua スクリプト（`Table::dump()`）で一括取得するため、40K route 規模になると数分以上かかる場合がある。Lua スクリプトの実行は Redis のシングルスレッドをブロックするため、dump 中は他の redis 操作も遅延する（issue #918）。

回避策:
- dump 対象を絞る: `redis-cli -n 1 KEYS "ASIC_STATE:SAI_OBJECT_TYPE_ROUTE*" | wc -l` で規模を確認してから採取。
- 規模が大きい環境では `sairedis.rec` を代替手段にし、dump は障害直後の最小状態で採取する。
- `show techsupport` 内の saidump は `--no-saidump` オプション（利用できる版）で省略可能。

## syncd 単体 restart の落とし穴

`sudo systemctl restart syncd` を実行すると、syncd が再起動後に `applyView` でスイッチ数の不一致エラーを起こすことがある：

```
applyView: condition current view switches: 0 != temporary view switches: 1
```

これは orchagent が `INIT_VIEW` → `APPLY_VIEW` を通知する前に syncd が再起動完了してしまい、syncd 側の「current view」が空になるためである（issue #639）。

現状の回避策:
- `syncd` 単体を restart するのではなく、**`sudo config reload`** や **swss docker 全体の restart** を行う。
- `syncd` restart は swss とセットで行わないと reconcile が成立しない設計になっている。

## cold boot 中の FDB event による orchagent crash

cold boot 時に、port が admin UP 状態でフォワーディングが始まる前に [FDB](../../reference/glossary.md#term-fdb) エントリが学習されると、orchagent (portsorch) の初期化シーケンスで問題が発生する（issue #1267、SONiC 202205 で報告）：

1. FDB 学習が default port bridge ID の参照カウントをインクリメント
2. `removeDefaultBridgePorts` が参照カウント > 0 で `SAI_STATUS_OBJECT_IN_USE` を返す
3. `portsorch` が異常終了（orchagent crash）

診断ポイント:
- `show interface status` で cold boot 直後に port が up になっていないか確認する。
- syslog で `removeDefaultVlanMembers` / `removeDefaultBridgePorts` 付近の SAI_STATUS を確認する。
- 理論上、cold boot では全 port が down 状態から始まるべきであり、port up notification が来ている場合は SAI または platform 側の問題を疑う。

## saidump の JSON parse error（show techsupport 時）

`show techsupport` または `saidump` 実行時に以下のようなエラーが出る場合がある（issue #1387）：

```
ERR syncd#saidump: :- dumpFromRedisRdbJson: JSON file /var/run/redis0/dump.json is invalid.
ERR syncd#saidump: :- dumpFromRedisRdbJson: JSON parsing error: unexpected end of input
```

原因: Redis の RDB dump ファイルが truncate されているか、saidump 実行時点でまだ書き込み中である。

対処:
1. `redis-cli SAVE` を手動で実行してから再試行する。
2. `dump.json` のサイズが 0 か極端に小さい場合は、Redis プロセスが正常稼働しているか確認する。
3. `show techsupport` の出力は JSON parse error があっても他の情報を含むため、tar.gz 自体は採取できる。

## VS（virtual switch）環境の既知動作差異

- **oper status 更新遅延**: admin down しても VS では port の oper status がしばらく `up` のまま残る場合がある。これは VS の tap device 経由でのリンク状態反映が実機の netlink と異なるためである（issue #555、PR #603 で修正済）。現行 master では解消しているが、古い image では発生する。
- **netlink message 受信の問題**: syncd-vs は起動直後の netlink dump は受け取れるが、その後の incremental link event を見失うことがある（issue #1357）。VS でのデータプレーン検証は制限付きと理解した上で使う。

## 関連ページ

- [SAI 失敗ハンドリング（handleSai*Status virtual + ERROR_DB）](../../platform/hld-for-handling-sai-failures.md)
- [Error Handling Framework（ERROR_DB / SAI 失敗の app への伝搬）](../../architecture/error-handling-framework-in-sonic.md)
- [SAI 失敗時の dump 取得（syncd_dump.sh / SAI_REDIS_NOTIFY_SYNCD_INVOKE_DUMP）](../../platform/dump-on-sai-failure.md)
- [dump utility（モジュール単位で複数 DB から関連 key を集約する debug CLI）](../../internals/dump-utility-for-easy-debugging.md)
- [Debug Framework（コンポーネント dump 登録 / assert 拡張）](../../architecture/debug-framework-in-sonic.md)
- [コンテナ health-check（k8s readiness probe）](../../internals/why-need-health-check.md)
- [System Ready（sysmonitor + per-app closest UP status の event 集約）](../../system/system-ready-hld.md)
- [Build / Packaging 章](../19-build-packaging/index.md)（FEATURE / [hostcfgd](../../reference/glossary.md#term-hostcfgd) との関係）
- [SRv6 / MPLS 章](../17-srv6-mpls/operations.md)（SAI 失敗の実例）

<!-- glossary-links-injected: 16a3bb018bc2 -->
