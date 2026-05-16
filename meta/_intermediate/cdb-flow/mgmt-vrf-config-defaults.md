# MGMT_VRF_CONFIG — Phase A 暗黙デフォルト調査

生成日: 2026-05-14

## 調査対象フィールド

### `mgmtVrfEnabled` (boolean)

| 項目 | 内容 | 証跡 |
|------|------|------|
| YANG default | `false` | `sonic-mgmt_vrf.yang` L28: `default false;` |
| ランタイム fallback | エントリ不在 → vrfmgr は DEL として処理 (管理 VRF 無効扱い) | `vrfmgr.cpp` L257-259: `if ((mgmt_vrf_enabled == false) || (in_band_mgmt_enabled == false)) op = DEL_COMMAND` |
| hostcfgd fallback | `mgmt_vrf.get('mgmtVrfEnabled', '')` — 空文字列。update_mgmt_vrf() L1653 で `if not enabled` ガードにより即 return (ノーオペレーション) | `hostcfgd` L1620, L1652-1654 |
| init_cfg.json デフォルト | なし (エントリ自体が存在しない) | `init_cfg.json.j2` に MGMT_VRF_CONFIG エントリなし |
| minigraph 派生 | XML `MgmtVrfGlobal/mgmtVrfEnabled` ノードが存在する場合のみ設定。存在しない場合 `mvrf = {}` (空 dict) → `results['MGMT_VRF_CONFIG']` も空 | `minigraph.py` L847, L928-934, L2308 |

### `in_band_mgmt_enabled` (boolean — YANG 未定義フィールド)

| 項目 | 内容 | 証跡 |
|------|------|------|
| YANG 定義 | **存在しない** (`sonic-mgmt_vrf.yang` に定義なし) | `sonic-mgmt_vrf.yang` 全文確認 |
| HLD 仕様 | デフォルト `"false"`。`mgmtVrfEnabled=true` のときのみ有効。インバンド管理 VRF 向け拡張フィールド | `SONiC_in_band_mgmt_via_mgmt_Vrf_HLD.md` L16, L32 |
| ランタイム fallback | vrfmgr.cpp で `in_band_mgmt_enabled = false` (C++ ローカル変数初期値)。フィールドがない場合は false 扱い → SET が DEL_COMMAND に変換される | `vrfmgr.cpp` L234, L246-252, L257 |
| vrforch.h 参照 | `{ "in_band_mgmt_enabled", REQ_T_BOOL }` として orchagent でも参照 | `sonic-swss/orchagent/vrforch.h` L37 |

## 発見した暗黙デフォルト・乖離

### 1. YANG-実装 discrepancy: `in_band_mgmt_enabled` フィールド
- **YANG 未定義だが実装で消費される**: `sonic-mgmt_vrf.yang` には `in_band_mgmt_enabled` leaf が存在しないが、`vrfmgr.cpp` と `vrforch.h` でフィールド値を読み取る。
- **影響**: YANG バリデーション上はこのフィールドへの書き込みが制約外。実装のみで処理される。
- **デフォルト**: C++ ローカル変数 `bool in_band_mgmt_enabled = false` が暗黙デフォルト。

### 2. SET → DEL 変換のトリガー条件 (死角)
- `mgmtVrfEnabled` フィールドが存在しても値が `"true"` でなければ `mgmt_vrf_enabled = false` (初期値のまま)。
- `in_band_mgmt_enabled` フィールドが存在しなければ `in_band_mgmt_enabled = false` (初期値のまま)。
- 両条件のいずれかが false → SET を DEL_COMMAND に変換。これはエントリ書き込み時に **無音で削除** される。

### 3. hostcfgd の silent drop
- `update_mgmt_vrf()` で `enabled = data.get('mgmtVrfEnabled', '')` が空文字列のとき即 return。
- 空文字列のまま SET された場合、chrony/interfaces-config の再起動が **一切行われない**。
- エラーログなし → **silent drop**。

### 4. mgmt VRF table ID ハードコード
- `#define MGMT_VRF_TABLE_ID 6000` (`vrfmgr.cpp` L15)。
- 通常 VRF は 1001-5097 の範囲から動的確保。mgmt VRF は固定 6000 番。
- 変更不可 (コンパイル時定数)。

### 5. 初期化時 mgmt netdev 保護 (warm restart 非時)
- `VrfMgr::VrfMgr()` 初期化ループで既存 VRF を列挙し `ip link del` で削除するが、`vrfName == "mgmt"` のとき **スキップ** して削除しない (L74-79)。
- 非 warm restart 時にも mgmt VRF が既存であれば保護される。

### 6. delLink("mgmt") の特殊処理
- `delLink()` L148-153: `vrfName == MGMT_VRF` の場合は `ip link del` を実行せず、`m_vrfTableMap` からのエントリ削除のみ行う。
- カーネル側の mgmt VRF netdev は hostcfgd が管理する (vrfmgr は管理しない) → **責務分割の乖離**。

### 7. setLink("mgmt") の特殊処理
- `setLink()` L176-183: `vrfName == MGMT_VRF` の場合は `ip link add` を実行せず、固定 table_id 6000 を `m_vrfTableMap` に登録するのみ。
- 実際の netdev 作成は hostcfgd の `interfaces-config` restart が担う。

### 8. VRF 削除の遅延条件 (DEL 経路)
- DEL 受信後、`m_stateVrfTable.get(vrfName)` が true かつ `isVrfObjExist(vrfName)` が false の場合のみ削除処理進行。
- `isVrfObjExist` が true のままだと DEL ループ待機 (`it++; continue`) → **書き込み順依存**。orchagent が STATE_VRF_OBJECT_TABLE を削除するまで netdev 削除が遅延する。

## 総括

| フィールド | デフォルト種別 | デフォルト値 | 乖離/注意 |
|-----------|-------------|------------|---------|
| `mgmtVrfEnabled` | YANG default + C++ ローカル変数 | `false` | YANG と実装一致 |
| `in_band_mgmt_enabled` | C++ ローカル変数 (YANG 未定義) | `false` | YANG-実装 discrepancy: YANG に leaf なし |

## 証跡ファイル

- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-mgmt_vrf.yang` (YANG 定義)
- `sonic-swss/cfgmgr/vrfmgr.cpp` (SET/DEL 処理・分岐・table ID ハードコード)
- `sonic-host-services/scripts/hostcfgd` (L1605-1694, MgmtIfaceCfg クラス)
- `sonic-buildimage/src/sonic-config-engine/minigraph.py` (L847, L928-934, L2308)
- `SONiC/doc/vrf/SONiC_in_band_mgmt_via_mgmt_Vrf_HLD.md` (in_band_mgmt_enabled HLD)
