# PIM_GLOBALS / PIM_INTERFACE — Phase H プラットフォーム差スキャンノート

対象テーブル: `PIM_GLOBALS`, `PIM_INTERFACE`
Consumer: `frrcfgd` / FRR `pimd`
スキャン範囲:
- `sonic-buildimage/dockers/docker-fpm-frr/frr/supervisord/supervisord.conf.j2`
- `sonic-buildimage/dockers/docker-fpm-frr/frr/supervisord/critical_processes.j2`
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` 全行
- `sonic-frr/pimd/pim_mroute.h`, `pim_instance.h`, `pim_oil.h`
調査日: 2026-05-18

---

## 1. frr_mgmt_framework_config フラグによる pimd / frrcfgd 起動制御

`supervisord.conf.j2` (L120-148) において、`ospfd` / `pimd` / `frrcfgd` の各 supervisord セクションは
`DEVICE_METADATA.localhost.frr_mgmt_framework_config == "true"` の条件ブロック内に配置されている。

```jinja2
{% if DEVICE_METADATA.localhost.frr_mgmt_framework_config is defined and
      DEVICE_METADATA.localhost.frr_mgmt_framework_config == "true" %}
[program:pimd]
command=/usr/lib/frr/pimd -A 127.0.0.1 -P 0
...
[program:frrcfgd]
command=/usr/local/bin/frrcfgd
{% else %}
[program:bgpcfgd]
...
{% endif %}
```

同様に `critical_processes.j2` でも `frr_mgmt_framework_config == "true"` の場合のみ `program:pimd` が
critical process リストに含まれる。

**影響**: `frr_mgmt_framework_config` が未設定または `"true"` 以外の場合、pimd と frrcfgd は起動せず、
`PIM_GLOBALS` / `PIM_INTERFACE` の CONFIG_DB エントリは処理されない（silent ignore）。
この設定フラグは DEVICE_METADATA|localhost に手動で設定する必要がある。

---

## 2. frrcfgd 内のプラットフォーム分岐

`frrcfgd.py` 全行 (`PIM_GLOBALS` ハンドラ L3805-3822, `PIM_INTERFACE` ハンドラ L3772-3803) を
`platform`, `asic`, `sub_platform`, `switch_type`, `chassis`, `namespace`, `vendor`,
`multi_asic`, `is_multi_npu` で grep したところ、**0 ヒット**。

frrcfgd は ASIC 種別・プラットフォーム文字列・multi-asic 判定を参照せずに動作する。
PIM テーブルのハンドラパスは `bgp_table_handler_common` → `__update_bgp()` → 固定パス。

---

## 3. multi-asic / VOQ chassis 構成での制約

frrcfgd は `multi_asic` / `namespace` を import しない (grep 0 ヒット)。
したがって multi-asic 環境では、各 asic namespace で独立した docker-fpm-frr コンテナ
(= frrcfgd + pimd) が起動する設計となる。

ただし PIM の実装上、単一の pimd プロセスがカーネルの mroute socket (`MRT_INIT`) を 1 VRF につき
1 回だけ開く。multi-asic 構成で複数の pimd が同一 VRF の mroute socket を競合して開こうとした場合の
動作は保証されていない（コミュニティ master の PIM HLD に multi-asic サポートの記載なし）。

実用上は、PIM は単一 ASIC / 単一 FRR コンテナ構成でのみ利用される。

---

## 4. MAXVIFS 上限

`pimd` は FRR の `pim_mroute.h` / `pim_instance.h` で `MAXVIFS = 256` を定義している。
カーネルの IP マルチキャスト転送テーブル (VIF index) は 0-255 の 256 エントリが上限。
`PIM_MAX_USABLE_VIFS = MAXVIFS - 1 = 255` が実際に PIM インタフェースとして使える最大数。

この制約はカーネル API (`setsockopt MRT_ADD_VIF`) 由来であり、ASIC 種別に依らずすべての
プラットフォームで共通。

---

## 5. 結論サマリ

| 観点 | 結果 | 根拠 |
|------|------|------|
| ASIC 種別 (Broadcom / Mellanox / Marvell / Cisco / vs 等) | **影響なし** | PIM は SAI 非経由。pimd がカーネル mroute API を直接使用。frrcfgd に platform 分岐コードなし |
| `frr_mgmt_framework_config` フラグ | **必須前提** | `false`/未設定の場合 pimd + frrcfgd が起動せず PIM_GLOBALS/PIM_INTERFACE は処理されない (`supervisord.conf.j2:120-148`) |
| multi-asic (`asicN` namespace) | **非対応** (実用上単一 ASIC 前提) | frrcfgd に namespace 分岐なし。multi-asic での複数 pimd 競合は非サポート |
| VOQ chassis (supervisor / line cards) | **不明 / 非推奨** | コミュニティ PIM HLD に chassis サポートの記載なし |
| MAXVIFS インタフェース上限 | **255** (プラットフォーム共通) | カーネル `MRT_ADD_VIF` API 由来。`pim_mroute.h:47-48` |
| テンプレート内プラットフォーム分岐 | **なし** | `frr.conf.j2` に pim テンプレートブロックなし。`supervisord.conf.j2` の分岐は frr_mgmt_framework_config フラグのみ |
