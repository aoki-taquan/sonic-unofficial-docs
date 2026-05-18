# PORTCHANNEL_INTERFACE テーブル — 暗黙参照マップ調査 (Phase C)

調査対象ソース:
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-portchannel.yang`
- `sonic-swss/cfgmgr/intfmgr.cpp`
- `sonic-swss/cfgmgr/natmgr.cpp`
- `sonic-swss/neighsyncd/neighsync.cpp`

## PORTCHANNEL_INTERFACE が参照するテーブル（→ 方向）

### YANG leafref 制約

| 参照先テーブル | YANG パス | 意味 |
|---|---|---|
| `PORTCHANNEL_LIST` (同 YANG 内) | `PORTCHANNEL_INTERFACE_LIST.name` → `/lag:sonic-portchannel/lag:PORTCHANNEL/lag:PORTCHANNEL_LIST/lag:name` | key の LAG 名は PORTCHANNEL テーブルに存在しなければならない |
| `PORTCHANNEL_IPPREFIX_LIST.name` | 同上 | IP プレフィクスロウの LAG 名も同様 |
| `VRF_LIST` (sonic-vrf.yang) | `PORTCHANNEL_INTERFACE_LIST.vrf_name` → `/vrf:sonic-vrf/vrf:VRF/vrf:VRF_LIST/vrf:name` | vrf_name フィールドは VRF テーブルに定義済みの VRF 名でなければならない |

ソース: `sonic-portchannel.yang:170-178, 227-229`

### ランタイム依存テーブル (intfmgrd)

`intfmgr.cpp` の `isIntfStateOk()` が SET 処理前に確認する STATE_DB テーブル:

| 確認先 DB / テーブル | 確認関数 | 目的 |
|---|---|---|
| `STATE_DB::LAG_TABLE` | `m_stateLagTable.get(alias, temp)` (`intfmgr.cpp:351-360`) | teamd が LAG を作成して STATE_DB に登録するまで処理保留 |
| `STATE_DB::VRF_TABLE` | `m_stateVrfTable.get(vrf_name, temp)` (`intfmgr.cpp:677-684`) | VRF が vrfmgrd により STATE_DB に登録されるまで処理保留 |
| `DEVICE_METADATA` (CONFIG_DB) | `cfgDeviceMetaDataTable.hget("localhost", "switch_type", ...)` (`intfmgr.cpp:72`) | VOQ / SmartSwitch 判定 |

## PORTCHANNEL_INTERFACE を参照するテーブル（← 方向）

### コード参照

| 参照元コンポーネント | 参照箇所 | 用途 |
|---|---|---|
| `natmgr.cpp:8178` | `CFG_LAG_INTF_TABLE_NAME` を `doNatIpInterfaceTask()` で購読 | NAT が PortChannel インタフェースの IP を取得して NAT テーブルを更新 |
| `neighsync.cpp:207` | `m_cfgLagInterfaceTable.get(port, values)` | PortChannel 上の neighbor を IPv6 link-local 判定で参照 |

### YANG 逆参照 (leafref)

他モジュールから `PORTCHANNEL_INTERFACE_LIST` を key として leafref 参照している YANG モデルは現行 sonic-yang-models には存在しない（`sonic-portchannel.yang` 内に完結）。

## ref_count ガード（orchagent）

`IntfsOrch` は RIF（Router Interface）を作成したポートについて内部参照カウント (`ref_count`) を管理する。`PORTCHANNEL_INTERFACE` の DEL を orchagent に送信しても、RIF が別オブジェクト（ネイバー / ルート）から参照されている場合は `Failed to remove ref count %d LAG %s` エラーを出力して処理を拒否する。

## 結論

- **YANG 依存**: `PORTCHANNEL` (name leafref) + `VRF` (vrf_name leafref) の 2 テーブルが上流
- **ランタイム依存**: STATE_DB の `LAG_TABLE` / `VRF_TABLE` を intfmgrd が参照
- **下流購読**: natmgrd・neighsyncd が PORTCHANNEL_INTERFACE を直接読み取る
- YANG 制約は存在するが、削除防護は YANG 逆 leafref ではなく orchagent の ref_count で実装されている
