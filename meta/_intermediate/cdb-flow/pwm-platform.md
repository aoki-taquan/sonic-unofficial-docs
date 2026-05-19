# WATERMARK_TABLE|TELEMETRY_INTERVAL — Phase H プラットフォーム差スキャンノート

対象エントリ: `CONFIG_DB WATERMARK_TABLE|TELEMETRY_INTERVAL`
Consumer: `WatermarkOrch::doTask(Consumer&)` → `handleWmConfigUpdate()`
スキャン範囲:
- `sonic-swss/orchagent/watermarkorch.cpp` 全行
- `sonic-swss/orchagent/orchdaemon.cpp:432-437,500`
- `sonic-swss/orchagent/main.cpp:997`

---

## getenv("platform") 分岐の有無

`watermarkorch.cpp` に `getenv("platform")` による ASIC 種別分岐は存在しない。`WATERMARK_TABLE|TELEMETRY_INTERVAL` の処理ロジック自体はプラットフォーム非依存。

---

## 構成・スイッチタイプ起因のプラットフォーム差

### fabric スイッチタイプ — WatermarkOrch が存在しない

`main.cpp:997` の分岐:

```cpp
else if (gMySwitchType != "fabric")
{
    orchDaemon = make_shared<OrchDaemon>(...);
}
```

`gMySwitchType == "fabric"` のとき `OrchDaemon` が生成されず、`orchdaemon.cpp:437` の `WatermarkOrch *wm_orch = new WatermarkOrch(...)` も実行されない。

| 構成 | WatermarkOrch | WATERMARK_TABLE 処理 |
|------|--------------|---------------------|
| 通常スイッチ / voq / chassis-packet / dpu | 存在 | 正常に interval 更新 |
| fabric スイッチ (`gMySwitchType == "fabric"`) | **存在しない** | **CONFIG_DB 書き込みは無効** |

fabric スイッチではウォーターマーク機能自体が存在しないため、telemetry interval 設定も意味を持たない。

### allPortsReady() ガード

`watermarkorch.cpp:56` / `watermarkorch.cpp:147`:

```cpp
if (!gPortsOrch->allPortsReady())
{
    return;
}
```

全フロントパネルポートが初期化完了するまで `doTask()` が early return する。これはスイッチタイプに関わらず適用されるが、VOQ / スーパーバイザー構成では初期化完了が遅れる場合がある。

### VOQ シャーシ — 挙動は通常スイッチと同一

`watermarkorch.cpp` に `gMySwitchType` 分岐は存在しない。VOQ シャーシでも `WATERMARK_TABLE|TELEMETRY_INTERVAL` の `interval` 更新は通常通り動作する。ただし PG watermark / queue watermark が実際にカウンタを収集するかは ASIC / ラインカード構成に依存する。

### multi-ASIC

`watermarkstat -n <namespace>` で namespace を指定すると当該 ASIC の `APPL_DB` に `WATERMARK_CLEAR_REQUEST` をパブリッシュする。`WATERMARK_TABLE|TELEMETRY_INTERVAL` の設定は各 ASIC namespace の orchagent が独立して読み取るが、telemetry タイマー周期は `watermarkcfg -c` / `CONFIG_DB` の書き込み側で各 ASIC に個別設定する必要がある（自動同期なし）。

---

## プラットフォーム差サマリ

| 差異点 | 条件 | WATERMARK_TABLE への影響 |
|--------|------|------------------------|
| WatermarkOrch 非存在 | `gMySwitchType == "fabric"` | CONFIG_DB 書き込みは無効（telemetry タイマーなし） |
| `doTask()` ブロック | 全ポート未 ready | interval 更新が遅延 |
| VOQ / multi-ASIC | 各構成 | 挙動は通常スイッチと同一（namespace 独立） |
| ASIC 種別 | ASIC 実装依存 | WATERMARK_TABLE 自体は影響なし（PG/Queue ウォーターマーク収集側に影響） |
