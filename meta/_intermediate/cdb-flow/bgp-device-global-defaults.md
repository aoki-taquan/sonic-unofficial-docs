---
phase: A
table: BGP_DEVICE_GLOBAL
generated: 2026-05-14
---

# BGP_DEVICE_GLOBAL — Phase A: implicit defaults (code-level)

## 調査対象コード

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_device_global.py`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-bgp-device-global.yang`
- `sonic-buildimage/files/build_templates/init_cfg.json.j2`
- `sonic-utilities/config/bgp_cli.py`

---

## STATE フィールド

### `tsa_enabled`

| 種別 | 値 | ソース |
|------|----|--------|
| YANG default | `"false"` | `sonic-bgp-device-global.yang:35` |
| init_cfg 書き込みデフォルト | `"false"` | `init_cfg.json.j2:62` — ビルド時に CONFIG_DB へ静的注入 |
| ランタイム fallback (Python クラス定数) | `"false"` (`TSA_DEFAULTS = "false"`) | `managers_device_global.py:12` |
| `__init__` setdefault 相当 | DB にキーが存在しない場合のみ directory キャッシュへ書き込む (`path_exist` ガード) | `managers_device_global.py:42-43` |
| `del_handler` fallback | `configure_tsa(data=None)` 呼び出し → `state = self.TSA_DEFAULTS` ("false") → isolate_unisolate_device("false") (TSB 実行) | `managers_device_global.py:78, 94` |
| configure_tsa fallback | `data` が None または "tsa_enabled" キーなし → `state = self.TSA_DEFAULTS` ("false") | `managers_device_global.py:94-98` |

**書き込み時 vs 実行時の乖離**: なし。YANG default / init_cfg / Python クラス定数すべて `"false"` で一致。  
`del_handler` 呼び出し時は TSB (`tsa_enabled="false"`) に相当するルートマップが FRR へ push される。

---

### `wcmp_enabled`

| 種別 | 値 | ソース |
|------|----|--------|
| YANG default | `"false"` | `sonic-bgp-device-global.yang:44` |
| init_cfg 書き込みデフォルト | `"false"` | `init_cfg.json.j2:63` |
| ランタイム fallback (Python クラス定数) | `"false"` (`WCMP_DEFAULTS = "false"`) | `managers_device_global.py:13` |
| `__init__` setdefault 相当 | DB にキーが存在しない場合のみ directory キャッシュへ書き込む | `managers_device_global.py:45-46` |
| `del_handler` fallback | `configure_wcmp(data=None)` → `state = self.WCMP_DEFAULTS` ("false") → set_wcmp("false") | `managers_device_global.py:80, 116` |

**書き込み時 vs 実行時の乖離**: なし。  
`set_wcmp("false")` は `bgpd.wcmp.conf.j2` を `wcmp_enabled="false"` でレンダリングし FRR へ push (extcommunity bandwidth を削除)。

---

### `idf_isolation_state`

| 種別 | 値 | ソース |
|------|----|--------|
| YANG default | `"unisolated"` | `sonic-bgp-device-global.yang:59` |
| init_cfg 書き込みデフォルト | `"unisolated"` | `init_cfg.json.j2:64` |
| ランタイム fallback (Python クラス定数) | `"unisolated"` (`IDF_DEFAULTS = "unisolated"`) | `managers_device_global.py:14` |
| `__init__` setdefault 相当 | DB にキーが存在しない場合のみ directory キャッシュへ書き込む | `managers_device_global.py:48-49` |
| `del_handler` fallback | `configure_idf(data=None)` → `state = self.IDF_DEFAULTS` ("unisolated") → downstream_isolate_unisolate("unisolated") | `managers_device_global.py:82, 130` |

**書き込み時 vs 実行時の乖離**: なし。  
`downstream_isolate_unisolate("unisolated")` は `idf_unisolate.conf.j2` をレンダリングし FRR へ push。ただし `switch_role` が SpineRouter / LowerSpineRouter / UpperSpineRouter 以外の場合はスキップ (`managers_device_global.py:260`)。

**追加 fallback**: `check_state_and_get_idf_isolation_routemaps()` は `idf_isolation_state == "unisolated"` の場合に空文字列を返す (isolate テンプレート適用なし) → 新 peer-group 追加時に unisolated がデファクトのデフォルト動作。

---

## CONFED フィールド

### `asn` / `peers`

| 種別 | 値 | ソース |
|------|----|--------|
| YANG default | なし (optional leaf) | `sonic-bgp-device-global.yang:69-81` |
| init_cfg 書き込みデフォルト | なし (BGP_DEVICE_GLOBAL|CONFED セクションなし) | `init_cfg.json.j2` |
| ランタイム fallback | なし。`managers_device_global.py` は CONFED を直接処理しない。`managers_bgp.py` が BGP_GLOBALS から `confederation_peers` / `confederation_id` を読んで FRR へ反映 | `managers_bgp.py` 間接参照 |

**書き込み時 vs 実行時の乖離**:  
CONFIG_DB に `BGP_DEVICE_GLOBAL|CONFED` エントリが存在しない場合、bgpcfgd は confederation 設定を FRR へ一切送出しない。FRR 側では `no bgp confederation identifier` が有効 (未設定)。

---

## chassis_tsa (内部状態)

`get_chassis_tsa_status()` は `CHASSIS_APP_DB.BGP_DEVICE_GLOBAL|STATE.tsa_enabled` を読む。非シャーシ環境またはキー不在時は `"false"` を返す (`managers_device_global.py:239`)。これは CONFIG_DB フィールドではなく内部ランタイム参照。

---

## サマリ

| フィールド | YANG default | init_cfg注入値 | Python fallback | del_handler fallback | 乖離 |
|-----------|-------------|----------------|-----------------|----------------------|------|
| `tsa_enabled` | `"false"` | `"false"` | `TSA_DEFAULTS="false"` | `"false"` (TSB実行) | なし |
| `wcmp_enabled` | `"false"` | `"false"` | `WCMP_DEFAULTS="false"` | `"false"` | なし |
| `idf_isolation_state` | `"unisolated"` | `"unisolated"` | `IDF_DEFAULTS="unisolated"` | `"unisolated"` | なし (SpineRouter以外はスキップ) |
| `asn` | なし | なし | なし | なし | N/A |
| `peers` | なし | なし | なし | なし | N/A |
