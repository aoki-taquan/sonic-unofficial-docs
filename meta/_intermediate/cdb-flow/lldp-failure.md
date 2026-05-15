# LLDP / LLDP_PORT 失敗挙動 (Phase D)

intermediate for `docs/reference/config-db/lldp.md` Phase D block.

## 調査対象ソース

- `sonic-buildimage/dockers/docker-lldp/lldpmgrd`

---

## lldpmgrd の構造的特性

`lldpmgrd` は CONFIG_DB の `LLDP` / `LLDP_PORT` テーブルを**直接購読しない**。
購読対象は以下の 3 テーブルのみ:

| 購読テーブル | DB | 用途 |
|------------|-----|------|
| `PORT` | APPL_DB | ポート oper_status 監視 + portidsubtype/alias 設定 |
| `MGMT_INTERFACE` | CONFIG_DB | Management IP 変化検知 |
| `DEVICE_METADATA` | CONFIG_DB | hostname 変化検知 |

このため、`LLDP|GLOBAL` や `LLDP_PORT|<ifname>` の書き込みは **lldpmgrd に到達しない**。
lldp 設定の大部分は `lldpd.conf.j2` / `lldpdSysDescr.conf.j2` のコンテナ起動時展開に依存する。

---

## 失敗パス一覧

### 1. hostname 取得失敗 → LOG_WARN + no-op

`lldpmgrd:84-87` — `update_hostname()`:

```python
if not hostname:
    self.log_warning("Ignoring invalid hostname: '{}'".format(hostname))
    return
```

- ログ: `LOG_WARNING "Ignoring invalid hostname: ''"`
- 効果: `lldpcli configure system hostname` を発行しない。lldpd の hostname は前回値（または起動時デフォルト）のまま
- rollback: なし（lldpd への変更未発行）

### 2. `lldpcli configure system hostname` 失敗 → LOG_WARN + `self.hostname` 未更新

`lldpmgrd:90-96` — `update_hostname()`:

```python
if proc.returncode != 0:
    self.log_warning("Command failed '{}': {}".format(cmd, stderr))
else:
    self.hostname = hostname
```

- ログ: `LOG_WARNING "Command failed ['lldpcli', 'configure', 'system', 'hostname', <name>]: <stderr>"`
- 効果: `self.hostname` が更新されない。次回 DEVICE_METADATA 変化で再度 `update_hostname()` が呼ばれるが、値が変化しなければスキップ（`if not self.hostname == hostname` 条件）
- **retry なし**（次回の DB 変化イベントまで再試行しない）

### 3. `lldpcli configure system ip management pattern` 失敗 → LOG_WARN + `self.mgmt_ip` 未更新

`lldpmgrd:109-114` — `update_mgmt_addr()`:

```python
if proc.returncode != 0:
    self.log_warning("Command failed '{}': {}".format(cmd, stderr))
else:
    self.mgmt_ip = ip
```

- ログ: `LOG_WARNING "Command failed ['lldpcli', 'configure', 'system', 'ip', 'management', 'pattern', <ip>]: <stderr>"`
- 効果: `self.mgmt_ip` が更新されない。lldpd が広告する Management Address TLV が変化しない
- **retry なし**

### 4. ポートが oper_status=down → pending_cmds キューイング（遅延）

`lldpmgrd:176-179` — `process_pending_cmds()`:

```python
if not self.is_port_up(port_name):
    self.log_info("port %s is not up, continue" % port_name)
    continue
```

- ログ: `LOG_INFO "port <ifname> is not up, continue"`
- 効果: lldpcli コマンドを発行せず `pending_cmds` に残す。10 秒ごとのメインループで再チェック
- **STATE_DB への記録なし**。ポートが up になれば自動再発行

### 5. `lldpcli configure ports` コマンド失敗 → RETRY_LIMIT=5 回 + silent drop

`lldpmgrd:193-200` — `process_pending_cmds()`:

```python
if port_item['failed_count'] >= RETRY_LIMIT:
    self.log_error("Command failed '{}': {} - command was failed {} times, disabling retry"
                   .format(cmd, stderr, RETRY_LIMIT+1))
    to_delete.append(port_name)
else:
    self.pending_cmds[port_name]['failed_count'] += 1
    self.pending_cmds[port_name]['failed_timestamp'] = time.time()
    self.log_info("Command failed '{}': {} - cmd failed {} times, retrying again"
                  .format(cmd, stderr, self.pending_cmds[port_name]['failed_count']))
```

- retry 間隔: `FAILED_CMD_TIMEOUT = 6` 秒
- retry 上限: `RETRY_LIMIT = 5`（5 回超過で **silent drop**)
- ログ成功時: なし（debug ログのみ）
- ログ失敗継続中: `LOG_INFO "cmd failed N times, retrying again"`
- ログ上限超過: `LOG_ERROR "command was failed N times, disabling retry"`
- 効果: 上限超過後、当該ポートの `portidsubtype local <alias>` / `description` が lldpd に未反映のまま継続。そのポートは誤った portid を広告し続ける
- **rollback なし**。STATE_DB への記録なし

### 6. `lldpcli resume` 失敗 → LOG_ERROR + `sys.exit(1)`

`lldpmgrd:340-341` — `run()`:

```python
if rc != 0:
    self.log_error("Failed to resume lldpd with command: 'lldpcli resume': {}".format(stderr))
    sys.exit(1)
```

- ログ: `LOG_ERROR "Failed to resume lldpd with command: 'lldpcli resume': <stderr>"`
- 効果: `lldpmgrd` プロセスが **`sys.exit(1)` で即終了**。`supervisord` が再起動を試みる
- 影響: lldpd が `pause` 状態のまま LLDP PDU を送出しない。`resume_lldp_sent = False` のため再起動後に再試行される

### 7. PORT_INIT_TIMEOUT (300 秒) 超過かつフロントエンドポートあり → LOG_ERROR + 強制 resume

`lldpmgrd:363-368` — `check_timeout()`:

```python
if time.time() - start_time > PORT_INIT_TIMEOUT:
    if device_info.is_frontend_port_present_in_host():
        self.log_error("Port init timeout reached ({} seconds), resuming lldpd...".format(PORT_INIT_TIMEOUT))
    return True
```

- ログ: `LOG_ERROR "Port init timeout reached (300 seconds), resuming lldpd..."`
- 効果: `PortInitDone` / `PortConfigDone` を強制 True にして `lldpcli resume` を発行。ポート設定が未完了でも LLDP PDU 送出を開始するため、一部ポートが誤った portid を広告する可能性がある
- **フロントエンドポート不在の場合**: `is_frontend_port_present_in_host()` が `False` → ログ出力なしで `return True`（silent timeout）

### 8. LLDP/LLDP_PORT フィールドへの書き込み → lldpmgrd に通知されない (構造的 no-op)

`lldpmgrd` は `LLDP` / `LLDP_PORT` テーブルを購読しないため:

- `redis-cli hset 'LLDP|GLOBAL' hello_time 10` → CONFIG_DB に書けるが lldpd に反映されない
- `redis-cli hset 'LLDP_PORT|Ethernet0' enabled false` → 同上
- `config lldp ...` CLI → sonic-utilities が CONFIG_DB を更新するが、lldpmgrd はそれを受信しない
- **エラーログなし**（構造的にイベントが発生しないため）

---

## retry / recovery まとめ

| 失敗種別 | retry | 上限 | 間隔 | recovery 条件 |
|---------|-------|------|------|--------------|
| hostname 更新 lldpcli 失敗 | なし | — | — | 次回 DEVICE_METADATA 変化 |
| mgmt IP 更新 lldpcli 失敗 | なし | — | — | 次回 MGMT_INTERFACE 変化 |
| portidsubtype lldpcli 失敗 | あり | 5 回 | 6 秒 | 5 回超過で silent drop |
| ポート down による遅延 | 自動 | なし | 10 秒ループ | ポート up 検知 |
| lldpcli resume 失敗 | supervisord 再起動 | — | — | lldpmgrd 再起動後 |
| LLDP/LLDP_PORT テーブル書き込み | 構造的 no-op | — | — | なし（設計上未購読） |

---

## STATE_DB / ERROR_TABLE への記録

- lldpmgrd は `STATE_DB` / `ERROR_TABLE` への書き込みを行わない
- lldp の neighbor 情報は `lldp-syncd` が `STATE_DB` の `LLDP_ENTRY_TABLE` に書き込む（lldpmgrd とは別プロセス）
- 失敗時のステータス記録はなし
