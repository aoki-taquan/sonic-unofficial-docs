# SYSTEM_DEFAULTS 暗黙参照マップ (Phase C)

## 調査対象
テーブル: `SYSTEM_DEFAULTS`
フェーズ: cross-refs (Phase C)

## 調査ソース

- `sonic-buildimage/files/build_templates/init_cfg.json.j2`
- `sonic-buildimage/files/build_templates/swss_vars.j2`
- `sonic-buildimage/files/build_templates/buffers_config.j2`
- `sonic-buildimage/files/build_templates/qos_config.j2`
- `sonic-buildimage/dockers/docker-fpm-frr/frr/supervisord/supervisord.conf.j2`
- `sonic-buildimage/src/sonic-config-engine/minigraph.py`
- `sonic-buildimage/src/sonic-config-engine/config_samples.py`
- `sonic-swss/orchagent/muxorch.cpp`

## 発見した暗黙参照

### SYSTEM_DEFAULTS.tunnel_qos_remap → TUNNEL / buffers / QoS

`swss_vars.j2:14` が `SYSTEM_DEFAULTS.tunnel_qos_remap.status == "enabled"` を評価して
`dscp_remapping = "enable"` フラグを orchagent.sh に渡す。
`buffers_config.j2:208` と `qos_config.j2:143` も同じ条件でバッファ・QoS テンプレートを分岐させる。
`minigraph.py:2212` は tunnel_qos_remap が有効な場合に `TUNNEL` テーブルへのエントリを生成する。

### SYSTEM_DEFAULTS.mux_tunnel_egress_acl → (DEVICE_METADATA / MuxPort)

`muxorch.cpp:1388` で `MuxAclHandler` がコンストラクタ内に `SYSTEM_DEFAULTS` テーブルを開き、
`mux_tunnel_egress_acl` を hget して Dual-ToR ACL の適用有無を決定する。
Mellanox プラットフォームでは `init_cfg.json.j2:188-197` で `enabled` として注入される。

### SYSTEM_DEFAULTS.software_bfd → docker-fpm-frr supervisord

`docker-fpm-frr/frr/supervisord/supervisord.conf.j2:213` が `software_bfd.status == "enabled"` を
評価して `bfdmon` プロセスの supervisord への登録を決定する。
`config_samples.py:186-188` が SmartSwitch DPU プロファイル時に強制 `enabled` を注入する。

### SYSTEM_DEFAULTS.polaris → config_samples (Pensando)

`config_samples.py:179-184` で `'pensando' in hwsku.lower()` のとき `polaris.status = "enabled"`
を設定する。他のキーとは異なり、どの daemon も購読していないが将来の拡張ポイントとして存在する。

### 参照方向まとめ

| 参照方向 | SYSTEM_DEFAULTS キー | 参照先 / 効果 | 条件 |
|---------|---------------------|--------------|------|
| → SYSTEM_DEFAULTS | `tunnel_qos_remap` | `swss_vars.j2` で `dscp_remapping` フラグを決定 | orchagent 起動時 |
| → SYSTEM_DEFAULTS | `tunnel_qos_remap` | `buffers_config.j2` / `qos_config.j2` でバッファ・QoS パラメータを分岐 | ビルド時テンプレート展開 |
| → SYSTEM_DEFAULTS | `tunnel_qos_remap` | `minigraph.py` が `TUNNEL` テーブルエントリを生成 | minigraph 変換時 |
| → SYSTEM_DEFAULTS | `mux_tunnel_egress_acl` | `muxorch` が Dual-ToR ACL 適用を決定 | MuxPort 初期化時（ランタイム） |
| → SYSTEM_DEFAULTS | `software_bfd` | `docker-fpm-frr supervisord.conf.j2` が `bfdmon` プロセス登録を決定 | コンテナ起動テンプレート展開時 |
| SYSTEM_DEFAULTS → | `synchronous_mode` (概念上) | 実体は `DEVICE_METADATA|localhost.synchronous_mode` — SYSTEM_DEFAULTS には格納されない | — |
| SYSTEM_DEFAULTS → | `dhcp_server` (概念上) | 実体は `FEATURE|dhcp_server.state` — SYSTEM_DEFAULTS には格納されない | — |

## Evidence

- `sonic-buildimage/files/build_templates/swss_vars.j2:14`
- `sonic-buildimage/files/build_templates/buffers_config.j2:208`
- `sonic-buildimage/files/build_templates/qos_config.j2:143`
- `sonic-buildimage/src/sonic-config-engine/minigraph.py:2212-2215`
- `sonic-buildimage/src/sonic-config-engine/config_samples.py:179-188`
- `sonic-buildimage/dockers/docker-fpm-frr/frr/supervisord/supervisord.conf.j2:213`
- `sonic-swss/orchagent/muxorch.cpp:1388-1390`
- `sonic-buildimage/files/build_templates/init_cfg.json.j2:188-197`
