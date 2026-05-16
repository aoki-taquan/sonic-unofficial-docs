# VLAN_MEMBER — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-swss/cfgmgr/vlanmgr.cpp`
- `sonic-swss/orchagent/portsorch.cpp`
- `sonic-swss/tests/test_vlan.py`

---

## 発見された定数一覧

### vlanmgr.cpp (#define)

| 定数名 | 値 | 用途 |
|--------|-----|------|
| `DOT1Q_BRIDGE_NAME` | `"Bridge"` | Linux dot1q ブリッジデバイス名（固定） |
| `VLAN_PREFIX` | `"Vlan"` | VLAN インタフェース名プレフィクス |
| `LAG_PREFIX` | `"PortChannel"` | LAG インタフェース名プレフィクス |

出典: `sonic-swss/cfgmgr/vlanmgr.cpp` lines 15–17

### tagging_mode enum 値 (vlanmgr.cpp)

| 値 | 受理 | bridge コマンド |
|----|------|----------------|
| `"untagged"` | ✅ | `pvid untagged` (vlanmgr.cpp:238) |
| `"tagged"` | ✅ | オプションなし (vlanmgr.cpp:246) |
| `"priority_tagged"` | ✅ | `pvid untagged`（untagged と同一） (vlanmgr.cpp:238) |
| その他 | ❌ | `SWSS_LOG_ERROR("Wrong tagging_mode")` で破棄 (vlanmgr.cpp:659–662) |

受理される tagging_mode は 3 値のみ。validation は vlanmgr.cpp:658–662 で実施。

### SAI VLAN_MEMBER 属性 (portsorch.cpp)

| SAI 属性 | 用途 |
|---------|------|
| `SAI_VLAN_MEMBER_ATTR_VLAN_ID` | メンバが所属する VLAN OID を指定 (portsorch.cpp:7531) |
| `SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID` | メンバポートのブリッジポート OID (portsorch.cpp:7535) |
| `SAI_VLAN_MEMBER_ATTR_VLAN_TAGGING_MODE` | タグモードの SAI 列挙値 (portsorch.cpp:7541) |

### SAI tagging_mode 列挙値マッピング (portsorch.cpp:7540–7547)

| CONFIG_DB 値 | SAI 定数 |
|------------|---------|
| `"untagged"` | `SAI_VLAN_TAGGING_MODE_UNTAGGED` |
| `"tagged"` | `SAI_VLAN_TAGGING_MODE_TAGGED` |
| `"priority_tagged"` | `SAI_VLAN_TAGGING_MODE_PRIORITY_TAGGED` |

デフォルト初期値: `SAI_VLAN_TAGGING_MODE_TAGGED` (portsorch.cpp:7540)。  
マッピング外の値は `assert(false)` (portsorch.cpp:7548)。

---

## 特記事項

1. **`priority_tagged` と `untagged` の bridge レベル同一性**: Linux bridge コマンドは両値とも `pvid untagged` を使用 (vlanmgr.cpp:238)。SAI レベルでは `SAI_VLAN_TAGGING_MODE_PRIORITY_TAGGED` として区別される。
2. **CLI 経路での `priority_tagged` 欠落**: `config vlan member add` (sonic-utilities/config/vlan.py:407) は `tagged`/`untagged` のみを許可し、`priority_tagged` を設定する CLI 経路は存在しない。
3. **デフォルト初期値**: portsorch.cpp は SAI 呼び出し直前に `SAI_VLAN_TAGGING_MODE_TAGGED` を初期値にセットし、文字列マッチで上書き。assert による安全網あり。

---

## 出典

- `sonic-swss/cfgmgr/vlanmgr.cpp` lines 15–17, 233–246, 648–662, 873
- `sonic-swss/orchagent/portsorch.cpp` lines 7531–7548
- `sonic-swss/tests/test_vlan.py` lines 351–353, 459–461
