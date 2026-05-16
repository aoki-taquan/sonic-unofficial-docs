# ZMQ 関連 CONFIG_DB フィールド — コード由来デフォルト調査メモ (Phase A)

調査日: 2026-05-14
対象: CONFIG_DB 上の ZMQ 関連フィールド群

---

## 調査対象ファイル

| ファイル | リポジトリ | 役割 |
|---------|-----------|------|
| `lib/orch_zmq_config.h` | sonic-swss | ZMQ 設定マクロ・関数宣言 |
| `lib/orch_zmq_config.cpp` | sonic-swss | `get_feature_status()` / `get_zmq_port()` / `create_local_zmq_client()` 実装 |
| `orchagent/orchdaemon.cpp` | sonic-swss | `get_feature_status(ORCH_NORTHBOND_DASH_ZMQ_ENABLED, true)` 呼び出し |
| `fpmsyncd/routesync.cpp` | sonic-swss | `create_local_zmq_client(ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED, false)` 呼び出し |
| `common/zmqserver.h` | sonic-swss-common | `ORCH_ZMQ_PORT = 8100` 定数定義 |
| `dockers/docker-orchagent/orch_zmq_tables.conf.j2` | sonic-buildimage | Jinja2 テンプレートで `orch_northbond_dash_zmq_enabled` / `orch_northbond_route_zmq_enabled` 参照 |
| `dockers/docker-orchagent/orchagent.sh` | sonic-buildimage | `DEVICE_METADATA|localhost.subtype` を読んで ZMQ アドレス (-q) を決定 |
| `dockers/docker-sonic-gnmi/gnmi-native.sh` | sonic-buildimage | SmartSwitch 時に `-zmq_port=8100` を gnmi に渡す |
| `src/sonic-yang-models/yang-models/sonic-smart-switch.yang` | sonic-buildimage | `DPU_LIST` の `orchagent_zmq_port` 葉定義 |

---

## フィールド別 コード由来デフォルト

### 1. `orch_northbond_dash_zmq_enabled` (DEVICE_METADATA|localhost)

**コード由来デフォルト**: `true`

```cpp
// sonic-swss/orchagent/orchdaemon.cpp:1329
if (get_feature_status(ORCH_NORTHBOND_DASH_ZMQ_ENABLED, true))
```

`get_feature_status()` のシグネチャ:
```cpp
// sonic-swss/lib/orch_zmq_config.cpp:83-110
bool swss::get_feature_status(std::string feature, bool default_value) {
    ...
    enabled = config_db.hget("DEVICE_METADATA|localhost", feature);
    if (!enabled) {
        // フィールド不在 → default_value を返す
        return default_value;
    }
    return *enabled == "true";
}
```

- フィールド **不在** → `default_value = true` → DASH ZMQ **有効**
- フィールド = `"true"` → 有効
- フィールド = `"false"` または他の文字列 → `*enabled == "true"` が偽 → **無効**

**Jinja2 テンプレートの判定**:
```jinja2
{# orch_zmq_tables.conf.j2:1 #}
{% if DEVICE_METADATA.localhost.orch_northbond_dash_zmq_enabled != "false" %}
DASH_VNET_TABLE
...
{% endif %}
```
Jinja2 では **フィールド不在**のとき `!= "false"` が真 → DASH テーブルを conf に追記。
C++ コードとの整合: どちらも「不在 → 有効」。

**デフォルトの根拠コード**:
- `sonic-swss/orchagent/orchdaemon.cpp:1329` — `get_feature_status(ORCH_NORTHBOND_DASH_ZMQ_ENABLED, true)`
- `sonic-buildimage/dockers/docker-orchagent/orch_zmq_tables.conf.j2:1` — `!= "false"` 判定

---

### 2. `orch_northbond_route_zmq_enabled` (DEVICE_METADATA|localhost)

**コード由来デフォルト**: `false`

```cpp
// sonic-swss/fpmsyncd/routesync.cpp:155
m_zmqClient(create_local_zmq_client(ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED, false)),
```

`create_local_zmq_client()` 内部:
```cpp
// sonic-swss/lib/orch_zmq_config.cpp:105-113
std::shared_ptr<swss::ZmqClient> swss::create_local_zmq_client(std::string feature, bool default_value) {
    auto enable = get_feature_status(feature, default_value);
    if (enable) {
        return create_zmq_client(ZMQ_LOCAL_ADDRESS);
    }
    return nullptr;
}
```

→ フィールド **不在** → `default_value = false` → ZMQ クライアント **nullptr** (= ROUTE ZMQ 無効)

同様に `fgnhgorch.cpp:27` / `routeresync.cpp:25` でも `create_local_zmq_client(ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED, false)` が呼ばれる。

**Jinja2 テンプレートの判定**:
```jinja2
{# orch_zmq_tables.conf.j2:27 #}
{% if DEVICE_METADATA.localhost.orch_northbond_route_zmq_enabled == "true" %}
ROUTE_TABLE
LABEL_ROUTE_TABLE
{% endif %}
```
Jinja2 では **フィールド不在**のとき `== "true"` が偽 → ROUTE テーブルを conf に追記しない。
C++ コードとの整合: どちらも「不在 → 無効」。

**デフォルトの根拠コード**:
- `sonic-swss/fpmsyncd/routesync.cpp:155` — `create_local_zmq_client(ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED, false)`
- `sonic-swss/orchagent/fgnhgorch.cpp:27` — 同上
- `sonic-swss/orchagent/routeresync.cpp:25` — 同上
- `sonic-buildimage/dockers/docker-orchagent/orch_zmq_tables.conf.j2:27` — `== "true"` 判定

---

### 3. `orchagent_zmq_port` (DPU|<name>)

**コード由来デフォルト**: なし（YANG で optional フィールド）

YANG 定義:
```yang
// sonic-smart-switch.yang:176-179
leaf orchagent_zmq_port {
    description "TCP listening port for ZMQ service on DPU orchagent";
    type inet:port-number;
}
```

- `default` 文なし → YANG validation のみ (inet:port-number = 1..65535)
- DPU orchagent 側は `-q tcp://<dpu_addr>` 形式でポートを含むアドレスを受け取り、
  ポート部はコード定数 `ORCH_ZMQ_PORT = 8100` をベースに計算する
- `orchagent_zmq_port` フィールドは SmartSwitch NPU 側が DPU への接続先ポートを知るための
  minigraph 由来メタ情報として保持される（読み出し側は gNMI の MixedDbClient など）

---

## システムレベル定数 (CONFIG_DB フィールドではない)

### `ORCH_ZMQ_PORT = 8100`

```cpp
// sonic-swss-common/common/zmqserver.h:16
static const int ORCH_ZMQ_PORT = 8100;
```

Namespace 分離時: `ORCH_ZMQ_PORT + NAMESPACE_ID + 1`
```cpp
// sonic-swss/lib/orch_zmq_config.cpp:37-51
int swss::get_zmq_port() {
    auto zmq_port = ORCH_ZMQ_PORT;
    const char* nsid = std::getenv("NAMESPACE_ID");
    // namespace start from 0, using original ZMQ port for global namespace
    zmq_port += std::stoi(nsid) + 1;
    return zmq_port;
}
```

- global namespace: NAMESPACE_ID 未設定 → port = 8100
- namespace 0: NAMESPACE_ID = "0" → port = 8101
- namespace N: port = 8100 + N + 1

### gnmi の ZMQ ポート (SmartSwitch のみ)

```bash
# sonic-buildimage/dockers/docker-sonic-gnmi/gnmi-native.sh:88-92
LOCALHOST_SUBTYPE=`sonic-db-cli CONFIG_DB hget "DEVICE_METADATA|localhost" "subtype"`
if [[ x"${LOCALHOST_SUBTYPE}" == x"SmartSwitch" ]]; then
    TELEMETRY_ARGS+=" -zmq_port=8100"
fi
```

→ `subtype == "SmartSwitch"` のとき gnmi に `-zmq_port=8100` を渡す。
この値は CONFIG_DB から読むのではなく gnmi-native.sh 内にハードコード。

### orchagent の ZMQ アドレス (SmartSwitch vs 他プラットフォーム)

```bash
# sonic-buildimage/dockers/docker-orchagent/orchagent.sh:105-118
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

→ ZMQ サーバアドレス (`-q`) はスクリプト内でハードコードされており、CONFIG_DB には存在しない。

---

## 要約表

| フィールド | CONFIG_DB キー | コード由来デフォルト | 根拠 |
|-----------|--------------|-------------------|------|
| `orch_northbond_dash_zmq_enabled` | `DEVICE_METADATA\|localhost` | `true` (不在時 DASH ZMQ 有効) | orchdaemon.cpp:1329 `get_feature_status(..., true)` |
| `orch_northbond_route_zmq_enabled` | `DEVICE_METADATA\|localhost` | `false` (不在時 ROUTE ZMQ 無効) | routesync.cpp:155 `create_local_zmq_client(..., false)` |
| `orchagent_zmq_port` | `DPU\|<name>` | なし (YANG optional) | sonic-smart-switch.yang:176-179 |

---

## Jinja2 vs C++ 判定方式の差異

| フィールド | Jinja2 判定 | C++ 判定 | 不在時挙動 |
|-----------|------------|---------|-----------|
| `orch_northbond_dash_zmq_enabled` | `!= "false"` | `== "true"` (get_feature_status) | Jinja2: 有効 / C++: default_value=true → 有効 |
| `orch_northbond_route_zmq_enabled` | `== "true"` | `== "true"` (get_feature_status) | Jinja2: 無効 / C++: default_value=false → 無効 |

**重要**: `orch_northbond_dash_zmq_enabled` について、Jinja2 は `!= "false"` で判定するが C++ は `== "true"` で判定する。
フィールドが `"true"` または **不在** の場合は両者で結果が一致するが、
フィールドが `"false"` 以外の無効値 (例: `"yes"`, `"1"`) の場合:
- Jinja2: 有効 (文字列が "false" でないため)
- C++: 無効 (`*enabled == "true"` が偽)

→ 実運用では `"true"` / `"false"` のみを使用すること。

---

## 証拠リンク

- `sonic-swss/orchagent/orchdaemon.cpp:1329` <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/orchdaemon.cpp#L1329>
- `sonic-swss/fpmsyncd/routesync.cpp:155` <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/fpmsyncd/routesync.cpp#L155>
- `sonic-swss/orchagent/fgnhgorch.cpp:27` <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/fgnhgorch.cpp#L27>
- `sonic-swss/orchagent/routeresync.cpp:25` <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/routeresync.cpp#L25>
- `sonic-swss/lib/orch_zmq_config.cpp` <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/lib/orch_zmq_config.cpp>
- `sonic-swss/lib/orch_zmq_config.h` <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/lib/orch_zmq_config.h>
- `sonic-swss-common/common/zmqserver.h:16` <https://github.com/sonic-net/sonic-swss-common/blob/158de8d3463ff4b841653f6d57190bb142b80d9c/common/zmqserver.h#L16>
- `sonic-buildimage/dockers/docker-orchagent/orch_zmq_tables.conf.j2` <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/dockers/docker-orchagent/orch_zmq_tables.conf.j2>
- `sonic-buildimage/dockers/docker-orchagent/orchagent.sh:105-118` <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/dockers/docker-orchagent/orchagent.sh#L105-L118>
- `sonic-buildimage/dockers/docker-sonic-gnmi/gnmi-native.sh:88-92` <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/dockers/docker-sonic-gnmi/gnmi-native.sh#L88-L92>
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-smart-switch.yang:176-179` <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-smart-switch.yang#L176-L179>
