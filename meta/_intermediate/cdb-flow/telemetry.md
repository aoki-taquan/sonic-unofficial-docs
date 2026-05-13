# TELEMETRY 例外条件調査メモ

ソース: `sonic-gnmi/gnmi_server/server.go` (SHA: eb635b7679b260c3fd0786a6d0734fc8e82c9a22)

## 抽出した例外条件

1. **起動時読み取りのみ** — `telemetry` コンテナは起動時に CONFIG_DB の `TELEMETRY|certs` /
   `TELEMETRY|gnmi` を一回読み込む。実行中に変更してもコンテナ再起動なしには反映されない。

2. **ポートが 0 または未設定** — `config.Port <= 0` のとき TCP リスナーは作成されない。
   `UnixSocket` も未設定の場合、`"no listener configured: port must be > 0 or unix_socket must be set"` を
   返して `NewServer()` がエラーを返す。gNMI サーバは起動しない。

3. **TCP リスナー失敗時の縮退** — 指定ポートで listen できない場合
   `"Failed to open listener port <port>: <err>; disabling TCP listener"` を Warningf して
   TCP リスナーを無効化（Unix ドメインソケットのみで継続）。

4. **UDS リスナー失敗時の縮退** — Unix ドメインソケットの作成に失敗した場合
   `"Failed to listen on unix socket <path>: <err>; disabling UDS listener"` を Warningf して
   UDS を無効化（TCP のみで継続）。

5. **TLS 設定の不整合** — `server_crt` / `server_key` のどちらか一方のみ設定されている場合、
   `"server certificate or key file path is empty"` を返してエラーにする。
   証明書ファイルが存在しない場合も `"server certificate file stat error"` を返す。

6. **CA 証明書ファイル不在** — mTLS 設定時に `ca_crt` パスが存在しない場合
   `"CA certificate file not found"` を返してエラーにする。
