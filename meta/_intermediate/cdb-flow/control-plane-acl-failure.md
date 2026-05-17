# ACL_TABLE (CTRLPLANE) — Phase D 失敗挙動スキャンノート

対象テーブル: `ACL_TABLE` (type=CTRLPLANE)
Consumer: `caclmgrd` (`sonic-host-services/scripts/caclmgrd`)、`AclOrch` (`sonic-swss/orchagent/aclorch.cpp`)
スキャン範囲: `get_acl_rules_and_translate_to_iptables_commands()`、`check_and_update_control_plane_acls()`、`run()` ループ、`AclOrch::doAclTableTask()`、`doAclRuleTask()` の CTRLPLANE 分岐

---

## caclmgrd 側の失敗経路

### SET 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | 自動回復 | evidence |
|---|---|---|---|---|
| `type != CTRLPLANE` | `get_acl_rules_...:743` | そのテーブルをスキップ（iptables ルール未生成） | なし（type 訂正 + ACL 変更イベント待ち） | `caclmgrd:743` |
| `acl_service` が `ACL_SERVICES` 外（例: 未知サービス名） | `get_acl_rules_...:748` | `log_warning()` → そのサービスをスキップ | なし（有効サービス名に書き直すこと） | `caclmgrd:748-752` |
| `rule_props` が空 / None | `get_acl_rules_...:770` | `log_warning()` → `continue`（ルールスキップ） | なし（ACL_RULE 再 SET が必要） | `caclmgrd:769-771` |
| `PRIORITY` キー欠落 | `get_acl_rules_...:776` | `log_error()` → `continue`（ルールスキップ） | なし（ACL_RULE 再 SET が必要） | `caclmgrd:774-777` |
| ACL_RULE の SRC_IP / SRC_IPV6 / DST_IP / DST_IPV6 が全て空 | `get_acl_rules_...:812` | `log_warning()` → テーブル全スキップ | あり（IP 付きルール追加後の次回更新で回復） | `caclmgrd:780-815` |
| dst_ports が空（EXTERNAL_CLIENT でポートが解決できない） | `get_acl_rules_...:818` | `log_warning()` → テーブルスキップ | あり（L4_DST_PORT 追加後の次回更新で回復） | `caclmgrd:816-821` |
| iptables コマンド実行失敗（非ゼロ exit） | `run_commands():236` | `log_error()` → 次のコマンドへ（途中停止なし） | なし（後続コマンドは継続されるが部分未設定が残る） | `caclmgrd:226-238` |
| 子スレッドで例外発生 | `check_and_update_...:981-987` | `log_error()` → `thread_exceptions[ns]` に格納 | なし（メインループが SIGKILL を自身に送信） | `caclmgrd:981-987`, `caclmgrd:1200-1201` |
| ip_version 混在（IPv4 テーブルに IPv6 ルール混入） | `get_acl_rules_...:801-808` | `log_error()` → 混在ルールを `acl_rules` から除去 | なし（矛盾ルールは恒久スキップ） | `caclmgrd:801-808` |

### DEL 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | 自動回復 | evidence |
|---|---|---|---|---|
| ACL_TABLE DEL (SubscriberStateTable 通知) | `run():1268-1286` | テーブル全体の変更フラグを立て `update_control_plane_acls()` を実行 | あり（iptables を全フラッシュして再生成） | `caclmgrd:1268-1303` |
| ACL_RULE DEL → テーブル内 iptables ルール削除 | `run():1268-1286` | テーブル変更フラグを立て `update_control_plane_acls()` を実行 | あり（次回更新でそのルールが生成されなくなる） | `caclmgrd:1268-1303` |

---

## orchagent (AclOrch) 側の失敗経路 — CTRLPLANE 専用分岐

| 失敗条件 | 検出箇所 | 結果 | evidence |
|---|---|---|---|
| `ACL_TABLE` type=CTRLPLANE の SET | `doAclTableTask()` | `m_ctrlAclTables` に登録のみ。SAI API 呼び出しなし | `aclorch.cpp:4276` (CTRLPLANE 分岐) |
| `ACL_RULE` 対応テーブルが `m_ctrlAclTables` 内に存在 | `doAclRuleTask():5554-5561` | INFO ログ → `erase(it)` → 恒久スキップ | `aclorch.cpp:5554-5561` |
| `ACL_RULE` 対応テーブルが未登録（ACL_TABLE 先着前） | `doAclRuleTask():5563` | `it++` → 次 tick で再試行（ACL_TABLE 登録後に CTRLPLANE erase） | `aclorch.cpp:5563-5566` |

---

## 補足

- **caclmgrd の失敗は iptables 部分未設定で継続**: `run_commands()` は各コマンドを順番に実行し、失敗コマンドは `log_error()` を出すが後続コマンドは継続する。この設計により 1 ルールの iptables 登録失敗が全体をブロックしない一方、ACL 抜け穴が生じる可能性がある。
- **子スレッド例外はメインプロセスごと SIGKILL**: `check_and_update_control_plane_acls()` 内で未捕捉例外が発生すると `thread_exceptions[namespace]` に記録され、メインループの次サイクルで `os.kill(os.getpid(), signal.SIGKILL)` が呼ばれ caclmgrd 全体がクラッシュする。systemd の `Restart=always` により自動再起動される。
- **orchagent 側の自動回復**: CTRLPLANE ACL_RULE は orchagent で erase されるため、orchagent 側の失敗概念は実質「SAI 投入失敗」ではなく「認識した上でスキップ」に過ぎない。
