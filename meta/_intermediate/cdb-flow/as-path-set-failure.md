# AS_PATH_SET — Phase D 失敗挙動スキャン

ソース:

- `sonic-net/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_as_path.py` (全 67 行)
- `sonic-net/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/config.py` (`ConfigMgr.push/commit`)
- `sonic-net/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/frr.py` (`FRR.get_config/write`)
- `sonic-net/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/manager.py` (`Manager.handler` retry セマンティクス)
- `sonic-net/sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` (`hdl_aspath_set`, `g_run_command`, `run_command`, vtysh client)

## bgpcfgd 経路 (AsPathMgr — DEVICE_METADATA 経由の T2_GROUP_ASNS)

| # | 失敗条件 | 検出箇所 | 結果 / ログ | retry? | evidence |
|---|---|---|---|---|---|
| B1 | `key != "localhost"` (例: 他ホスト name) | `managers_as_path.py:31,61` | `return True` で **silent drop**。ログなし、`set_queue` にも積まれない | なし (True 返却なので再投入対象外) | `managers_as_path.py:30-32, 60-62` |
| B2 | `data` に `t2_group_asns` キーなし | `managers_as_path.py:34-37` | `asns=None` → `new_asns=set()` のまま既存 ASN を **全削除** (差分が old - {} = old 全件) | n/a (正常パスとして処理される) | `managers_as_path.py:33-41, 51-53` |
| B3 | `t2_group_asns` 値が空文字 `""` | `managers_as_path.py:40` | `"".split(",")` → `[""]` → `new_asns={""}`。`""` は old に無く既存 ASN 全削除 & `permit __` を 1 本 push (FRR 側で構文エラー) | なし (push 段階で発覚) | `managers_as_path.py:38-41` |
| B4 | `re.compile` で `bgp as-path access-list T2_GROUP_ASNS seq \d+ permit _(\d+)_` がマッチしない (FRR 出力フォーマット変化) | `managers_as_path.py:43-49` | `old_asns={}` → 既存削除フェーズスキップ → 重複エントリが FRR 側に残存 (silent leak) | なし | `managers_as_path.py:43-49` |
| B5 | `cfg_mgr.update()` が vtysh 取得失敗 | `frr.py:33-38` (`get_config`) | `log_crit` 出力 & 空文字列返却 → `get_text()` 空 → 既存削除全スキップ。`set_handler` は **True を返す**ため queue 再投入なし | なし | `frr.py:33-38`, `config.py:17-29`, `managers_as_path.py:45-46` |
| B6 | `cfg_mgr.push()` 後の `commit()` で `vtysh -f` が失敗 (FRR daemon 不在等) | `frr.py:43-55` (`write`) | `log_err` で tempfile/rc/stderr 出力。**ファイル削除は g_debug=False 時のみスキップで残存**。`commit()` は False 返却するが、AsPathMgr.set_handler は `cfg_mgr.push()` の戻り (`True`) しか確認していないため気付かない | なし | `frr.py:43-55`, `config.py:38-44, 53-63` |
| B7 | `AsPathMgr.set_handler` が `return True` 固定 | `managers_as_path.py:58, 66` | FRR commit 失敗・vtysh 不在・上記いずれの異常でも **常に成功扱い**。`Manager.handler` の retry キュー (`set_queue`) には載らない | **retry なし**(構造的) | `managers_as_path.py:58, 66`, `manager.py:43-46` |
| B8 | `del_handler` 呼び出し時に `cfg_mgr.push("no ...")` が後段 commit で失敗 | `managers_as_path.py:65` | push 自体は changes バッファに積むのみで True。次の commit 周期で vtysh 失敗時 `log_err` のみ。再試行なし | なし | `managers_as_path.py:65`, `config.py:38-44` |

### bgpcfgd 経路の retry 設計

- `Manager.handler` (`manager.py:43-46`) は `set_handler` が **False** を返したときのみ `set_queue` に保留し、依存変化 (`on_deps_change`) で再評価する。AsPathMgr は常に True を返すため **失敗の遡及的リトライ機構なし**。
- AsPathMgr の唯一の retry 契機は CONFIG_DB 上の `DEVICE_METADATA|localhost.t2_group_asns` を **再 SET** する外部操作のみ。

## frrcfgd 経路 (AS_PATH_SET テーブル全般)

| # | 失敗条件 | 検出箇所 | 結果 / ログ | retry? | evidence |
|---|---|---|---|---|---|
| F1 | `args` が 2 要素未満 (`name` と member list の一方不足) | `frrcfgd.py:1010-1011` | `return None` で cmd 生成スキップ → 上位 `run_command` が `'failed to get upd cmd from value'` を **LOG_ERR 出力**。FRR には何も送らない | なし (`status` 未更新で次回 startup スキャンで再評価) | `frrcfgd.py:1009-1011, 746` |
| F2 | `as_path_set_member` 空リスト (`len(args[1]) == 0`) | `frrcfgd.py:1016` | OP_DELETE 以外は ADD ループ自体に入らず、既に `no bgp as-path access-list <name>` (全削除) のみが cmd_list に残る → 結果として **silent な全消去** | n/a | `frrcfgd.py:1014-1019` |
| F3 | `vtysh -c "bgp as-path access-list <name> permit <regex>"` が rc != 0 (regex 構文不正等で FRR 側拒否) | `frrcfgd.py:763-766` | `g_run_command` が False 返却 → `syslog.LOG_ERR 'failed running FRR command: <cmd>'` & **以降の cmd を break で打ち切り**。`STAT_SUCC` は付与されず data エントリは未確定状態のまま | **同一 SET 内の後続コマンドのみスキップ。CONFIG_DB 側からの再 SET がない限り自動 retry なし** | `frrcfgd.py:753-768` |
| F4 | FRR bgpd client への socket 接続失敗 | `frrcfgd.py:186-198` | `retry_cnt > 100 or not main_loop` で諦め。初期化中は **最大 100 回 (100ms 間隔) リトライ**、main_loop 中なら **即座に諦め**て `failed to connect to frr daemon` LOG_ERR | あり(初期化中 100 回 / main_loop 中 0 回) | `frrcfgd.py:185-198` |
| F5 | bgpd socket への send/recv 失敗 (実行中切断) | `frrcfgd.py:263-271, 363-365` | `failed to send command to frr daemon` / `socket writing failed` LOG_ERR。`run_vtysh_command` が False → `g_run_command` False → F3 と同じく LOG_ERR + break | なし | `frrcfgd.py:263-271, 354-365` |
| F6 | bgpd 応答 ret_code != 0 (enable / vtysh コマンド失敗) | `frrcfgd.py:212-215, 356` | `enable command failed: ret_code=%d` / `failed running VTYSH command` LOG_ERR | なし | `frrcfgd.py:212-215, 354-357` |
| F7 | `ignore_fail=True` が指定された vtysh コマンド | `frrcfgd.py:52, 59, 760-762` | rc != 0 でも LOG_ERR を出さず **silent に成功扱い**。AS_PATH_SET の hdl は `tuple` を返さないため通常該当しないが、混在経路で発生し得る | n/a | `frrcfgd.py:47-60, 759-762` |
| F8 | `as_path_set_member` の regex が不正 (FRR が `% Invalid regular expression`) | FRR 側 | F3 と同じ経路。frrcfgd 側では **regex 構文を一切検証していない**。LOG_ERR にコマンド本体は出るが FRR 側の理由文字列は記録されない | なし | `frrcfgd.py:1016-1019, 763-765` |
| F9 | OP_DELETE で `as_set_name` が `daemon.as_path_set_list` に未登録 (存在しないセット名の DEL) | `frrcfgd.py:1014` | `if as_set_name in daemon.as_path_set_list` 条件で `no bgp as-path access-list` push せず → ADD ループも OP_DELETE で抑止 → cmd_list 空 → **vtysh 呼び出しなし**(silent skip)。LOG_ERR/WARN なし | n/a | `frrcfgd.py:1013-1019` |
| F10 | startup スキャン時 `'as_path_set_member' in entry` が False (member 欠落エントリ) | `frrcfgd.py:2251` | 該当 entry は `as_path_set_list` 未登録 → 以降の DEL 操作で F9 経路に流れる (silent skip) | n/a | `frrcfgd.py:2251` |
| F11 | `action: deny` を CONFIG_DB に投入 | `frrcfgd.py:1018`, `bgpd.conf.db.j2:16` | `'{} permit {}'` ハードコードのため **`action` キーは読まれず**、`permit` で送信される。CONFIG_DB と FRR 設定の意味的乖離 (deny は **silent drop ではなく silent override**) | n/a | `frrcfgd.py:1018`, `bgpd.conf.db.j2:16` |

### frrcfgd 経路の retry 設計

- 個別 vtysh コマンド rc != 0 時は **同一 SET 内の以降を break で打ち切る**だけで、CONFIG_DB 監視ループからの自動再試行はない (`frrcfgd.py:765-766`)。
- 失敗した entry は `STAT_SUCC` に昇格せず、次回フル スキャン (`frrcfgd` 再起動 / `'as_path_set_member' in entry` 再評価) でのみ再投入される (`frrcfgd.py:2251, 769-773`)。
- FRR daemon 接続自体は 100 回 (10 秒) まで再試行 (`frrcfgd.py:185-198`)。これは AS_PATH_SET 固有ではなく全テーブル共通。

## 共通: silent drop / silent override の分類

| 種別 | 該当ケース | 利用者影響 |
|---|---|---|
| silent drop (ログなし・無反映) | B1 (非 localhost key), F9 (存在しない DEL), F10 (member 欠落), B4 (regex マッチなしによる残骸) | 設定意図と実 FRR 状態の乖離。`vtysh -c "show ip as-path-access-list"` で要確認 |
| silent override | F11 (`action: deny` → `permit`) | YANG 上の意味と FRR 動作が異なる (Phase E でも DISCREPANCY として記載済み) |
| LOG_ERR + 後段スキップ | F1, F3, F5, F6, F8 | syslog (`/var/log/syslog`) 監視必須 |
| LOG_CRIT | B5 (vtysh `show running` 失敗) | get_config 失敗は重大。bgpcfgd の他 Manager にも波及 |

## 結論 (Phase D)

1. **retry 機構は構造的に弱い**。AsPathMgr は常に True を返す設計、frrcfgd は失敗時 break のみ。永続的な retry は CONFIG_DB 側の再 SET に依存する。
2. **silent drop が多い**: 4 ケース (B1, F9, F10, B4) で **ログを出さずに無反映**。運用上 `vtysh -c "show ip as-path-access-list"` と CONFIG_DB の照合が唯一の発見手段。
3. **regex 検証の責務はすべて FRR 側**: SONiC 側は構文・長さ・空文字を含めて一切検証していない。F3 / F8 経路でのみ LOG_ERR となる。
4. **`action: deny` は silent override** (Phase E で既出だが Phase D の文脈では「失敗ではなく仕様化された誤動作」として再分類)。

evidence: `managers_as_path.py:7,30-66`; `config.py:17-63`; `frr.py:33-55`; `manager.py:34-65`; `frrcfgd.py:47-60,185-198,263-271,354-365,1009-1020,2251,746,753-773`
