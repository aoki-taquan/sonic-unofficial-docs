# mgmt-vrf-config — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`MGMT_VRF_CONFIG`

## 段階 1: Consumer 登録

- **hostcfgd** (`sonic-host-services/scripts/hostcfgd`): `MGMT_VRF_CONFIG` テーブルを `ConfigDBConnector` で購読。

## 段階 2: CFG → APPL 翻訳

- hostcfgd が `mgmtVrfHandler` を呼び出し、`mgmt` VRF を作成または削除する。
- APP_DB への書き込みは行わない (カーネル直接操作)。

## 段階 3: APPL → SAI

- SAI 経由なし。`ip vrf add mgmt` / `ip vrf del mgmt` をシステムコールで実行。
- `/etc/iproute2/rt_tables` に mgmt VRF エントリを追加。

## 段階 4: タイミング + 副作用

- VRF 作成は即時 (カーネルコール)。eth0 を mgmt VRF に移すまでに一時的な接続断が生じる。
- 副作用: `mgmtVrfEnabled = true` 時に eth0 が mgmt namespace に移動。SSH 接続が一時的に切断される可能性。
