# mgmt-port — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`MGMT_PORT`

## 段階 1: Consumer 登録

- **hostcfgd** (`sonic-host-services/scripts/hostcfgd`): `MGMT_PORT` テーブルを `ConfigDBConnector` で購読。
- スレッド: hostcfgd メインループ内で `subscribe` コールバック登録。

## 段階 2: CFG → APPL 翻訳

- hostcfgd が `MGMT_PORT` エントリを受け取り、`/etc/network/interfaces.d/` 向け設定断片を `j2` テンプレートで生成。
- CFG→APP_DB への書き込みは行わない (カーネル直接設定)。

## 段階 3: APPL → SAI

- SAI 経由なし。`ifconfig`/`ethtool` を syscall で直接発行して eth0 の speed/MTU/admin_status を設定。
- 再起動時は `ifupdown2` が `/etc/network/interfaces` を読み込んでカーネル設定を復元。

## 段階 4: タイミング + 副作用

- CONFIG_DB への書き込み後、hostcfgd コールバックは数秒以内にカーネル設定を反映する。
- サービス再起動 (`systemctl restart networking`) が必要な場合もある。
- 副作用: eth0 admin down 時に SSH セッションが切断される可能性がある。
