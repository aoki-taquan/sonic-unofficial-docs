# BGP_GLOBALS — プラットフォーム差調査 (Task F Phase H)

ソース精読: `bgpcfgd/` (`main.py`, `managers_bgp.py`, `managers_device_global.py`, `managers_chassis_app_db.py`)、`frrcfgd/frrcfgd.py`、`templates/bgpd/bgpd.conf.db.j2`。

## 結論サマリ

BGP_GLOBALS 本体（router-id / local_asn / graceful-restart 等）の処理に**プラットフォーム固有分岐はない**。ただし以下の **3 つの隣接機能**がプラットフォーム種別に依存して挙動を変える:

1. **chassis TSA 伝播** — `is_chassis()` が true のとき `ChassisAppDbMgr` が追加登録される
2. **switch_role による IDF isolation スキップ** — `SpineRouter` / `LowerSpineRouter` / `UpperSpineRouter` 以外では IDF 経路分離が無効
3. **switch_type / subtype による AsPath Manager 限定起動** — `SpineRouter/UpstreamLC` および `UpperSpineRouter` のみ `AsPathMgr` が追加される

multi-asic 構成では bgpcfgd は各 ASIC コンテナで独立に起動し、各 ASIC 専用の CONFIG_DB を購読する。BGP_GLOBALS の処理自体に namespace 分岐コードはない。

`frrcfgd.py` および `bgpd.conf.db.j2` にはプラットフォーム分岐なし（grep 0 ヒット確認済み）。

---

## 詳細調査

### 1. chassis 環境: `ChassisAppDbMgr` の条件付き登録

`main.py:112-113`:
```python
if device_info.is_chassis():
    managers.append(ChassisAppDbMgr(common_objs, "CHASSIS_APP_DB", "BGP_DEVICE_GLOBAL"))
```

- 非 chassis 環境: `ChassisAppDbMgr` は登録されない → `CHASSIS_APP_DB` を購読しない
- chassis 環境: スーパーバイザの `BGP_DEVICE_GLOBAL.tsa_enabled` 変化を監視し、line card の TSA 状態を `DeviceGlobalCfgMgr.isolate_unisolate_device()` に伝播する

`managers_chassis_app_db.py:40-44`:
```python
if "tsa_enabled" in data:
    if self.lc_tsa == "false":  # line card 自身が TSA 中でない場合のみ
        self.dev_cfg_mgr.isolate_unisolate_device(data["tsa_enabled"])
```

**BGP_GLOBALS 本体との関係**: TSA は BGP_DEVICE_GLOBAL テーブル経由で適用される route-map 操作であり、BGP_GLOBALS フィールドを直接書き換えない。ただし BGP peer-group テンプレートレンダリング時に `check_state_and_get_tsa_routemaps()` が chassis_tsa を確認する (`managers_device_global.py:238-251`)。

### 2. chassis TSA 状態取得

`managers_device_global.py:238-251`:
```python
def get_chassis_tsa_status(self):
    chassis_tsa_status = "false"
    if not device_info.is_chassis():
        return chassis_tsa_status  # 非 chassis は常に "false"
    ch = swsscommon.SonicV2Connector(...)
    ch.connect(ch.CHASSIS_APP_DB, False)
    chassis_tsa_status = ch.get(ch.CHASSIS_APP_DB, "BGP_DEVICE_GLOBAL|STATE", 'tsa_enabled')
    return chassis_tsa_status
```

- 非 chassis: 常に `"false"` を返す（CHASSIS_APP_DB に接続しない）
- chassis: `CHASSIS_APP_DB.BGP_DEVICE_GLOBAL|STATE.tsa_enabled` を参照

### 3. switch_role による IDF isolation 制御

`managers_device_global.py:260-261`:
```python
if self.switch_role and self.switch_role not in ["SpineRouter", "LowerSpineRouter", "UpperSpineRouter"]:
    log_debug("DeviceGlobalCfgMgr:: Skipping IDF isolation configuration on %s" % self.switch_role)
    return True
```

`switch_role` は `DEVICE_METADATA|localhost|type` から取得 (`managers_device_global.py:54`)。

| switch_role 値 | IDF isolation 適用 |
|---------------|------------------|
| `SpineRouter` | 適用される |
| `LowerSpineRouter` | 適用される |
| `UpperSpineRouter` | 適用される |
| `LeafRouter` / `ToRRouter` / 未設定 / 空 | **スキップ** |

IDF isolation は BGP_DEVICE_GLOBAL テーブルの `idf_isolation_state` で制御され、BGP_GLOBALS を直接操作しない。ただし peer-group テンプレートに反映される。

### 4. switch_type/subtype による AsPath Manager 条件起動

`main.py:122-130`:
```python
is_upstream_lc = (type == "SpineRouter" and subtype == "UpstreamLC")
is_upper_spine_router = (type == "UpperSpineRouter")
if is_upstream_lc or is_upper_spine_router:
    managers.append(AsPathMgr(common_objs, "CONFIG_DB", "DEVICE_METADATA"))
```

AsPath Manager は BGP_GLOBALS ではなく `DEVICE_METADATA` テーブルを購読し、AS_PATH 操作のポリシーを管理する。BGP_GLOBALS テーブルとの直接の相互作用はない。

### 5. VOQ chassis: BGP_VOQ_CHASSIS_NEIGHBOR

`main.py:91`:
```python
BGPPeerMgrBase(common_objs, "CONFIG_DB", "BGP_VOQ_CHASSIS_NEIGHBOR", "voq_chassis", False),
```

VOQ chassis 環境でのみ実際に設定が入るテーブルだが、`BGPPeerMgrBase` は**常時**登録される（条件なし）。データがある場合のみ実際に FRR コマンドが生成される。BGP_GLOBALS 本体処理との分岐関係はない。

### 6. multi-asic: per-ASIC bgpcfgd 独立起動

multi-asic 環境では各 ASIC コンテナ（`bgp0`, `bgp1`, ...）が独立して `bgpcfgd` を起動する。各インスタンスは対応する ASIC namespace の CONFIG_DB（`asic0`, `asic1`, ...）に接続し、BGP_GLOBALS を購読する。

`bgpcfgd` コード内に `is_multi_asic()` / `is_multi_npu()` の呼び出しは**存在しない**（全ディレクトリ grep 0 ヒット）。namespace 切り替えやループ処理も実装されていない。各 bgpcfgd インスタンスが単一 CONFIG_DB を前提に設計されているため、multi-asic 対応はコンテナ多重起動で実現される。

### 7. frrcfgd: プラットフォーム分岐なし

`frrcfgd.py` に `chassis`, `tsa`, `switch_role`, `switch_type`, `multi_asic`, `is_chassis`, `VOQ` 等の文字列でのヒットなし（grep 確認済み）。frrcfgd は platform-agnostic に BGP_GLOBALS を処理する。

### 8. bgpd.conf.db.j2: プラットフォーム分岐なし

`bgpd.conf.db.j2` に `chassis`, `tsa`, `switch_role`, `switch_type`, `multi_asic`, `voq` 等のヒットなし（grep 確認済み）。テンプレート内の分岐は BGP_GLOBALS フィールド値（boolean / uint）のみに依存する。

---

## grep カバレッジ証跡

| 検索対象 | ファイル | ヒット数 | 結果 |
|---------|--------|--------|-----|
| `chassis\|tsa\|switch_role` | `frrcfgd.py` | 0 | 分岐なし |
| `chassis\|tsa\|switch_role` | `bgpd.conf.db.j2` | 0 | 分岐なし |
| `multi.asic\|is_multi_asic` | `bgpcfgd/` 全体 | 0 (テストのみ) | 本番コードに分岐なし |
| `is_chassis` | `main.py` | 1 | ChassisAppDbMgr 登録のみ |
| `switch_role\|switch_type` | `managers_device_global.py` | 3 | IDF/AsPath 制御のみ |
| `VOQ` | `managers_device_global.py` | 1 | TSA route-map 分類のみ |
