# MGMT_VRF_CONFIG — Phase D: 失敗挙動

ソース: `sonic-swss/cfgmgr/vrfmgr.cpp`, `sonic-host-services/scripts/hostcfgd`

## 抽出した失敗パターン

### 1. カーネル VRF netdev 作成失敗 → SWSS_LOG_ERROR (処理継続)

`VrfMgr::doTask()` (vrfmgr.cpp:281-284) で `setLink(vrfName)` が false を返した場合:

| 条件 | 挙動 |
|------|------|
| `setLink()` 失敗 | `SWSS_LOG_ERROR("Failed to create vrf netdev %s", vrfName.c_str())` をログ (vrfmgr.cpp:283) |
| エラー後の後続処理 | STATE_DB への `state=ok` 書き込みは **継続される** (vrfmgr.cpp:286-289) |
| netdev 未作成状態での STATE_DB 書き込み | STATE_VRF_TABLE に `state=ok` が登録されるが実際の netdev は存在しない — **不整合** |

- mgmt VRF の場合は `setLink()` が常に true を返す（table_id 6000 を map に登録するのみ、`ip link add` を実行しない）。この経路でのエラーは通常 VRF (非 mgmt) のみ発生。

### 2. カーネル VRF netdev 削除失敗 → SWSS_LOG_ERROR (処理継続)

`VrfMgr::doTask()` (vrfmgr.cpp:356-358) で `delLink(vrfName)` が false を返した場合:

| 条件 | 挙動 |
|------|------|
| `delLink()` 失敗 | `SWSS_LOG_ERROR("Failed to remove vrf netdev %s", vrfName.c_str())` をログ (vrfmgr.cpp:358) |
| エラー後の後続処理 | `SWSS_LOG_NOTICE("Removed vrf netdev %s")` が引き続き出力される — 実失敗でも成功ログ |

- mgmt VRF の場合は `delLink()` が `ip link del` を実行しないため（hostcfgd が管理）、通常この経路ではエラーが発生しない。

### 3. VRF VNI マップ設定失敗 → ループ継続スキップ

`doVrfVxlanTableCreateTask()` が false を返した場合 (vrfmgr.cpp:296-300):

| 条件 | 挙動 |
|------|------|
| `doVrfVxlanTableCreateTask()` 失敗 | `SWSS_LOG_ERROR("VRF VNI Map Config Failed")` をログ (vrfmgr.cpp:298) |
| エントリの処理 | `consumer.m_toSync.erase(it)` でエントリを消費して **スキップ** — 再試行なし |

この経路は `CFG_VRF_TABLE_NAME` および `CFG_MGMT_VRF_CONFIG_TABLE_NAME` で発生しうる。

### 4. 未知オペレーション → SWSS_LOG_ERROR (ドロップ)

SET でも DEL でもない op コードを受信した場合 (vrfmgr.cpp:365-366):

| 条件 | 挙動 |
|------|------|
| 未知 op | `SWSS_LOG_ERROR("Unknown operation: %s", op.c_str())` (vrfmgr.cpp:366) |
| 後続処理 | `it = consumer.m_toSync.erase(it)` でエントリ消費 — 再試行なし |

### 5. hostcfgd: systemd サービス再起動失敗 → LOG_ERR + 即 return

`MgmtIfaceCfg::update_mgmt_vrf()` (hostcfgd:1659-1666) の `try/except subprocess.CalledProcessError` ブロック:

| 条件 | 挙動 |
|------|------|
| `systemctl stop chrony` 失敗 | `subprocess.CalledProcessError` 例外 → `LOG_ERR` ログ + `return` |
| `systemctl restart interfaces-config` 失敗 | 同上 |
| `systemctl start chrony` 失敗 | 同上 |
| エラーメッセージ | `syslog.LOG_ERR`: `"Failed to restart management vrf services"` (hostcfgd:1664) |
| キャッシュ更新 | `self.mgmt_vrf_enabled` は更新されない — 次回も同じ値で再試行される |

### 6. hostcfgd: IP 設定 (eth0 デフォルトルート削除) の失敗 → LOG_WARNING + return

`mgmtVrfEnabled = 'true'` 時の eth0 デフォルトルート確認・削除処理 (hostcfgd:1683-1693):

| 条件 | 挙動 |
|------|------|
| `/proc/net/route` の grep 失敗 | `subprocess.CalledProcessError` → `syslog.LOG_WARNING`: `"MgmtIfaceCfg: Could not delete eth0 route"` + `return` (hostcfgd:1688-1691) |
| `ip -4 route del default dev eth0 metric 202` の失敗 | `run_cmd` の第2引数 `False` → 失敗しても例外を投げない (silent failure) (hostcfgd:1693) |

### 7. hostcfgd: mgmtVrfEnabled が空文字列 → silent drop

`update_mgmt_vrf()` (hostcfgd:1652-1654):

| 条件 | 挙動 |
|------|------|
| `data.get('mgmtVrfEnabled', '')` が空文字列 | 即 `return` — chrony/interfaces-config 再起動なし、エラーログなし |
| 現在値と同じ値で SET された場合 | `enabled == self.mgmt_vrf_enabled` → 同様に即 `return` (冪等) |

## ソース根拠

- `sonic-swss/cfgmgr/vrfmgr.cpp:281-284` — setLink 失敗 → SWSS_LOG_ERROR
- `sonic-swss/cfgmgr/vrfmgr.cpp:286-289` — エラー後も STATE_DB に state=ok 書き込み
- `sonic-swss/cfgmgr/vrfmgr.cpp:354-359` — delLink 失敗 → SWSS_LOG_ERROR
- `sonic-swss/cfgmgr/vrfmgr.cpp:296-300` — VNI マップ設定失敗 → erase + スキップ
- `sonic-swss/cfgmgr/vrfmgr.cpp:365-366` — 未知 op → SWSS_LOG_ERROR
- `sonic-host-services/scripts/hostcfgd:1652-1654` — 空 mgmtVrfEnabled → silent drop
- `sonic-host-services/scripts/hostcfgd:1659-1666` — systemd 再起動失敗 → LOG_ERR + return
- `sonic-host-services/scripts/hostcfgd:1683-1693` — eth0 ルート削除失敗 → LOG_WARNING + return
