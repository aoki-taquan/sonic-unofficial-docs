# macsec-port — Phase H: プラットフォーム差分

## 調査対象

- `sonic-swss/orchagent/macsecorch.cpp` — `MACsecOrchContext::get_port_id()`, `get_switch_id()`, `createMACsecPort()`, stat manager 選択ロジック

## Gearbox PHY の有無によるバックエンド分岐

MACsec の SAI 処理バックエンドは、ポートに Gearbox PHY が割り当てられているか、かつその PHY が MACsec をサポートするかで 2 経路に分岐する。

### port_id 決定ロジック (L351-381)

```
get_gearbox_phy() → phy が存在?
  Yes → phy->macsec_supported == true?
    Yes → force_npu = false → port->m_line_side_id を使用 (PHY 側)
    No  → force_npu = true  → port->m_port_id を使用 (NPU 側)
          + SWSS_LOG_NOTICE "backend=NPU (phy marked unsupported)"
  No  → force_npu = true   → port->m_port_id を使用 (NPU 側)
```

### switch_id 決定ロジック (L384-420)

```
phy が存在 && macsec_supported == true?
  Yes → switch_id = port->m_switch_id (PHY スイッチ)
  No  → switch_id = gSwitchId (グローバル NPU スイッチ)
        + force_npu = true かつ m_switch_id != gSwitchId の場合 SWSS_LOG_NOTICE
```

## Gearbox PHY 有効時のみ実行される処理

`createMACsecPort()` (L1505-1527) の PHY 専用コードパス:

| 処理 | 条件 | evidence |
|------|------|---------|
| `setPFCForward(port_id, true)` — PFC フォワードを有効化 | `phy != nullptr` | L1507 |
| Port IPG 退避 (`getPortIPG`) + MACsec IPG 設定 (`setPortIPG`) | `phy != nullptr && phy->macsec_ipg != 0` | L1515-1526 |
| `deleteMACsecPort()` 時の PFC フォワード無効化 + IPG 復元 | `phy != nullptr` | L1774-1785 |

Gearbox PHY なし (NPU バックエンド) では PFC フォワード変更・IPG 変更は一切行われない。

## FlexCounter / COUNTERS_DB のバックエンド分岐

stat manager 選択 (L2536-2567):

| stat manager | 条件 |
|---|---|
| `m_gb_macsec_sa_stat_manager` (COUNTERS_GB_MACSEC_TABLE 相当) | `phy != nullptr && phy->macsec_supported` |
| `m_macsec_sa_stat_manager` (NPU 側 COUNTERS_DB) | それ以外 |

カウンタマップ / フロー stat manager も同様に GB 系と NPU 系で分岐する (L2544-2566)。

## プラットフォーム別サマリ

| 構成 | バックエンド | port_id | PFC Forward | IPG 調整 | FlexCounter |
|------|-----------|---------|------------|---------|------------|
| Gearbox PHY + `macsec_supported=true` | PHY (line side) | m_line_side_id | **あり** | **あり** (macsec_ipg != 0 の場合) | GB 系 |
| Gearbox PHY + `macsec_supported=false` | NPU | m_port_id | なし | なし | NPU 系 |
| Gearbox PHY なし | NPU | m_port_id | なし | なし | NPU 系 |
