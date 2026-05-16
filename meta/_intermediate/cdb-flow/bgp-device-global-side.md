# BGP_DEVICE_GLOBAL — Phase F: 副次 DB 書込スキャン中間ファイル

生成日: 2026-05-16 (Task F Phase F / cdb_q67_f)

## 調査対象

`docs/reference/config-db/bgp-device-global.md` 配下の CONFIG_DB `BGP_DEVICE_GLOBAL` テーブル (`|STATE` / `|CONFED`) への SET/DEL に対して、主購読者 (`bgpcfgd` の `DeviceGlobalCfgMgr` / `ChassisAppDbMgr`、orchagent の `BgpGlobalStateOrch`) が CONFIG_DB 以外の DB へ書き込みを行うか。`CHASSIS_APP_DB.BGP_DEVICE_GLOBAL|STATE` への書込 (シャーシ supervisor 経路) も含む。

## 走査範囲

- `.cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_device_global.py` (主購読者: `DeviceGlobalCfgMgr`)
- `.cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_chassis_app_db.py` (シャーシ supervisor LC 側の `ChassisAppDbMgr`)
- `.cache/sonic-sources/sonic-swss/orchagent/bfdorch.cpp` / `bfdorch.h` (`BgpGlobalStateOrch` 実体および連鎖先 `BfdOrch::handleTsaStateChange`)
- `.cache/sonic-sources/sonic-buildimage/dockers/docker-fpm-frr/base_image_files/{TSA,TSB,TS,idf_isolation}` (CLI からの直接書込スクリプト)

## 走査コマンドと結果

### 1. `DeviceGlobalCfgMgr` 本体の DB 書込 API 呼出

```bash
grep -nE "Producer|Notification|hset|\.set\(|publish|Table\(" \
  .cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_device_global.py
```

結果: **マッチ 0 件**。`set_handler` / `del_handler` / `configure_tsa` / `configure_wcmp` / `configure_idf` / `set_wcmp` / `isolate_unisolate_device` / `downstream_isolate_unisolate` のいずれも DB Producer / Table API を直接呼ばない。すべて以下のいずれかに閉じる:

- `self.directory.put(self.db_name, self.table_name, ...)` (in-process directory キャッシュへの記録のみ、Redis 書込ではない)
- `self.cfg_mgr.commit()` / `self.cfg_mgr.update()` / `self.cfg_mgr.push(cmd)` (FRR への vtysh 流入: bgpd プロセスへのコマンド送出、DB 書込なし)

唯一の **DB アクセス** は `get_chassis_tsa_status()` 内の `swsscommon.SonicV2Connector` で `CHASSIS_APP_DB.BGP_DEVICE_GLOBAL|STATE` を **read** するのみ (`managers_device_global.py:245-247`)。書込みではない。

### 2. `ChassisAppDbMgr` (supervisor LC 上の購読者)

```bash
grep -nE "Producer|hset|\.set\(|publish|Table\(" \
  .cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_chassis_app_db.py
```

結果: **マッチ 0 件**。`ChassisAppDbMgr.set_handler` は `dev_cfg_mgr.cfg_mgr.commit()` / `update()` / `isolate_unisolate_device()` を呼ぶのみ。`CHASSIS_APP_DB` の `BGP_DEVICE_GLOBAL|STATE` への書込みは bgpcfgd ではなく **CLI 側スクリプト** (後述 §4) が行う。

### 3. `BgpGlobalStateOrch` (orchagent 直接 CFG 購読)

```bash
grep -nE "m_state|Producer|hset|Notification|FlexCounter|COUNTERS|ASIC_DB" \
  .cache/sonic-sources/sonic-swss/orchagent/bfdorch.cpp \
  | sed -n '/BgpGlobalStateOrch/,/^[A-Za-z]/p'
```

`BgpGlobalStateOrch::doTask` (bfdorch.cpp:793-840) は CONFIG_DB の `BGP_DEVICE_GLOBAL|STATE.tsa_enabled` 変更を読み出し、`tsa_enabled` 内部フラグを更新する以外は **`BfdOrch::handleTsaStateChange(state)` を呼ぶだけ** (bfdorch.cpp:821-825)。`BgpGlobalStateOrch` 自身は STATE_DB / COUNTERS_DB / ASIC_DB に直接書込まない。コンストラクタ (bfdorch.cpp:729-736) も SAI capability 問合せ (`offload_supported`) のみで DB 書込なし。

ただし **`handleTsaStateChange` 経由で BfdOrch が間接的に副次 DB 書込を起こす**:

```bash
grep -n "handleTsaStateChange\|m_stateBfdSessionTable\|m_stateSoftBfdSessionTable\|remove_bfd_session\|create_bfd_session" \
  .cache/sonic-sources/sonic-swss/orchagent/bfdorch.cpp
```

`BfdOrch::handleTsaStateChange` (bfdorch.cpp:683-704):

- `tsaState == true`: 既存セッション全てに対し `notify_session_state_down()` + `remove_bfd_session()` を呼ぶ。`remove_bfd_session` は `m_stateBfdSessionTable.del(peer)` (STATE_DB / `BFD_SESSION_TABLE`、bfdorch.cpp:629) を実行し、SAI `remove_bfd_session()` も発行する (ASIC_DB 経由)。
- `tsaState == false`: 退避していたセッションを `create_bfd_session()` で再作成。`m_stateBfdSessionTable.set()` (STATE_DB) と SAI `create_bfd_session()` を発行 (bfdorch.cpp:565)。

これは `BGP_DEVICE_GLOBAL|STATE.tsa_enabled` 変更が **間接的かつ条件付き** で STATE_DB / ASIC_DB に波及する経路。条件は「現時点で `bfd_session_cache` に登録された BFD セッションが存在する」こと。

### 4. CLI スクリプト経由の CHASSIS_APP_DB 書込

```bash
grep -nE "CHASSIS_APP_DB.*HMSET|HMSET.*BGP_DEVICE_GLOBAL" \
  .cache/sonic-sources/sonic-buildimage/dockers/docker-fpm-frr/base_image_files/{TSA,TSB,TS}
```

検出:

- `TSA:19` — `CHASSIS_TSA_STATE_UPDATE="CHASSIS_APP_DB HMSET BGP_DEVICE_GLOBAL|STATE tsa_enabled true"` (シャーシ supervisor で `TSA` 実行時)
- `TSB:19` — 同上 `false`
- `TS:16,25` — 状態確認スクリプトが `TSA_STATE_UPDATE` JSON を CONFIG_DB へ書き戻し

これらは **CLI から直接** `sonic-db-cli` 経由で CHASSIS_APP_DB に書き込むパスであり、`bgpcfgd` の購読 handler から起動されるものではない。CONFIG_DB の `BGP_DEVICE_GLOBAL|STATE` への SET 自体は連動して CLI スクリプトが `sonic-cfggen -a` で行う (TSA:23-30 / TSB:23-30)。bgpcfgd の handler 内では発生しない。

### 5. CLI スクリプト経由の STATE_DB アクセス

```bash
grep -n "STATE_DB" .cache/sonic-sources/sonic-buildimage/dockers/docker-fpm-frr/base_image_files/{TSA,TSB}
```

- `TSA:50` / `TSB:49`: `sonic-db-cli STATE_DB HDEL "ALL_SERVICE_STATUS|tsa_tsb_service" "running"` — TSA/TSB 実行完了時に `tsa_tsb_service` の running フラグを STATE_DB から削除する。これは `BGP_DEVICE_GLOBAL` テーブル自体ではなく、`tsa_tsb_service` のサービス管理側 STATE_DB エントリ。CONFIG_DB `BGP_DEVICE_GLOBAL` 書込みの副次効果としてではなく、CLI 完了処理として実行される。

## 結論

CONFIG_DB `BGP_DEVICE_GLOBAL|{STATE,CONFED}` の SET/DEL に対する副次 DB 書込は以下のとおり整理できる。

### bgpcfgd 経路 (`DeviceGlobalCfgMgr` / `ChassisAppDbMgr`)

**副次 DB への直接書込みは 0 件**。すべて FRR への vtysh コマンド送出 (`cfg_mgr.push`) と in-process directory キャッシュ更新 (`directory.put`) に閉じる。`CHASSIS_APP_DB.BGP_DEVICE_GLOBAL|STATE` は **read のみ** (`get_chassis_tsa_status`)。

### orchagent 経路 (`BgpGlobalStateOrch`)

**直接書込みは 0 件**。`tsa_enabled` 変更時に `BfdOrch::handleTsaStateChange()` を呼び、これが **STATE_DB / `BFD_SESSION_TABLE` と ASIC_DB / SAI BFD オブジェクト** に **間接的・条件付き** で波及する (アクティブな BFD セッションが存在する場合のみ)。`BgpGlobalStateOrch` コンストラクタは SAI capability 問合せのみで DB 書込なし。

### CLI / シェルスクリプト経路

- `TSA` / `TSB` 実行: シャーシ supervisor LC で **CHASSIS_APP_DB / `BGP_DEVICE_GLOBAL|STATE`** に `tsa_enabled` を HMSET (これが `bgpcfgd` の各 LC `ChassisAppDbMgr` で再購読され FRR に伝播)
- `TSA` / `TSB` 完了時: **STATE_DB / `ALL_SERVICE_STATUS|tsa_tsb_service`** から `running` フィールドを HDEL

これらは CLI が直接行う書込であり、`BGP_DEVICE_GLOBAL` CONFIG_DB エントリ書込みの主購読者 (bgpcfgd) 内では発生しない。ただし運用観点では `config bgp device-global tsa enable` / `TSA` コマンドの**副次効果**として観察される。

## 根拠サマリ

| 検証項目 | ファイル/行 | 結果 |
|---|---|---|
| `DeviceGlobalCfgMgr` 内の Producer / Table API | `managers_device_global.py` 全体 | 0 件 (FRR push のみ) |
| `DeviceGlobalCfgMgr` の DB read | `managers_device_global.py:245-247` | `CHASSIS_APP_DB.BGP_DEVICE_GLOBAL|STATE` の read のみ |
| `ChassisAppDbMgr` 内の DB 書込 | `managers_chassis_app_db.py` 全体 | 0 件 |
| `BgpGlobalStateOrch::doTask` の DB 書込 | `bfdorch.cpp:793-840` | 0 件 (in-process flag 更新 + `BfdOrch` dispatch) |
| `BfdOrch::handleTsaStateChange` の STATE_DB 書込 | `bfdorch.cpp:683-704,565,629` | TSA on/off で `m_stateBfdSessionTable.del` / `.set` を **条件付き** に実行 |
| `BfdOrch::handleTsaStateChange` の SAI 呼出 | `bfdorch.cpp:551-630` | `sai_bfd_api->create_bfd_session` / `remove_bfd_session` (条件付き) |
| CLI `TSA` / `TSB` の CHASSIS_APP_DB 書込 | `dockers/docker-fpm-frr/base_image_files/TSA:19,TSB:19` | `HMSET BGP_DEVICE_GLOBAL|STATE tsa_enabled <bool>` |
| CLI `TSA` / `TSB` 完了の STATE_DB 書込 | `TSA:50,TSB:49` | `HDEL ALL_SERVICE_STATUS|tsa_tsb_service running` |

## ページ反映方針

本ページの `<!-- side-effects -->` ブロックでは以下を明記する:

1. `bgpcfgd` 経路は副次 DB 書込ゼロ (FRR push のみ)
2. orchagent 経路 (`BgpGlobalStateOrch`) は `tsa_enabled` 変化を `BfdOrch` に dispatch、BFD セッション存在時のみ STATE_DB / ASIC_DB へ間接波及
3. シャーシ supervisor で `TSA`/`TSB` CLI を実行した場合の CHASSIS_APP_DB 書込
4. CLI 完了時の `ALL_SERVICE_STATUS|tsa_tsb_service` STATE_DB 更新

SET / DEL の表は CONFIG_DB `BGP_DEVICE_GLOBAL|STATE` への書込み単位で記述する。`|CONFED` は副次 DB 書込なし (FRR への confederation push のみ) で同様に 0 行。
