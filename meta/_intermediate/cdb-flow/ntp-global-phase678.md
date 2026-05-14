# NTP_GLOBAL — Phase 6/7/8 中間ファイル

生成日: 2026-05-14 (batch cdb_batch_3)

<!-- derivation -->
## Phase 6: 自動派生代入スキャン

### 全ソース — 該当なし

minigraph.py は NTP_SERVER を生成するが NTP_GLOBAL への代入はなし。config_samples.py / db_migrator.py / init_cfg.json.j2 も同様。NTP_GLOBAL は CLI で明示設定。

**結論**: Phase 6 派生なし。

<!-- /derivation -->

<!-- derivation -->
## Phase 7: 条件付き manager/orch 登録

### hostcfgd — NtpCfg クラス

```python
# hostcfgd:1272  class NtpCfg(object)
# hostcfgd:2512
self.config_db.subscribe(swsscommon.CFG_NTP_GLOBAL_TABLE_NAME,
    lambda table, key, data: self.ntp_cfg.handler(table, key, data))
```

NtpCfg は **常時** 登録。条件付き登録なし。

<!-- /derivation -->

<!-- handler-branching -->
## Phase 8: manager メソッド内 early return / dispatch

### NtpCfg.handler() — 分岐

NTP_GLOBAL 変更時:
1. `src_intf` → `/etc/ntp.conf` 再生成
2. `vrf` → ntp サービス再起動
3. `authentication` → ntp key ファイル再生成

early return: テーブル名が NTP_GLOBAL / NTP_SERVER / NTP_KEY 以外 → 処理スキップ。

<!-- /handler-branching -->
