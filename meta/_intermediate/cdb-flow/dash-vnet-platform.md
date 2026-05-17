# DASH_VNET — Phase H: プラットフォーム差調査

## 調査対象ソース

- `sonic-net/sonic-swss` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`
  - `orchagent/main.cpp` — `gMySwitchType` 判定 (L658, L809, L990-994)
  - `orchagent/orchdaemon.cpp` — `DpuOrchDaemon` 起動条件 (L1313-1345)
  - `orchagent/dash/dashvnetorch.cpp` — `addVnet()` / `addVnetPost()` / SAI 属性設定 (L42-108)
  - `orchagent/saihelper.cpp` — `SAI_API_DASH_VNET` 初期化 (L253-254)
  - `orchagent/crmorch.cpp` — `CRM_DASH_VNET` / `CRM_DASH_IPV4_PA_VALIDATION` 等 (L52-70)

## 結論

**DPU (switch_type="dpu") 専用。他の switch_type では DashVnetOrch が起動しない。**
DPU 動作前提が唯一の制約であり、伝統的 ASIC ベンダー別分岐（mellanox / broadcom / barefoot 等）は存在しない。

---

## 根拠

### 1. DpuOrchDaemon 起動条件 — switch_type="dpu" のみ

`main.cpp:990-994`:

```cpp
if (gMySwitchType == "dpu")
{
    dpu_app_db = make_shared<DBConnector>("DPU_APPL_DB", 0, true);
    dpu_app_state_db = make_shared<DBConnector>("DPU_APPL_STATE_DB", 0, true);
    orchDaemon = make_shared<DpuOrchDaemon>(..., dpu_app_db.get(), dpu_app_state_db.get(), ...);
}
```

- `gMySwitchType` は `getCfgSwitchType()` が `DEVICE_METADATA|localhost|switch_type` から読み取る (main.cpp:658)。
- `"dpu"` 以外の switch_type（`""` / `"voq"` / `"fabric"` / `"chassis-packet"` 等）では `DpuOrchDaemon` が生成されず、
  `DashVnetOrch` も `DashOrch` も一切登録されない。
- SmartSwitch の NPU 側 (`gMySwitchSubType == "SmartSwitch"` かつ `gMySwitchType != "dpu"`) も同様に DASH orchagent は不起動 (orchdaemon.cpp:613)。

### 2. DashVnetOrch は DPU_APPL_DB に接続

`orchdaemon.cpp:1335-1339`:

```cpp
vector<string> dash_vnet_tables = {
    APP_DASH_VNET_TABLE_NAME,
    APP_DASH_VNET_MAPPING_TABLE_NAME
};
DashVnetOrch *dash_vnet_orch = new DashVnetOrch(m_dpu_appDb, dash_vnet_tables, m_dpu_appstateDb, dash_zmq_server);
```

- `m_dpu_appDb` は `DPU_APPL_DB`（通常 APPL_DB とは別接続）。
- `m_dpu_appstateDb` は `DPU_APPL_STATE_DB`（結果書き戻し先）。
- `DASH_VNET_TABLE` / `DASH_VNET_MAPPING_TABLE` は DPU_APPL_DB に存在する。通常 T0/T1 の APPL_DB とは独立。

### 3. SAI_API_DASH_VNET — ベンダー分岐なし

`saihelper.cpp:253-254`:

```cpp
sai_api_query((sai_api_t)SAI_API_DASH_VNET,              (void**)&sai_dash_vnet_api);
sai_api_query((sai_api_t)SAI_API_DASH_OUTBOUND_CA_TO_PA, (void**)&sai_dash_outbound_ca_to_pa_api);
```

- `platform` 環境変数による条件分岐なし。SAI DASH extension API はすべてのプラットフォームで同一インターフェイスを呼ぶ。
- `dashvnetorch.cpp` の `addVnet()` (L53-108) / `addVnetMap()` / `addOutboundCaToPa()` にも `platform` / `sub_platform` 参照なし。

### 4. CRM カウンタ — IPv4/IPv6 区別のみ

`crmorch.cpp:52-70` に定義される `CRM_DASH_VNET` / `CRM_DASH_IPV4_PA_VALIDATION` / `CRM_DASH_IPV6_PA_VALIDATION` / `CRM_DASH_IPV4_OUTBOUND_CA_TO_PA` / `CRM_DASH_IPV6_OUTBOUND_CA_TO_PA` はプラットフォームに依らず同一。
`addOutboundCaToPaPost()` が `ctxt.dip.isV4()` で IPv4 / IPv6 カウンタを使い分けるが、これはアドレスファミリ差であり ASIC 種別差ではない (`dashvnetorch.cpp:525`)。

### 5. gMaxBulkSize — 起動時引数、プラットフォーム非依存

`DashVnetOrch` コンストラクタが使う `gMaxBulkSize` (`main.cpp` で設定) はコマンドライン引数 `--max-bulk-size` で指定されるデプロイ時パラメータ。
ASIC ベンダー別のデフォルト差はなく、`orchdaemon.cpp` 内でも DASH 向けの分岐はない。

### 6. 従来型プラットフォーム文字列 (orch.h) との関係

`orch.h:40-50` が定義する `MLNX_PLATFORM_SUBSTRING` / `BRCM_PLATFORM_SUBSTRING` 等は `AclOrch` / `PortsOrch` 等で使われるが、`DashVnetOrch` / `DashOrch` / `DpuOrchDaemon` のコードには一切登場しない。DASH 系 orchagent は従来型プラットフォーム分岐を持たない設計。

---

## まとめ

| 観点 | 実態 |
|------|------|
| 動作プラットフォーム | `switch_type=dpu` のノードのみ (`main.cpp:990`) |
| ASIC ベンダー別分岐 | **なし** (SAI DASH extension が抽象化) |
| IPv4 / IPv6 差 | CRM カウンタ・bulker エントリのアドレスファミリ区別のみ |
| SmartSwitch NPU 側 | DashVnetOrch **不起動** (DASH は DPU ロールのみ) |
| T0 / T1 / VOQ chassis | DASH_VNET テーブル自体が存在しない (DPU_APPL_DB 専用) |
| gMaxBulkSize | デプロイ時チューニングパラメータ。ベンダー依存なし |
