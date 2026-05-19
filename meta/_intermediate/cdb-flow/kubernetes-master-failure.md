# KUBERNETES_MASTER — 失敗挙動調査 (Phase D)

## 調査対象
- `sonic-buildimage/src/sonic-ctrmgrd/ctrmgr/ctrmgrd.py`
- `sonic-buildimage/src/sonic-ctrmgrd/ctrmgr/kube_commands.py`

## 調査日: 2026-05-19

---

## 1. kube_join_master 失敗 → JOIN_RETRY によるリトライ

`RemoteServerHandler.do_join()` (`ctrmgrd.py:429-455`):
- `kube_commands.kube_join_master(ip, port, insecure)` が非ゼロ ret を返した場合:
  - `st_server[ST_SER_CONNECTED] = "false"` を STATE_DB に書き込む
  - `remote_connected = False`
  - `datetime.timedelta(seconds=remote_ctr_config[JOIN_RETRY])` 後にタイマー登録 (`register_timer`)
  - `self.pending = True` でポーリングループを待機させる
- `JOIN_RETRY` のデフォルト値: **10 秒** (`ctrmgrd.py:113`)
- join 成功時のみ `STATE_DB:KUBERNETES_MASTER|SERVER.connected = "true"` に更新

## 2. kube_reset_master 失敗

`do_reset()` (`ctrmgrd.py:418-426`):
- `kube_commands.kube_reset_master(True)` の戻り値は無視する（`void` 扱い）
- reset 失敗は syslog にのみ出力される（`log_debug("kube_reset_master called")`）
- `st_server[ST_SER_CONNECTED]` は即 `"false"` に書き込まれる（kube_reset_master の成否にかかわらず）

## 3. kube_write_labels 失敗 → LABEL_RETRY によるリトライ

`LabelsPendingHandler.update_node_labels()` (`ctrmgrd.py:668-685`):
- `kube_commands.kube_write_labels(self.set_labels)` が非ゼロを返した場合:
  - `self.pending = True`
  - `remote_ctr_config[LABEL_RETRY]` 秒後にタイマー再登録
  - `LABEL_RETRY` のデフォルト値: **2 秒** (`ctrmgrd.py:114`)
- STATE_DB `KUBE_LABELS|SET` への書き込みは `kube_write_labels` 内部で行われる。失敗時は書き込み未完のまま retrying になる

## 4. DNS 解決失敗 (FQDN ip)

- `ip` フィールドに FQDN を設定した場合、`kube_join_master` 内部の kubelet 設定生成時に DNS 解決が試みられる
- 起動早期（DNS キャッシュ未熱）や DNS サービス未起動時は解決失敗 → `kube_join_master` 非ゼロ返却 → JOIN_RETRY ループへ

## 5. CONFIG_DB 変化検知中の select エラー

`ctrmgrd.py:273-275`:
```python
raise Exception("Received error from select")
```
select() が EINTR 以外のエラーを返した場合は例外送出 → ctrmgrd プロセス abort → systemd 再起動（自己回復）。

## 6. FEATURE reset-failed

`ctrmgrd.py:154`:
```python
subprocess.call(["systemctl", "reset-failed", str(feat)])
```
systemctl reset-failed は失敗してもプロセスを止めない（`subprocess.call` の戻り値を無視）。

## まとめ

| 失敗箇所 | 回復方式 | タイムアウト/リトライ間隔 |
|---|---|---|
| kube_join_master 失敗 | timer 再試行 | JOIN_RETRY (デフォルト 10s) |
| kube_reset_master 失敗 | ログのみ・connected=false 確定 | なし (再試行なし) |
| kube_write_labels 失敗 | timer 再試行 | LABEL_RETRY (デフォルト 2s) |
| select() エラー | ctrmgrd プロセス abort → systemd 再起動 | systemd restart delay |
| DNS 解決失敗 | JOIN_RETRY ループ | JOIN_RETRY (デフォルト 10s) |
