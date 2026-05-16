# BGP_DEVICE_GLOBAL — プラットフォーム差調査 (Task F Phase H)

**対象**: `docs/reference/config-db/bgp-device-global.md`
**スコープ**: ASIC 種別 / HwSku / chassis / multi-asic / switch_role / SAI capability などに依る分岐検出
**ソース ref**: `sonic-buildimage` master 9ea932ec2, `sonic-swss` master HEAD

---

## 結論

BGP_DEVICE_GLOBAL は SAI に直接マップされない上位「動作スイッチ」テーブルだが、以下 4 系統のプラットフォーム / ロール依存分岐が実装で確認された。

1. **`is_chassis()` + chassis_tsa** — `device_info.is_chassis()` が真の VOQ / packet-based chassis のみ CHASSIS_APP_DB を読みに行き、上位シャーシ TSA が個別 LC の TSA 操作を抑止する。
2. **`switch_role` (`DEVICE_METADATA.localhost.type`)** — `idf_isolation_state` の FRR push は `SpineRouter` / `LowerSpineRouter` / `UpperSpineRouter` のみで実施。ToR / LeafRouter 等では handler が早期 return しテンプレートを送出しない。
3. **`switch_type == 'chassis-packet'` (VOQ ルートマップ整形)** — TSA route-map 整形で `_INTERNAL_` / `VOQ_` を含む route-map をシャーシ内 LC 間セッション扱いし `internal_route_map=1` を渡してテンプレート分岐させる。
4. **SAI BFD offload capability (`use_software_bfd`)** — BGP_DEVICE_GLOBAL 直下のフィールドではないが、`BgpGlobalStateOrch::getSoftwareBfd()` が SAI capability query (`SAI_SWITCH_ATTR_SUPPORTED_IPV4/IPV6_BFD_SESSION_OFFLOAD_TYPE`) で hw BFD offload 不可なら `use_software_bfd=true` を返し、BFD orch を software-BFD 経路 (STATE_DB.SOFTWARE_BFD_SESSION_TABLE) に切替える。**ASIC / プラットフォーム差**として BGP_DEVICE_GLOBAL を読む唯一の SAI 経路。

ASIC ベンダー (Broadcom / Mellanox / Marvell / Innovium / Cisco) 単位の **直接的な** 分岐は無い (`grep -in 'broadcom\|mellanox\|marvell\|innovium\|cisco' managers_device_global.py` で 0 ヒット)。すべて switch_type / switch_role / SAI capability 経由の間接分岐。

---

## 根拠

### 1. `device_info.is_chassis()` ガード

```python
# sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_device_global.py:238-251
def get_chassis_tsa_status(self):
    chassis_tsa_status = "false"
    if not device_info.is_chassis():
        return chassis_tsa_status
    try:
        ch = swsscommon.SonicV2Connector(use_unix_socket_path=False)
        ch.connect(ch.CHASSIS_APP_DB, False)
        chassis_tsa_status = ch.get(ch.CHASSIS_APP_DB, "BGP_DEVICE_GLOBAL|STATE", 'tsa_enabled')
    except Exception as e:
        log_err(...)
    return chassis_tsa_status
```

- 非シャーシ装置: 常に `"false"` を返し、CHASSIS_APP_DB アクセスはスキップ。
- シャーシ (`is_chassis()` 判定): pmon の `chassisd` が CHASSIS_APP_DB へ書き込む `BGP_DEVICE_GLOBAL|STATE.tsa_enabled` を Supervisor LC から各 LC が参照する。

呼出元:
- `configure_tsa()` (`managers_device_global.py:100,106`): `chassis_tsa == "false"` のときのみ個別 LC TSA を FRR に push。シャーシ全体 TSA が有効ならスキップ。
- `check_state_and_get_tsa_routemaps()` (`managers_device_global.py:175,177`): TSA route-map 生成判定で `tsa_status=="true"` か `chassis_tsa=="true"` のどちらでも isolate テンプレートを発火させる。

### 2. `switch_role` による IDF handler 早期 return

```python
# managers_device_global.py:253-262
def downstream_isolate_unisolate(self, idf_isolation_state):
    if idf_isolation_state not in ["unisolated", "isolated_withdraw_all", "isolated_no_export"]:
        log_err(...); return False
    if self.switch_role and self.switch_role not in ["SpineRouter", "LowerSpineRouter", "UpperSpineRouter"]:
        log_debug("DeviceGlobalCfgMgr:: Skipping IDF isolation configuration on %s" % self.switch_role)
        return True   # ← FRR push せず成功扱い
    ...
```

`switch_role` の取得元は `DEVICE_METADATA|localhost.type` (`managers_device_global.py:53-54`)。

| `switch_role` 値 | IDF push 挙動 |
|----|----|
| `SpineRouter` / `LowerSpineRouter` / `UpperSpineRouter` | `idf_isolate.conf.j2` / `idf_unisolate.conf.j2` を FRR に push |
| `ToRRouter` / `LeafRouter` / `BackEndToRRouter` / 空文字列 | early return。テンプレート未適用 (CONFIG_DB 値は変わるが FRR 動作は無変化) |

### 3. `switch_type == 'chassis-packet'` の VOQ ルートマップ整形

```python
# managers_device_global.py:210-227 (__generate_routemaps_from_template)
for rm in sorted(route_map_names):
    # For packet-based chassis, the bgp session between the linecards are also considered internal sessions
    if "_INTERNAL_" in rm or "VOQ_" in rm:
        is_internal="1"
    else:
        is_internal="0"
    ...
    cmd += template.render(route_map_name=rm, ip_version=ipv, ip_protocol=ipp, internal_route_map=is_internal, ...)
```

`VOQ_` プレフィクス route-map は VOQ system (`switch_type=voq`) で minigraph により生成される。chassis-packet では `_INTERNAL_` が LC 間 iBGP セッション名に付与され、TSA 適用時にスキップされず TSA route-map に取り込まれる (テンプレート側 `internal_route_map==1` で deny 40 を挿入しない or 取り扱い差別化)。

### 4. SAI BFD offload capability — `use_software_bfd`

```cpp
// sonic-swss/orchagent/bfdorch.cpp:729-791
BgpGlobalStateOrch::BgpGlobalStateOrch(DBConnector *db, string tableName):
    Orch(db, tableName)
{
    tsa_enabled = false;
    bool ipv6 = true;
    bfd_offload = (offload_supported(!ipv6) && offload_supported(ipv6));
}

bool BgpGlobalStateOrch::getSoftwareBfd() { return !bfd_offload; }

bool BgpGlobalStateOrch::offload_supported(bool get_ipv6) {
    sai_attribute_t attr;
    attr.id = get_ipv6 ? SAI_SWITCH_ATTR_SUPPORTED_IPV6_BFD_SESSION_OFFLOAD_TYPE
                       : SAI_SWITCH_ATTR_SUPPORTED_IPV4_BFD_SESSION_OFFLOAD_TYPE;
    sai_query_attribute_capability(gSwitchId, SAI_OBJECT_TYPE_SWITCH, attr.id, &capability);
    ...
    return (attr.value.u32list.list[0] != SAI_BFD_SESSION_OFFLOAD_TYPE_NONE);
}
```

BgpGlobalStateOrch は CONFIG_DB.BGP_DEVICE_GLOBAL を購読する Orch だが、コンストラクタ時点で SAI に v4/v6 BFD offload capability を問い合わせ、両方サポートされていれば `bfd_offload=true` → `getSoftwareBfd()=false`。一方を欠くと `getSoftwareBfd()=true` で BfdOrch (`bfdorch.cpp:111-218`) が hw BFD パスをスキップし STATE_DB.SOFTWARE_BFD_SESSION_TABLE へ書き込む software 経路に切替える。

つまり **BGP_DEVICE_GLOBAL.tsa_enabled** を read する Orch のクラス内部状態として、SAI capability に依存する ASIC 差が定着している (BGP_DEVICE_GLOBAL のフィールド経由ではないが、CONFIG_DB.BGP_DEVICE_GLOBAL テーブル → Orch → BFD パス分岐の系として接続)。

### `software_bfd` feature gate (bgpcfgd 側)

```python
# sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py:118-119
if 'software_bfd' in sys_defaults and 'status' in sys_defaults['software_bfd'] and sys_defaults['software_bfd']['status'] == 'enabled':
    log_notice("software_bfd feature is enabled, starting bfd manager")
```

これは `constants.yml` の `software_bfd.status` を参照する。プラットフォーム別 `constants.yml` 上書きは標準 image では未提供 (`files/image_config/constants/constants.yml` 1 ファイル共通) のため、image build 時に固定化される。runtime の SAI capability 分岐 (上記 4.) とは独立の build-time gate。

---

## 検出されなかった分岐

- **HwSku / `device/<platform>/` 別ディレクトリ**: `managers_device_global.py` に platform 名・HwSku 参照は 0 ヒット。
- **multi-asic / asic-namespace**: bgpcfgd は per-namespace に起動するが、各インスタンスは BGP_DEVICE_GLOBAL を独立に処理する。namespace 別フィールドや handler 分岐は無し。
- **vendor ASIC 名 (Broadcom / Mellanox / Marvell / Innovium / Cisco / Nephos / Centec)**: 直接の if/elif 分岐は無し。すべて SAI capability / `is_chassis()` / `switch_type` 経由の間接分岐。
- **`use_software_bfd` という名前の CONFIG_DB フィールド**: BGP_DEVICE_GLOBAL には**存在しない**。Orch の内部 state (`bfd_offload`) として SAI capability に依存して runtime 決定される。タスク指示文で「use_software_bfd」が BGP_DEVICE_GLOBAL のフィールドであるかのように示唆されているが、コード上はそうではない (`bfdorch.cpp` の local variable 名)。

---

## evidence 一覧 (file:line)

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_device_global.py:53-54` (switch_role 取得)
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_device_global.py:100,106` (chassis_tsa ガード)
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_device_global.py:213-225` (VOQ_/INTERNAL ルートマップ分岐)
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_device_global.py:238-251` (is_chassis ガード)
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_device_global.py:253-262` (switch_role による IDF 早期 return)
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py:118-119` (software_bfd feature gate)
- `sonic-swss/orchagent/bfdorch.cpp:114-120` (use_software_bfd local var)
- `sonic-swss/orchagent/bfdorch.cpp:729-791` (BgpGlobalStateOrch + SAI capability query)
- `sonic-swss/orchagent/orchdaemon.cpp:239-240` (BgpGlobalStateOrch インスタンス化)
