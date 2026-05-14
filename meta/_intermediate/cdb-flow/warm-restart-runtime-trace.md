# warm-restart — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`WARM_RESTART`

## 段階 1: Consumer 登録

- **各サービス (swss, syncd, bgp 等)**: 起動時に `WARM_RESTART` テーブルを `ConfigDBConnector` で読み込む。
- **system_halt_app** / **warmboot-finalizer**: warm restart フロー全体を管理。

## 段階 2: CFG → APPL 翻訳

- 各サービスが `WARM_RESTART` テーブルの `enable` / `neighsyncd_timer` 等を読み込み、warm restart モードで起動するかを決定。
- STATE_DB `WARM_RESTART_TABLE` に現在の warm restart 状態を書き込む。

## 段階 3: APPL → SAI

- SAI: warm restart 時は syncd が `SAI_SWITCH_ATTR_WARM_BOOT_WRITE/READ_FILE` を使用して ASIC 状態を保存・復元する。
- swss / orchagent は warm restart 完了後に APP_DB を再生して SAI との整合を確認する。

## 段階 4: タイミング + 副作用

- warm restart の完了時間はサービス数・ルート数に依存。数十秒〜数分。
- 副作用: warm restart が失敗するとコールドリスタートにフォールバックし、トラフィックが完全断になる。
- STATE_DB `WARM_RESTART_TABLE` で各サービスの進捗を確認可能。
