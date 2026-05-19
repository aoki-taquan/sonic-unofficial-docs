# stp-orch — Phase H プラットフォーム差分調査

## 結論

`StpOrch` は ASIC から `SAI_SWITCH_ATTR_MAX_STP_INSTANCE` を取得する 1 か所のみにプラットフォーム依存がある。orchdaemon はプラットフォーム条件なしで `gStpOrch` を常に登録し、multi-ASIC / VOQ chassis 分岐コードは存在しない。

## 根拠

### 1. 初期化時の SAI ASIC 能力取得

`stporch.cpp:28-42` で `StpOrch` コンストラクタは 2 属性をまとめて取得する:

```cpp
attr.id = SAI_SWITCH_ATTR_DEFAULT_STP_INST_ID;
attrs.push_back(attr);
attr.id = SAI_SWITCH_ATTR_MAX_STP_INSTANCE;
attrs.push_back(attr);
status = sai_switch_api->get_switch_attribute(gSwitchId, (uint32_t)attrs.size(), attrs.data());
if (status == SAI_STATUS_SUCCESS)
{
    m_defaultStpId = attrs[0].value.oid;
    updateMaxStpInstance(attrs[1].value.u32);
    ret = true;
}
```

取得成功時は `updateMaxStpInstance()` (`stporch.cpp:603-615`) が `m_maxStpInstance = max_stp_instances - 1` を計算し、`STATE_STP_TABLE|GLOBAL.max_stp_inst` に書き込む。`stpmgrd` はこの値をポーリングして実効上限として使用する。

**プラットフォーム差**: ASIC が報告する `SAI_SWITCH_ATTR_MAX_STP_INSTANCE` の値がプラットフォームごとに異なる。VS（仮想スイッチ）では SAI 取得が失敗する場合があり、その際は `m_defaultStpId` と `m_maxStpInstance` が未初期化のまま残る（`ret = false` ログのみ）。

### 2. orchdaemon への登録 — プラットフォーム条件なし

`orchdaemon.cpp:262-263`:

```cpp
gStpOrch = new StpOrch(m_applDb, m_stateDb, stp_tables);
gDirectory.set(gStpOrch);
```

`gMySwitchType` / `is_multi_npu()` / `isChassisDbInUse()` による条件分岐なし。すべてのプラットフォームで `StpOrch` は初期化される。

### 3. multi-ASIC / VOQ chassis

`stporch.cpp` には `is_multi_npu()` / `gMySwitchType` / `CHASSIS_APP_DB` / `asicN namespace` の参照が一切ない。StpOrch は常にホスト namespace の APPL_DB を使用し、asicN namespace 向けの分散制御機構は存在しない。

### 4. SAI STP API — 全プラットフォーム共通

`create_stp` / `remove_stp` / `create_stp_port` / `remove_stp_port` / `set_stp_port_attribute` は SAI の標準インタフェースであり、ベンダー固有の拡張属性を使用していない。状態マッピングも `SAI_STP_PORT_STATE_BLOCKING / LEARNING / FORWARDING` の標準 3 状態のみ。

## まとめ

| 観点 | 結果 | 根拠 |
|------|------|------|
| ASIC 種別 (Broadcom / Mellanox 等) | SAI 取得成否で `max_stp_instances` が変わるのみ。処理ロジックは同一 | `stporch.cpp:34-42` |
| VS（仮想スイッチ） | SAI 取得失敗時は `m_defaultStpId` / `m_maxStpInstance` 未初期化のまま動作継続 | `stporch.cpp:42` (`ret = false` ログのみ) |
| multi-asic (`is_multi_npu() == True`) | 非対応（分岐なし） | `stporch.cpp` 全体 grep で `is_multi_npu` 出現なし |
| VOQ chassis | 各 host で独立適用 | CHASSIS_APP_DB / asicN 参照なし |
| warm-reboot | 対応コードなし（全プラットフォーム共通） | `stporch.cpp` に `WarmStart` 参照なし |
| j2 テンプレート / platform_config.json | **なし** | `sonic-buildimage/device/` grep で STP orch 設定注入なし |

## ソース参照

- `stporch.cpp:17-43` — コンストラクタ、SAI 初期化
- `stporch.cpp:603-615` — `updateMaxStpInstance()`
- `orchdaemon.cpp:257-263` — `gStpOrch` 登録
