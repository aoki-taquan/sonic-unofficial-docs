# vrf-orch — プラットフォーム差調査 (Phase H)

調査対象: `sonic-swss/orchagent/vrforch.cpp`, `sonic-swss/orchagent/vrforch.h`, `sonic-swss/cfgmgr/vrfmgr.cpp`, `sonic-buildimage/dockers/docker-orchagent/supervisord.conf.j2`, `sonic-swss/orchagent/orchdaemon.cpp`

調査日: 2026-05-19

## 調査サマリ

`VRFOrch::addOperation` / `delOperation` および `vrfmgrd` の実装にはコード上のプラットフォーム固有分岐（`getenv("platform")` 等）は存在しない。SAI 属性は capability query なしに無条件で投入される。ただし以下の 4 系統のプラットフォーム差が実在する。

## 1. fabric ASIC — vrfmgrd 非起動

`supervisord.conf.j2:247-262`:

```jinja
{% if is_fabric_asic == 0 %}
[program:vrfmgrd]
...
{%- endif %}
```

fabric ASIC スロット（chassis linecard のファブリック面プロセス）では `vrfmgrd` が起動しない。

- `APPL_DB VRF_TABLE` は書き込まれない → `VRFOrch::addOperation` がトリガされない
- `STATE_DB VRF_OBJECT_TABLE` も書き込まれない

一方、`VRFOrch` 自体は `orchdaemon.cpp:283` で無条件にインスタンス化される。ただし APPL_DB に VRF_TABLE エントリが届かないため実質 no-op。

## 2. SAI 属性の capability query なし — vendor SAI 依存

`VRFOrch::addOperation()` は以下の SAI 属性を capability query なしで直接 `create_virtual_router()` / `set_virtual_router_attribute()` に渡す:

| SAI 属性 | フィールド | vendor SAI 未サポート時の挙動 |
|---|---|---|
| `SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V4_STATE` | `v4` | `create_virtual_router` / `set_virtual_router_attribute` が `SAI_STATUS_NOT_SUPPORTED` 等を返す → `handleSaiCreateStatus` / `handleSaiSetStatus` がエラー処理 |
| `SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V6_STATE` | `v6` | 同上 |
| `SAI_VIRTUAL_ROUTER_ATTR_SRC_MAC_ADDRESS` | `src_mac` | 同上 |
| `SAI_VIRTUAL_ROUTER_ATTR_VIOLATION_TTL1_PACKET_ACTION` | `ttl_action` | 同上 |
| `SAI_VIRTUAL_ROUTER_ATTR_VIOLATION_IP_OPTIONS_PACKET_ACTION` | `ip_opt_action` | 同上 |
| `SAI_VIRTUAL_ROUTER_ATTR_UNKNOWN_L3_MULTICAST_PACKET_ACTION` | `l3_mc_action` | 同上 |

フィールドが省略された場合は attrs ベクタに追加されないため、SAI デフォルト（実装依存）が適用される。VS（仮想スイッチ）SAI は `create_virtual_router` を正常終了させるが、attribute の実値は無視することが多い。

## 3. mgmt VRF — 構成依存の非対称挙動（platform 非依存）

VRF 名が `"mgmt"` の場合、vrfmgrd は Linux VRF デバイスを作成しない（`setLink()` が固定テーブル ID `6000` を使用するのみ）。ただし APPL_DB への書き込みは通常通り実行される (`vrfmgr.cpp:181-183, 289, 303`)。

VRFOrch 側では `mgmtVrfEnabled` / `in_band_mgmt_enabled` フィールドが `SWSS_LOG_INFO("MGMT VRF field: %s ignored")` でスキップされ、SAI 属性に変換されない (`vrforch.cpp:74-78`)。SAI `create_virtual_router()` 自体は呼ばれるため `VRF_OBJECT_TABLE|mgmt` は書き込まれる。

この非対称性はプラットフォームではなく構成（`MGMT_VRF_CONFIG.mgmtVrfEnabled`）依存。

## 4. カーネル l3mdev モジュール依存

vrfmgrd は Linux カーネルの `l3mdev` サブシステムに依存する。`l3mdev-table` カーネルモジュール対応カーネル（4.15+ 以降が目安）が前提。`TABLE_LOCAL_PREF=1001` で pref 0 の local テーブルルールを置き換えるコンスタラクタ処理 (`vrfmgr.cpp:98-106`) は、`l3mdev-table` の前提に基づく設計。

カーネルが l3mdev 未対応の場合（古い kernel / 一部のコンテナ環境）:
- `ip link add ... type vrf table <id>` が失敗 → `EXEC_WITH_ERROR_THROW` が例外を throw → vrfmgrd クラッシュ
- supervisord により再起動されるが、loop crash が継続する

## 5. warm restart での初期化差異

vrfmgrd のコンストラクタは `WarmStart::isWarmStart()` 分岐を持つ:

- **Cold start**: 既存 Linux VRF デバイス（`mgmt` 以外）を `ip link del` で削除してプール再計算
- **Warm restart**: 既存デバイスのテーブル ID を `m_vrfTableMap` に再登録し `m_freeTables` から除外（削除しない）

この差異はプラットフォームではなく warm restart 設定（`WARM_RESTART_TABLE` / feature flag）依存。

## 証跡

- `sonic-buildimage/dockers/docker-orchagent/supervisord.conf.j2` L247–263（`is_fabric_asic == 0` 条件と vrfmgrd）
- `sonic-swss/orchagent/orchdaemon.cpp` L283（VRFOrch 無条件インスタンス化）
- `sonic-swss/orchagent/vrforch.cpp` L38–84（capability query なしの SAI attr 投入）
- `sonic-swss/orchagent/vrforch.cpp` L74–78（mgmt VRF フィールドスキップ）
- `sonic-swss/cfgmgr/vrfmgr.cpp` L12–16（VRF_TABLE_START / MGMT_VRF_TABLE_ID 定数）
- `sonic-swss/cfgmgr/vrfmgr.cpp` L65–111（WarmStart 分岐と l3mdev 初期化）
- `sonic-swss/cfgmgr/vrfmgr.cpp` L176–183（mgmt VRF setLink 特殊処理）
