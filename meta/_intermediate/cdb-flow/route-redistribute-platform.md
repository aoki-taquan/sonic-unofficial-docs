# ROUTE_REDISTRIBUTE — プラットフォーム差調査

Task F Phase H: `ROUTE_REDISTRIBUTE` テーブル適用時のプラットフォーム/構成差を `frrcfgd` (`sonic-frr-mgmt-framework`) および `bgpcfgd` (`sonic-bgpcfgd`) の関連コードから精読した結果。

## 結論

**プラットフォーム差なし**。ROUTE_REDISTRIBUTE 経路は FRR vtysh への BGP コマンド生成のみを行い、ASIC 種別・SmartSwitch・VOQ chassis 構成に依存しない。

## 根拠

### 1. frrcfgd ROUTE_REDISTRIBUTE ハンドラにプラットフォーム分岐なし

`frrcfgd.py` L3149–3168 の ROUTE_REDISTRIBUTE ハンドラは:

- `key.split('|')` で `src_proto, dst_proto, af` の 3 値を取り出す
- `dst_proto != 'bgp'` チェック (L3156–3158) のみ実行
- `router bgp {asn} vrf {vrf}` → `address-family {af} unicast` → `redistribute {src_proto}` の FRR vtysh コマンドを生成

`platform|asic|chassis|SmartSwitch|smartswitch|VOQ|voq|multi_asic|is_chassis|is_smartswitch` 等のキーワードを `frrcfgd.py` 全体でスキャンしたが、ROUTE_REDISTRIBUTE コードパスでは **0 ヒット**。

### 2. frrcfgd 自体に chassis / SmartSwitch 固有処理なし

`frrcfgd.py` 全体に `VOQ`・`chassis`・`SmartSwitch` 参照が皆無。frrcfgd は BGP vtysh インターフェース専用デーモンであり、chassis 構成の分岐はない。

### 3. bgpcfgd の VOQ / chassis 処理は ROUTE_REDISTRIBUTE と無関係

`bgpcfgd/main.py` L112–113:

```python
if device_info.is_chassis():
    managers.append(ChassisAppDbMgr(common_objs, "CHASSIS_APP_DB", "BGP_DEVICE_GLOBAL"))
```

chassis 判定時に追加されるのは `ChassisAppDbMgr`（TSA 状態の chassis 同期）のみ。  
`BGP_VOQ_CHASSIS_NEIGHBOR` (L91) は VOQ chassis 向けの BGP ネイバー管理であり、再配布とは独立。  
`managers_static_rt.py` (`StaticRouteMgr`) には `is_chassis()` / `is_smartswitch()` の呼び出しは存在しない。

### 4. FRR バージョン差ゲートなし

`frrcfgd.py` および `managers_static_rt.py` に `frr_version`・`FRR_VERSION`・`frr_ver` 等のバージョン条件分岐は存在しない。SONiC master は FRR バージョンを SONiC ビルドシステムで固定して統一ビルドするため、実行時バージョン判定が不要。

### 5. Jinja2 テンプレートにプラットフォーム分岐なし

`bgpd.conf.db.addr_family.j2` L64–76 の redistribute ブロックは `vrf` / `af_str` によるキー一致のみで制御。`platform|asic|chassis|SmartSwitch|VOQ` 参照は 0 ヒット。

### 6. SmartSwitch での扱い

SmartSwitch (DPU) 構成で bgpcfgd / frrcfgd が NPU 側で動く場合も、ROUTE_REDISTRIBUTE テーブル自体の処理ロジックは変わらない。SmartSwitch 固有の BGP 経路処理は別の設定テーブル（`BGP_VOQ_CHASSIS_NEIGHBOR` 等）で担われる。

### 7. VOQ chassis での扱い

VOQ chassis の linecard では、各 linecard host で独立に frrcfgd / bgpcfgd が起動し、各ホストの CONFIG_DB を購読する。ROUTE_REDISTRIBUTE はホストスコープの BGP 設定であり、chassis 間の集中管理機構はない。supervisor / linecard 間の TSA 同期は `ChassisAppDbMgr` が担い、redistribute 設定には影響しない。

## evidence

- `frrcfgd.py` L3149–3168: ROUTE_REDISTRIBUTE ハンドラ（プラットフォーム分岐なし）
- `frrcfgd.py` L3156–3157: `dst_proto != 'bgp'` バリデーションのみ
- `bgpcfgd/main.py` L112–113: `is_chassis()` → `ChassisAppDbMgr` 追加（redistribute と無関係）
- `bgpcfgd/main.py` L91: `BGP_VOQ_CHASSIS_NEIGHBOR` manager（redistribute と無関係）
- `managers_static_rt.py` L221–252: `enable_redistribution_command` / `disable_redistribution_command`（platform 条件なし）
- `bgpd.conf.db.addr_family.j2` L64–76: redistribute Jinja2 ブロック（platform 分岐なし）
