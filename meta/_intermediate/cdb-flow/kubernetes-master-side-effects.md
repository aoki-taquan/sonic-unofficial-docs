# kubernetes-master — Phase F 副次 DB 書込 調査ノート

## 調査対象

- `sonic-buildimage/src/sonic-ctrmgrd/ctrmgr/ctrmgrd.py`

## 調査結果サマリ

`ctrmgrd` が `KUBERNETES_MASTER` 設定変化に応じて書き込む副次 DB エントリは以下の通り。

### STATE_DB 書込

1. `KUBERNETES_MASTER|SERVER` (connected / update_time / ip / port)
   - `RemoteServerHandler.do_join()` / `do_reset()` → `set_db_entry()` (L413-414, L423, L435-437)
   - join 成功時: connected="true", ip, port, update_time
   - join 失敗 / reset 時: connected="false", update_time

2. `KUBE_LABELS|SET` (sonic_version / hwsku / deployment_type / worker.sonic/platform)
   - `set_node_labels()` → `mod_db_entry()` (L306-307)
   - do_join() 成功直後に呼ばれる (L440)

3. `KUBE_LABELS|SET` (<feat>_enabled)
   - `FeatureTransitionHandler.handle_update()` → `mod_db_entry()` (L505-506)
   - CONFIG_DB:FEATURE.<feat>.set_owner 変化時

4. `FEATURE|<feat>` (restart="true")
   - `restart_systemd_service()` → `mod_db_entry()` (L157-158)
   - サービス再起動判断時

### APPL_DB / ASIC_DB / FLEX_COUNTER_DB / COUNTERS_DB

- ctrmgrd は ProducerStateTable / NotificationProducer を保有しない
- SAI 非経由のため ASIC_DB / FLEX_COUNTER_DB への書込なし
- COUNTERS_DB 参照なし

## Evidence

- `ctrmgrd.py:157-158` restart_systemd_service
- `ctrmgrd.py:292-307` set_node_labels
- `ctrmgrd.py:411-414` set_db_entry for SERVER state
- `ctrmgrd.py:418-426` do_reset
- `ctrmgrd.py:429-455` do_join
- `ctrmgrd.py:505-506` mod_db_entry for KUBE_LABELS feat_enabled
- `ctrmgrd.py:659-681` LabelsPendingHandler.update_node_labels
