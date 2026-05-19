# PREFIX_SET — プラットフォーム差異調査 (Phase H)

調査日: 2026-05-19
調査対象: sonic-buildimage, sonic-frr-mgmt-framework

## 調査方針

PREFIX_SET / PREFIX テーブルは frrcfgd 経由で FRR に反映される純ソフトウェアルーティングポリシー機能であり、SAI/ASIC には一切関与しない。プラットフォーム差異は「frrcfgd が動くか否か」と「frrcfgd の動作環境」の 2 点に集約される。

## 調査結果

### A. frr_mgmt_framework_config フラグ (最重要)

`docker-fpm-frr/frr/supervisord/supervisord.conf.j2:163-168` の確認:

```jinja2
{% if DEVICE_METADATA.localhost.frr_mgmt_framework_config is defined
      and DEVICE_METADATA.localhost.frr_mgmt_framework_config == "true" %}
[program:frrcfgd]
command=/usr/local/bin/frrcfgd
{% else %}
[program:bgpcfgd]
command=/usr/local/bin/bgpcfgd
{% endif %}
```

- `frr_mgmt_framework_config = "true"` のとき: **frrcfgd** が起動し PREFIX_SET/PREFIX を消費する
- それ以外のとき: **bgpcfgd** が起動し PREFIX_SET/PREFIX は消費されない (bgpcfgd にこのテーブルのハンドラなし)

この差異はプラットフォーム種別ではなく、`DEVICE_METADATA.localhost.frr_mgmt_framework_config` フィールドの設定値によって決まる。

### B. ospfd/pimd の有効化

`supervisord.conf.j2:120-148` の確認:

```jinja2
{% if DEVICE_METADATA.localhost.frr_mgmt_framework_config is defined
      and DEVICE_METADATA.localhost.frr_mgmt_framework_config == "true" %}
[program:ospfd]
...
[program:pimd]
...
{% endif %}
```

PREFIX テーブル (TABLE_DAEMON: `['zebra', 'bgpd', 'ospfd', 'pimd']`) の ADD/DEL は ospfd/pimd にも vtysh コマンドを発行するが、これらのデーモンは `frr_mgmt_framework_config = true` 環境でのみ起動する。非 frr-mgmt-framework 環境では ospfd/pimd への vtysh 発行は no-op または接続失敗になる (frrcfgd 自体が起動しないため実害なし)。

### C. gen_frr.conf.j2 / gen_bgpd.conf.j2 条件分岐

`gen_frr.conf.j2:1` / `gen_bgpd.conf.j2:1` も同じ条件で分岐:
- `frr_mgmt_framework_config = true`: bgpd.conf.db.j2 → bgpd.conf.db.pref_list.j2 経由で PREFIX_SET/PREFIX を FRR 設定に展開
- それ以外: bgpd.conf.j2 (旧来の sonic-cfggen テンプレート) を使用、PREFIX_SET は静的展開なし

### D. SmartSwitch / DPU

frrcfgd は `docker-fpm-frr` コンテナ内で動作する。SmartSwitch の DPU 側では BGP/FRR スタックが NPU 上のコンテナに集約される設計のため、DPU には `docker-fpm-frr` がデプロイされず frrcfgd も動作しない。PREFIX_SET は NPU 側のルーティングポリシーとしてのみ機能する。

### E. VS (仮想スイッチ)

VS 環境では vtysh が通常動作するため、frrcfgd の PREFIX_SET 処理に差異はない。FRR は純ソフトウェアのため ASIC 照会なし。`frr_mgmt_framework_config` フラグが設定されていれば物理 ASIC と同一動作する。

### F. ASIC 依存なし

PREFIX_SET / PREFIX の処理は全て FRR 内部の BGP/OSPF/PIM ポリシー処理で完結する。SAI 呼び出しは一切ない。ASIC ベンダー固有の条件分岐はコード中に存在しない。

## 証跡ファイル

- `sonic-buildimage/dockers/docker-fpm-frr/frr/supervisord/supervisord.conf.j2:84,120,163`
- `sonic-buildimage/dockers/docker-fpm-frr/frr/gen_frr.conf.j2:1`
- `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/gen_bgpd.conf.j2:1`
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py:83,87`
