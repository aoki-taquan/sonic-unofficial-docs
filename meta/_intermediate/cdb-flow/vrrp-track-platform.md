# VRRP_TRACK — Phase H プラットフォーム差 スキャンノート

## 調査対象

- `sonic-utilities/config/main.py` (add_track_interface / remove_track_interface)
- `SONiC/doc/vrrp/VRRP_Adaptation_HLD.md`
- `SONiC/doc/vrrp/sonic-vrrp.yang`

## 結論

`VRRP_TRACK` テーブル自体のエントリ書き込み・読み込みに ASIC 種別・multi-asic 構成・VOQ chassis 依存はない。

## 根拠

### CLI 経路

`config/main.py` の `add_track_interface()` / `remove_track_interface()` は以下を参照しない:
- `is_multi_npu()` / `is_multi_asic()`
- `platform` / `asic_type` 環境変数
- namespace iteration

VRRP は host-side FRR 機能であり、SAI を経由しない。`VRRP_TRACK` の内容は macvlanmgrd → FRR vrrpd に直接渡されるため、ASIC 種別の影響を受けない。

### YANG 経路

`sonic-vrrp.yang` は platform 分岐を持たない。leafref バリデーションは ASIC 非依存のテーブル存在チェックのみ。

### SAI 関連（間接）

HLD L519-520: `SAI_ROUTER_INTERFACE_ATTR_IS_VIRTUAL` は一部ベンダー SAI が未サポートの場合に `sai_query_attribute_capability` でフォールバックする。ただしこれは `vrrporch` / ASIC_DB 側の話であり、`VRRP_TRACK` → FRR vrrpd の経路には影響しない。

### multi-asic

VRRP は `sonic-net/sonic-utilities/config/main.py` において namespace オプションを持たない。FRR は各 host namespace で独立動作し、`VRRP_TRACK` は host-scope CONFIG_DB のみを参照する。

## スキャン日

2026-05-19
