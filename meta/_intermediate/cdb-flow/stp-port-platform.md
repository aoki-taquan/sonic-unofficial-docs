# Phase H 中間ファイル — STP_PORT プラットフォーム差異分析

## 調査対象

- `sonic-net/sonic-swss` `cfgmgr/stpmgr.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-net/sonic-swss` `cfgmgr/stpmgr.h` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-net/sonic-swss` `cfgmgr/stpmgrd.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-net/sonic-swss` `orchagent/stporch.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## 結論サマリー

`STP_PORT` テーブルの処理に ASIC ベンダー固有のコード分岐は存在しない。
stpmgrd は SAI を直接呼ばず、Unix Domain Socket 経由で stpd に IPC を送信する設計であり、
ASIC 差異は stpd 内部で吸収される。

ただし以下 3 点においてプラットフォーム依存の挙動が観測される。

---

## 1. STP プロトコルモード (L2_PVSTP vs L2_MSTP)

`STP_PORT` テーブルは PVST / MST の両モードで使用されるが、フィールドセットが異なる。

```cpp
// stpmgr.cpp:doStpPortTask()
if (l2ProtoEnabled == L2_NONE)
{
    it++;   // SET を defer (DEL は即消費・ドロップ)
    continue;
}
```

- `l2ProtoEnabled == L2_PVSTP` の場合: `portfast`・`uplink_fast`・`bpdu_guard_do_disable` フィールドが処理される
- `l2ProtoEnabled == L2_MSTP` の場合: `edge_port`・`link_type`・`bpdu_guard_do` フィールドが処理される。
  `link_type` 処理は `stoi(field.c_str())` バグ (stpmgr.cpp:611-613) のため事実上クラッシュを引き起こす (Phase D 参照)
- `l2ProtoEnabled == L2_NONE` の場合: SET はキューに残留、DEL は即消去

**プロトコルモードはプラットフォームではなく CLI 設定 (`STP|GLOBAL.mode`) で決まる**が、
STP 自体をサポートしない構成 (DPU / SmartSwitch NPU 側 PVST 不使用) では `stpmgrd` が起動しないため
このテーブルは実質的に無効化される。

---

## 2. ASIC ごとの最大 STP インスタンス数 (SAI_SWITCH_ATTR_MAX_STP_INSTANCE)

`stporch.cpp` 初期化時に SAI 属性 `SAI_SWITCH_ATTR_MAX_STP_INSTANCE` を照会し、
`STATE_DB:STP_TABLE|GLOBAL.max_stp_inst` に書き込む (stporch.cpp:29-40, 603-615)。

```cpp
// stporch.cpp:32-38
attr.id = SAI_SWITCH_ATTR_MAX_STP_INSTANCE;
status = sai_switch_api->get_switch_attribute(gSwitchId, (uint32_t)attrs.size(), attrs.data());
if (status == SAI_STATUS_SUCCESS)
{
    updateMaxStpInstance(attrs[1].value.u32);  // → STATE_DB:STP_TABLE|GLOBAL.max_stp_inst に書き込み
}
```

`stpmgrd` 起動時に `getStpMaxInstances()` (stpmgr.cpp:1381-1413) がこの値を読み取り
`max_stp_instances` に設定する。
この制限は `STP_PORT` が直接参照するわけではなく、上位の `doStpVlanTask()` で `IS_INST_ID_AVAILABLE()` 
マクロがインスタンス割り当て上限をチェックすることで間接的に `STP_PORT` の有効 VLAN 数を制限する。

| プラットフォーム例 | SAI 照会結果 | `max_stp_instances` 実効値 | 備考 |
|-------------------|-------------|---------------------------|------|
| 多くの Broadcom ASIC | 成功 (255 以上) | SAI 値 - 1 | デフォルト STP インスタンス分を除く |
| 一部 Marvell / 低グレード ASIC | 成功 (少ない値) | SAI 値 - 1 | 有効化可能 VLAN / ポート数が制限される |
| VS (仮想スイッチ) | 失敗 または 0 | `STP_DEFAULT_MAX_INSTANCES` = 255 (フォールバック) | stpmgr.cpp:1407-1410 |

SAI 照会失敗時フォールバック:
```cpp
// stpmgr.cpp:1407-1410
if (max_stp_instances == 0)
{
    max_stp_instances = STP_DEFAULT_MAX_INSTANCES;  // = 255
    SWSS_LOG_NOTICE("set default max stp instance %d", max_stp_instances);
}
```

`getStpMaxInstances()` は `STATE_DB:STP_TABLE|GLOBAL` を最大 60 秒ポーリングし (stpmgr.cpp:1388-1405)、
タイムアウトしても値が取得できない場合は `STP_DEFAULT_MAX_INSTANCES = 255` を使用する。

---

## 3. ebtables PVST マルチキャストフィルタ (PVST モード時)

PVST モード有効化時、stpmgr コンストラクタがカーネル ebtables ルールを設定する。
`STP_PORT` の処理自体は ebtables に依存しないが、PVST が有効な環境でのみ `STP_PORT` が
stpd に到達するため、間接的に環境依存となる。

```cpp
// stpmgr.cpp:113-117 (PVST 有効化時に ADD)
" ebtables -A FORWARD -d 01:00:0c:cc:cc:cd -j DROP";

// stpmgr.cpp:161-165 (STP 無効化時に DELETE)
"ebtables -D FORWARD -d 01:00:0c:cc:cc:cd -j DROP";
```

- **標準 SONiC (物理 ASIC)**: ebtables が有効で Cisco PVST+ マルチキャストが適切に遮断される
- **VS (仮想スイッチ)**: ebtables 呼び出しは成功するがハードウェアフラッディングが発生しないため実効影響なし
- **ebtables 非存在環境 (コンテナ)**: `system()` 失敗時は `SWSS_LOG_DEBUG` のみ出力され stpmgrd は継続動作
- **SmartSwitch DPU**: stpmgrd 通常非起動のため対象外

---

## 調査結果まとめ

| 観点 | 標準 PVST (物理 ASIC) | MSTP モード | VS / コンテナ | SmartSwitch DPU |
|------|----------------------|-------------|--------------|-----------------|
| STP_PORT 処理 | PVST フィールドセット | MST フィールドセット | 動作 (ebtables no-op の場合あり) | 非起動 |
| max_stp_instances | SAI 照会値 - 1 | SAI 照会値 - 1 | 255 (フォールバック) | N/A |
| ebtables PVST フィルタ | 有効 | 無効 (PVST 以外) | no-op の場合あり | N/A |
| link_type (MST) | N/A | **バグ: stoi(field) クラッシュ** | 同左 | N/A |
