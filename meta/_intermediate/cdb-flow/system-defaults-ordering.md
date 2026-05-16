# SYSTEM_DEFAULTS — Phase B (ordering) 調査証跡

## 調査対象

- `sonic-buildimage/files/build_templates/init_cfg.json.j2` (SHA 9ea932ec)
- `sonic-buildimage/files/build_templates/swss_vars.j2` (SHA 9ea932ec)
- `sonic-buildimage/dockers/docker-orchagent/supervisord.conf.j2` (SHA 9ea932ec)
- `sonic-buildimage/dockers/docker-orchagent/orchagent.sh` (SHA 9ea932ec)
- `sonic-buildimage/dockers/docker-fpm-frr/frr/supervisord/supervisord.conf.j2` (SHA 9ea932ec)
- `sonic-swss/orchagent/muxorch.cpp` (SHA 4305596)

## 処理順・起動順の詳細

### ステージ 0: ビルド時テンプレート展開

`init_cfg.json.j2` が `sonic-cfggen` によりテンプレート展開され、`SYSTEM_DEFAULTS` エントリ
（`mux_tunnel_egress_acl`、`software_bfd`、`polaris` 等）がビルド成果物の `init_cfg.json` に焼き込まれる。
`swss_vars.j2` も同様に展開され `dscp_remapping`（= `tunnel_qos_remap` 値）が確定する。
`docker-fpm-frr/supervisord.conf.j2` では `SYSTEM_DEFAULTS.software_bfd.status == "enabled"` のとき
`bfdmon` プログラムが supervisord 設定に含まれる（含まれない場合はエントリ自体が生成されない）。

### ステージ 1: swss コンテナ起動シーケンス (docker-orchagent)

supervisord が `dependent_startup` プラグインで以下の順に各プロセスを起動する:

| priority | プロセス | 起動待機条件 | SYSTEM_DEFAULTS との関係 |
|---------|---------|-------------|--------------------------|
| 1 | `rsyslogd` | — (autostart は dependent_startup 管理) | なし |
| 3 | `portsyncd` | `rsyslogd:running` | なし（起動後にCFG_DBを購読するが SYSTEM_DEFAULTS 直接参照なし） |
| 3 | `gearsyncd` | `rsyslogd:running` | なし |
| 4 | `orchagent` | `portsyncd:running`（fabric の場合は `rsyslogd:running`） | **`orchagent.sh` が `sonic-cfggen -d -t swss_vars.j2` を実行し `synchronous_mode`/`dscp_remapping` を読み取る。`-s` フラグ（同期モード）の付与有無を決定** |
| 5 | `swssconfig` | `orchagent:running` | なし（FDB/ARP/ports/vxlan/switch.json 適用） |
| 6 | `coppmgrd` | `orchagent:running` | なし |
| 6 | `restore_neighbors` | `swssconfig:exited` | なし |
| 7 | `neighsyncd` | `swssconfig:exited` | なし |
| 8 | `vlanmgrd` | `swssconfig:exited` | なし |
| 9 | `intfmgrd` | `swssconfig:exited` | なし（DEVICE_METADATA 経由で interface_naming_mode を読む） |
| 10 | `portmgrd` / `fabricmgrd` | `swssconfig:exited` | なし |
| 11 | `buffermgrd` | `swssconfig:exited` | なし |
| 12 | `enable_counters` | `swssconfig:exited` | なし |
| 13 | `vrfmgrd` | `swssconfig:exited` | なし |
| 15 | `nbrmgrd` | `swssconfig:exited` | なし |
| 16 | `vxlanmgrd` | `swssconfig:exited` | なし |
| 17 | `tunnelmgrd` / `fdbsyncd` | `swssconfig:exited` | なし |
| 18 | `countersyncd` | `swssconfig:exited` | なし |

> **重要**: SYSTEM_DEFAULTS はスタートアップの priority=4（orchagent 起動前）に `sonic-cfggen` 経由で
> `swss_vars.json` へ変換済みの値として読まれる。orchagent 自身は CONFIG_DB を直接購読せず、
> 起動シェルスクリプト (`orchagent.sh`) がその値を引数として orchagent バイナリに渡す。

### ステージ 2: ランタイム参照（orchagent 内）

`MuxAclHandler::MuxAclHandler()` のコンストラクタ（`muxorch.cpp:1388`）が MuxPort を初期化するたびに
`CONFIG_DB` の `SYSTEM_DEFAULTS|mux_tunnel_egress_acl` を `hget` で読む。
これは orchagent がすでに起動済みの状態（ランタイム）で、ポート追加イベント処理時に逐次発生する。

### ステージ 3: docker-fpm-frr コンテナ

`supervisord.conf.j2` の Jinja2 展開時（コンテナ起動前のテンプレート生成時）に
`SYSTEM_DEFAULTS.software_bfd.status == "enabled"` を評価し、`bfdmon` を supervisord に登録するかを決定する。
`bgpd` (priority 相当) が running になった後に `bfdmon` が起動するよう `dependent_startup_wait_for=bgpd:running` が設定される。

## 結論

SYSTEM_DEFAULTS の処理順は以下の 3 段階に整理できる:

1. **ビルド時** — `sonic-cfggen` テンプレート展開で `init_cfg.json`・`swss_vars.j2`・`supervisord.conf.j2` へ値が焼き込まれる
2. **起動時（priority=4、orchagent 直前）** — `orchagent.sh` が `sonic-cfggen -d -t swss_vars.j2` で `SYSTEM_DEFAULTS` を読み取り、`synchronous_mode` 等の引数を決定する
3. **ランタイム** — `MuxAclHandler` が MuxPort 初期化ごとに `mux_tunnel_egress_acl` を CONFIG_DB から逐次読む
