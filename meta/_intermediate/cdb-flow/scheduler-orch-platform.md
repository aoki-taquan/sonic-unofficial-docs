# scheduler-orch Phase H (platform) — 調査メモ

## ソース
- `sonic-swss/orchagent/qosorch.cpp` @ 4305596156d70e9797e8a881b3d19b46de0bce0d
  - `handleSchedulerTable()` L1347–1509: platform 条件分岐ゼロ
  - `applySchedulerToQueueSchedulerGroup()` L1630–1703: `gMySwitchType == "voq"` チェックあり（QUEUE → SCHEDULER バインド時）
  - `handleQueueTable()` L1750–: `gMySwitchType == "voq"` チェックあり（リモートシステムポートスキップ）
- `sonic-swss/orchagent/qosorch.h` @ 同 ref: platform 定数参照なし

## 結論

`handleSchedulerTable()` 自体には ASIC ベンダー / `platform` / `sub_platform` に依存するコード分岐が存在しない。
プラットフォーム差は SAI 層での暗黙サポート有無という形で間接的に現れる。

### VoQ 差異（唯一の switchType 分岐）

`applySchedulerToQueueSchedulerGroup()` の冒頭で `gMySwitchType == "voq"` を確認し、
リモートシステムポート宛のキューに対しては SAI スケジューラグループへのバインドをスキップする。
SCHEDULER オブジェクト自体の作成（SAI `create_scheduler()`）は VoQ モードでもスキップされない。

### SAI 暗黙サポート差異

SCHEDULER テーブルの各フィールドは SAI 属性として直接投入されるため、
ASIC が特定のスケジューリングアルゴリズムや帯域制御属性をサポートしない場合、
SAI 側で `SAI_STATUS_NOT_SUPPORTED` を返し orchagent が `task_failed` 相当のエラーを記録する。

- `type=DWRR`: Marvell-Prestera 等の一部 ASIC では未サポートの場合あり
- `type=STRICT`: 全段 Strict Priority を SAI レベルで禁じる ASIC あり
- `cir/pir/cbs/pbs`: 帯域制御系は ASIC モデルにより未実装の SAI 属性がある

## Phase H ブロック記述方針

コード側に platform 分岐がないため「実装コードは ASIC 非依存、差は SAI 層」という構成で記述する。
