# state-bgp Phase H — プラットフォーム差分調査

調査日: 2026-05-19
調査対象:
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_chassis_app_db.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_device_global.py`
- `sonic-swss/fpmsyncd/bgp_eoiu_marker.py`
- `sonic-buildimage/src/sonic-bmpcfgd/bmpcfgd/bmpcfgd.py`

---

## 結論サマリー

| テーブル | プラットフォーム差分 | 差分の種類 |
|---------|-----------------|----------|
| `BGP_STATE_TABLE` | **あり** | Warm Restart 有効時のみ書き込まれる（機能フラグ依存） |
| `BGP_PEER_CONFIGURED_TABLE` | **あり（VOQ Chassis + software_bfd）** | `is_chassis()` 分岐で ChassisAppDbMgr 追加、`software_bfd` フラグで BfdMgr 追加 |
| `BGP_NEIGHBOR_TABLE` / BMP テーブル | **なし** | bmpcfgd に platform 分岐なし |

---

## 1. BGP_STATE_TABLE — Warm Restart 機能ゲート

`bgp_eoiu_marker.py` は起動直後に `WarmStart::checkWarmStart("bgp", "bgp", False)` を呼び出し、
`isWarmStart()` が `False` の場合は即座に終了する（bgp_eoiu_marker.py L191–197）。

→ **Warm Restart が有効でないデプロイでは `BGP_STATE_TABLE` は一切書き込まれない**。

Warm Restart の有効化は CONFIG_DB `WARM_RESTART` テーブルで制御され、
プラットフォーム（ハードウェア種別）ではなく運用設定による制御である。
ただし SONIC イメージビルド時の `FEATURE` テーブル設定によっても left-off されうる。

---

## 2. BGP_PEER_CONFIGURED_TABLE — VOQ Chassis 分岐

`main.py` L112–114:
```python
if device_info.is_chassis():
    managers.append(ChassisAppDbMgr(common_objs, "CHASSIS_APP_DB", "BGP_DEVICE_GLOBAL"))
```

VOQ Chassis 構成では `ChassisAppDbMgr` が追加登録され、Supervisor の TSA（Traffic Shift Away）
状態変化を `CHASSIS_APP_DB.BGP_DEVICE_GLOBAL.tsa_enabled` から購読する。
Supervisor 側の TSA 状態変化が発生すると `DeviceGlobalCfgMgr.isolate_unisolate_device()` が
呼び出され、全 BGP ピアの isolate/unisolate が FRR に投入される。

この動作は `BGP_PEER_CONFIGURED_TABLE` の書き込み内容自体には影響しないが、
BGP ピアの実際のセッション状態（active/passive）に波及する。

また VOQ Chassis 向けに `BGP_VOQ_CHASSIS_NEIGHBOR` テーブルも `BGPPeerMgrBase` として
常時登録されており（main.py L91）、このテーブルのエントリも `BGP_PEER_CONFIGURED_TABLE`
へ同じ経路（`update_state_db()`）で書き込まれる。非 VOQ 環境ではこのテーブルにエントリが
存在しないため実質的に無効。

`BGPPeerMgrBase.update_state_db()` 自体には `switch_type` / `sub_role` / `is_chassis()` による
条件分岐は一切存在しない（grep 確認: 0 件）。

---

## 3. software_bfd フィーチャーゲート — BfdMgr 追加

`main.py` L117–120:
```python
sys_defaults = config_db.get_table('SYSTEM_DEFAULTS')
if 'software_bfd' in sys_defaults and 'status' in sys_defaults['software_bfd'] \
        and sys_defaults['software_bfd']['status'] == 'enabled':
    managers.append(BfdMgr(common_objs, "STATE_DB", swsscommon.STATE_BFD_SOFTWARE_SESSION_TABLE_NAME))
```

`SYSTEM_DEFAULTS.software_bfd.status == "enabled"` の場合のみ `BfdMgr` が起動する。
BfdMgr は `STATE_DB.BFD_SOFTWARE_SESSION_TABLE` を購読し、BFD セッション状態に基づいて
BGP ピアの admin_status を変更する（`vtysh -c "neighbor <peer> shutdown"` / `no shutdown`）。

この制御が有効な場合、`BGP_PEER_CONFIGURED_TABLE` への書き込みは admin_status 変化
（shutdown/no shutdown）の FRR 反映後に発生しうる。software_bfd 無効時は BGP ピアの
BFD 状態連動シャットダウンは FRR 自体の BFD 実装に委ねられる。

---

## 4. BMP テーブル — プラットフォーム差分なし

`bmpcfgd.py` には `device_info.is_chassis()` / `is_multi_asic()` / `switch_type` 参照が
一切存在しない。BMP_STATE_DB テーブルの書き込み・削除動作は全プラットフォームで同一。

---

## 5. マルチ ASIC（multi-ASIC）差分

`bgpcfgd` 本体（main.py / managers_bgp.py）には multi-ASIC 対応コードが存在しない。
multi-ASIC 環境では各 ASIC namespace ごとに bgpcfgd インスタンスが起動するため、
`BGP_PEER_CONFIGURED_TABLE` は各 namespace の STATE_DB に独立して書き込まれる。
SNMP サブエージェント（sonic-snmpagent）は全 namespace の STATE_DB を横断収集するが、
これは consumer 側の実装であり本テーブルの書き込み動作に影響しない。
