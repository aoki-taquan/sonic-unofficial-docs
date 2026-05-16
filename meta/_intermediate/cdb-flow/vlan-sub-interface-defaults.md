# VLAN_SUB_INTERFACE フィールド暗黙デフォルト調査メモ

調査日: 2026-05-16
対象テーブル: CONFIG_DB `VLAN_SUB_INTERFACE`

## 調査対象ファイル

- `sonic-swss/cfgmgr/intfmgr.cpp` (IntfMgr クラス、sub-interface 経路)
- `sonic-swss/cfgmgr/vlanmgr.cpp` (VlanMgr クラス、関連: VLAN tag / MTU 既定)

---

## マクロ定義 (intfmgr.cpp)

```cpp
// sonic-swss/cfgmgr/intfmgr.cpp:24-29
#define MTU_INHERITANCE     "0"
#define LOOPBACK_DEFAULT_MTU_STR "65536"
#define DEFAULT_MTU_STR 9100
```

`MTU_INHERITANCE = "0"` は「親 IF の MTU を継承する」というセンチネル値。
`DEFAULT_MTU_STR = 9100` は親 IF の MTU が取得できない場合のフォールバック値 (`updateSubIntfMtu` で使用)。

---

## フィールド別 暗黙デフォルト

### `mtu`

**コード由来デフォルト**: `"0"` (MTU_INHERITANCE、親 IF の MTU を継承)

```cpp
// sonic-swss/cfgmgr/intfmgr.cpp:973-978
if (!mtu.empty())
{
    // ... setHostSubIntfMtu(alias, mtu, parentMtu) で親 MTU を上限に clamp
}
else
{
    FieldValueTuple fvTuple("mtu", MTU_INHERITANCE);
    data.push_back(fvTuple);
    m_subIntfList[alias].mtu = MTU_INHERITANCE;
}
```

`mtu` フィールドが CONFIG_DB に存在しない場合、`intfmgrd` が APP_DB へ `mtu = "0"` を書き、`updateSubIntfMtu()` 経路で実効値は親 IF の MTU と同値になる。

親 IF MTU が取得できない場合 (`updateSubIntfMtu`):

```cpp
// sonic-swss/cfgmgr/intfmgr.cpp:418-421
string subif_config_mtu = m_subIntfList[intf].mtu;
if (subif_config_mtu == MTU_INHERITANCE || subif_config_mtu.empty())
    subif_config_mtu = std::to_string(DEFAULT_MTU_STR);  // 9100
```

---

### `admin_status`

**コード由来デフォルト**: `"up"`

```cpp
// sonic-swss/cfgmgr/intfmgr.cpp:980-985
if (adminStatus.empty())
{
    adminStatus = "up";
    FieldValueTuple fvTuple("admin_status", adminStatus);
    data.push_back(fvTuple);
}
```

その後 `setHostSubIntfAdminStatus(alias, adminStatus, parentAdmin)` で実効 admin status を決定:

```cpp
// sonic-swss/cfgmgr/intfmgr.cpp:512-525
std::string IntfMgr::setHostSubIntfAdminStatus(
    const string &alias, const string &admin_status, const string &parent_admin_status)
{
    if (parent_admin_status == "up" || admin_status == "down")
    {
        // 親が up のときのみ sub-IF の admin_status を ip link で適用
        // ただし sub-IF 側が down 指定なら親に関わらず down 適用
        setIntfAdminStatus(alias, admin_status);
        return admin_status;
    }
    // 親が down の場合は sub-IF は親に従う (parent_admin_status を返す)
    ...
}
```

実効値:

| 親 admin_status | sub-IF 指定 | 実効 admin_status |
|-----------------|-------------|-------------------|
| `up` | `up` (省略時の既定含む) | `up` |
| `up` | `down` | `down` |
| `down` | `up` | `down` (親に従う) |
| `down` | `down` | `down` |

---

### `vlan` (encapsulation VLAN ID, short-name 形式)

**コード由来デフォルト**: なし (必須)

```cpp
// sonic-swss/cfgmgr/intfmgr.cpp:936-940
if (vlanId == "0" || vlanId.empty())
{
    SWSS_LOG_INFO("Vlan ID not configured for sub interface %s", alias.c_str());
    return false;  // リトライ待ち
}
```

short-name (`Po1.10`, `Eth0.100` 等) の場合に `vlan` フィールドが省略されると `addHostSubIntf` 自体を実行せず、CONFIG_DB に値が現れるまでリトライ待ちになる。実装上は必須フィールド。

long-name (`Ethernet0.100`, `PortChannel10.100`) では `vlanId = std::to_string(subIntfId)` で名前のドット後 ID が自動採用される:

```cpp
// sonic-swss/cfgmgr/intfmgr.cpp:763-767
int subIntfId = subIf.subIntfIdx();
if (subIntfId > 0)
{
    vlanId = std::to_string(subIntfId);
}
```

---

### `loopback_action` / `vrf_name` / `vnet_name`

**コード由来デフォルト**: なし (empty pass-through)

`intfmgr.cpp:782-828` で各フィールドはローカル変数初期化が空文字 (`""`)。空のまま APP_DB へ書き戻されるブロックは `if (!loopback_action.empty())` 等でガードされ、未指定時は APP_DB に当該キーが現れない。`orchagent` / `intfsorch` 側のデフォルトに従う。

---

## parent / sub-IF 関係 (派生情報)

- sub-interface alias は `<parent>.<vlanId>` 形式。`subIntf` クラスが `parentIntf()` と `subIntfIdx()` を提供 (intfmgr.cpp:753, 757, 762)。
- `parentAlias.empty()` でない (= sub-IF と判定された) パスでのみ MTU / admin_status の上記既定処理が走る (intfmgr.cpp:931 以降)。
- 親 IF が `isIntfStateOk()` を満たさない場合は `return false` でリトライ待ち (intfmgr.cpp:833-837)。
- 親 MTU は `getIntfMtu(subIf.parentIntf())` で取得し、`setHostSubIntfMtu` で sub-IF MTU を親 MTU 以下にクランプする (intfmgr.cpp:959-960)。

---

## 関連: vlanmgr.cpp の VLAN tag 既定

vlanmgr は `VLAN` / `VLAN_MEMBER` テーブル担当で VLAN_SUB_INTERFACE は直接扱わないが、参考までに encapsulation/tagging に関する既定:

```cpp
// sonic-swss/cfgmgr/vlanmgr.cpp:18-19
#define DEFAULT_VLAN_ID     "1"
#define DEFAULT_MTU_STR     "9100"
```

- `VLAN_MEMBER.tagging_mode` 既定: `"untagged"` (`vlanmgr.cpp:648`)。
- VLAN bridge の Default VLAN は `1`。VLAN_SUB_INTERFACE は通常別系統 (kernel 上は `type vlan id` の sub-IF) で、bridge default VLAN とは独立。

---

## 要約表

| フィールド | コード由来デフォルト | 出典 | 備考 |
|-----------|---------------------|------|------|
| `mtu` | `"0"` (MTU_INHERITANCE) | intfmgr.cpp:975-977 | 実効値は親 IF の MTU。親 MTU 不明時は `9100` |
| `admin_status` | `"up"` | intfmgr.cpp:982-983 | 親が `down` の場合は親に従う |
| `vlan` (short-name) | なし (必須) | intfmgr.cpp:936-940 | 未設定時はリトライ待ち |
| `vlan` (long-name) | 名前のドット後 ID | intfmgr.cpp:763-767 | `subIntfIdx()` から自動採用 |
| `loopback_action` | なし (省略時 APP_DB に書かない) | intfmgr.cpp:893-898 | orchagent 側既定に従う |
| `vrf_name` / `vnet_name` | なし (省略時 default VRF) | intfmgr.cpp:789-792 | leafref。空のまま pass-through |

---

## 証拠リンク

- `sonic-swss/cfgmgr/intfmgr.cpp:24-29` — マクロ定義 (`MTU_INHERITANCE`, `DEFAULT_MTU_STR`)
- `sonic-swss/cfgmgr/intfmgr.cpp:753-767` — `subIntf` 経路、`subIntfIdx()` 採用
- `sonic-swss/cfgmgr/intfmgr.cpp:931-1005` — `parentAlias` 非空時の MTU / admin_status 既定処理
- `sonic-swss/cfgmgr/intfmgr.cpp:512-530` — `setHostSubIntfAdminStatus` (親との合成)
- `sonic-swss/cfgmgr/intfmgr.cpp:407-429` — `updateSubIntfMtu` (親 MTU 不明時の `DEFAULT_MTU_STR` 採用)
- `sonic-swss/cfgmgr/vlanmgr.cpp:18-19, 648` — 参考 (VLAN tag 既定、`tagging_mode` 既定)
