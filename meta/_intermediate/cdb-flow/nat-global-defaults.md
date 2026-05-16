# NAT_GLOBAL Phase A — フィールド暗黙デフォルト調査

**対象**: `docs/reference/config-db/nat.md` (NAT_GLOBAL テーブル)
**日時**: 2026-05-14
**調査範囲**: sonic-swss/orchagent/natorch.cpp, sonic-swss/cfgmgr/natmgr.cpp, sonic-swss/cfgmgr/natmgr.h, sonic-swss/orchagent/natorch.h, sonic-buildimage/src/sonic-yang-models/yang-models/sonic-nat.yang

---

## フィールド列挙

NAT_GLOBAL|Values の全フィールド:
1. `admin_mode` — enabled/disabled
2. `nat_timeout` — uint32 300..432000
3. `nat_tcp_timeout` — uint32 300..432000
4. `nat_udp_timeout` — uint16 120..600

---

## コード由来デフォルト一覧

### NatOrch (orchagent) コンストラクタ (natorch.cpp:63-73)

```cpp
admin_mode = "disabled";   // L64
timeout = 600;              // L67
tcp_timeout = 86400;        // L70
udp_timeout = 300;          // L73
```

### NatMgr (natmgrd) コンストラクタ (natmgr.cpp:55-65)

```cpp
natAdminMode = DISABLED;              // L56 == "disabled"
m_natTimeout = NAT_TIMEOUT_DEFAULT;   // L59 == 600
m_natTcpTimeout = NAT_TCP_TIMEOUT_DEFAULT; // L62 == 86400
m_natUdpTimeout = NAT_UDP_TIMEOUT_DEFAULT; // L65 == 300
```

定数は natmgr.h:64,69,73:
```cpp
#define NAT_TIMEOUT_DEFAULT        600
#define NAT_TCP_TIMEOUT_DEFAULT    86400
#define NAT_UDP_TIMEOUT_DEFAULT    300
```

---

## 特記事項・暗黙挙動

### 1. YANG default と実装 hardcode の二重設定
- YANG default: `nat_timeout=600`, `nat_tcp_timeout=86400`, `nat_udp_timeout=300`
- コードの hardcode: NatOrch L67/70/73、NatMgr L59/62/65 — 値は一致。ただし NAT_GLOBAL|Values が CONFIG_DB に存在しない場合、natorch/natmgrd はハードコード値で動作し YANG validate は通らない。

### 2. timeout 変更は admin_mode=enabled 時のみ APPL_DB に伝播
- natmgr.cpp:7286-7313: `if (isNatEnabled())` 条件でのみ fvVector に追加。
- `admin_mode=disabled` 状態でタイムアウト変更しても APPL_DB には書かれない。
- `admin_mode=enabled` に切り替えた時点 (enableNatFeature() 内 L5686-5704) でデフォルト値以外のタイムアウトだけ追記 (`if (m_natTcpTimeout != NAT_TCP_TIMEOUT_DEFAULT)` など)。
- **隠れたバグ**: デフォルト値から変更→admin_mode disabled→admin_mode enabled の順に操作しても、enableNatFeature() が呼ばれた時点で非デフォルト値のみ APPL_DB に書き込まれる。default 値へのリセットは DEL_COMMAND 操作が必要。

### 3. gIsNatSupported — プラットフォーム依存 silent drop
- main.cpp:936-948: `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY == 0` の場合 `gIsNatSupported = false`。
- natorch.cpp:2541-2544: `enableNatFeature()` 冒頭で `gIsNatSupported == false` → `SWSS_LOG_NOTICE + return` (silent drop)。
- CONFIG_DB に `admin_mode=enabled` を書いても、SAI が SNAT エントリを 0 としか報告しないプラットフォームでは NAT が有効化されない。admin_mode は "enabled" に見えるが SAI 操作は行われない。

### 4. gNhTrackingSupported — BRCM プラットフォームのみ有効
- natorch.cpp:144-148: `getenv("platform")` が "broadcom" を含む場合のみ `gNhTrackingSupported = true`。
- enableNatFeature() L2570-2574: BRCM のみ `m_neighOrch->attach(this)` — DNAT の next-hop 追跡。
- 非 BRCM 環境では DNAT エントリの next-hop 変化追跡が行われず、経路変更時に DNAT エントリが stale になる可能性。

### 5. NatOrch::doNatGlobalTableTask の assert クラッシュ
- natorch.cpp:2938: `assert(mode == "enabled" || mode == "disabled")`
- natmgr.cpp は APPL_DB に書く前に `if ((adminModeFound == true) and ((adminMode != ENABLED) and (adminMode != DISABLED)))` でガード (L7250-7256) するが、直接 APPL_DB 書き込みや YANG バリデーション迂回でインバリッドな値が入ると orchagent が abort する。

### 6. DEL_COMMAND 時のデフォルト回帰
- natmgr.cpp:7343-7365: NAT_GLOBAL DEL 時は timeout 3種を DEFAULT 値にリセットし APPL_DB に書き込む。ただし `natAdminMode == ENABLED` 時のみ APPL_DB 書き込みが実行される。`disabled` のまま DEL した場合は APPL_DB への書き込みはなく、内部変数のみリセット。

### 7. YANG nat_type default の STATIC_NAT vs NAT_BINDINGS 非対称
- STATIC_NAT.nat_type: `default dnat` (yang L101, L141)
- NAT_BINDINGS.nat_type: `default snat` (yang L280)
- ドキュメントの「例外条件」に `nat_type のデフォルト = "dnat"` とあるのは STATIC_NAT/STATIC_NAPT の話。BINDINGS は逆。

### 8. タイムアウト重複定義 (NatOrch と NatMgr が別々に保持)
- NatOrch の `timeout/tcp_timeout/udp_timeout` は APPL_DB → NatOrch の経路
- NatMgr の `m_natTimeout/m_natTcpTimeout/m_natUdpTimeout` は CONFIG_DB → NatMgr の経路
- 両者は独立した変数を持ち、起動直後は同じデフォルト値だが、CONFIG_DB 変更時は NatMgr → APPL_DB → NatOrch の順で伝播。

---

## dead field / dead consumer

- `nat_port` (NAT_POOL): YANG に定義あり、CLI で設定可。実装 (natmgr.cpp) でも処理される。dead ではない。
- `twice_nat_id` (NAT_BINDINGS/STATIC_NAT): YANG 定義あり。NatMgr/NatOrch で処理されている。dead ではない。

---

## 結論

| フィールド | YANG default | コード fallback | 乖離 |
|-----------|-------------|----------------|------|
| `admin_mode` | `disabled` | hardcode `"disabled"` (NatOrch L64, NatMgr L56) | 一致 |
| `nat_timeout` | `600` | hardcode `600` (NatOrch L67, NatMgr L59, #define L64) | 一致 |
| `nat_tcp_timeout` | `86400` | hardcode `86400` (NatOrch L70, NatMgr L62, #define L69) | 一致 |
| `nat_udp_timeout` | `300` | hardcode `300` (NatOrch L73, NatMgr L65, #define L73) | 一致 |

YANG default と実装 hardcode は全フィールドで一致。
主要な discrepancy は:
1. **プラットフォーム依存 silent drop** (`gIsNatSupported=false` 環境で `admin_mode=enabled` が無視)
2. **タイムアウト変更の遅延伝播** (`admin_mode=disabled` 中の変更は APPL_DB に届かない)
3. **nat_type default の STATIC_NAT vs BINDINGS 非対称** (既存ドキュメントに `"dnat"` とのみ記載あり — BINDINGS は `snat`)
