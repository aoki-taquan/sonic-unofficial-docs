# DOT1X / PAC テーブル — Phase D 失敗挙動 中間ファイル

生成日: 2026-05-18 (q67-f-batch203-next)
対象テーブル: `PAC_PORT_CONFIG_TABLE`, `HOSTAPD_GLOBAL_CONFIG_TABLE`
Consumer: `pacmgrd` (`sonic-pac/pacmgr/pacmgr.cpp`), `hostapdmgrd` (`sonic-pac/hostapdmgr/hostapdmgr.cpp`)

---

## SET 処理における失敗経路

### PAC_PORT_CONFIG_TABLE (pacmgrd)

| # | 失敗条件 | 検出箇所 | 結果 | ログ出力 |
|---|---------|---------|------|---------|
| 1 | ポートキーに `E` プレフィックスなし (`key.find("E") == npos`) | `processPacPortConfTblEvent()` L166 | `continue` でスキップ（DB エントリ無視） | `SWSS_LOG_NOTICE "Invalid key format..."` |
| 2 | `fpGetIntIfNumFromHostIfName()` 失敗（インタフェース未存在等） | `processPacPortConfTblEvent()` L172-174 | `continue` でスキップ（設定未反映） | `SWSS_LOG_NOTICE "Unable to get the internal interface number..."` |
| 3 | `port_control_mode` に無効値 | `doPacPortTableSetTask()` L227 | `WARN` ログのみ → DEF 値 (`force-authorized`) を使用して処理継続 | `SWSS_LOG_WARN "Invalid port control mode received: ..."` |
| 4 | `host_control_mode` に無効値 | `doPacPortTableSetTask()` L240 | `WARN` ログのみ → DEF 値 (`multi-host`) を使用して処理継続 | `SWSS_LOG_WARN "Invalid host control mode received: ..."` |
| 5 | `reauth_enable` に `true`/`false` 以外 | `doPacPortTableSetTask()` L251 | `WARN` ログのみ → DEF 値 (`false`) を使用して処理継続 | `SWSS_LOG_WARN "Invalid value received for reauth enable: ..."` |
| 6 | `reauth_period_from_server` に無効値 | `doPacPortTableSetTask()` L269 | `WARN` ログのみ → DEF 値 (`true`) を使用して処理継続 | `SWSS_LOG_WARN "Invalid option received for reauth period from server: ..."` |
| 7 | `port_pae_role` に無効値 | `doPacPortTableSetTask()` L291 | `WARN` ログのみ → DEF 値 (`none`) を使用して処理継続 | `SWSS_LOG_WARN "Invalid option received for port pae role: ..."` |
| 8 | `priority_list` に `dot1x`/`mab` 以外 | `doPacPortTableSetTask()` L314 | `WARN` ログのみ → DEF 値で処理継続 | `SWSS_LOG_WARN "Invalid option received for priority list: ..."` |
| 9 | `method_list` に無効値 | `doPacPortTableSetTask()` L340 | `WARN` ログのみ → DEF 値で処理継続 | `SWSS_LOG_WARN "Invalid option received for method list: ..."` |
| 10 | `authmgrPortControlModeSet()` が FAIL（新規エントリ時） | `doPacPortTableSetTask()` L358-360 | 内部 cache を DEF に戻して `return false` → `processDbEvent()` が `false` を返す | `SWSS_LOG_ERROR "Unable to set the authentication port control mode."` |
| 11 | `authmgrHostControlModeSet()` が FAIL（新規エントリ時） | `doPacPortTableSetTask()` L365 | DEF に戻して `return false` | `SWSS_LOG_ERROR "Unable to set the authentication host control mode."` |
| 12 | `authmgrPortReAuthEnabledSet()` が FAIL（新規エントリ時） | `doPacPortTableSetTask()` L372 | DEF に戻して `return false` | `SWSS_LOG_ERROR "Unable to set the authentication reauth enable."` |
| 13 | `authmgrPortControlModeSet()` が FAIL（既存エントリ更新時） | `doPacPortTableSetTask()` L458 | `return false` | `SWSS_LOG_ERROR "Unable to set the authentication port control mode."` |
| 14 | 各 `authmgr*Set()` が FAIL（既存エントリ更新時） | `doPacPortTableSetTask()` L474,490,514,530,546,562 | `return false` | 対応する SWSS_LOG_ERROR |

### HOSTAPD_GLOBAL_CONFIG_TABLE (pacmgrd)

| # | 失敗条件 | 検出箇所 | 結果 | ログ出力 |
|---|---------|---------|------|---------|
| 15 | DEL 操作 | `processPacHostapdConfGlobalTblEvent()` L1182 | `continue` で無視（DEL は非サポート） | `SWSS_LOG_WARN "Unexpected DEL operation on HOSTAPD_GLOBAL_CONFIG_TABLE, ignoring"` |
| 16 | `dot1x_system_auth_control` を `true` に設定後 `authmgrPortClientAuthStatusUpdate()` が失敗 | `processPacHostapdConfGlobalTblEvent()` L1175 | エラーログなし。`m_glbl_info.enable_auth` は更新済みのまま残る（状態不整合） | なし |

## return false の連鎖挙動

`doPacPortTableSetTask()` / `doPacPortTableDeleteTask()` が `false` を返すと、`processPacPortConfTblEvent()` L187 で `return false` が連鎖し、`processDbEvent()` が `false` を返す。このとき `pacmgr_main.cpp` の main ループは `pacmgr.processDbEvent(sel)` の戻り値を評価しない（`void` 相当の扱い）ため、pacmgrd プロセス自体は継続する。

ただし当該エントリの処理は中断され、同一バッチ内の後続エントリも処理されない（`for (auto entry : entries)` ループが `return false` で終了するため）。

## DEL 失敗経路

| # | 失敗条件 | 検出箇所 | 結果 | ログ出力 |
|---|---------|---------|------|---------|
| 17 | `authmgrPortInfoReset()` が FAIL | `doPacPortTableDeleteTask()` L616 | キャッシュがリセットされない（DEL 対象ポートの設定が残存）。`return true` は維持されるためエラー伝播なし | なし（`SWSS_LOG_ERROR` の明示記述なし） |

## STATE_DB / ERROR_TABLE への記録

`PAC_PORT_CONFIG_TABLE` / `HOSTAPD_GLOBAL_CONFIG_TABLE` の失敗に関する STATE_DB への書き込みはなし。障害情報は syslog のみに出力される。

```bash
# syslog 確認コマンド（swss コンテナ内）
journalctl -u swss | grep -i pacmgr
# または pac コンテナ内のログ
docker logs pac 2>&1 | grep -E "ERROR|WARN"
```

## 証跡

`sonic-buildimage/src/sonic-pac/pacmgr/pacmgr.cpp:140-200,218-345,355-415,444-565,613-665`
