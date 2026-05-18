# gnmi-dialin Phase B — 書込み順依存調査メモ

調査日: 2026-05-18
対象ページ: `docs/reference/config-db/gnmi-dialin.md`
フェーズ: Phase B (書込み順依存)

## 調査対象ソース

| ファイル | リポジトリ | 役割 |
|---------|-----------|------|
| `dockers/docker-sonic-gnmi/supervisord.conf` | sonic-net/sonic-buildimage | supervisord 起動順序定義 |
| `dockers/docker-sonic-gnmi/gnmi-native.sh` | sonic-net/sonic-buildimage | CONFIG_DB 読み取りと telemetry 起動スクリプト |
| `dockers/docker-sonic-gnmi/start.sh` | sonic-net/sonic-buildimage | コンテナ起動前処理スクリプト |
| `telemetry/telemetry.go` | sonic-net/sonic-gnmi | gNMI サーバ Go バイナリ（TLS 動的リロード実装含む） |

## 起動シーケンス詳細

```
supervisord 起動
  ├─ rsyslogd (priority=1, dependent_startup=true)
  ├─ start.sh (priority=2, dependent_startup_wait_for=rsyslogd:running)
  │    └─ container_startup.py 実行
  │    └─ /var/sonic/config_status 生成
  ├─ gnmi-native.sh (priority=3, dependent_startup_wait_for=start:exited)
  │    ├─ sonic-cfggen -d -t telemetry_vars.j2 → GNMI|gnmi, GNMI|certs 読み取り
  │    ├─ sonic-db-cli CONFIG_DB hget DEVICE_METADATA|localhost subtype → SmartSwitch 判定
  │    ├─ sonic-db-cli CONFIG_DB hget MGMT_VRF_CONFIG|vrf_global mgmtVrfEnabled → VRF 判定
  │    └─ exec /usr/sbin/telemetry ${TELEMETRY_ARGS}
  └─ dialout.sh (priority=4, dependent_startup_wait_for=gnmi-native:running)
```

## 順序依存の証跡

### supervisord.conf

```ini
[program:start]
priority=2
dependent_startup_wait_for=rsyslogd:running

[program:gnmi-native]
priority=3
dependent_startup_wait_for=start:exited

[program:dialout]
priority=4
dependent_startup_wait_for=gnmi-native:running
```

### gnmi-native.sh の CONFIG_DB 読み取りタイミング

```bash
TELEMETRY_VARS=$(sonic-cfggen -d -t $TELEMETRY_VARS_FILE)  # 一括読み取り
LOCALHOST_SUBTYPE=`sonic-db-cli CONFIG_DB hget "DEVICE_METADATA|localhost" "subtype"`
MGMT_VRF_ENABLED=`sonic-db-cli CONFIG_DB hget "MGMT_VRF_CONFIG|vrf_global" "mgmtVrfEnabled"`
exec /usr/sbin/telemetry ${TELEMETRY_ARGS}  # フォアグラウンドで起動（戻らない）
```

スクリプトは `exec` で telemetry バイナリを置き換えるため、起動後の CONFIG_DB 変更は反映されない。

## 主要な発見

1. **設定変更は再起動が必要**: `gnmi-native.sh` は起動時に CONFIG_DB を 1 回読み取るだけ。以降の `GNMI|gnmi` / `GNMI|certs` 変更は `docker restart gnmi` が必要。

2. **TLS 証明書ファイルのみ動的リロード**: `telemetry.go` は `fsnotify` で証明書ファイルの変更を監視してリロードするが、証明書パス自体の変更はコンテナ再起動が必要。

3. **dialout の依存**: `dialout.sh` は `gnmi-native:running` を待つため、gNMI サーバが起動失敗した場合（不正な port 値等）は dialout も起動しない。

4. **CONFIG_DB 不在時のフォールバック**: `GNMI` テーブルが存在しない場合でもスクリプトはデフォルト値でサーバを起動する。CONFIG_DB への書込みは必須ではない。

5. **SmartSwitch / VRF は起動時スナップショット**: `DEVICE_METADATA` と `MGMT_VRF_CONFIG` は起動時に一度だけ読まれる。変更後はコンテナ再起動が必要。
