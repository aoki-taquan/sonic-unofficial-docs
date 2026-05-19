# KUBERNETES_MASTER — Phase F 副次 DB 書込 調査ノート

## 調査対象

- `sonic-buildimage/src/sonic-ctrmgrd/ctrmgr/ctrmgrd.py`
- 調査日: 2026-05-19

## 調査方法

`ctrmgrd.py` を `set(`, `hset(`, `ProducerStateTable`, `AppTable`, `APPL_DB`, `STATE_DB` でスキャンして副次書込みを全列挙。

## STATE_DB 書込み

### RemoteServerHandler.do_join() 成功時

`ctrmgrd.py:436-440`:
```python
st_server[ST_SER_CONNECTED] = "true"
st_server[ST_SER_UPDATE_TS] = datetime.now().isoformat()
st_server["ip"] = self.ip
st_server["port"] = self.port
```

`STATE_DB::KUBERNETES_MASTER|SERVER` に connected/update_time/ip/port を書き込む。

### RemoteServerHandler.do_reset() または join 失敗時

`ctrmgrd.py:423` (do_reset):
```python
st_server[ST_SER_CONNECTED] = "false"
```

`ctrmgrd.py:444` (join 失敗後):
```python
st_server[ST_SER_CONNECTED] = "false"
```

### set_node_labels() (join 成功後)

`ctrmgrd.py:297-307,440`:
- `STATE_DB::KUBE_LABELS|SET` に sonic_version, hwsku, deployment_type, worker.sonic/platform を書き込む
- `deployment_type` は `DEVICE_METADATA.localhost.type` から取得 (`ctrmgrd.py:297-299`)

### FeatureTransitionHandler (FEATURE.set_owner 変化時)

`ctrmgrd.py:505-506`:
- `STATE_DB::KUBE_LABELS|SET.<feat>_enabled = "true"` を書き込む

## CONFIG_DB 書込み

### restart_systemd_service()

`ctrmgrd.py:157-158`:
- `CONFIG_DB::FEATURE|<feature>.restart = "true"` を書き込む（サービス再起動が必要な場合）

## APPL_DB 書込み

なし。`ctrmgrd.py` 全体に ProducerStateTable / AppTable への書込みなし。

## SAI 書込み

なし。K8s 統合はホスト OS 処理で SAI を経由しない。
