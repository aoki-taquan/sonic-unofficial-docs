# sonic-gnmi Issue Decisions

## #565: Default sonic-gnmi/ build failing due to go package "protoc-gen-gofast" [CLOSED]
**判定: SKIP** — ビルド環境問題（Go バージョン互換性）。実装ドキュメントに不要。

## #562: Enhance testing framework to use gNMIc for testing [OPEN]
**判定: DOC → docs/management/gnmi-testing-with-gnmic.md**
gNMIc を docker-ptf に組み込んで PTF テストを gNMIc ベースに移行する取り組み。テスト方法論として有用。

## #490: Unable to trigger azure pipeline jobs in sonic-gnmi of PR#485 [CLOSED]
**判定: SKIP** — CI/CD インフラ問題。ドキュメント化不要。

## #333: unable to perform SET, Translib write is disabled [OPEN]
**判定: DOC → docs/management/gnmi-translib-write-enable.md**
`ENABLE_TRANSLIB_WRITE=y` でビルドしないと gNMI SET が無効になる重要な設定事項。

## #272: First record does not look like a TLS handshake [OPEN]
**判定: DOC → docs/management/gnmi-tls-troubleshooting.md**（既存 gnmi-usage.md に統合可能）
TLS 設定ミスで発生するよくあるエラー。`-notls` フラグの使い分けを既存ページに追記。

## #153: OpenConfig API not working with SONIC OS [CLOSED]
**判定: SKIP** — 機能要求の一般的議論。クローズ済み。

## #20: gnmi set request error [OPEN]
**判定: DOC → #333 と同ページに統合**
Translib write 無効が原因の gNMI SET エラー。#333 と同内容。

## #26: Memory grows until OOM with slow telemetry collector and lots of data. [OPEN]
**判定: DOC → docs/management/gnmi-streaming-telemetry-pitfalls.md**
slow collector で dial-in telemetry のキューが溢れて OOM になる挙動。RESOURCE_EXHAUSTED エラーと reconnect 動作を説明。

## #34: What's the roadmap of sonic-telemetry [CLOSED]
**判定: SKIP** — 古いロードマップ質問。クローズ済み、内容なし。
