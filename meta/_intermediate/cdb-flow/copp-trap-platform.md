# COPP_TRAP — Phase H: プラットフォーム差 (SAI capability / vendor)

生成日: 2026-05-15  
対象ページ: `docs/reference/config-db/copp-trap.md`  
evidence sources: `sonic-swss/orchagent/copporch.cpp`, `sonic-swss/orchagent/orch.h`, `sonic-swss/orchagent/main.cpp`

---

## H-1. SAI capability クエリと fallback

`CoppOrch::publishTrapIdsCapability()` (copporch.cpp:240-299) が起動時に一度だけ実行される。

```
sai_query_attribute_enum_values_capability(gSwitchId,
    SAI_OBJECT_TYPE_HOSTIF_TRAP,
    SAI_HOSTIF_TRAP_ATTR_TRAP_TYPE,
    &enum_values_capability)
```

- **成功**: ベンダー SAI が返した trap_id 一覧を `supported_trap_ids` (unordered_set) に格納し、STATE_DB `COPP_TRAP_CAPABILITY_TABLE|traps` に `trap_ids` フィールドとして publish。
- **失敗 (SAI_STATUS != SUCCESS)**: SWSS_LOG_NOTICE を出力し、ソースコード内に static に定義された `default_supported_trap_ids` (copporch.cpp:106-151) へフォールバック。

### `default_supported_trap_ids` — フォールバックリスト

capability クエリ非対応のベンダー SAI 向けに定義された静止リスト (copporch.cpp:106-151)。以下の trap_id を含む:

`stp, lacp, eapol, lldp, pvrst, igmp_query, igmp_leave, igmp_v1_report, igmp_v2_report, igmp_v3_report, sample_packet, switch_cust_range, arp_req, arp_resp, dhcp, ospf, pim, vrrp, bgp, dhcpv6, ospfv6, isis, vrrpv6, bgpv6, neigh_discovery, mld_v1_v2, mld_v1_report, mld_v1_done, mld_v2_report, ip2me, ssh, snmp, router_custom_range, l3_mtu_error, ttl_error, udld, bfd, bfdv6, src_nat_miss, dest_nat_miss, ldp, bfd_micro, bfdv6_micro`

注: `neighbor_miss` はこのフォールバックリストに**含まれない**。  
`copp_cfg.j2` は `neighbor_miss` エントリを定義するが、フォールバック時は SAI が非対応として個別スキップされる。

---

## H-2. NAT 非対応プラットフォーム

`gIsNatSupported` フラグ (orchdaemon.cpp:78, main.cpp:935-948) は、起動時に `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` を SAI に問い合わせ、返値が 0 の場合は `false` のまま (デフォルト)。

- NAT 非対応スイッチ (`gIsNatSupported == false`) では、`src_nat_miss` / `dest_nat_miss` の trap_id は `getTrapIdList()` 内でスキップ (SWSS_LOG_NOTICE)。copporch.cpp:401-405

---

## H-3. Mellanox / Marvell-Prestera — trap_priority 非対応

`getenv("platform")` で文字列照合 (orch.h:41-42):

```c
#define MLNX_PLATFORM_SUBSTRING "mellanox"
#define MRVL_PRST_PLATFORM_SUBSTRING "marvell-prestera"
```

- 上記プラットフォームでは `SAI_HOSTIF_TRAP_ATTR_TRAP_PRIORITY` を SET しない。
  - `initDefaultTrapIds()` (copporch.cpp:332-368): TTL_ERROR デフォルト trap 設定時にも priority を skip
  - `processCoppTrap()` (copporch.cpp:1184-1195): `trap_priority` フィールド受信時も skip
- 影響: `COPP_GROUP.trap_priority` フィールドを設定しても、Mellanox / Marvell-Prestera ではハードウェアに反映されない (NOTICE ログなし — サイレント skip)。

---

## H-4. STATE_DB への capability publish

`CoppOrch` コンストラクタが以下の STATE_DB テーブルを管理:

| STATE_DB テーブル | 定数名 | 内容 |
|---|---|---|
| `COPP_TRAP_CAPABILITY_TABLE` | `STATE_COPP_TRAP_CAPABILITY_TABLE_NAME` | `traps` key に `trap_ids` フィールド (カンマ区切り、ベンダー SAI 対応分) |
| `COPP_TRAP_TABLE` | `STATE_COPP_TRAP_TABLE_NAME` | 各 trap の `hw_status` (updateTrapOperStatus で更新) |

`show copp capabilities` 等のコマンドはこの STATE_DB エントリを参照する。

---

## H-5. `neighbor_miss` の特殊性

- `trap_id_map` には `neighbor_miss → SAI_HOSTIF_TRAP_TYPE_NEIGHBOR_MISS` が含まれる (copporch.cpp:99)
- しかし `default_supported_trap_ids` には含まれない (capability クエリ非対応のベンダーでは非サポート扱い)
- `copp_cfg.j2` L135-136 で `neighbor_miss` エントリが定義されているため、capability クエリが成功するベンダー SAI でのみ有効化される

---

## まとめ

| プラットフォーム差 | 影響フィールド | 挙動 | evidence |
|---|---|---|---|
| SAI capability クエリ非対応 | `trap_ids` | `default_supported_trap_ids` へフォールバック。`neighbor_miss` 等一部 trap_id が無効 | copporch.cpp:263-271 |
| NAT 非対応 (`SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY == 0`) | `trap_ids`: `src_nat_miss`, `dest_nat_miss` | スキップ (NOTICE ログ) | main.cpp:935-948, copporch.cpp:401-405 |
| Mellanox (`mellanox`) | `trap_priority` | SAI_HOSTIF_TRAP_ATTR_TRAP_PRIORITY を SET しない (サイレント) | copporch.cpp:354, 1189 |
| Marvell-Prestera (`marvell-prestera`) | `trap_priority` | 同上 | copporch.cpp:354, 1189 |
| その他 (Broadcom 等) | `trap_priority` | priority=1 デフォルト設定、カスタム値も有効 | copporch.cpp:356-358 |
