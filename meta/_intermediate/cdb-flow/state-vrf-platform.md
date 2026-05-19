# state-vrf — プラットフォーム差調査 (Phase H)

調査対象: `sonic-swss/cfgmgr/vrfmgr.cpp`, `sonic-swss/orchagent/vrforch.cpp`, `sonic-swss/orchagent/vrforch.h`, `sonic-buildimage/dockers/docker-orchagent/supervisord.conf.j2`

## 調査サマリ

`VRF_TABLE` / `VRF_OBJECT_TABLE` の書き込み経路（`vrfmgrd` と `VRFOrch`）にはコード上のプラットフォーム固有分岐（`getenv("platform")` 等）は存在しない。ただし以下のプラットフォーム起因の差異が存在する。

## fabric ASIC での vrfmgrd 非起動

`supervisord.conf.j2:247-262` の条件:

```jinja
{% if is_fabric_asic == 0 %}
[program:vrfmgrd]
...
{%- endif %}
```

fabric ASIC スロット（linecard の ASIC ファブリック側プロセス）では `vrfmgrd` が起動しない。
- `STATE_DB:VRF_TABLE` は書き込まれない
- `APP_DB:APP_VRF_TABLE` も書き込まれない → `VRFOrch` がトリガされない
- `STATE_DB:VRF_OBJECT_TABLE` も書き込まれない

通常の NIC/NPU スロット（`is_fabric_asic == 0`）では両テーブルとも通常通り動作する。

## mgmt VRF の非対称性（プラットフォーム非依存だが構成依存）

VRF 名が `"mgmt"` の場合:
- `vrfmgrd`: `setLink("mgmt")` は Linux VRF デバイスを作成せず、予約テーブル ID `6000` (`MGMT_VRF_TABLE_ID`) をそのまま使用する。その後 `m_stateVrfTable.set()` を呼ぶため `VRF_TABLE|mgmt` は書き込まれる（`vrfmgr.cpp:176-183, 289`）。
- `VRFOrch`: mgmt VRF のフィールド（`mgmtVrfEnabled`, `in_band_mgmt_enabled`）は SAI 属性に変換せず `continue` でスキップ（`vrforch.cpp:74-78`）。SAI `create_virtual_router()` は呼ばれないため `VRF_OBJECT_TABLE|mgmt` は書き込まれない（`vrforch.cpp:74-78`）。

この非対称性はプラットフォームではなく VRF 名（`"mgmt"` か否か）で決まるが、mgmt VRF を持つかどうかは構成（`MGMT_VRF_CONFIG`）依存。

## VRFOrch の SAI 属性サポート — platform 条件なし

`VRFOrch::addOperation()` は `SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V4_STATE`, `SAI_VIRTUAL_ROUTER_ATTR_SRC_MAC_ADDRESS`, `SAI_VIRTUAL_ROUTER_ATTR_VIOLATION_TTL1_PACKET_ACTION`, `SAI_VIRTUAL_ROUTER_ATTR_VIOLATION_IP_OPTIONS_PACKET_ACTION`, `SAI_VIRTUAL_ROUTER_ATTR_UNKNOWN_L3_MULTICAST_PACKET_ACTION` を直接 `create_virtual_router()` / `set_virtual_router_attribute()` に渡す。`getenv("platform")` による分岐は存在しない。SAI 実装がこれらの属性をサポートしない場合は SAI エラーが返り、`handleSaiCreateStatus()` / `handleSaiSetStatus()` がエラー処理する（`VRF_OBJECT_TABLE` は書き込まれない）。

## 証跡

- `sonic-buildimage/dockers/docker-orchagent/supervisord.conf.j2` L247–262（`is_fabric_asic == 0` 条件）
- `sonic-swss/cfgmgr/vrfmgr.cpp` L148, 176–183, 289（mgmt VRF 特殊処理と `m_stateVrfTable.set()`）
- `sonic-swss/orchagent/vrforch.cpp` L74–78（mgmt VRF フィールドスキップ）, L93–120（SAI `create_virtual_router` と `m_stateVrfObjectTable.hset()`）
- `sonic-swss/orchagent/orchdaemon.cpp` L283（`VRFOrch` 無条件インスタンス化）
