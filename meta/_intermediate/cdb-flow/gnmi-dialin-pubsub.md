# gnmi-dialin pubsub 調査メモ (Phase G)

## 調査日: 2026-05-19
## 対象: sonic-net/sonic-gnmi, sonic-net/sonic-buildimage

## 結論

`GNMI|gnmi` / `GNMI|certs` テーブルに対する Redis Subscribe は存在しない。
起動スクリプト `gnmi-native.sh` が `sonic-cfggen -d` で起動時 1 回だけ読み取る。

## SubscriberStateTable / ConsumerStateTable の使用有無

- `grep -r "SubscriberStateTable\|ConsumerStateTable" sonic-gnmi/` → 0 件
- CONFIG_DB への Subscribe は一切なし
- `GNMI_CLIENT_CERT` は `Get_entry()` による直接ポーリングのみ

## fsnotify による証明書監視

`telemetry.go:434-448` で `fsnotify.Watcher` を作成し、証明書ファイルを監視。
ファイル変更時に `serverControlSignal` へ `ServerRestart` を送信 → gRPC サーバ再起動。

## STATE_DB 書込み

`connection_manager.go:32-61` で Subscribe RPC の開始/終了時に
`TELEMETRY_CONNECTIONS` Hash に `HSet` / `HDel` を行う（write-only、subscribe なし）。

## evidence

- sonic-net/sonic-buildimage:dockers/docker-sonic-gnmi/gnmi-native.sh:19-98 (ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)
- sonic-net/sonic-gnmi:telemetry/telemetry.go:434-476 (ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22)
- sonic-net/sonic-gnmi:gnmi_server/clientCertAuth.go:254-277 (ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22)
- sonic-net/sonic-gnmi:gnmi_server/connection_manager.go:32-61 (ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22)
