# PORT — Phase H: プラットフォーム/SAI 差異 中間ファイル

生成日: 2026-05-15 (Phase H)

## 調査対象ソース

- `sonic-swss/orchagent/portsorch.cpp`
- `sonic-swss/orchagent/orch.h`
- `sonic-buildimage/src/sonic-config-engine/minigraph.py`
- `sonic-buildimage/device/<vendor>/*/port_config.ini`
- `sonic-buildimage/device/<vendor>/*/platform_asic`

---

## 1. vendor プラットフォーム文字列定義 (orch.h)

```cpp
// sonic-swss/orchagent/orch.h:40-49
#define MRVL_TL_PLATFORM_SUBSTRING   "marvell-teralynx"
#define MRVL_PRST_PLATFORM_SUBSTRING "marvell-prestera"
#define MLNX_PLATFORM_SUBSTRING      "mellanox"
#define BRCM_PLATFORM_SUBSTRING      "broadcom"
#define VS_PLATFORM_SUBSTRING        "vs"
#define CISCO_8000_PLATFORM_SUBSTRING "cisco-8000"
#define XS_PLATFORM_SUBSTRING        "xsight"
```

環境変数 `platform` (例: `"mellanox"`, `"broadcom"`, `"vs"`) が SWSS コンテナに渡され、ランタイムで `isMlnxPlatform()` 等で判定。

---

## 2. SAI capability クエリ — PORT 関連

PortsOrch 初期化時にプラットフォームの SAI 実装に対して capability を問い合わせ、非対応機能はスキップ。

### 2a. speed: SAI_PORT_ATTR_SUPPORTED_SPEED

```cpp
// portsorch.cpp:3113
attr.id = SAI_PORT_ATTR_SUPPORTED_SPEED;
status = sai_port_api->get_port_attribute(port_id, 1, &attr);
// 失敗時: "Unable to validate speed for port %s. Not supported by platform"
// → supported_speeds を空リストとして STATE_DB に書き込まない
```

一部プラットフォーム (SAI_STATUS_NOT_SUPPORTED / SAI_STATUS_NOT_IMPLEMENTED) では速度バリデーション不可。その場合は CONFIG_DB の `speed` 値をそのまま SAI に送り、SAI_STATUS_INVALID_PARAMETER が返るまで検知不能。

### 2b. autoneg: SAI_PORT_ATTR_SUPPORTED_AUTO_NEG_MODE

```cpp
// portsorch.cpp:3181
attr.id = SAI_PORT_ATTR_SUPPORTED_AUTO_NEG_MODE;
status = sai_port_api->get_port_attribute(port.m_port_id, 1, &attr);
// 成功: port.m_cap_an = attr.value.booldata ? 1 : 0
// SAI_STATUS_SUCCESS 以外: port.m_cap_an = 1 (デフォルトで有効扱い)
// エラー: "autoneg is not supported (cap=%d)"
```

- autoneg 非対応プラットフォームでは `m_cap_an = 0` → `SWSS_LOG_ERROR + タスク破棄`。

### 2c. FEC: SAI_PORT_ATTR_SUPPORTED_FEC_MODE

```cpp
// portsorch.cpp:3230
attr.id = SAI_PORT_ATTR_SUPPORTED_FEC_MODE;
status = sai_port_api->get_port_attribute(port_id, 1, &attr);
// 非対応: "No supported_fecs exposed to STATE_DB for port %s
//          since fetching supported FEC modes is not supported by the vendor"
```

- `SAI_PORT_FEC_MODE_AUTO` は「autoneg が有効でない場合は機能しない」という制約が portsorch 側に追加されている (`portsorch.cpp:5335-5336`)。
- 非サポート FEC モードを設定しようとすると "Unsupported port %s FEC mode %s" → タスク破棄。

### 2d. fast_linkup: SAI_PORT_ATTR_FAST_LINKUP_ENABLED

```cpp
// portsorch.cpp:1038
if (gSwitchOrch->querySwitchCapability(SAI_OBJECT_TYPE_PORT,
                                        SAI_PORT_ATTR_FAST_LINKUP_ENABLED))
    m_fastLinkupPortAttrSupported = true;
// 非対応: "Fast link-up is not supported on this platform"
```

- capability クエリが false の場合、`fast_linkup` フィールドは無視 (ログのみ、タスク破棄なし)。

### 2e. pfc_asym: SAI_PORT_PRIORITY_FLOW_CONTROL_MODE

```cpp
// portsorch.cpp:5433-5436
// 設定失敗時: "Port %s asymmetric PFC configuration is not supported: skipping..."
```

- WARN ログを出力してスキップ (エラー扱いにならない)。

### 2f. TPID: SAI_PORT_ATTR_TPID

- TPID はデフォルト (`0x8100`) と異なる値のときのみ SAI set を実行 (`portsorch.cpp:1337`)。
- SAI 非対応の場合は `handleSaiSetStatus` 経由でエラー処理 (`portsorch.cpp:2352`)。
- VLAN TPID は `sai_query_attribute_enum_values_capability` で事前チェック (`portsorch.cpp:900,919`)。

---

## 3. Mellanox 固有の挙動

```cpp
// portsorch.cpp:689-700
static bool isMlnxPlatform() {
    const auto *platform = std::getenv("platform");
    return platform && std::strstr(platform, MLNX_PLATFORM_SUBSTRING);
}
```

### 3a. ポート trim 統計

```cpp
// portsorch.cpp:858-864
if (isMlnxPlatform() &&
    isPortStatSupported(SAI_PORT_STAT_TRIM_PACKETS) &&
    isPortStatSupported(SAI_PORT_STAT_TX_TRIM_PACKETS) &&
    !isPortStatSupported(SAI_PORT_STAT_DROPPED_TRIM_PACKETS))
{
    portStatPlugins += "," + nvdaPortTrimSha;  // NVIDIA 専用 flex counter プラグイン追加
}
```

### 3b. LAG distribution-only モード非対応

```cpp
// portsorch.cpp:6362,6379
// "distribution-only mode is not supported on Mellanox platform"
// → LAG MEMBER の enable 時は collection を先に有効、disable 時は distribution を先に無効化
```

---

## 4. port_config.ini — platform 依存のレーン/速度定義

各プラットフォーム固有の `port_config.ini` が `sonic-cfggen` によって PORT テーブルのデフォルト値に変換される。

| ベンダ | ハードウェア例 | レーン構成例 |
|--------|-----------|-----------|
| Mellanox (NVIDIA) | MSN2700 | `Ethernet0: lanes=0,1,2,3` (4 レーン × QSFP28) |
| Broadcom | BCM956960K | `Ethernet0: lanes=1,2,3,4, speed=100000` |

- `lanes` はプラットフォームのレーンマッピングに完全依存。他プラットフォームへの設定の移植不可。
- `speed` フィールドのデフォルト値も `port_config.ini` に記載 (例: Broadcom BCM956960K は全ポート 100G)。

---

## 5. platform_asic ファイルと ASIC タイプ識別

各デバイスディレクトリの `platform_asic` ファイルが ASIC タイプを示す。

| platform_asic 値 | 主な vendor / 例 |
|-----------------|----------------|
| `broadcom` | Arista, Supermicro, Dell (Trident/Tomahawk) |
| `broadcom-dnx` | Arista (Jericho2/3) |
| `broadcom-legacy-th` | 旧 Arista (Tomahawk legacy) |
| `mellanox` | NVIDIA Spectrum シリーズ |
| `marvell-teralynx` | Supermicro SSE-T7132S |
| `barefoot` | Arista 7170 (Intel Tofino) |

SWSS の `orchdaemon.cpp:635,733` では platform 文字列で mellanox / vs 系と broadcom 系の初期化フローを分岐させている。

---

## 6. minigraph.py の FEC デフォルト生成 (100G 限定)

```python
# minigraph.py:2428-2433
# generate default 100G FEC only if FECDisabled is not true and 'fec' is not defined in port_config.ini
if linkmetas.get(alias, {}).get('FECDisabled', '').lower() == 'true':
    port['fec'] = 'none'
elif not port.get('fec') and port.get('speed') == '100000':
    port['fec'] = 'rs'
```

- 100G ポートは `FECDisabled=true` の minigraph プロパティがない限り自動的に `fec: rs` が付与される。
- 25G 以下や 400G は明示設定が必要 (`port_config.ini` か `config interface fec` CLI)。

---

## 7. SAI capability クエリ失敗時の STATE_DB 影響

| 機能 | SAI クエリ属性 | 非対応時の動作 | STATE_DB への影響 |
|------|-------------|------------|----------------|
| speed バリデーション | SAI_PORT_ATTR_SUPPORTED_SPEED | WARN ログ、バリデーションスキップ | `supported_speeds` フィールドなし |
| FEC サポートリスト | SAI_PORT_ATTR_SUPPORTED_FEC_MODE | INFO ログ、スキップ | `supported_fecs` フィールドなし |
| autoneg 対応確認 | SAI_PORT_ATTR_SUPPORTED_AUTO_NEG_MODE | デフォルト `cap_an=1` | - |
| fast_linkup | SAI_PORT_ATTR_FAST_LINKUP_ENABLED | NOTICE ログ、設定無視 | - |

---

## 証跡

- `sonic-swss/orchagent/portsorch.cpp` lines 689-700 (isMlnxPlatform), 858-864 (trim stat), 947-1006 (capability queries), 3102-3320 (supported speeds/FEC/autoneg), 3540 (fast_linkup), 5319-5336 (FEC auto), 6362,6379 (LAG distribution-only)
- `sonic-swss/orchagent/orch.h` lines 40-49 (platform string defines)
- `sonic-buildimage/src/sonic-config-engine/minigraph.py` lines 2428-2433 (FEC default)
- `sonic-buildimage/device/mellanox/x86_64-mlnx_msn2700-r0/ACS-MSN2700/port_config.ini`
- `sonic-buildimage/device/broadcom/x86_64-bcm_xlr-r0/BCM956960K/port_config.ini`
- `sonic-buildimage/device/*/platform_asic` (複数)
