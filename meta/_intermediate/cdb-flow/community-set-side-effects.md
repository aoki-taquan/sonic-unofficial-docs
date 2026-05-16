# community-set — Phase F 副次 DB 書込スキャン (side-effects)

対象テーブル: `CONFIG_DB / COMMUNITY_SET`、`CONFIG_DB / EXTENDED_COMMUNITY_SET`
対象スクリプト:

- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/` (起動時テンプレートパス)

## スキャン結果

### FRR bgpd running-config への書込

`frrcfgd.BGPConfigDaemon` は `COMMUNITY_SET` / `EXTENDED_COMMUNITY_SET` テーブルを購読し、
`g_run_command()` → `BgpdClientMgr.run_vtysh_command()` 経由で `vtysh` コマンドを bgpd に送信する。

```python
# frrcfgd.py:47-62  g_run_command
def g_run_command(table, command, use_bgpd_client, daemons, ignore_fail=False):
    ...
    if not bgpd_client.run_vtysh_command(table, command, daemons) and not ignore_fail:
        syslog.syslog(syslog.LOG_ERR, 'command execution failure. Command: "{}"'.format(command))
        return False
    return True
```

`TABLE_DAEMON` マッピング (`frrcfgd.py:84-85`):

```python
'COMMUNITY_SET':          ['bgpd'],
'EXTENDED_COMMUNITY_SET': ['bgpd'],
```

`hdl_com_set` (`frrcfgd.py:981-1007`) が生成するコマンド:

| 条件 | 発行 vtysh コマンド |
|---|---|
| `set_type=standard`, `match_action=any`, member=`65000:100` | `bgp community-list standard <name> permit 65000:100` |
| `set_type=standard`, `match_action=all`, members=`[65000:100, 65000:200]` | `bgp community-list standard <name> permit 65000:100 65000:200` |
| `set_type=expanded`, `match_action=any`, member=`.*:100` | `bgp community-list expanded <name> permit .*:100` |
| `op=DELETE` | `no bgp community-list <type> <name>` |
| `EXTENDED_COMMUNITY_SET` | `bgp extcommunity-list ...`（同ハンドラ、`extended=True`） |

### CONFIG_DB / STATE_DB / APPL_DB への副次書込

0 件。`frrcfgd` は `COMMUNITY_SET` を読取専用で消費し、FRR bgpd running-config のみを更新する。

### bgpcfgd の役割

`bgpcfgd` は起動時に Jinja2 テンプレート (`bgpd.conf.db.comm_list.j2`) 経由で bgpd.conf を生成するが、
ランタイムの設定変更は `frrcfgd` が担う。`bgpcfgd` は `COMMUNITY_SET` をランタイムに vtysh 書込しない。

## 副次書込まとめ

| 副次書込先 | 操作 | キー/コマンドパターン | evidence |
|---|---|---|---|
| FRR `bgpd` running-config | SET | `bgp community-list {standard\|expanded} <name> permit <members>` | `frrcfgd.py:993-1006` |
| FRR `bgpd` running-config | DELETE | `no bgp community-list {standard\|expanded} <name>` | `frrcfgd.py:989-990` |
| FRR `bgpd` running-config | SET (ext) | `bgp extcommunity-list ...` | `frrcfgd.py:1975` |
| CONFIG_DB | なし | — | 読取専用 |
| STATE_DB | なし | — | ヒット 0 件 |
| APPL_DB | なし | — | ヒット 0 件 |

## 失敗時挙動

`g_run_command()` 失敗時は `syslog LOG_ERR` を出力して `continue`（再試行なし）。
FRR と CONFIG_DB の設定乖離が発生し得る。<!-- evidence: frrcfgd.py:47-62, 2879-2881 -->
