# auto-techsupport — 書込み順依存 (Phase B) 調査メモ

対象テーブル: `AUTO_TECHSUPPORT|GLOBAL` / `AUTO_TECHSUPPORT_FEATURE|<feature>`
ソース: `sonic-utilities/scripts/coredump_gen_handler.py` (82 行) / `sonic-utilities/scripts/techsupport_cleanup.py` (59 行) / 共有 `utilities_common/auto_techsupport_helper.py` / `sonic-buildimage/files/image_config/sysctl/90-sonic.conf`

## 順序依存の全体像

1. **boot/sysctl 段階**: `kernel.core_pattern` がカーネルに反映されるまで、coredump → `coredump-compress` パイプは起動しない。
2. **handler 進入条件チェック順**: GLOBAL `state` → FEATURE `state` → rate-limit。前段未充足は後段を全てスキップ。
3. **handler 内アクション順**: `handle_core_dump_creation_event()` (techsupport 起動 + STATE_DB 書込) → `handle_coredump_cleanup()` (古い core 削除)。同一プロセス内で必ずこの順。
4. **techsupport_cleanup 内順**: `cleanup_process()` (ファイル削除) → `clean_state_db_entries()` (STATE_DB から対応エントリ削除)。
5. **warm reboot**: 本 2 スクリプトおよび helper に `WARM_RESTART` / `warm-reboot` 参照は 0 hit。STATE_DB `AUTO_TECHSUPPORT_DUMP_INFO` は永続化されるため、warm reboot 後も rate-limit timestamp は引き継がれる。

## 起動順 (boot / kernel core_pattern)

- `90-sonic.conf:45` で `kernel.core_pattern=|/usr/local/bin/coredump-compress %e %t %p %P` を設定。
- `coredump-compress` は bash スクリプトで、gzip 圧縮後 `setsid python3 /usr/local/bin/coredump_gen_handler.py` をバックグラウンド起動。
- **依存**: sysctl 適用前にプロセスがクラッシュした場合、kernel は default pattern (`core`) を使うため `coredump_gen_handler.py` は呼ばれない。systemd の `systemd-sysctl.service` 完了前に critical process が落ちると techsupport が走らない経路がある。
- **依存**: `coredump-compress` 自体が存在しないと kernel pipe オープン失敗で core が落ちない。`sonic-utilities` の deb インストール完了が前提。

## CONFIG_DB 読取り順 (handler 進入条件)

`coredump_gen_handler.py` (entry: `main()` → `CriticalProcCoreDumpHandle.handle_core_dump_creation_event()`)

| 順 | 読取りキー | フィールド | 値による分岐 | 行 |
|---|---|---|---|---|
| 1 | `AUTO_TECHSUPPORT|GLOBAL` | `state` | `!= "enabled"` → syslog NOTICE 出して即 return。以降の FEATURE 読取りはスキップ | `coredump_gen_handler.py:47-49` |
| 2 | `trim_masic_suffix(container)` で multi-asic suffix を除去 | — | 同一 FEATURE エントリで multi-asic 全 instance を表現する前提 | `:52` |
| 3 | `AUTO_TECHSUPPORT_FEATURE|<feature>` | `state` | `!= "enabled"` → syslog NOTICE 出して return | `:54-58` |
| 4 | `invoke_ts_command_rate_limited()` 内で `AUTO_TECHSUPPORT|GLOBAL.rate_limit_interval` と `AUTO_TECHSUPPORT_FEATURE|<feature>.rate_limit_interval` を読取り | `rate_limit_interval` | rate-limit に該当すれば techsupport 起動せず exit | `auto_techsupport_helper.py:316-330` |

**重要**: GLOBAL が未設定 / `disabled` の場合、FEATURE 側がいくら `enabled` でも何も起動しない (GLOBAL kill switch)。逆に GLOBAL が `enabled` でも FEATURE エントリが存在しない / `disabled` のコンテナはスキップされる (per-feature kill switch)。`init_cfg.json.j2` 側で feature テンプレートを GLOBAL `state` に合わせて生成 (`infer_auto_ts_capability`) するため、通常運用では GLOBAL → FEATURE の伝搬が成立する。

`techsupport_cleanup.py` 側も同じ順で GLOBAL `state` → `max_techsupport_limit` を読取る (`:27`, `:32`)。GLOBAL `disabled` なら掃除も走らない。

## handler 内アクション順 (`coredump_gen_handler.py:main()`)

```
main(args):
  1. db.connect(CFG_DB); db.connect(STATE_DB)               # :70-71
  2. verify_recent_file_creation(/var/core/<name>)         # :73 — 古い core の再 invocation を遮断 (TIME_BUF=20s)
  3. CriticalProcCoreDumpHandle(...).handle_core_dump_creation_event()  # :76-77 — techsupport 起動 + STATE_DB hset
  4. handle_coredump_cleanup(args.name, db)                # :78 — /var/core の max_core_limit 超過分を削除
```

**順序の意味**:
- 段階 3 が techsupport 出力 (`/var/dump/sonic_dump_*.tar.gz`) を生成し、`invoke_ts_command_rate_limited()` 内で `write_to_state_db()` が `AUTO_TECHSUPPORT_DUMP_INFO|<ts_name>` を書き込む (`auto_techsupport_helper.py:302-310`)。
- 段階 4 が **直後に** `/var/core` の容量制限を評価する。**もし順序が逆だった場合**、たった今 trigger になった core ファイルを techsupport 採取前に削除してしまい、techsupport 内に core が含まれない事故が起きる。現実装は順序を厳格に守ることでこれを防いでいる。
- `handle_coredump_cleanup` は `/var/core` のみを操作し `/var/dump` には触れない。`/var/dump` 側の掃除は `techsupport_cleanup.py` が `generate_dump` から別途呼ばれる経路で行われる。

## techsupport_cleanup 内順 (`techsupport_cleanup.py:handle_techsupport_creation_event()`)

```
1. verify_recent_file_creation(/var/dump/<name>)            # :23 — 古い ts の重複起動を遮断
2. AUTO_TS state != enabled → return                        # :27 — GLOBAL kill switch 再確認
3. max_ts = AUTO_TS.max_techsupport_limit (float fallback)  # :32-36
4. removed_files = cleanup_process(max_ts, TS_PTRN_GLOB, TS_DIR)  # :43 — 物理ファイル削除を先行
5. clean_state_db_entries(removed_files, db)                # :44 — STATE_DB エントリを後追い削除
```

**順序の意味**: ファイル削除 → STATE_DB 削除 の順は意図的。
- もし STATE_DB 削除を先行すると、`cleanup_process` が失敗 (権限・FS エラー) した場合に **ファイルは残り STATE_DB エントリだけ消える** という不整合 (rate-limit 判定でファイル数だけ増えて見える状態) が起きる。
- 現順だとファイル削除失敗時に STATE_DB は手付かずで残り、次回起動で再試行が可能。

## warm reboot との関係

- `coredump_gen_handler.py` / `techsupport_cleanup.py` / `auto_techsupport_helper.py` を grep しても `WARM_RESTART` / `warm-reboot` / `warm_restart` の参照は **0 hit**。
- すなわち warm reboot 専用の停止/再開ロジックを持たず、kernel が継続稼働している以上 `kernel.core_pattern` も維持される。warm reboot 中に critical process が落ちた場合でも `coredump-compress` は通常通り起動する。
- ただし warm reboot 中は host service / container 再起動の関係で `AUTO_TECHSUPPORT_FEATURE|<feature>` の `state` が一時的に書き換わる可能性があり、その瞬間に core が落ちると skip される (副作用)。CONFIG_DB は warm reboot で保持されるため通常はそのまま。
- `AUTO_TECHSUPPORT_DUMP_INFO` は **STATE_DB に保存** され、STATE_DB は warm reboot 跨ぎで保持される (`auto_techsupport_helper.py` の `write_to_state_db` 経由)。rate-limit timestamp が warm reboot を跨いで尊重されるため、warm reboot 直後に再 trigger が連続発火することはない。

## 起動シーケンス図

```
[kernel boot]
  ↓
systemd-sysctl.service: 90-sonic.conf 適用
  → kernel.core_pattern=|/usr/local/bin/coredump-compress %e %t %p %P
  ↓
[critical process がクラッシュ]
  ↓
kernel が coredump-compress を pipe 起動 → /var/core/<pfx>core.gz 生成
  ↓
setsid python3 coredump_gen_handler.py <name> <container>
  ↓
db.get(CFG_DB, AUTO_TECHSUPPORT|GLOBAL, state)
   ├─ != enabled → 終了
   └─ == enabled
       ↓
       db.get(CFG_DB, AUTO_TECHSUPPORT_FEATURE|<container>, state)
        ├─ != enabled → 終了
        └─ == enabled
            ↓
            invoke_ts_command_rate_limited
             ├─ rate-limit hit → 終了
             └─ pass → show techsupport 起動 → /var/dump/sonic_dump_*.tar.gz
                   ↓
                   write_to_state_db(STATE_DB, AUTO_TECHSUPPORT_DUMP_INFO|<ts>)
                   ↓
[handler 復帰] → handle_coredump_cleanup → /var/core の max_core_limit 超過分削除
```

## 既知の落とし穴

- `kernel.core_pattern` が sysctl 適用前に upstream プロセスがクラッシュすると core 自体が flat な `core` ファイルとして書かれ、pipe 起動されない → techsupport も走らない。`systemd-sysctl.service` の `Before=` 関係を疑う必要がある。
- `coredump_gen_handler.py:73` の `verify_recent_file_creation` は `TIME_BUF=20s` 以内の作成を要求。NTP 巻き戻し / 時計ずれで false negative になり得る (`auto_techsupport_helper.py:69`)。
- handler が `setsid` でバックグラウンド起動されるため、`coredump-compress` 親プロセスが既に exit している。handler の exit status は kernel に伝わらないので失敗は syslog でしか観測できない。
- GLOBAL `state=enabled` + 全 FEATURE `state=disabled` の構成は文法上有効だが、techsupport が一切起動しないため検出が困難。`config auto-techsupport-feature enable <feature>` で個別有効化が必要。

## evidence 行ハイライト

- `sonic-utilities/scripts/coredump_gen_handler.py:17,22,47,55,77-78`
- `sonic-utilities/scripts/techsupport_cleanup.py:13-18,27,43-44`
- `sonic-utilities/utilities_common/auto_techsupport_helper.py:60-67,69-71,302-310,316-330`
- `sonic-buildimage/files/image_config/sysctl/90-sonic.conf:45,55`
- `sonic-utilities/scripts/coredump-compress` (全体 — bash wrapper)
