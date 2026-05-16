# MGMT_VRF_CONFIG 副次 DB 書込 詳細分析 (Phase F)

> 調査日: 2026-05-16
> ソース: `sonic-swss/cfgmgr/vrfmgr.cpp`, `sonic-host-services/scripts/hostcfgd`, `sonic-buildimage/files/image_config/interfaces/interfaces.j2`

## 概要

`MGMT_VRF_CONFIG|vrf_global` への SET/DEL が CONFIG_DB 外へ引き起こす書込みおよびカーネル・ファイルシステム操作を整理する。主担当プロセスは `vrfmgrd` (cfgmgr/vrfmgr.cpp) と `hostcfgd` (sonic-host-services/scripts/hostcfgd)。

---

## 1. vrfmgrd (cfgmgr/vrfmgr.cpp)

CONFIG_DB `MGMT_VRF_CONFIG` を購読し、管理 VRF の Linux netdev 登録と下流 DB への書込みを担当する。

### 1-1. SET 時副次書込み（mgmtVrfEnabled=true かつ in_band_mgmt_enabled=true の場合のみ）

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 | ソース |
|------|------------------|-----------------|------|--------|
| `m_stateVrfTable.set("mgmt", [{state:"ok"}])` | STATE_DB / `VRF_TABLE` | `mgmt` field=`state` value=`ok` | setLink 後（mgmt VRF は table_id=6000 を内部 map に登録するのみ） | vrfmgr.cpp:289 |
| `m_appVrfTableProducer.set("mgmt", fields)` | APPL_DB / `VRF_TABLE` | `mgmt` | CFG_MGMT_VRF_CONFIG_TABLE_NAME 経由 SET の場合 | vrfmgr.cpp:293–304 |

カーネル副作用 (DB 外):
- mgmt VRF の場合 `setLink("mgmt")` は `ip link add` を実行せず table_id=6000 を内部 map に登録するのみ (vrfmgr.cpp:176–183)
- 実際のカーネル netns 作成・`ip vrf add mgmt` は hostcfgd の `interfaces-config` restart が担う（責務分離）

### 1-2. DEL 時副次書込み

SET 時に `mgmtVrfEnabled=false` または `in_band_mgmt_enabled=false` の場合は `op = DEL_COMMAND` に強制変換 (vrfmgr.cpp:257)。

| 操作 | 対象 DB / テーブル | キー | 条件 | ソース |
|------|------------------|------|------|--------|
| `m_appVrfTableProducer.del("mgmt")` | APPL_DB / `VRF_TABLE` | `mgmt` | STATE_DB に該当エントリが存在する場合 | vrfmgr.cpp:338 |
| `m_stateVrfTable.del("mgmt")` | STATE_DB / `VRF_TABLE` | `mgmt` | 同上 | vrfmgr.cpp:339 |

カーネル副作用: `delLink("mgmt")` は `ip link del` を実行せず内部 map からエントリを削除するのみ (vrfmgr.cpp:148–153)。

DEL 遅延条件: orchagent が `STATE_DB.VRF_OBJECT_TABLE|mgmt` を保持する間、`isVrfObjExist()` で DEL をブロックし無制限待機 (vrfmgr.cpp:331–345)。

---

## 2. hostcfgd (sonic-host-services/scripts/hostcfgd)

CONFIG_DB `MGMT_VRF_CONFIG` を `ConfigDBConnector` で購読し、`mgmt_vrf_handler` → `update_mgmt_vrf()` を呼び出す。

### 2-1. SET 時副次書込み・カーネル操作

DB への直接書込みはなし。以下のシステムコールを順次実行する:

| 操作 | 対象 | 条件 | ソース |
|------|------|------|--------|
| `systemctl stop chrony` | chrony デーモン停止 | `mgmtVrfEnabled` 変更時 | hostcfgd:1660 |
| `systemctl restart interfaces-config` | `/etc/network/interfaces` 再生成 + `ifup eth0` | 同上 | hostcfgd:1661 |
| `systemctl start chrony` | chrony デーモン再起動（mgmt VRF で NTP 動作） | 同上 | hostcfgd:1662 |

`interfaces-config` が行う `/etc/network/interfaces` 書込み:
- `interfaces.j2` テンプレートが `MGMT_VRF_CONFIG.vrf_global.mgmtVrfEnabled == "true"` を評価 (interfaces.j2:9)
- `true` の場合: `auto mgmt` / `iface mgmt` / `vrf-table 6000` スタンザを追記 (interfaces.j2:10–12)
- `auto lo-m` / `up ip link set dev lo-m master mgmt` も追記（mgmt VRF 用 loopback） (interfaces.j2:13–15)
- eth0 に `vrf mgmt` オプションを付与 (interfaces.j2:88–90)
- `/etc/network/interfaces` への実際の書込みは `sonic-cfggen -t interfaces.j2,/etc/network/interfaces` コマンドが担う (interfaces-config.sh:69)

### 2-2. mgmtVrfEnabled=true 時の追加カーネル操作

`/proc/net/route` を grep して eth0 の metric=202 デフォルトルートが存在する場合:
- `ip -4 route del default dev eth0 metric 202` で eth0 のデフォルトルートを削除 (hostcfgd:1693)

---

## 3. STATE_DB / APPL_DB スキーマまとめ

| 論理役割 | DB | テーブル名定数 | 実テーブル名 | 書込みプロセス |
|---------|-----|--------------|------------|--------------|
| VRF readiness sentinel | STATE_DB | `STATE_VRF_TABLE_NAME` | `VRF_TABLE` | vrfmgrd (vrfmgr.cpp:289) |
| APPL VRF エントリ | APPL_DB | `APP_VRF_TABLE_NAME` | `VRF_TABLE` | vrfmgrd (vrfmgr.cpp:303) |

スキーマ定義: `sonic-swss-common/common/schema.h:429` (STATE_DB) / `schema.h:80` (APPL_DB)

VXLAN_VRF_TABLE / VNET_TABLE への書込みは MGMT_VRF_CONFIG 経路では発生しない（VNI 非ゼロかつ EVPN NVO トンネル設定時のみ、mgmt VRF では通常未設定）。

---

## 4. ファイルシステム書込みまとめ

| ファイル | 書込み内容 | トリガー | 担当 |
|---------|-----------|---------|------|
| `/etc/network/interfaces` | mgmt VRF スタンザ追加 (`vrf-table 6000`, `vrf mgmt`, `auto lo-m` 等) | `interfaces-config` restart | `sonic-cfggen` (interfaces.j2) |
| `/etc/sysctl.d/90-dhcp6-systcl.conf` | DHCPv6 sysctl 設定（間接的に再生成） | `interfaces-config` restart | `sonic-cfggen` |

---

## 5. 確認コマンド

```bash
# STATE_DB VRF readiness sentinel
sonic-db-cli STATE_DB hgetall 'VRF_TABLE|mgmt'

# APPL_DB VRF エントリ
sonic-db-cli APPL_DB hgetall 'VRF_TABLE:mgmt'

# /etc/network/interfaces 内容確認
grep -A5 'iface mgmt' /etc/network/interfaces

# mgmt VRF 状態確認
show mgmt-vrf
ip vrf show mgmt
```
