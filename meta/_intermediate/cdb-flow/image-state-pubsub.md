# image-state — Phase G 通信メカニズムスキャンノート

対象: `/etc/sonic/sonic_version.yml`
Consumer: なし（Redis pub/sub 不使用。ファイルシステム直読み）
スキャン範囲: sonic-py-common device_info.py、sonic-gnmi non_db_client.go、sonic-ctrmgrd ctrmgrd.py

---

## 結論: Redis pub/sub なし（ファイル直読みのみ）

`/etc/sonic/sonic_version.yml` は Redis テーブルではなくファイルシステム上の静的 YAML ファイルである。
Redis keyspace notification / ConsumerStateTable / SubscriberStateTable はいずれも関与しない。

| コンポーネント | 読み方式 | キャッシュ | 変更通知 |
|---|---|---|---|
| `get_sonic_version_info()` (Python) | `open()` + YAML parse | `sonic_ver_info` グローバル変数（プロセス永続） | なし |
| `non_db_client.go` (Go) | `os.ReadFile()` + YAML | `sync.Once` | なし（`InvalidateVersionFileStash()` はテスト用） |
| `ctrmgrd.py` | `get_sonic_version_info()` 経由 | 同上 | なし |

## 調査証跡

- `device_info.py:511-525`: `os.path.isfile()` チェック → `open()` → yaml.load → `sonic_ver_info` キャッシュ
- `non_db_client.go:302-336`: `sync.Once`ブロック内 `os.ReadFile(SONIC_VERSION_FILEPATH)` + YAML デシリアライズ
- `ctrmgrd.py:292-306`: `device_info.get_sonic_version_info()` 経由で `build_version` を取得し STATE_DB 書き込み（Kubernetes 環境のみ）
- sonic-swss / orchagent には `/etc/sonic/sonic_version.yml` を ConsumerStateTable / SubscriberStateTable で購読するコードなし（grep 0件）
