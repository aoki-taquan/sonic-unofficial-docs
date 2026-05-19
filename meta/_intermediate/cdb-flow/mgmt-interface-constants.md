# MGMT_INTERFACE — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-swss/cfgmgr/intfmgr.cpp` (IntfMgr ハードコード定数)
- `sonic-buildimage/src/sonic-config-engine/minigraph.py` (eth0 名ハードコード、gwaddr 算出)

---

## 1. IntfMgr 静的定数 (intfmgr.cpp L24-29)

| 定数名 | 値 | 用途 | ソース行 |
|---|---|---|---|
| `DEFAULT_MTU_STR` | **9100** | 通常インターフェース MTU フォールバック値。`mtu` フィールド欠落時に適用 | `intfmgr.cpp:402` |
| `LOOPBACK_DEFAULT_MTU_STR` | **65536** | Loopback インターフェース (`Loopback*`) 作成時の固定 MTU | `intfmgr.cpp:201` |
| `MTU_INHERITANCE` | **"0"** | サブインターフェースが親 MTU を継承するセンチネル値 | `intfmgr.cpp:24` |
| `VRF_MGMT` | **"mgmt"** | 管理 VRF 名。`MGMT_VRF_CONFIG.mgmtVrfEnabled=true` 時に `ip route add ... table mgmt` へ渡される | `intfmgr.cpp:26` |

## 2. eth0 ハードコード (minigraph.py)

`minigraph.py:2874,2880` で管理インターフェース名として `"eth0"` がリテラルでハードコード。XML `ManagementIPInterfaces` に記載のインターフェース名に関わらず MGMT_INTERFACE キーの第1要素は常に `eth0` 固定。

## 3. MGMT_INTERFACE と DEFAULT_MTU_STR の関係

MGMT_INTERFACE テーブル自体には `mtu` フィールドが YANG で定義されていない。`DEFAULT_MTU_STR=9100` は `INTERFACE` / `VLAN_INTERFACE` 等の通常 IF 向けであり、管理 IF (`eth0`) の MTU は kernel/platform デフォルト（通常 1500）に依存する。
