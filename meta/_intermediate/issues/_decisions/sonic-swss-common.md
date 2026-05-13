# sonic-swss-common Issue Decisions

## #653: Too many FD events on modifying PORT table in CONFIG_DB [CLOSED]
**判定: SKIP** — クローズ済み。CONFIG_DB テーブル変更時の FD イベント過多。内容なし。

## #603: hostcfgd blocks forever on SIGTERM during warm boot [CLOSED]
**判定: SKIP** — クローズ済み。pubsub.cpp の無限ループ修正。warm boot 既存ページでカバー済みの可能性大。

## #507: Why linkToDbNative must be called before linkToDb? [OPEN]
**判定: DOC → docs/internals/swss-common-db-link-ordering.md**
`linkToDbNative` → `linkToDb` の順序制約と、二重呼び出し時のクラッシュ原因。API 設計上の重要知見。内部実装理解に必要。

## #322: make database config optional [OPEN]
**判定: DOC → docs/internals/swss-common-database-config.md**（既存ページに追記）
database_config.json が必須になった経緯と `DEFAULT_UNIXSOCKET` 廃止。非公式コンテナイメージでの利用時の注意点。

## #236: Continuous ProducerStateTable del/set call may leave stale FV in table data [CLOSED]
**判定: SKIP** — クローズ済み。設計上の懸念としてトリアージ済み、対処内容不明。
