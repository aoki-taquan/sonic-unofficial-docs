# tacplus-server — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`TACPLUS / TACPLUS_SERVER`

## 段階 1: Consumer 登録

- **hostcfgd**: `TACPLUS` / `TACPLUS_SERVER` テーブルを `ConfigDBConnector` で購読。

## 段階 2: CFG → APPL 翻訳

- hostcfgd の `tacplusHandler` が `/etc/tacplus_servers` / PAM 設定を更新し認証デーモンを再起動。
- APP_DB への書き込みなし。

## 段階 3: APPL → SAI

- SAI 経由なし。TACACS+ は SSH/コンソール認証のコントロールプレーン処理。

## 段階 4: タイミング + 副作用

- 設定変更は次回ログインから有効。既存 SSH セッションには影響なし。
- 副作用: TACACS+ サーバ到達不能時に `auth_type=local` フォールバックが必要。
