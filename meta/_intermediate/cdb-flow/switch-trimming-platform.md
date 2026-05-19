# switch-trimming — Phase H プラットフォーム差 調査ノート

## 調査対象

- `sonic-swss/orchagent/switchorch.cpp`（SWITCH_TRIMMING 処理本体）
- `sonic-swss/orchagent/switch/trimming/capabilities.cpp`
- `sonic-swss/orchagent/switch/trimming/schema.h`、`helper.cpp`
- `sonic-swss/orchagent/portsorch.cpp` L689-706, L855-865
- `sonic-swss/orchagent/orch.h` L40-50（プラットフォーム定数）

## 調査日

2026-05-19

## 結論

`SWITCH_TRIMMING` テーブルの SET/DEL 処理 (`doCfgSwitchTrimmingTableTask()` / `setSwitchTrimming()`) に **コード上のプラットフォーム分岐は存在しない**。
ただしハードウェアサポートは実行時 SAI capability クエリによって決まるため、ASIC ベンダー間で機能可用性が異なる。
また、トリミング関連の **カウンタ計算** は NVIDIA/Mellanox プラットフォームでのみ追加 Lua スクリプトが動作する。

## 1. SWITCH_TRIMMING SET 処理のプラットフォーム差

`sonic-swss/orchagent/switchorch.cpp` を `platform|BRCM|MLNX|broadcom|mellanox|cisco|marvell|barefoot|vendor` で grep → **0 ヒット**（trimming 関連）。

`sonic-swss/orchagent/switch/trimming/` ディレクトリ配下 4 ファイルでも同様に **0 ヒット**。

コード分岐なし。

## 2. SAI capability による実行時プラットフォーム差

`SwitchTrimmingCapabilities::queryCapabilities()` (`capabilities.cpp L142-179`) が orchagent 起動時に SAI へ問い合わせる。

```cpp
// capabilities.cpp L142-146
SwitchTrimmingCapabilities::SwitchTrimmingCapabilities()
{
    queryCapabilities();
    writeCapabilitiesToDb();
}
```

`queryCapabilities()` が各 SAI 属性の `query_attribute_capability()` を呼び、未サポートなら `isAttrSupported = false`。
`isSwitchTrimmingSupported()` が `false` を返すと `setSwitchTrimming()` 冒頭の guard が全フィールドを no-op にする。

この挙動は ASIC ベンダーが SAI 実装で capability を返すかどうかに依存する。
`STATE_DB:SWITCH_CAPABILITY|switch.SWITCH_TRIMMING_CAPABLE` に `"true"/"false"` として書き出される。

## 3. NVIDIA/Mellanox 固有のカウンタ Lua プラグイン

`portsorch.cpp L855-864`:

```cpp
// Nvidia custom trim stat calculation
if (isMlnxPlatform() &&
    isPortStatSupported(SAI_PORT_STAT_TRIM_PACKETS) &&
    isPortStatSupported(SAI_PORT_STAT_TX_TRIM_PACKETS) &&
    !isPortStatSupported(SAI_PORT_STAT_DROPPED_TRIM_PACKETS))
{
    portStatPlugins += "," + nvdaPortTrimSha;
}
```

`isMlnxPlatform()` は `getenv("platform")` に `"mellanox"` 文字列が含まれるかを判定する (`portsorch.cpp L689-706`)。

- `nvda_port_trim_drop.lua` は FLEX_COUNTER_DB の port stat Lua プラグインとして登録される
- このスクリプトは `SAI_PORT_STAT_TRIM_PACKETS` と `SAI_PORT_STAT_TX_TRIM_PACKETS` の差分から `DROPPED_TRIM_PACKETS` を計算する
- 非 NVIDIA/Mellanox プラットフォームではこのプラグインは登録されない

## 4. VS (Virtual Switch) プラットフォームでの扱い

DVS テスト (`tests/dvslib/dvs_switch.py`) は `CONFIG_SWITCH_TRIMMING = "SWITCH_TRIMMING"` として参照している。
VS ではおそらく SAI stub が capability を返さず `SWITCH_TRIMMING_CAPABLE = "false"` となり no-op になるが、テストコードで明示的な確認はなし。

## 5. multi-asic / VOQ chassis

`orchdaemon.cpp L200` の `conf_switch_trim` は `m_configDb`（host CONFIG_DB）を購読する。
multi-asic での per-asic namespace や VOQ chassis での supervisor 側 DB への展開は実装されていない。
`SWITCH_TRIMMING` は switch グローバル設定であり、host 単一インスタンスが全 ASIC に適用する想定。
