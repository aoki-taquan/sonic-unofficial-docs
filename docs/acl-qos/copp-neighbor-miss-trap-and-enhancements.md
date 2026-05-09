---
title: CoPP Neighbor Miss trap と enum capability query（show copp configuration）
area: acl-qos
verification: hld-only
last_verified: 2026-05-09
sources:
  - repo: sonic-net/SONiC
    path: doc/copp/Copp_Neighbor_Miss_Trap_And_Enhancements.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - COPP_TRAP
    - COPP_GROUP
  cli:
    - show copp configuration
  yang:
    - sonic-copp
---

!!! warning "裏取りステータス: HLD-only"
    本ページは公式 HLD（Rev 0.1, 2025-02）のみを根拠に書かれている。`Copporch` の SAI enum capability query 実装、`STATE_DB.COPP_TRAP_CAPABILITY_TABLE` のスキーマ、`show copp configuration` CLI の sonic-utilities 取り込みは未確認。

# CoPP Neighbor Miss trap と enum capability query（`show copp configuration`）

## 概要

SONiC の CoPP（Control Plane Policing）はトラップ単位でレートを切るが、本 HLD は次の 4 点を一括で改善する[^1]:

1. **Neighbor miss trap** の追加: ARP / ND 解決前の IP パケット（neighbor miss）が CPU に殺到すると IP2ME など他の重要トラフィックを巻き添えにする。これを **`SAI_HOSTIF_TRAP_TYPE_NEIGHBOR_MISS`** で個別 policer に分離する
2. **SAI enum capability query** で trap type サポートを事前確認し、未対応 trap を投げて orchagent が例外を出すバグを根絶
3. **STATE_DB に対応 trap 一覧と各 trap の `hw_status`** を公開し、可視化
4. **`show copp configuration` CLI** を新設して CoPP 設定と HW status をまとめて見られるようにする

## 動作仕様

### 全体構造

```mermaid
flowchart LR
    SAI[SAI 実装] -->|enum capability query| CO[Copporch]
    CO --> SUP[supported_trap_ids リスト]
    SUP --> ST1[(STATE_DB\nCOPP_TRAP_CAPABILITY_TABLE|traps)]
    APPL[(APPL_DB\nCoPP trap 設定)] --> CO
    CO --> CHK{supported?}
    CHK -->|Yes| INS[create_hostif_trap\nhw_status=installed]
    CHK -->|No| ERR[syslog ERR\nhw_status=not-installed]
    INS --> ST2[(STATE_DB\nCOPP_TRAP_TABLE|<trap>)]
    ERR --> ST2
    CLI[show copp configuration] --> CFG[(copp_cfg.json / CONFIG_DB)]
    CLI --> ST2
```

### Init フロー

`Copporch` 初期化時[^1]:

1. `sai_query_attribute_enum_values_capability` で `SAI_HOSTIF_TRAP_ATTR_TRAP_TYPE` の対応値を問い合わせる
2. 結果を `supported_trap_ids` ローカルリストに保持
3. SAI が enum capability query 自体を非対応の場合、後方互換のため **`default_supported_trap_ids`**（既存 Copporch が知っている全 trap）をフォールバックに使う
4. `supported_trap_ids` を `STATE_DB.COPP_TRAP_CAPABILITY_TABLE|traps` に出版する

### Config フロー

APPL_DB 経由で CoPP trap 設定を受けた際[^1]:

1. `supported_trap_ids` に含まれているか確認
2. 含まれていれば SAI に `create_hostif_trap` で投入し `STATE_DB.COPP_TRAP_TABLE|<trap>` に `hw_status=installed`
3. 含まれていなければ syslog `ERR` を出して `hw_status=not-installed`（未試行）

これにより「BGP 機能が無効な T0 で BGP trap だけ未 install」などが CLI から判別可能になる。

### Neighbor miss trap デフォルト設定

`copp_cfg.j2` に以下を追加[^1]:

新規 trap group `queue1_group3`:

```json
"queue1_group3": {
  "trap_action": "trap",
  "trap_priority": "1",
  "queue": "1",
  "meter_type": "packets",
  "mode": "sr_tcm",
  "cir": "200",
  "cbs": "200",
  "red_action": "drop"
}
```

新規 trap `neighbor_miss`:

```json
"neighbor_miss": {
  "trap_ids": "neighbor_miss",
  "trap_group": "queue1_group3",
  "always_enabled": "true"
}
```

`always_enabled=true` なので feature flag に関わらず常に有効。CIR/CBS=200 packets/s で `red_action=drop`。

### STATE_DB スキーマ

```
COPP_TRAP_CAPABILITY_TABLE|traps
    trap_ids : "stp,lacp,eapol,lldp,...,neighbor_miss,...,bgp,bgpv6,bfd,..."

COPP_TRAP_TABLE|<trap_name>
    state     : "ok" | ...
    hw_status : "installed" | "not-installed"
```

例:

```json
"COPP_TRAP_TABLE|neighbor_miss": {
  "state": "ok",
  "hw_status": "installed"
}

"COPP_TRAP_CAPABILITY_TABLE|traps": {
  "trap_ids": "stp,lacp,eapol,lldp,...,neighbor_miss,...,bgp,bgpv6,bfd,..."
}
```

`hw_status` 列が今回の追加。`COPP_TRAP_CAPABILITY_TABLE` はテーブル新設[^1]。

<!-- evidence:
source: sonic-net/SONiC/doc/copp/Copp_Neighbor_Miss_Trap_And_Enhancements.md#L78-L92 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
excerpt: |
  During initialization, Copporch in Orchagent will perform an SAI enum capability query to identify supported trap types and maintain them in a local list called `supported_trap_ids`.
  Additionally, Copporch will maintain a list called `default_supported_trap_ids` ...
  If the SAI does not support the enum capability query API, Copporch will assume that the `default_supported_trap_ids` are supported for backward compatibility.
reasoning: 「enum capability query で対応 trap を絞る」「query 自体が無ければ default にフォールバック」という設計の根拠。
-->

### SAI API

新規 SAI API は無し。既存 API のみで実装[^1]:

| API | 属性 | 値 |
|-----|------|---|
| `sai_query_attribute_enum_values_capability` | `SAI_HOSTIF_TRAP_ATTR_TRAP_TYPE` | （列挙値取得） |
| `create_hostif_trap_fn` | `SAI_HOSTIF_TRAP_ATTR_TRAP_TYPE` | `SAI_HOSTIF_TRAP_TYPE_NEIGHBOR_MISS` |
| `remove_hostif_trap_fn` | 同 | 同 |
| `set_hostif_trap_attribute_fn` | 同 | `sai_object_id_t` |

### YANG

`sonic-copp` に変更なし[^1]。

### Warmboot / Fastboot

影響なし[^1]。

## 設定

### CLI

新設: `show copp configuration`

```
show
└── copp
    └── configuration
        └── detailed [--trapid <trapid> | --group <group>]
```

サマリ出力例（HLD 抜粋, 一部省略）[^1]:

```
TrapId           Trap Group     Action  CBS   CIR  Meter Type  Mode    HW Status
---------------  -------------  ------  ----  ---  ----------  ------  -------------
arp_req          queue4_group2  copy    600   600  packets     sr_tcm  installed
bgp              queue4_group1  trap   6000  6000  packets     sr_tcm  not-installed
neighbor_miss    queue1_group3  trap    200   200  packets     sr_tcm  installed
```

詳細表示:

```bash
show copp configuration detailed --trapid neighbor_miss
show copp configuration detailed --group queue1_group3
```

`--trapid` は trap 単位、`--group` は trap_group 単位の詳細を出す[^1]。

### 関連する CONFIG_DB

既存 `COPP_TRAP` / `COPP_GROUP` を使う。スキーマ変更なし（追加 default は `copp_cfg.j2` テンプレ側）。

### 関連する YANG

`sonic-copp` を再利用（変更なし）[^1]。

## 制限事項

- Neighbor miss trap の SAI 対応は **ベンダー依存**。`SAI_HOSTIF_TRAP_TYPE_NEIGHBOR_MISS` を実装していない ASIC では `hw_status=not-installed` となる
- `default_supported_trap_ids` は SAI が enum capability query を持たない古い ASIC 向けフォールバック。新 trap を入れた場合に「この trap が default に含まれていない」と未 install になる可能性
- HLD のデフォルト値（CIR/CBS=200、queue=1）はデバイス・トラフィックパターンに合わせて調整余地あり

## 干渉する機能

- **`Copporch`**: 主要変更箇所。capability query と hw_status の更新が追加
- **既存 trap（arp_req / bgp / lldp 等）**: 全部 `hw_status` を新規に持つようになる
- **`copp_cfg.j2` テンプレート**: 新規 group / trap が追加される。既存設定との merge に注意
- **`show` 系 CLI**: `show copp configuration` 新設。既存スクリプトが従来出力を parse している場合、互換性確認

## トラブルシューティング

- ARP 解決前の IP トラフィックで CPU 高負荷の場合、`show copp configuration` で `neighbor_miss` の `hw_status=installed` を確認
- `not-installed` のまま戻らない trap がある場合、SAI が enum capability query で当該 trap を返していない可能性。`STATE_DB.COPP_TRAP_CAPABILITY_TABLE|traps.trap_ids` で確認
- 設定したのに ASIC に反映されない場合、syslog の `Copporch` ERR を確認

## 引用元

[^1]: `sonic-net/SONiC` `doc/copp/Copp_Neighbor_Miss_Trap_And_Enhancements.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- concerns hint:
- Copporch の SAI enum capability query (sai_query_attribute_enum_values_capability) 実装
- supported_trap_ids / default_supported_trap_ids の管理コード
- STATE_DB COPP_TRAP_CAPABILITY_TABLE と COPP_TRAP_TABLE.hw_status の最終スキーマ
- copp_cfg.j2 への queue1_group3 / neighbor_miss 追加の master 反映
- show copp configuration CLI の sonic-utilities 取り込み
- SAI_HOSTIF_TRAP_TYPE_NEIGHBOR_MISS のベンダー実装状況
-->
