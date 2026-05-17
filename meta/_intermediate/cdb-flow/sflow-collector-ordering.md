# sflow-collector — Phase B (ordering) intermediate

## 調査日時
2026-05-17

## 調査対象ソース
- `sonic-swss/cfgmgr/sflowmgr.cpp` (全行精読)
- `sonic-swss/cfgmgr/sflowmgrd.cpp` (全行精読)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-sflow.yang`
- `sonic-utilities/config/main.py` (sflow collector add/del 周辺)
- `SONiC/doc/sflow/sflow_hld.md`

## 主要発見事項

### SFLOW_COLLECTOR の購読者
- **sflowmgrd (C++) は SFLOW_COLLECTOR を購読しない** (`sflowmgrd.cpp` の TableConnector リストに存在しない)
- YANG 定義と HLD (sflow_hld.md:130) では「sflowmgrd が SFLOW_COLLECTOR を監視して /etc/hsflowd.conf を更新」と記述されているが、現在の実装では直接購読なし → HLD との乖離

### SFLOW_COLLECTOR の実際の経路
- CLI (`config sflow collector add`) が直接 `config_db.mod_entry('SFLOW_COLLECTOR', name, {...})` で書き込む
- hsflowd は `/etc/hsflowd.conf` (起動時) から collector 設定を読む
- collector の変更が反映されるには hsflowd の再起動が必要（sflowmgrd が SFLOW global admin_state の変更をトリガーに `service hsflowd restart` を呼ぶ）

### YANG 制約 (must)
- `collector_vrf = 'mgmt'` は MGMT_VRF_CONFIG.vrf_global.mgmtVrfEnabled = 'true' が前提 (sonic-sflow.yang:86-88)
- max-elements 2 (sonic-sflow.yang:62) → CLI も同様に 2 コレクタ上限チェックあり (main.py:9354)

### 書込み順依存
- O1: SFLOW_COLLECTOR は SFLOW|global に依存しない (CONFIG_DB への直接書き込み)
- O2: collector_vrf='mgmt' を使う場合、先に MGMT_VRF_CONFIG|vrf_global の mgmtVrfEnabled=true 設定が必要 (YANG must 制約)
- O3: collector 変更を即座に反映するには SFLOW|global の admin_state 変更 (→ hsflowd restart) が別途必要
- O4: 最大 2 エントリまで (max-elements 2)。3 つ目を書くと YANG バリデーション / CLI チェックで拒否

## 結論
SFLOW_COLLECTOR は CONFIG_DB への直接書き込みエントリであり、動的購読経路はない。
hsflowd は起動時設定ファイルから読むため、コレクタ変更の有効化には hsflowd 再起動が必要。
