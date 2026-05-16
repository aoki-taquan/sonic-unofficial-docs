# appl-mclag — Phase H (プラットフォーム差) 中間調査

対象: `docs/reference/config-db/appl-mclag.md`
書込主体: `mclagsyncd` (sonic-swss) + `iccpd` (sonic-buildimage)

## 1. ASIC 別 isolation-group capability 分岐

`mclaglink.cpp:190-378` の `setPortIsolate()` は **環境変数 `platform`** を `getenv()` で取得し、許可リスト一致時のみ `ISOLATION_GROUP_TABLE` を書き込む。不一致時は ACL fallback (`ACL_TABLE_TABLE` + `ACL_RULE_TABLE`) へ分岐。

```cpp
// mclaglink.cpp:192-202
static const unordered_set<string> supported {
    BRCM_PLATFORM_SUBSTRING,   // "broadcom"
    BFN_PLATFORM_SUBSTRING,    // "barefoot"
    CTC_PLATFORM_SUBSTRING,    // "centec"
    CLX_PLATFORM_SUBSTRING,    // "clounix"
    MRVL_PRST_PLATFORM_SUBSTRING, // "marvell-prestera"
    MRVL_TL_PLATFORM_SUBSTRING    // "marvell-teralynx"
};
const char *platform = getenv("platform");
if (platform != nullptr && supported.find(string(platform)) != supported.end())
{ /* ISOLATION_GROUP_TABLE 経路 */ }
else
{ /* ACL fallback 経路 */ }
```

`platform` 環境変数の供給元: `docker-iccpd/iccpd.sh:3`:

```bash
export platform=$(sonic-cfggen -d -y /etc/sonic/sonic_version.yml --var asic_type)
```

すなわち CONFIG_DB の `DEVICE_METADATA|localhost.platform` ではなく **`asic_type`** に依存する。`asic_type` 値が上記 6 種以外の場合は全て ACL fallback。

| asic_type 値 | APPL_DB 書込先 | 下流 SAI |
|---|---|---|
| `broadcom` | `ISOLATION_GROUP_TABLE` | `SAI_OBJECT_TYPE_ISOLATION_GROUP` (sai_isolation_group_api) |
| `barefoot` | `ISOLATION_GROUP_TABLE` | 同上 |
| `centec` | `ISOLATION_GROUP_TABLE` | 同上 |
| `clounix` | `ISOLATION_GROUP_TABLE` | 同上 |
| `marvell-prestera` | `ISOLATION_GROUP_TABLE` | 同上 |
| `marvell-teralynx` | `ISOLATION_GROUP_TABLE` | 同上 |
| `mellanox` / `vs` / `innovium` / 未設定 / その他 | `ACL_TABLE_TABLE` + `ACL_RULE_TABLE` (key=`mclag`/`mclag:mclag`) | `SAI_OBJECT_TYPE_ACL_TABLE`/`ACL_ENTRY` (PACKET_ACTION=DROP) |

### 観測差分（運用者向け）

- ACL fallback では `OUT_PORTS` から `PortChannel` を除外し Ethernet ポートのみが対象 (`mclaglink.cpp:352`)。
- ISOLATION_GROUP 経路では `MEMBERS` から `Ethernet` を除外し PortChannel のみが対象 (`mclaglink.cpp:258`)。**分離対象オブジェクトの粒度が ASIC により異なる**。
- ACL fallback では `OUT_PORTS` 空 (`op_len == 0`) で `ACL_TABLE_TABLE.mclag` 全体を DEL するが、ISOLATION_GROUP 経路では `MEMBERS` を空文字列にしてエントリを保持する (ICCP up 時)。

## 2. multi-ASIC (multi-NPU) 動作

iccpd / mclagsyncd は **multi-asic を直接サポートしない**。

- `docker-iccpd/Dockerfile.j2`・`iccpd.service.j2`・`sonic_debian_extension.j2:1093-1095` 共通で per-namespace 起動ロジック無し。`iccpd.service` は **host 名前空間で 1 個のみ** 起動 (デフォルト disable、`systemctl enable iccpd` で有効化)。
- `iccpd.j2` テンプレートは `MC_LAG`・`DEVICE_METADATA['localhost']['mac']` の **デフォルト CONFIG_DB のみ** 参照。`asic0`/`asic1` の per-namespace config を読まない。
- `mclagsyncd` の Redis 接続は `DBConnector("APPL_DB",0)` 形式で **host (asic 非指定)** のみ。`SonicV2Connector(use_unix_socket_path=True, namespace=...)` 相当の呼び出し無し (`mclaglink.cpp:1796-1816`)。

結論: 公式 community SONiC では **single-ASIC platform 上の MCLAG のみが想定スコープ**。Multi-ASIC platform (T2/chassis) で iccpd を起動した場合は CONFIG_DB[0] のみが有効で、front-end ASIC 群への伝播は保証外。

## 3. ベンダー差 (ASIC SAI capability の差)

| ベンダー / asic_type | ISOLATION_GROUP capability | 備考 |
|---|---|---|
| Broadcom (Tomahawk/Trident) | あり | SAI_OBJECT_TYPE_ISOLATION_GROUP 完全サポート |
| Barefoot Tofino | あり | P4-Studio で実装 |
| Centec | あり | community fork で実装 |
| Clounix | あり | community fork で実装 |
| Marvell Prestera (Falcon) | あり | mclaglink.h で明示サポート |
| Marvell Teralynx (旧 Innovium) | あり | 2024-Q3 以降に追加 (`mclaglink.h:59`) |
| Mellanox (Spectrum) | **なし** (ACL fallback) | mclaglink.h サポートリスト外 |
| VS (simulator) | **なし** (ACL fallback) | dev/CI 用 |

`mellanox` プラットフォームで MCLAG を構成した場合は `ACL_TABLE|mclag` + `ACL_RULE|mclag:mclag` 経由で egress port isolation を実現する。ACL 経路は **L3 ACL table type** を使うため L3 ACL リソースを 1 つ消費する点に留意。

## 4. iccpd 側のプラットフォーム非依存性

iccpd (`sonic-buildimage/src/iccpd/`) は ICCP プロトコル (RFC 7275) 実装で **ASIC 識別ロジックを持たない**。`grep -nE 'platform|asic'` で iccpd ソースに ASIC 分岐は無し (確認済み)。タイマー定数 (`CONNECT_INTERVAL_SEC=1`, `HEARTBEAT_TIMEOUT_SEC=15`, `TRANSIT_INTERVAL_SEC=1` 等、`scheduler.h:40-42`) は全プラットフォーム共通。

## 5. 結論

| 観点 | プラットフォーム差 |
|---|---|
| `ISOLATION_GROUP_TABLE` 書込 | asic_type が `broadcom`/`barefoot`/`centec`/`clounix`/`marvell-prestera`/`marvell-teralynx` のみ |
| `ACL_TABLE_TABLE` + `ACL_RULE_TABLE` フォールバック | 上記以外 (例: `mellanox`, `vs`) |
| `MCLAG_FDB_TABLE` / `LAG_TABLE` / `PORT_TABLE` / `INTF_TABLE` | 全プラットフォーム共通 |
| iccpd タイマー・IPC 定数 | 全プラットフォーム共通 |
| multi-ASIC (chassis/T2) | サポート外 (host 名前空間 CONFIG_DB のみ参照) |

調査範囲: `sonic-swss/mclagsyncd/{mclaglink.cpp,mclaglink.h,mclag.h}`, `sonic-buildimage/src/iccpd/`, `sonic-buildimage/dockers/docker-iccpd/`, `sonic-buildimage/files/build_templates/iccpd.service.j2`.
