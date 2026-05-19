# vlan-state platform 調査ノート

## 調査対象
- `sonic-swss/cfgmgr/vlanmgr.cpp` (HEAD)
- `sonic-swss/cfgmgr/vlanmgrd.cpp` (HEAD)
- `sonic-buildimage/dockers/docker-orchagent/supervisord.conf.j2`
- `sonic-buildimage/device/pensando/arm64-elba-asic-flash128-r0/system_health_monitoring_config.json`

## 結論サマリ

`STATE_DB VLAN_TABLE` の書込スキーマ・格納先・通信方式はプラットフォーム共通。ただし vlanmgrd プロセスの**起動有無**がプラットフォームによって異なる。

## 1. fabric ASIC では vlanmgrd 不起動

`supervisord.conf.j2` の以下テンプレートで制御される:

```jinja
{% set is_fabric_asic = 0 %}
{% if DEVICE_METADATA.localhost.switch_type == "fabric" %}
{% set is_fabric_asic = 1 %}
{% endif %}
...
{% if is_fabric_asic == 0 %}
[program:vlanmgrd]
command=/usr/bin/vlanmgrd
```

`switch_type = "fabric"` の場合（VOQ chassis のファブリック ASIC カード等）、vlanmgrd は起動せず、`STATE_DB VLAN_TABLE` へのエントリは一切書き込まれない。

`switch_type = "voq"` (line card) や `switch_type = "switch"` (T0/T1 fixed) では is_fabric_asic=0 となり vlanmgrd は通常起動する。

ソース: `supervisord.conf.j2:33-38,164-177`

## 2. vlanmgr.cpp にプラットフォーム分岐なし

`vlanmgr.cpp` 全 1008 行を grep:
- `platform`, `mellanox`, `broadcom`, `mlnx`, `brcm`, `voq`, `chassis`, `switch_type`, `is_multi_npu`, `getenv` のいずれもヒット 0
- SAI API は一切呼ばない（Linux kernel bridge 操作のみ）

STATE_DB への書込みは vlanmgr.cpp:443 の固定 `m_stateVlanTable.set(key, [("state","ok")])` のみ。

## 3. Pensando (arm64-elba) では vlanmgrd をヘルスチェック対象外

```json
// device/pensando/arm64-elba-asic-flash128-r0/system_health_monitoring_config.json
"services_to_ignore": ["vlanmgrd", "vxlanmgrd"]
```

vlanmgrd 自体は起動するが、system_health_monitor がプロセス死活監視の対象から除外している。DPU アーキテクチャ固有の理由（Elba ASIC では VLAN 管理が異なる可能性）があると推測されるが、コードに明示なし。

## 4. DEFAULT_MTU_STR は全プラットフォーム共通

```c
// vlanmgrd.cpp:18
#define DEFAULT_MTU_STR "9100"
```

platform env や hwsku に依存せず 9100 バイト固定。

## 5. multi-asic (NPU 複数) での挙動

`vlanmgrd.cpp` は namespace を一切参照しない（DBConnector("CONFIG_DB", 0) 固定）。multi-asic 環境では各 ASIC namespace ごとに swss コンテナが独立して起動し、その中の vlanmgrd が各 namespace の STATE_DB (Redis index STATE_DB_INDEX) に書き込む。アーキテクチャ上、VLAN_TABLE は asic0/asic1 ごとに独立して存在する。

## Evidence
- `supervisord.conf.j2:33-38` (is_fabric_asic 定義)
- `supervisord.conf.j2:164-177` (vlanmgrd program block with is_fabric_asic guard)
- `vlanmgr.cpp` 全行 grep で platform/SAI 分岐なし確認
- `device/pensando/arm64-elba-asic-flash128-r0/system_health_monitoring_config.json` (services_to_ignore)
