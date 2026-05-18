# vlan-state Phase C: テーブル間クロスリファレンス調査

## 調査対象

STATE_DB `VLAN_TABLE` の暗黙参照テーブルを特定する。

## 書き込み側クロスリファレンス

### vlanmgr.cpp 側の依存

`VlanMgr::doVlanTask()` は `VLAN_TABLE` に書き込む前に以下を参照する:

1. **CONFIG_DB `VLAN`** (`CFG_VLAN_TABLE_NAME`) — 書き込みトリガー兼キーソース。`VLAN|VlanN` の SET/DEL が `doVlanTask()` を起動し、キー `VlanN` がそのまま `VLAN_TABLE|VlanN` のキーに転写される (`vlanmgr.cpp:443`)。
2. **gMacAddress** (グローバル変数) — `isVlanMacOk()` 経由で確認。未確定の間は全タスクを早期リターンする (`vlanmgr.cpp:318-322`)。

### gMacAddress の由来

`gMacAddress` は `vlanmgrd.cpp` 起動時に `syncd` / `APP_DB SWITCH_TABLE|switch` の `mac` フィールドから取得される。`DEVICE_METADATA|localhost` の `mac` フィールドとも連動する。

## 読み取り側クロスリファレンス（consumers）

STATE_DB `VLAN_TABLE` を `isVlanStateOk()` 相当のエントリ存在確認で参照する consumers:

| consumer | ファイル | 呼び出し箇所 | 用途 |
|---------|---------|------------|------|
| `vlanmgrd` 自身 | `cfgmgr/vlanmgr.cpp` | L371, L517-530, L642, L867 | warm-restart 重複スキップ / VLAN_MEMBER 追加前ガード |
| `intfmgrd` | `cfgmgr/intfmgr.cpp` | L39 (init), L655 (`isIntfStateOk`) | VLAN インタフェース (SVI) 設定前の readiness ガード |
| `nbrmgrd` | `cfgmgr/nbrmgr.cpp` | L48 (init) | ネイバーエントリ設定前ガード（`m_stateVlanTable` メンバーとして保持） |
| `stpmgrd` | `cfgmgr/stpmgr.cpp` | L31 (init), L210, L1276-1282 | STP VLAN/ポート設定前ガード (`isVlanStateOk`) |
| `natmgrd` | `cfgmgr/natmgr.cpp` | L39 (init), L102 (`isPortStateOk`) | NAT エントリ設定前の VLAN readiness ガード |
| `vxlanmgrd` | `cfgmgr/vxlanmgr.cpp` | L194 (init), L537, L767-774 | VXLAN tunnel member 設定前ガード (`isVlanStateOk`) |

## キー転写パターン

```
CONFIG_DB VLAN|VlanN  →  (vlanmgrd doVlanTask)  →  STATE_DB VLAN_TABLE|VlanN
```

キー名の変換はなく、`VlanN` がそのまま転写される。

## 参照方向サマリー

```
CONFIG_DB VLAN|VlanN ──SET/DEL──► vlanmgrd ──► STATE_DB VLAN_TABLE|VlanN
                                                         │
                             ┌───────────────────────────┤ 存在確認（GET）
                             ▼
           intfmgrd / nbrmgrd / stpmgrd / natmgrd / vxlanmgrd
```

## evidence

- `vlanmgr.cpp`: L27-33 (init), L318-322 (MAC guard), L371-378 (warm-restart), L437-443 (SET write order), L456-463 (DEL), L517-530 (isVlanStateOk), L642 (member guard)
- `intfmgr.cpp`: L39, L649-659
- `stpmgr.cpp`: L31, L210, L1276-1282
- `natmgr.cpp`: L39, L100-108
- `vxlanmgr.cpp`: L194, L537, L767-774
- `nbrmgr.cpp`: L48
- `schema.h`: L423 (`STATE_VLAN_TABLE_NAME = "VLAN_TABLE"`)
