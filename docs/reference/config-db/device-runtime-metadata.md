---
title: DEVICE_RUNTIME_METADATA テーブル
description: "DEVICE_RUNTIME_METADATA テーブル — CONFIG_DB に永続化されない、起動時に計算で組み立てられる 仮想テーブル。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-py-common/sonic_py_common/device_info.py
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/tests/yang_model_tests/tests_config/feature.json
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - DEVICE_RUNTIME_METADATA
    - DEVICE_METADATA
    - FEATURE
  cli: []
  yang: []
  _no_related_cli: true
  _no_related_yang: true
---

# DEVICE_RUNTIME_METADATA テーブル

## 概要

[CONFIG_DB](../../reference/glossary.md#term-config_db) に永続化されない、起動時に計算で組み立てられる **仮想テーブル**[^1]。`sonic_py_common.device_info.get_device_runtime_metadata()` が hwsku / chassis / port-config 情報から生成し、`sonic-cfggen` の Jinja 環境に投入される。`FEATURE.has_per_asic_scope` などのテンプレ条件式から `DEVICE_RUNTIME_METADATA['ETHERNET_PORTS_PRESENT']` のように参照される。[CONFIG_DB](../../reference/glossary.md#term-config_db) ファイルには通常永続化されない。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>DEVICE_RUNTIME_METADATA")]
  DM["sonic-cfggen"]
  CDB --> DM
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

[CONFIG_DB](../../reference/glossary.md#term-config_db) テーブル形式の慣習に従うが、実体は `sonic-cfggen` のテンプレ変数辞書である。論理的には:

```text
DEVICE_RUNTIME_METADATA|CHASSIS_METADATA
DEVICE_RUNTIME_METADATA|ETHERNET_PORTS_PRESENT
DEVICE_RUNTIME_METADATA|MACSEC_SUPPORTED
```

## サブキーとフィールド

| サブキー | フィールド | 値 | 説明 |
|---------|-----------|----|------|
| `CHASSIS_METADATA` | `module_type` | `supervisor` / `linecard` | シャーシ環境でのみ存在。`is_supervisor()` の判定結果 |
| `ETHERNET_PORTS_PRESENT` | (直値) | `True`/`False` | `port_config.ini` がプラットフォーム配下に存在するかどうか。`get_path_to_port_config_file()` の結果 |
| `MACSEC_SUPPORTED` | (直値) | `True`/`False` | プラットフォーム JSON で MACsec 機能が宣言されているか |

実コードでは `runtime_metadata` 辞書に `chassis_metadata` / `port_metadata` / `macsec_support_metadata` を merge して返している[^1]。

## 用途 (Jinja からの参照例)

```jinja
"has_per_asic_scope": "{% if not DEVICE_RUNTIME_METADATA['ETHERNET_PORTS_PRESENT']
  or ('CHASSIS_METADATA' in DEVICE_RUNTIME_METADATA
       and DEVICE_RUNTIME_METADATA['CHASSIS_METADATA']['module_type'] in ['supervisor']) %}False{% else %}True{% endif %}"
```

(`init_cfg.json.j2` の `FEATURE` テーブル展開で使用)[^2]。

<!-- defaults -->
## コード由来の暗黙デフォルト (Phase A)

<!-- evidence: sonic-buildimage/src/sonic-py-common/sonic_py_common/device_info.py / sonic-buildimage/files/build_templates/init_cfg.json.j2 / sonic-host-services/scripts/featured -->

`DEVICE_RUNTIME_METADATA` は **CONFIG_DB に永続化されない仮想テーブル** で、`sonic_py_common.device_info.get_device_runtime_metadata()` が起動時にプラットフォーム検出結果から自動生成する (`device_info.py:735-747`)。ユーザー設定経路 (CLI / minigraph / db_migrator / YANG transformer) は存在しないため、全フィールドが **コード由来デフォルト** となる。

### サブキー存在条件のデフォルト

| サブキー | 既定の存在条件 | 判定 |
|---------|--------------|------|
| `CHASSIS_METADATA` | **chassis 環境でのみ存在**。非 chassis (典型 ToR / leaf) ではキー自体なし | `is_chassis()` = `(is_voq_chassis() and not is_disaggregated_chassis()) or is_packet_chassis() or is_virtual_chassis()` (`device_info.py:667-668`) |
| `ETHERNET_PORTS_PRESENT` | **常に存在** | `port_config.ini` 探索結果を `True`/`False` で必ずセット |
| `MACSEC_SUPPORTED` | **常に存在** | `platform_env.conf` 未配置でも `False` を必ずセット |

### フィールド既定値

| サブキー / フィールド | コード由来デフォルト | 検出ロジック | 出典 |
|----------------------|---------------------|-------------|------|
| `CHASSIS_METADATA.module_type` | `'linecard'` (`supervisor=1` が `platform_env.conf` に無い場合) / `'supervisor'` (ある場合) | `'supervisor' if is_supervisor() else 'linecard'` | `device_info.py:738`, `is_supervisor()` L699-712 |
| `CHASSIS_METADATA.chassis_type` | `'packet'` (`switch_type` が `voq`/`fabric` 以外、または `chassisdb.conf` 不在) / `'voq'` (両条件成立) | `'voq' if is_voq_chassis() else 'packet'` | `device_info.py:739`, `is_voq_chassis()` L630-634 |
| `ETHERNET_PORTS_PRESENT` | `False` (`get_path_to_port_config_file()` が None を返す = supervisor / fabric card 等) / `True` (port_config.ini 検出時) | `bool(get_path_to_port_config_file(hwsku=None, asic="0" if is_multi_npu() else None))` | `device_info.py:741` |
| `MACSEC_SUPPORTED` | `False` (`platform_env.conf` 未配置 / `macsec_enabled` 行なし / `macsec_enabled=0`) / `True` (`macsec_enabled=1`) | `bool(is_macsec_supported())` | `device_info.py:742`, `is_macsec_supported()` L714-732 |

### platform 自動検出のフォールバック挙動

- **`platform_env.conf` が存在しないプラットフォーム** → `is_supervisor()=False`, `is_macsec_supported()=0`。結果として `MACSEC_SUPPORTED=False`、(chassis 環境の場合) `module_type='linecard'` がデフォルトになる (`device_info.py:700-702, 720-721`)。
- **`switch_type` 未設定** (`get_platform_info().get('switch_type')` が空) → `is_voq_chassis()=False`, `is_packet_chassis()=False` → 仮想 chassis でなければ `is_chassis()=False` → `CHASSIS_METADATA` キー自体が生成されない。
- **multi-NPU プラットフォーム** → `get_path_to_port_config_file()` 呼び出し時に `asic="0"` を指定して ASIC#0 名前空間の port_config.ini を確認する (`device_info.py:741`)。

### init_cfg.json.j2 が参照するデフォルト経路

`featured` (sonic-host-services) も含め、デフォルト値は最終的に `init_cfg.json.j2` の FEATURE エントリ生成へ反映される (具体的な分岐は本ページ「例外条件・特殊挙動」表を参照):

- `ETHERNET_PORTS_PRESENT=False` または `module_type=supervisor` の組み合わせで `bgp` / `teamd` / `has_per_asic_scope` が `disabled` / `False` に倒れる。
- `MACSEC_SUPPORTED=False` で `macsec` feature が `disabled`。
- `CHASSIS_METADATA` キーなしの環境では `has_global_scope=True` がデフォルト。

> **書き込み不能**: ユーザーが `config_db.json` でこのテーブルを上書きしても、`get_device_runtime_metadata()` が `sonic-cfggen` 実行時に再生成するため反映されない。
<!-- /defaults -->

<!-- value-behavior -->
## 値依存挙動マトリクス

### `ETHERNET_PORTS_PRESENT` (True/False)

| 値 | 挙動 |
|----|------|
| `True` | [port_config.ini](../../reference/glossary.md#term-port-config-ini) が存在。init_cfg.json.j2 が `has_per_asic_scope = "True"` を生成可能 |
| `False` | [port_config.ini](../../reference/glossary.md#term-port-config-ini) なし（supervisor 等）。init_cfg.json.j2 が `has_per_asic_scope = "False"` を生成 |

### `CHASSIS_METADATA.module_type` (supervisor/linecard)

| 値 | 挙動 |
|----|------|
| `supervisor` | init_cfg.json.j2 の Jinja 条件式で per-asic インスタンスを False に設定 |
| `linecard` | per-asic インスタンス有効として扱う |
| キー自体が存在しない（非 chassis） | linecard 相当として扱われる（`'CHASSIS_METADATA' in DEVICE_RUNTIME_METADATA` が False） |

### `MACSEC_SUPPORTED` (True/False)

| 値 | 挙動 |
|----|------|
| `True` | init_cfg.json.j2 に MACsec 関連 FEATURE エントリが含まれる |
| `False` / キーなし | MACsec FEATURE エントリは生成されない |

> 明示的な enum 制約なし。[YANG](../../reference/glossary.md#term-yang) スキーマなし。CONFIG_DB に永続化されない仮想テーブル。

<!-- /value-behavior -->

## 注意点

- [YANG](../../reference/glossary.md#term-yang) モジュールは存在しない (`sonic-yang-models/yang-models/` 配下にスキーマなし)
- CONFIG_DB の永続テーブルではなく、`sonic-cfggen` 実行時にのみ存在するメモリ上の名前空間
- ベンダー / hwsku によりキーの有無が変わる (chassis でない箱では `CHASSIS_METADATA` キー自体が存在しない)

<!-- ref-triangle:start -->

## 関連リファレンス

- (関連リンクなし)

<!-- ref-triangle:end -->

## 引用元

[^1]: `src/sonic-py-common/sonic_py_common/device_info.py::get_device_runtime_metadata`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-py-common/sonic_py_common/device_info.py#L735>
[^2]: 使用例: `src/sonic-yang-models/tests/yang_model_tests/tests_config/feature.json` ほか init_cfg テンプレ群. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/tests/yang_model_tests/tests_config/feature.json>

## 関連ページ
- [CONFIG_DB: DEVICE_METADATA](device-metadata.md)
- [CONFIG_DB: FEATURE](feature.md)

<!-- ops-hint -->
## 運用ヒント

### 典型値

- CONFIG_DB に永続化されない仮想テーブル。`sonic-cfggen` 実行時のメモリ上に展開される。
- サブキー: `CHASSIS_METADATA` (chassis のみ) / `ETHERNET_PORTS_PRESENT` / `MACSEC_SUPPORTED`。

### よくある誤設定

- 手動でこのテーブルを `config_db.json` に書こうとしても無視される (テンプレ生成専用)。
- chassis でない箱で `CHASSIS_METADATA` が存在しないことを前提に書かれていないテンプレを使うとエラー。

### 確認コマンド

```bash
sonic-cfggen -d -v "DEVICE_RUNTIME_METADATA"
sonic-cfggen -d -v "DEVICE_RUNTIME_METADATA['ETHERNET_PORTS_PRESENT']"
```
<!-- /ops-hint -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

| consumer | 条件 | 挙動 |
|---|---|---|
| init_cfg.json.j2 | `ETHERNET_PORTS_PRESENT = False` | `bgp` / `teamd` feature の初期 state を `disabled` に設定（j2:67,75） |
| init_cfg.json.j2 | `CHASSIS_METADATA.module_type = supervisor` | `bgp` feature を `disabled`、`has_per_asic_scope=False` に設定（j2:67,107） |
| init_cfg.json.j2 | `CHASSIS_METADATA.module_type = linecard` | `has_global_scope=False` に設定（j2:106） |
| init_cfg.json.j2 | `MACSEC_SUPPORTED = False` または platform_env.conf に `macsec_enabled=0` | device type が SpineRouter 系でも `macsec` feature を `disabled` に設定（j2:90） |
| device_info.py | `platform_env.conf` が存在しない | `is_macsec_supported()` が 0 を返し `MACSEC_SUPPORTED=False` となる（device_info.py:720-721） |

> **Evidence**: [sonic-buildimage](../../reference/glossary.md#term-sonic-buildimage) `files/build_templates/init_cfg.json.j2:67,75,90,106-107`; `src/sonic-py-common/sonic_py_common/device_info.py:720-747`
<!-- /cdb-exceptions -->


<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`sonic-cfggen` / 各種設定生成スクリプト が CONFIG_DB の `DEVICE_RUNTIME_METADATA` テーブルを購読する。

`DEVICE_RUNTIME_METADATA` は動的に生成されるデバイス情報 (mac address 等) を保持。

### 段階 2 — CFG→APPL 翻訳

なし (APPL_DB 中継なし)

### 段階 3 — APPL→SAI

なし (SAI 非経由 — ランタイムメタデータ)

### 段階 4 — タイミングと副作用

**適用タイミング**: デバイス起動時に `sonic-cfggen` が生成して CONFIG_DB に書き込む。実行時に参照されるが基本的に読み取り専用。

**副作用**: 直接的なネットワーク動作への影響なし。`DEVICE_METADATA` と組み合わせてシステム設定生成に使用。
<!-- /runtime-trace -->

<!-- entry-points -->
## 書き込み入り口 (Direction A)

対象テーブル: `DEVICE_RUNTIME_METADATA`

### CLI
- なし (CLI 書き込みパスなし)

### minigraph / sonic-cfggen
- なし

### REST / gNMI (sonic-mgmt-common)
- なし (対応 OpenConfig/SONiC YANG transformer なし)

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- なし

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- 起動時に `sonic-cfggen` や `platform_env.conf` スクリプトが実行環境情報 (platform name, HW SKU 等) を注入する。YANG モデルなし・スキーマレス
<!-- /entry-points -->

<!-- glossary-links-injected: e33fec70e206 -->
