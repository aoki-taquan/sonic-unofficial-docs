# SUBNET_DECAP — フィールド暗黙デフォルト調査メモ (Phase A)

調査日: 2026-05-14
対象テーブル: CONFIG_DB `SUBNET_DECAP`

## 調査対象ファイル

- `sonic-swss/orchagent/tunneldecaporch.h` — `SubnetDecapConfig` 構造体定義 (行 48-55, 97-103)
- `sonic-swss/orchagent/tunneldecaporch.cpp` — `doSubnetDecapTask()` (行 566-699)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-subnet-decap.yang` — YANG 定義
- `sonic-buildimage/dockers/docker-orchagent/ipinip.json.j2` — ビルド時テンプレート

---

## フィールド別 暗黙デフォルト

### `status`

**YANG デフォルト**: `disable` (sonic-subnet-decap.yang:39)

**コード由来デフォルト**: `false` (C++ bool)

```cpp
// tunneldecaporch.h:97-103
SubnetDecapConfig subnetDecapConfig = {
    false,   // enable
    "",      // src_ip
    "",      // src_ip_v6
    "IPINIP_SUBNET",    // tunnel (ハードコード)
    "IPINIP_SUBNET_V6"  // tunnel_v6 (ハードコード)
};
```

`doSubnetDecapTask()` (tunneldecaporch.cpp:578) で `bool enable = false;` をローカル初期化。
`fvField == "status"` を読んだ場合のみ `enable = (fvValue(fv) == "enable")` で上書き (行 626)。

DEL_COMMAND 受信時 (行 693): `subnetDecapConfig.enable = false` にリセット。

YANG と実装が一致: デフォルト `disable` / `false`。

---

### `src_ip`

**YANG**: `mandatory true`、デフォルト値なし

**コード由来デフォルト**: 空文字列 `""` (C++ std::string ゼロ初期化)

```cpp
// tunneldecaporch.h:100
std::string src_ip;  // デフォルト = ""
```

`doSubnetDecapTask()` (行 574): `string src_ip_str;` をローカル宣言 (空文字列)。
`fvField == "src_ip"` が存在しない場合 `src_ip_str` は空のまま。

**silent drop 条件**: `src_ip_str.empty() && src_ip_v6_str.empty()` の場合 (行 636-640):
```cpp
SWSS_LOG_ERROR("Both src_ip and src_ip_v6 of subnet decap are not set.");
valid = false;
```
→ どちらか一方のみ設定した場合はエラーにならずに受理される（片方のみでも動作する）。

**経路依存乖離**: YANG では両フィールドとも `mandatory true` だが、
実装では両方とも未設定の場合のみエラー。片方未設定は silent に無視される。

**初回設定 vs 更新の非対称性** (行 651-665):
```cpp
if (subnetDecapConfig.src_ip.empty()) {
    subnetDecapConfig.src_ip = src_ip_str;  // 初回: 無条件上書き
} else if (subnetDecapConfig.src_ip != src_ip_str) {
    if (subnetDecapConfig.enable) {
        // enable 時のみ既存 term の src_ip を更新
        setIpAttribute(subnetDecapConfig.tunnel, src_ip_str);
    }
    subnetDecapConfig.src_ip = src_ip_str;
}
```
→ `enable = false` の状態で `src_ip` を変更すると、struct は更新されるが
既存の SAI tunnel term entry の src_ip は変更されない（書込み順依存乖離）。

---

### `src_ip_v6`

**YANG**: `mandatory true`、デフォルト値なし

**コード由来デフォルト**: 空文字列 `""` (C++ std::string ゼロ初期化)

`src_ip` と同様のパターン (行 667-685)。`enable = false` 状態での更新時、
`subnetDecapConfig.src_ip_v6` は更新されるが SAI tunnel term は更新されない。

---

### `tunnel` / `tunnel_v6` (隠しフィールド)

**YANG に存在しない隠しハードコード値**:

```cpp
// tunneldecaporch.h:101-103
std::string tunnel    = "IPINIP_SUBNET";     // ハードコード
std::string tunnel_v6 = "IPINIP_SUBNET_V6";  // ハードコード
```

CONFIG_DB の `SUBNET_DECAP` には存在しないが、orchagent が内部で保持する
トンネル名。`ipinip.json.j2` (行 95, 162) の `TUNNEL_DECAP_TABLE:IPINIP_SUBNET`
および `TUNNEL_DECAP_TABLE:IPINIP_SUBNET_V6` と対応する。

`TUNNEL_DECAP_TABLE:IPINIP_SUBNET` の生成条件 (ipinip.json.j2:93):
```jinja2
{% if subnet_decap.enable %}
```
→ `SUBNET_DECAP.status == 'enable'` のエントリが 1 件以上存在する場合のみ
ビルド時に APP_DB 側トンネルエントリが生成される。

---

## シングルトン制約

`subnetDecapConfig` は `TunnelDecapOrch` クラスの単一メンバ変数。
CONFIG_DB に複数の `SUBNET_DECAP|*` エントリを書いても、
最後に処理された SET_COMMAND の値で上書きされる。
複数エントリを書いた場合の挙動は処理順序依存（書込み順依存乖離）。

---

## ipinip.json.j2 ビルド時デフォルト

`SUBNET_DECAP.status == 'enable'` の場合のみ `TUNNEL_DECAP_TABLE:IPINIP_SUBNET` が生成される。
`TUNNEL_DECAP_TABLE:IPINIP_SUBNET` の属性ハードコード:
- `tunnel_type`: `"IPINIP"` (固定)
- `dscp_mode`: Broadcom T1 → `"pipe"`, Broadcom 非 T1 → `"uniform"`, 非 Broadcom → `"pipe"` (プラットフォーム依存)
- `ecn_mode`: `"copy_from_outer"` (固定)
- `ttl_mode`: `"pipe"` (固定)
- VLAN アドレスの term entry: `term_type = "MP2MP"`, `subnet_type = "vlan"` (固定)

これらは CONFIG_DB の `SUBNET_DECAP` テーブルには現れず、
`ipinip.json.j2` がビルド時に APP_DB に直接注入する暗黙値。

---

## dead consumer 調査

- `ipinip.json.j2` が `SUBNET_DECAP.status` を参照するが、
  `SUBNET_DECAP` 全体のエントリを購読する consumer は `TunnelDecapOrch` のみ。
- `tunnelmgrd` が `SUBNET_DECAP` を参照する記述は位相 6/7/8 分析にあるが、
  実装上は `orchagent` の `TunnelDecapOrch` が唯一の consumer。
  `tunnelmgrd` はトンネル関連のユーザー空間サービスだが、
  `SUBNET_DECAP` の購読は確認されていない（phase678 分析の記述は不正確）。

---

## 要約表

| フィールド | YANG デフォルト | コード由来デフォルト | 乖離・注意点 |
|-----------|--------------|------------------|------------|
| `status` | `disable` | `false` (C++ bool) | YANG/実装一致 |
| `src_ip` | なし (mandatory) | `""` (空文字列) | 片方未設定は silent 受理（YANG mandatory 違反を実装が無視） |
| `src_ip_v6` | なし (mandatory) | `""` (空文字列) | 同上 |
| `tunnel` | (YANG に存在しない) | `"IPINIP_SUBNET"` ハードコード | CONFIG_DB から設定不可の隠し値 |
| `tunnel_v6` | (YANG に存在しない) | `"IPINIP_SUBNET_V6"` ハードコード | CONFIG_DB から設定不可の隠し値 |
| `dscp_mode` (APP_DB) | (YANG に存在しない) | Broadcom T1: `"pipe"`, Broadcom 非T1: `"uniform"`, 他: `"pipe"` | プラットフォーム依存 |
| `ecn_mode` (APP_DB) | (YANG に存在しない) | `"copy_from_outer"` | ハードコード |
| `ttl_mode` (APP_DB) | (YANG に存在しない) | `"pipe"` | ハードコード |

---

## 証拠リンク

- `tunneldecaporch.h:48-55` — `SubnetDecapConfig` 構造体定義
- `tunneldecaporch.h:97-103` — `subnetDecapConfig` メンバ初期化値
- `tunneldecaporch.cpp:566-699` — `doSubnetDecapTask()` 全実装
- `tunneldecaporch.cpp:624-626` — `status` フィールド解析
- `tunneldecaporch.cpp:636-640` — 両 src_ip 未設定時エラー
- `tunneldecaporch.cpp:651-665` — `src_ip` 初回/更新分岐・enable 依存更新
- `tunneldecaporch.cpp:667-685` — `src_ip_v6` 同パターン
- `tunneldecaporch.cpp:693` — DEL_COMMAND での enable リセット
- `ipinip.json.j2:37-42` — `subnet_decap.enable` 集計ロジック
- `ipinip.json.j2:93-123` — `IPINIP_SUBNET` トンネルのビルド時生成
- `sonic-subnet-decap.yang:37-53` — `status` の YANG default + mandatory 制約
