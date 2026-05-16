# COPP_TRAP テーブル — Phase E: ハードコード定数調査

## 調査対象ファイル

- `sonic-swss/orchagent/copporch.h`
- `sonic-swss/orchagent/copporch.cpp`
- `sonic-buildimage/files/image_config/copp/copp_cfg.j2`

---

## ハードコード定数一覧

### フィールド名定数 (copporch.h)

COPP_TRAP に直接関係するフィールド名定数。CONFIG_DB のキーとして参照される。

| 定数名 | 値 | 定義場所 | 用途 |
|--------|-----|---------|------|
| `copp_trap_id_list` | `"trap_ids"` | `copporch.h:26` | COPP_TRAP の trap_ids フィールド識別子 |
| `copp_trap_action_field` | `"trap_action"` | `copporch.h:27` | COPP_GROUP の trap_action フィールド識別子 |
| `copp_trap_priority_field` | `"trap_priority"` | `copporch.h:28` | COPP_GROUP の trap_priority フィールド識別子 |
| `copp_queue_field` | `"queue"` | `copporch.h:30` | COPP_GROUP の queue フィールド識別子 |
| `copp_policer_cbs_field` | `"cbs"` | `copporch.h:36` | policer の CBS フィールド識別子 |
| `copp_policer_cir_field` | `"cir"` | `copporch.h:37` | policer の CIR フィールド識別子 |
| `copp_policer_pbs_field` | `"pbs"` | `copporch.h:38` | policer の PBS フィールド識別子 |
| `copp_policer_pir_field` | `"pir"` | `copporch.h:39` | policer の PIR フィールド識別子 |

### ランタイム定数 (copporch.cpp)

| 定数名 | 値 | 定義場所 | 用途 |
|--------|-----|---------|------|
| `default_trap_group` | `"default"` | `copporch.cpp:184` | 初期化時のデフォルトトラップグループ名 |
| `default_trap_ids` (TTL_ERROR) | `SAI_HOSTIF_TRAP_TYPE_TTL_ERROR` | `copporch.cpp:185-187` | 起動時に自動インストールされるデフォルト trap ID |
| default trap priority | **1** | `copporch.cpp:357` | デフォルト trap の SAI_HOSTIF_TRAP_ATTR_TRAP_PRIORITY 値（Mellanox / Marvell を除く） |
| `HOSTIF_TRAP_COUNTER_POLLING_INTERVAL_MS` | **10000** ms | `copporch.cpp:189` | hostif trap カウンタのポーリング間隔 |

### ビルド時デフォルト値 (copp_cfg.j2)

`copp_cfg.j2` が生成する `COPP_GROUP` エントリの queue / priority / cir / cbs ハードコード値。COPP_TRAP は trap_group を通じてこれらの値を間接的に参照する。

| グループ名 | queue | trap_priority | cir (pps) | cbs (packets) |
|-----------|-------|--------------|-----------|----------------|
| `default` | **0** | — | **600** | **600** |
| `queue4_group1` | **4** | **4** | **6000** | **6000** |
| `queue4_group2` | **4** | **4** | **600** | **600** |
| `queue4_group3` | **4** | **4** | **100** / **300**※ | **100** / **300**※ |
| `queue1_group1` | **1** | **1** | **6000** | **6000** |
| `queue1_group2` | **1** | **1** | **600** | **600** |
| `queue1_group3` | **1** | **1** | **200** | **200** |
| `queue2_group1` | **2** | **1** | **1000** | **1000** |

※ `queue4_group3` の cir/cbs は `DEVICE_METADATA.localhost.type` に `'Mgmt'` が含まれる場合 **300**、含まれない場合 **100** (`copp_cfg.j2:36-43`)。

### COPP_TRAP → COPP_GROUP マッピング (copp_cfg.j2)

| COPP_TRAP エントリ | trap_ids | trap_group |
|-------------------|----------|------------|
| `bgp` | `bgp,bgpv6` | `queue4_group1` (cir=6000, queue=4) |
| `lacp` | `lacp` | `queue4_group1` (cir=6000, queue=4) |
| `arp` | `arp_req,arp_resp,neigh_discovery` | `queue4_group2` (cir=600, queue=4) |
| `lldp` | `lldp` | `queue4_group3` (cir=100/300, queue=4) |
| `dhcp_relay` | `dhcp,dhcpv6` | `queue4_group3` (cir=100/300, queue=4) |
| `udld` | `udld` | `queue4_group3` (cir=100/300, queue=4) |
| `ip2me` | `ip2me` | `queue1_group1` (cir=6000, queue=1) |
| `macsec` | `eapol` | `queue4_group1` (cir=6000, queue=4) |
| `nat` | `src_nat_miss,dest_nat_miss` | `queue1_group2` (cir=600, queue=1) |
| `sflow` | `sample_packet` | `queue2_group1` (cir=1000, queue=2) |
| `neighbor_miss` | `neighbor_miss` | `queue1_group3` (cir=200, queue=1) |

---

## 特記事項

1. **trap_priority はプラットフォーム依存** — `processCoppTrap()` 内で `MLNX_PLATFORM_SUBSTRING` / `MRVL_PRST_PLATFORM_SUBSTRING` が検出された場合、`SAI_HOSTIF_TRAP_ATTR_TRAP_PRIORITY` は設定されない (`copporch.cpp:1186-1194`)。Mellanox・Marvell では trap_priority フィールドが実質 no-op。
2. **queue / cir / cbs は COPP_GROUP 側の定数** — COPP_TRAP 自体は queue/cir/cbs を持たず、`trap_group` 参照を通じて COPP_GROUP の値を間接参照する構造。queue/cir/cbs の実ハードコード値は COPP_GROUP 側に存在。
3. **copp_cfg.j2 生成値は /etc/sonic/copp_cfg.json に書き出される** — ビルド時に `sonic-cfggen` が処理し、コンテナ起動時に CONFIG_DB へロード。YANG スキーマとは別経路。
4. **デフォルト TTL_ERROR trap** — `initDefaultTrapIds()` が起動時に SAI_HOSTIF_TRAP_TYPE_TTL_ERROR を `default` トラップグループに priority=1 でインストール。CONFIG_DB に記載はなく純粋にハードコード (`copporch.cpp:330-368`)。
