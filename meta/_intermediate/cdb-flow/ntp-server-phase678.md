# NTP_SERVER — Phase 6/7/8 中間ファイル

生成日: 2026-05-14 (batch cdb_batch_3)

<!-- derivation -->
## Phase 6: 自動派生代入スキャン

### minigraph.py — NTP_SERVER 自動生成

```
# minigraph.py:2646
results['NTP_SERVER'] = dict((item, {'iburst': 'on'}) for item in ntp_servers)
```

`ntp_servers` は minigraph XML の `<NtpServer>` タグから抽出 (L1434-L1452)。各サーバに `{'iburst': 'on'}` を自動設定。

### config_samples.py — NTP_SERVER 自動生成

```
# config_samples.py:190
data['NTP_SERVER'] = {ntp_server: {} for ntp_server in ntp_server_ips}
```

<!-- /derivation -->

<!-- derivation -->
## Phase 7: 条件付き manager/orch 登録

### hostcfgd — NtpCfg

```python
# hostcfgd:2514
self.config_db.subscribe(swsscommon.CFG_NTP_SERVER_TABLE_NAME, ...)
```

NTP_SERVER を NtpCfg が常時購読。条件付き登録なし。

<!-- /derivation -->

<!-- handler-branching -->
## Phase 8: manager メソッド内 early return / dispatch

### NtpCfg — NTP_SERVER ハンドラ分岐

| 操作 | 処理 |
|------|------|
| SET | `/etc/ntp.conf` に `server <ip> iburst` 追加 + ntpd リスタート |
| DEL | 該当 `server` 行削除 + ntpd リスタート |

early return: IP アドレスが不正フォーマット → エラーログして return。

<!-- /handler-branching -->
