# radius — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`RADIUS / RADIUS_SERVER`

## 段階 1: Consumer 登録

- **hostcfgd**: `RADIUS` / `RADIUS_SERVER` テーブルを `ConfigDBConnector` で購読。

## 段階 2: CFG → APPL 翻訳

- hostcfgd の `radiusHandler` が PAM / AAA 設定ファイル (`/etc/pam.d/`, `/etc/freeradius/`) を更新し、認証デーモンを再起動。
- APP_DB への書き込みなし。

## 段階 3: APPL → SAI

- SAI 経由なし。RADIUS は SSH/コンソール認証のコントロールプレーン処理。

## 段階 4: タイミング + 副作用

- 設定反映は hostcfgd が PAM 設定を書き換えた直後から有効。既存 SSH セッションは影響なし (新規ログインから適用)。
- 副作用: RADIUS サーバが到達不能の場合は `auth_type=local` フォールバックの有無に注意。
