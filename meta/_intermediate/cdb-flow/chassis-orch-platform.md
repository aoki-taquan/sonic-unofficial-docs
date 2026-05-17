# PASS_THROUGH_ROUTE_TABLE / ChassisOrch プラットフォーム差異調査メモ (Phase H)

調査日: 2026-05-17
対象テーブル: CONFIG_DB `PASS_THROUGH_ROUTE_TABLE`
フェーズ: H（プラットフォーム差分抽出）

## 調査対象ファイル

- `sonic-net/sonic-swss/orchagent/main.cpp`
- `sonic-net/sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-net/sonic-swss/orchagent/orchdaemon.h`
- `sonic-net/sonic-swss/orchagent/chassisorch.cpp`

---

## switch_type による orchagent デーモンクラス選択

`main.cpp:658` で `getCfgSwitchType()` が `DEVICE_METADATA|localhost.switch_type` を読み取り、
`gMySwitchType` に格納する。有効値は以下:

| `switch_type` | 使用 OrchDaemon クラス | `OrchDaemon::init()` 呼び出し |
|-------------|---------------------|------------------------------|
| `"switch"` (デフォルト) | `OrchDaemon` | Yes |
| `"voq"` | `OrchDaemon` | Yes |
| `"chassis-packet"` | `OrchDaemon` | Yes |
| `"dpu"` | `DpuOrchDaemon` | Yes (super 呼び出し: `orchdaemon.cpp:1325`) |
| `"fabric"` | `FabricOrchDaemon` | **No** (独立 init、super 未呼び出し) |

```cpp
// main.cpp:990-1009
if (gMySwitchType == "dpu")
    orchDaemon = make_shared<DpuOrchDaemon>(...);
else if (gMySwitchType != "fabric")
    orchDaemon = make_shared<OrchDaemon>(...);
else
    orchDaemon = make_shared<FabricOrchDaemon>(...);
```

---

## ChassisOrch の switch_type 分岐

`OrchDaemon::init()` 内の `ChassisOrch` 生成コード（`orchdaemon.cpp:290-294`）に
`gMySwitchType` ガードは**存在しない**。

```cpp
// orchdaemon.cpp:290-294
const vector<string> chassis_frontend_tables = {
    CFG_PASS_THROUGH_ROUTE_TABLE_NAME,
};
ChassisOrch* chassis_frontend_orch = new ChassisOrch(m_configDb, m_applDb, chassis_frontend_tables, vnet_rt_orch);
gDirectory.set(chassis_frontend_orch);
```

→ `switch="switch"` / `"voq"` / `"chassis-packet"` / `"dpu"` のすべてで ChassisOrch が生成・有効化される。

---

## 各 switch_type での実質的挙動差異

### `"voq"` — 設計用途のプラットフォーム

VoQ チャシスのフロントエンドルータとして設計されており、ChassisOrch が本来機能する想定環境。
`VNetRouteOrch` も同一 `OrchDaemon::init()` 内で生成され（`orchdaemon.cpp:281`）、依存が満たされる。

### `"switch"` — 一般スイッチ（意図外）

一般スイッチ環境でも ChassisOrch が生成・動作する。ただし VNet / VoQ 構成を行わない限り
CONFIG_DB `PASS_THROUGH_ROUTE_TABLE` への書き込みは行われず、ChassisOrch は待機状態に留まる。
「silent standby」となり、機能的影響はない。

### `"chassis-packet"` — chassis-packet モード

`OrchDaemon::init()` が呼ばれるため ChassisOrch は生成される。
`chassis-packet` は VoQ に近い構成だが ChassisOrch の動作条件（VNet 設定・`PASS_THROUGH_ROUTE_TABLE` 書き込み）に差異はない。

### `"dpu"` — SmartSwitch DPU

`DpuOrchDaemon::init()` は `OrchDaemon::init()` を `super` 呼び出しするため（`orchdaemon.cpp:1325`）、
ChassisOrch が生成される。ただし DPU では VNet パススルー機能を使用しない想定のため、
`PASS_THROUGH_ROUTE_TABLE` へのエントリ書き込みは行われない（silent standby）。

### `"fabric"` — ファブリックカード専用

`FabricOrchDaemon::init()` は `OrchDaemon::init()` を**呼び出さない**（`orchdaemon.cpp:1292-1310`）。
ChassisOrch は**生成されない**。`PASS_THROUGH_ROUTE_TABLE` の購読者も存在しない。

---

## platform 環境変数（ハードウェアプラットフォーム）

`OrchDaemon::init()` の冒頭（`orchdaemon.cpp:190`）で `getenv("platform")` を読み取るが、
`ChassisOrch` の生成にこの値は使用されない。ハードウェアベンダー依存分岐は存在しない。

```cpp
// orchdaemon.cpp:190
string platform = getenv("platform") ? getenv("platform") : "";
// ... ChassisOrch 生成には利用されない
```

---

## まとめ

| switch_type | ChassisOrch 生成 | 実質的動作 |
|------------|-----------------|-----------|
| `"voq"` | ○ | 設計用途。VNet パススルールート転送が機能する |
| `"switch"` | ○ | Silent standby。PASS_THROUGH_ROUTE_TABLE 書き込みなし |
| `"chassis-packet"` | ○ | VoQ 準拠構成。VNet 設定次第で動作 |
| `"dpu"` | ○ | Silent standby（DPU では VNet パススルー未使用） |
| `"fabric"` | ✗ | FabricOrchDaemon が OrchDaemon::init() を呼ばないため生成なし |

---

## 証拠リンク

- `main.cpp:658` — `getCfgSwitchType()` 呼び出し
- `main.cpp:990-1009` — switch_type 別 orchDaemon クラス選択
- `orchdaemon.cpp:290-294` — ChassisOrch 生成（ガードなし）
- `orchdaemon.cpp:1292-1310` — `FabricOrchDaemon::init()` （super 未呼び出し）
- `orchdaemon.cpp:1322-1325` — `DpuOrchDaemon::init()` が `OrchDaemon::init()` を呼び出す
- `orchdaemon.h:139-155` — `FabricOrchDaemon` / `DpuOrchDaemon` クラス定義
