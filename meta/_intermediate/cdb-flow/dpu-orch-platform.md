# dpu-orch — Phase H プラットフォーム差分調査メモ

調査日: 2026-05-19
対象: DpuOrchDaemon / DEVICE_METADATA DPU フィールドに関わる platform / subtype / switch_type 依存分岐

## 調査対象ファイル

- `sonic-swss/orchagent/main.cpp` (getCfgSwitchType, gMySwitchSubType)
- `sonic-swss/orchagent/orchdaemon.cpp` (OrchDaemon::init SmartSwitch 分岐, DpuOrchDaemon)
- `sonic-buildimage/dockers/docker-orchagent/orchagent.sh` (platform 分岐, subtype SmartSwitch 分岐)
- `sonic-buildimage/dockers/docker-orchagent/enable_counters.py` (switch_type=dpu 分岐)
- `sonic-buildimage/dockers/docker-orchagent/switch.json.j2` (switch_type!=dpu 分岐)
- `sonic-buildimage/dockers/docker-orchagent/ipinip.json.j2` (switch_type=dpu → 空配列)
- `sonic-buildimage/dockers/docker-orchagent/orch_zmq_tables.conf.j2` (orch_northbond_dash_zmq_enabled 条件)

---

## 1. platform (asic_type) 分岐: orchagent.sh MAC アドレス取得

`orchagent.sh` は `swss_vars.j2` から `asic_type` を `export platform=<value>` として取得し、
MAC アドレス取得元を分岐する。DPU 向けの主要プラットフォームは以下:

```bash
# orchagent.sh:86-92
elif [ "$platform" == "nvidia-bluefield" ]; then
    ORCHAGENT_ARGS+="-m $MAC_ADDRESS"   # eth0 からの通常取得
elif [ "$platform" == "pensando" ]; then
    MAC_ADDRESS=$(ip link show int_mnic0 | grep ether | awk '{print $2}')
    if [ "$MAC_ADDRESS" == "" ]; then
        MAC_ADDRESS=$(ip link show eth0-midplane | grep ether | awk '{print $2}')
    fi
    ORCHAGENT_ARGS+="-m $MAC_ADDRESS"
```

| `platform` 値 | MAC 取得元 | DPU 用途 |
|--------------|-----------|---------|
| `nvidia-bluefield` | `eth0` (swss_vars.j2 経由) | NVIDIA BlueField DPU |
| `pensando` | `int_mnic0` → `eth0-midplane` フォールバック | AMD/Pensando Elba DPU |
| その他 | `eth0` (swss_vars.j2 経由) | 汎用フォールバック |

`switch_type = "dpu"` であっても、この分岐は `platform` 変数値によって決まり `switch_type` とは独立している。

---

## 2. subtype 分岐: SmartSwitch ZMQ アドレス (orchagent.sh)

```bash
# orchagent.sh:107-116
LOCALHOST_SUBTYPE=`sonic-db-cli CONFIG_DB hget "DEVICE_METADATA|localhost" "subtype"`
if [[ x"${LOCALHOST_SUBTYPE}" == x"SmartSwitch" ]]; then
    midplane_mgmt_state=$( ip -json -4 addr show eth0-midplane | jq -r ".[0].operstate" )
    if [[ $midplane_mgmt_state == "UP" ]]; then
        ORCHAGENT_ARGS+=" -q tcp://eth0-midplane"
    else
        ORCHAGENT_ARGS+=" -q tcp://127.0.0.1"
    fi
else
    ORCHAGENT_ARGS+=" -q tcp://127.0.0.1"
fi
```

SmartSwitch (NPU 側) では `subtype = "SmartSwitch"` が設定されている。DPU 上の orchagent は
`switch_type = "dpu"` であり `subtype` は通常 `SmartSwitch` ではないため、ZMQ アドレスは
`tcp://127.0.0.1` (loopback) になる。

| 動作環境 | `subtype` | ZMQ アドレス |
|---------|-----------|------------|
| SmartSwitch NPU 側 | `SmartSwitch` | `tcp://eth0-midplane`（midplane UP 時）/ `tcp://127.0.0.1`（DOWN 時） |
| DPU 上 orchagent (`switch_type=dpu`) | 通常未設定 | `tcp://127.0.0.1` |

---

## 3. subtype 分岐: DashEniFwdOrch 追加 (OrchDaemon::init)

```cpp
// orchdaemon.cpp:613-618
if (gMySwitchSubType == "SmartSwitch")
{
    DashEniFwdOrch *dash_eni_fwd_orch = new DashEniFwdOrch(m_configDb, m_applDb,
        APP_DASH_ENI_FORWARD_TABLE, gNeighOrch);
    gDirectory.set(dash_eni_fwd_orch);
    m_orchList.push_back(dash_eni_fwd_orch);
}
```

`gMySwitchSubType` は `getCfgSwitchType()` (`main.cpp:269`) で `DEVICE_METADATA|localhost.subtype` を読む。
`subtype = "SmartSwitch"` の場合 `DashEniFwdOrch` が `OrchDaemon::init()` に追加される。

DPU 上の `DpuOrchDaemon::init()` は `OrchDaemon::init()` を先行呼出しする
(`orchdaemon.cpp:1324`) ため、NPU 側の `OrchDaemon` でこの分岐が実行される。

---

## 4. switch_type 分岐: switch.json.j2 — SWITCH_TABLE ECMP/FDB 設定

```jinja
{# switch.json.j2:35 #}
{% if not DEVICE_METADATA.localhost.switch_type or DEVICE_METADATA.localhost.switch_type != "dpu" %}
    "ecmp_hash_seed": "...",
    "lag_hash_seed": "...",
    "fdb_aging_time": "600",
    ...
{% endif %}
```

`switch_type = "dpu"` のとき `SWITCH_TABLE:switch` への ECMP hash seed / LAG hash seed /
FDB aging time / ordered_ecmp 設定が **一切生成されない**。DPU の SAI は標準 NPU の ECMP
ハッシュ・FDB エージング機能を持たないため、これらのパラメータを適用しない。

---

## 5. switch_type 分岐: ipinip.json.j2 — IP-in-IP デカプ設定

```jinja
{# ipinip.json.j2:1 #}
{% if DEVICE_METADATA['localhost']['switch_type'] == "dpu" %}
[]
{% else %}
... (通常 NPU 用 IP-in-IP テーブル生成) ...
{% endif %}
```

`switch_type = "dpu"` のとき `ipinip.json.j2` は空配列 `[]` を出力し、
`TUNNEL_DECAP_TABLE` / `TUNNEL_DECAP_TERM_TABLE` が一切生成されない。
DPU は IP-in-IP デカプセルを DASH パイプラインで処理するため、
orchagent/syncd の汎用トンネルデカプ設定は不要。

---

## 6. switch_type 分岐: enable_counters.py — ENI / DASH_METER カウンタ有効化

```python
# enable_counters.py:43-44
if platform_info.get('switch_type') == 'dpu':
    for key in dpu_counters:   # ["ENI", "DASH_METER"]
        enable_counter_group(db, key)
```

`switch_type = "dpu"` のとき `ENI` および `DASH_METER` の FLEX_COUNTER_TABLE エントリが有効化される。
通常 NPU では有効化されない DPU 固有カウンタグループである。

---

## 7. orch_zmq_tables.conf.j2 — ZMQ テーブルリストの動的生成

```jinja
{% if DEVICE_METADATA.localhost.orch_northbond_dash_zmq_enabled != "false" %}
DASH_VNET_TABLE
... (DASHテーブル群) ...
{% endif %}
{% if DEVICE_METADATA.localhost.orch_northbond_route_zmq_enabled == "true" %}
ROUTE_TABLE
LABEL_ROUTE_TABLE
{% endif %}
```

`orch_northbond_dash_zmq_enabled` が `"false"` でない（= `"true"` または欠如）場合、
全 DASH テーブルが `/etc/swss/orch_zmq_tables.conf` に書き込まれる。
このファイルは orchagent 起動時に `load_zmq_tables()` が読み込み、ZMQ クライアントが
これらのテーブルを購読する。プラットフォーム種別ではなく CONFIG_DB フィールド値で制御される。

---

## 結論

| 分岐軸 | 条件 | DPU 時の挙動 | evidence |
|--------|------|------------|---------|
| `platform` (asic_type) | `nvidia-bluefield` | MAC = eth0、`-m` 付与 | orchagent.sh:86 |
| `platform` (asic_type) | `pensando` | MAC = int_mnic0 → eth0-midplane | orchagent.sh:88-91 |
| `subtype` | `SmartSwitch` | ZMQ = tcp://eth0-midplane (midplane UP 時) | orchagent.sh:107-113 |
| `subtype` | `SmartSwitch` (NPU 側 OrchDaemon::init) | DashEniFwdOrch 追加 | orchdaemon.cpp:613-618 |
| `switch_type` | `dpu` | switch.json.j2: ECMP/FDB 設定スキップ | switch.json.j2:35 |
| `switch_type` | `dpu` | ipinip.json.j2: IP-in-IP デカプ設定スキップ | ipinip.json.j2:1 |
| `switch_type` | `dpu` | enable_counters.py: ENI/DASH_METER カウンタ有効化 | enable_counters.py:43 |
| `orch_northbond_dash_zmq_enabled` | `!= "false"` | orch_zmq_tables.conf に DASH テーブル群追加 | orch_zmq_tables.conf.j2:1-25 |
