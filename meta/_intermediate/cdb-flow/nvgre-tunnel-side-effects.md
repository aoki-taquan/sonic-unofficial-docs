# NVGRE_TUNNEL / NVGRE_TUNNEL_MAP — Phase F 副次 DB 書込 調査ノート

## 調査対象

- `sonic-swss/orchagent/nvgreorch.cpp`
- `sonic-swss/orchagent/nvgreorch.h`
- 調査日: 2026-05-19

## 調査方法

`nvgreorch.cpp` 全行を `AppTable`, `ProducerStateTable`, `StateTable`, `hset(`, `set(`, `APPL_DB`, `STATE_DB`, `COUNTERS_DB`, `FLEX_COUNTER_DB` でスキャンして副次書込みを確認。

## ASIC_DB 書込み（SAI 経由）

`NvgreTunnelOrch` / `NvgreTunnelMapOrch` は CONFIG_DB の変化を受けて直接 SAI API を呼び出す。syncd が SAI 呼び出しを ASIC_DB に反映する。

### SET NVGRE_TUNNEL

`NvgreTunnel` コンストラクタ (`nvgreorch.cpp:62-333`) が以下を順次 SAI 呼び出し:

1. `sai_tunnel_map_api->create_tunnel_map()` ×4 (MAP_T_VLAN/MAP_T_BRIDGE × encap/decap)
   - `SAI_OBJECT_TYPE_TUNNEL_MAP` 4個
   - evidence: `nvgreorch.cpp:106-155`

2. `sai_tunnel_api->create_tunnel()` ×1
   - `SAI_OBJECT_TYPE_TUNNEL` (type=SAI_TUNNEL_TYPE_NVGRE)
   - evidence: `nvgreorch.cpp:177-205`

3. `sai_tunnel_api->create_tunnel_term_table_entry()` ×1
   - `SAI_OBJECT_TYPE_TUNNEL_TERM_TABLE_ENTRY` (type=SAI_TUNNEL_TERM_TABLE_ENTRY_TYPE_P2MP)
   - evidence: `nvgreorch.cpp:235-261`

### SET NVGRE_TUNNEL_MAP

`addMapperEntry()` (`nvgreorch.cpp:390-442`) が:
- `sai_tunnel_map_api->create_tunnel_map_entry()` ×2 (decap: VSID→VLAN + encap: VLAN→VSID)
- `SAI_OBJECT_TYPE_TUNNEL_MAP_ENTRY` 2個
- evidence: `nvgreorch.cpp:415-441`

### DEL NVGRE_TUNNEL

`removeNvgreTunnel()` (`nvgreorch.cpp:282-330`) が上記 SAI オブジェクトを逆順で削除:
- `remove_tunnel_term_table_entry()` → `remove_tunnel()` → `remove_tunnel_map()` ×4

### DEL NVGRE_TUNNEL_MAP

`delMapperEntry()` (`nvgreorch.cpp:519-544`) が:
- `sai_tunnel_map_api->remove_tunnel_map_entry()` ×2

## APPL_DB 書込み

なし。`nvgreorch.cpp` に ProducerStateTable / AppTable への書込みは存在しない。

## STATE_DB 書込み

なし。`nvgreorch.cpp` に StateTable / `hset()` への書込みは存在しない。

## FLEX_COUNTER_DB 書込み

なし。`nvgreorch.cpp` に `addFlexCounter` / `FLEX_COUNTER_DB` 参照は存在しない。

## COUNTERS_DB 書込み

なし。NVGRE トンネル統計のカウンタマップ登録は nvgreorch.cpp で行われない。
