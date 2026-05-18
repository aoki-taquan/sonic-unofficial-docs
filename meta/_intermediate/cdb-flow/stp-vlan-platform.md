# Phase H 中間ファイル — STP_VLAN / STP_VLAN_PORT プラットフォーム差異分析

## 調査対象

- `sonic-net/sonic-swss` `cfgmgr/stpmgr.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-net/sonic-swss` `cfgmgr/stpmgr.h` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-net/sonic-swss` `cfgmgr/stpmgrd.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-net/sonic-swss` `orchagent/stporch.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## 結論サマリー

`STP_VLAN` / `STP_VLAN_PORT` テーブルの処理に ASIC ベンダー固有の分岐は存在しない。
stpmgr は SAI を直接呼ばず、Unix Domain Socket 経由で stpd に IPC を送信する設計であり、
ASIC 差異は stpd 内部で吸収される。

ただし以下 3 点においてプラットフォーム依存の挙動が観測される。

---

## 1. STP プロトコルモード (L2_PVSTP vs L2_MSTP)

`STP_VLAN` / `STP_VLAN_PORT` テーブルは **PVST (L2_PVSTP) 専用** のテーブルである。

```cpp
// stpmgr.cpp:260 — PVST モードでのみ allocL2Instance が呼ばれる
if (l2ProtoEnabled == L2_PVSTP)
{
    newInstance = 1;
    instId = allocL2Instance(vlan_id);
    ...
}
```

- `l2ProtoEnabled == L2_MSTP` の場合: `STP_VLAN` の SET を受信しても `allocL2Instance` が呼ばれず、
  `newInstance = 0` のまま IPC メッセージが送信される。
  MSTP での per-VLAN ブリッジパラメータは `STP_MST_INST` テーブルが担う。
- `l2ProtoEnabled == L2_NONE` の場合: `doStpVlanTask()` は `stpGlobalTask == false` ガードで即時 return、
  または SET で `l2ProtoEnabled == L2_NONE` チェック (stpmgr.cpp:210) にかかり `it++; continue` となる。

DEL の場合も `l2ProtoEnabled == L2_NONE` ならエントリを erase するのみで IPC は送信しない (stpmgr.cpp:246-250)。

**プロトコルモードはプラットフォームではなく CLI 設定 (`STP|GLOBAL.mode`) で決まる**が、
STP プロトコル自体をサポートしない構成 (DPU / SmartSwitch NPU 側 PVST 不使用) ではこのテーブルは実質的に無効化される。

---

## 2. ASIC ごとの最大 STP インスタンス数 (SAI_SWITCH_ATTR_MAX_STP_INSTANCE)

`stporch.cpp` 初期化時に SAI 属性 `SAI_SWITCH_ATTR_MAX_STP_INSTANCE` を照会し、
`STATE_STP|GLOBAL.max_stp_inst` に書き込む (stporch.cpp:29-40, 605-612)。

```cpp
// stporch.cpp:32-38
attr.id = SAI_SWITCH_ATTR_MAX_STP_INSTANCE;
status = sai_switch_api->get_switch_attribute(gSwitchId, (uint32_t)attrs.size(), attrs.data());
if (status == SAI_STATUS_SUCCESS)
{
    m_maxStpInstance = (sai_uint16_t)max_stp_instances - 1;
    m_stpTable->set("GLOBAL", {{"max_stp_inst", to_string(m_maxStpInstance)}});
}
```

`stpmgrd` 起動時に `getStpMaxInstances()` (stpmgr.cpp:1381-1413) がこの値を読み取り `max_stp_instances` に設定する。

| プラットフォーム例 | SAI 値 | `max_stp_instances` 実効値 | 備考 |
|-------------------|--------|---------------------------|------|
| 多くの Broadcom ASIC | SAI 照会成功: 255 以上 | SAI 値 - 1 | DefaultSTPインスタンスを除く |
| 一部 Marvell / 低グレード ASIC | SAI 照会成功: 少ない値 | SAI 値 - 1 | STP_VLAN 有効化数が制限される |
| VS (仮想スイッチ) | SAI 照会失敗 または 0 | `STP_DEFAULT_MAX_INSTANCES` = 255 (フォールバック) | stpmgr.cpp:1407-1410 |

SAI 照会が失敗した場合 (`max_stp_instances == 0`) はフォールバック:
```cpp
// stpmgr.cpp:1407-1410
if (max_stp_instances == 0)
{
    max_stp_instances = STP_DEFAULT_MAX_INSTANCES;  // = 255
    SWSS_LOG_NOTICE("set default max stp instance %d", max_stp_instances);
}
```

CLI が `PVST_MAX_INSTANCES = 255` を超える VLAN に STP を有効化しようとすると warning のみで打ち切られる (stpmgr.cpp:260-265 / Phase E で既述)。

---

## 3. ebtables PVST マルチキャストフィルタ

PVST モードでは Cisco PVST+ マルチキャストアドレス (`01:00:0c:cc:cc:cd`) の転送をブロックする
ebtables ルールをカーネルに挿入する。

```cpp
// stpmgr.cpp:47-48 (コンストラクタ)
int ret = system("ebtables -D FORWARD -d 01:00:0c:cc:cc:cd -j DROP");

// stpmgr.cpp:113-117 (PVST 有効化時に ADD)
" ebtables -A FORWARD -d 01:00:0c:cc:cc:cd -j DROP";
int ret = swss::exec(cmd, res);

// stpmgr.cpp:161-165 (STP 無効化時に DELETE)
"ebtables -D FORWARD -d 01:00:0c:cc:cc:cd -j DROP";
int ret_pvst = swss::exec(pvst_cmd, res_pvst);
```

- **標準 SONiC (Broadcom / Mellanox / その他物理 ASIC)**: ebtables が有効なため PVST マルチキャストが
  適切に遮断される。
- **VS (仮想スイッチ)**: ebtables 呼び出しは成功するが、仮想環境ではハードウェアフラッディングが
  発生しないため実効的なトラフィック影響はない。ebtables が `/sbin/ebtables` として存在しない
  コンテナ環境では `system()` が失敗し `SWSS_LOG_DEBUG("ebtables ret %d", ret)` のみ出力される。
- **SmartSwitch DPU**: DPU 側では `stpmgrd` は通常起動しないため、この ebtables 操作は不要。

---

## 調査結果まとめ

| 観点 | 標準 PVST (物理 ASIC) | MSTP モード | VS / コンテナ | SmartSwitch DPU |
|------|----------------------|-------------|--------------|-----------------|
| STP_VLAN 処理 | 完全動作 | 無効化 (L2_MSTP 分岐) | 動作 (ebtables は no-op の場合あり) | 非起動 |
| allocL2Instance | 実行 | スキップ | 実行 | N/A |
| max_stp_instances | SAI 照会値 - 1 | N/A | 255 (フォールバック) | N/A |
| ebtables PVST フィルタ | 有効 | 削除 (DEL 時) | no-op の場合あり | N/A |
