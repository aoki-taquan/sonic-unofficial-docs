# device-runtime-metadata — Phase H: プラットフォーム差分

## 調査目的

`get_device_runtime_metadata()` が返す仮想テーブルの各フィールドが、ASIC ベンダ / ハードウェアプラットフォーム種別 / マルチ ASIC 構成によってどのように変化するかを整理する。

## 調査根拠

- `sonic-buildimage/src/sonic-py-common/sonic_py_common/device_info.py` L603-747 全行精読
- `sonic-buildimage/src/sonic-py-common/sonic_py_common/device_info.py` L511-570 (get_platform_info / get_sonic_version_info)
- `sonic-buildimage/src/sonic-py-common/sonic_py_common/device_info.py` L671-696 (is_smartswitch / is_dpu)

---

## 1. `CHASSIS_METADATA` — chassis 種別によるフィールド差

`CHASSIS_METADATA` キー自体の有無および内部フィールド値は、スイッチの構成種別に完全に依存する。

| プラットフォーム種別 | `CHASSIS_METADATA` 生成有無 | `module_type` | `chassis_type` | 判定関数 |
|---|---|---|---|---|
| 通常 ToR / Leaf / Spine (非 chassis) | **なし** (`is_chassis()=False`) | — | — | `is_chassis()` が `False` を返す |
| VOQ chassis (linecard) | 生成 | `'linecard'` | `'voq'` | `is_voq_chassis()=True`、`is_supervisor()=False` |
| VOQ chassis (supervisor) | 生成 | `'supervisor'` | `'voq'` | `is_voq_chassis()=True`、`is_supervisor()=True` (`platform_env.conf` に `supervisor=1`) |
| Packet chassis (linecard) | 生成 | `'linecard'` | `'packet'` | `is_packet_chassis()=True`、`is_supervisor()=False` |
| Packet chassis (supervisor) | 生成 | `'supervisor'` | `'packet'` | `is_packet_chassis()=True`、`is_supervisor()=True` |
| Virtual chassis (VS / テスト環境) | 生成 | `'linecard'` または `'supervisor'` | `'voq'` または `'packet'` | `is_virtual_chassis()=True` — `asic_type == "vs"` かつ `switch_type` が `"dummy-sup"`/`"voq"`/`"chassis-packet"` のいずれか。`sonic_version.yml` の `asic_type` が `"vs"` であること (`device_info.py:660-661`) |
| Disaggregated chassis | **なし** (`is_chassis()=False`) | — | — | `is_voq_chassis()=True` だが `is_disaggregated_chassis()=True` のため `is_chassis()` が `False` (`device_info.py:667-668`) |

### VOQ chassis の必須ファイル

- `chassisdb.conf` が存在すること (`is_chassis_config_absent()=False`): `is_voq_chassis()` が `True` になるための必要条件
- `switch_type` が `voq` または `fabric` であること (CONFIG_DB `DEVICE_METADATA|localhost.switch_type`)

---

## 2. `ETHERNET_PORTS_PRESENT` — プラットフォームによる差

| プラットフォーム種別 | 値 | 理由 |
|---|---|---|
| 通常 ToR / Leaf / Spine | `True` | hwsku ディレクトリ配下に `port_config.ini` または `platform.json` が存在する |
| Supervisor カード (chassis) | `False` | supervisor の hwsku には `port_config.ini` が存在しないのが標準 |
| Fabric カード (VOQ chassis) | `False` | fabric カードはデータプレーンポートを持たず `port_config.ini` 不在 |
| Multi-ASIC プラットフォーム | ASIC #0 の `port_config.ini` 存在に依存 | `get_path_to_port_config_file(hwsku=None, asic="0")` で ASIC 番号を `"0"` にハードコード (`device_info.py:741`) |
| VS (Virtual Switch) テスト環境 | `True` (通常) | VS プラットフォームのテスト用 hwsku に `port_config.ini` が付属するため |

---

## 3. `MACSEC_SUPPORTED` — プラットフォームによる差

| プラットフォーム種別 | 値 | 理由 |
|---|---|---|
| MACsec 非対応ハードウェア (大多数) | `False` | `platform_env.conf` 不在、または `macsec_enabled=0` |
| MACsec 対応ハードウェア (一部 Broadcom 等) | `True` | `platform_env.conf` に `macsec_enabled=1` が記述されている |
| VS / コンテナ環境 | `False` | `platform_env.conf` 不在のため `is_macsec_supported()=0` |

MACsec 対応の宣言は `platform_env.conf` への `macsec_enabled=1` 行追記のみで制御される。YANG スキーマ・BUILD フラグ・ASIC ベンダ別ハードコードは存在しない。

---

## 4. Virtual Chassis (VS) — asic_type="vs" の特殊性

`is_virtual_chassis()` は `get_platform_info().get('asic_type')` が `"vs"` であることを条件に含む (`device_info.py:660-661`)。`asic_type` は `sonic_version.yml` の `asic_type` フィールドから `get_platform_info()` 経由で読み込まれる (`device_info.py:550-551`)。

- VS 環境では `sonic_version.yml` に `asic_type: vs` が書き込まれる
- `switch_type` が `"dummy-sup"` / `"voq"` / `"chassis-packet"` のいずれかであれば `CHASSIS_METADATA` が生成される
- 実機 (非 VS) では `asic_type` が `"vs"` になることはないため、`is_virtual_chassis()` は `False` に固定される

---

## 5. SmartSwitch / DPU — 影響なし

`is_smartswitch()` および `is_dpu()` は `platform.json` 内の `"DPUS"` / `"DPU"` キー存在を確認する (`device_info.py:679-694`)。しかし `get_device_runtime_metadata()` はこれらの関数を参照しない。SmartSwitch / DPU 構成であっても、`DEVICE_RUNTIME_METADATA` のフィールド構造・値に直接的な差異は生じない。

---

## 6. Multi-ASIC — `ETHERNET_PORTS_PRESENT` の判定のみに影響

Multi-ASIC 環境 (`is_multi_npu()=True`) では、`get_path_to_port_config_file()` 呼び出し時に `asic="0"` を指定する (`device_info.py:741`)。これにより ASIC #0 の `port_config.ini` 存否で `ETHERNET_PORTS_PRESENT` を決定する。ASIC #1 以降の存否は確認されない。`CHASSIS_METADATA` および `MACSEC_SUPPORTED` は multi-ASIC 構成の影響を受けない。

---

## 総括

| フィールド / キー | プラットフォーム依存度 | 主要要因 |
|---|---|---|
| `CHASSIS_METADATA` (有無) | **高** | `switch_type`・`chassisdb.conf` 存在・`platform_env.conf`・`asic_type=vs` の組み合わせ |
| `CHASSIS_METADATA.module_type` | **高** | `platform_env.conf` の `supervisor=1` 行の有無 |
| `CHASSIS_METADATA.chassis_type` | **高** | `switch_type` が `voq`/`fabric` か `chassis-packet` か |
| `ETHERNET_PORTS_PRESENT` | **中** | hwsku の `port_config.ini` 存否。supervisor/fabric では `False` |
| `MACSEC_SUPPORTED` | **低** | `platform_env.conf` の `macsec_enabled=1` 行の有無。多くのプラットフォームで `False` |
