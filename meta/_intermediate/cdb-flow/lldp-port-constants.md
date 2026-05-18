# LLDP_PORT — ハードコード定数調査 (Phase E)

調査日: 2026-05-18  
調査対象: `sonic-buildimage/dockers/docker-lldp/lldpmgrd`

## lldpmgrd モジュールレベル定数

`lldpmgrd:33-35` に明示定義:

```python
PORT_INIT_TIMEOUT = 300    # lldpmgrd:33
FAILED_CMD_TIMEOUT = 6     # lldpmgrd:34
RETRY_LIMIT = 5            # lldpmgrd:35
```

- `PORT_INIT_TIMEOUT=300`: PortInitDone/PortConfigDone を最大 300 秒待機。超過すると強制 `lldpcli resume`。
- `FAILED_CMD_TIMEOUT=6`: lldpcli 失敗後の再試行インターバル（秒）。
- `RETRY_LIMIT=5`: ポートごとの lldpcli 最大再試行回数。超過で silent drop。

```python
SELECT_TIMEOUT_MS = 1000 * 10    # lldpmgrd:291
REDIS_TIMEOUT_MS = 0             # lldpmgrd:50 (class attribute)
```

- `SELECT_TIMEOUT_MS=10000`: Redis select のタイムアウト兼 `process_pending_cmds` 実行周期（約 10 秒）。
- `REDIS_TIMEOUT_MS=0`: ブロッキング接続。

## lldpd.conf.j2 の LLDP_PORT 関連ハードコード

起動時に `sonic-cfggen` が展開する `lldpd.conf.j2` のうち、per-port portidsubtype に影響する固定設定:

```jinja2
{# lldpd.conf.j2:30-31 #}
configure lldp portidsubtype ifname
{# lldpd.conf.j2:33 #}
pause
```

- `portidsubtype ifname`: 全ポートへのグローバル初期値。lldpmgrd が起動後に `local <alias>` で per-port 上書きする二段構成。
- `pause`: lldpd 起動直後から LLDP PDU 送出停止。lldpmgrd の `lldpcli resume` 発行まで。

eth0 per-port 設定（`lldpd.conf.j2:17-21`）:

```jinja2
{% if MGMT_PORT and MGMT_PORT[mgmt_if.port_name] and MGMT_PORT[mgmt_if.port_name].alias %}
configure ports eth0 lldp portidsubtype local {{ MGMT_PORT[mgmt_if.port_name].alias }}
{% else %}
configure ports eth0 lldp portidsubtype local {{ mgmt_if.port_name }}
{% endif %}
```

eth0 の portidsubtype は `MGMT_PORT.alias` 有無で切り替わる。これは `lldpd.conf.j2` のハードコードであり CONFIG_DB `LLDP_PORT` を参照しない。

## YANG default 値（LLDP_PORT フィールド）

`sonic-lldp.yang` の `lldp_mode_config` grouping:

| フィールド | YANG default | lldpmgrd 読み取り | 実効 |
|-----------|-------------|-----------------|-----|
| `enabled` | `true` | 読まれない（dead field） | YANG バリデーションのみ |
| `mode` | なし（enum 2 値のみ） | 読まれない（dead field） | lldpd 組み込みデフォルト双方向 |

## 結論

LLDP_PORT 固有のハードコード定数は主に retry/timeout 制御に集中する。lldpmgrd が `LLDP_PORT` テーブルを直接購読しないため、`enabled` / `mode` フィールドの YANG default は CONFIG_DB バリデーション上の意味しか持たない。per-port LLDP 動作は APPL_DB PORT_TABLE の oper_status イベントと CONFIG_DB PORT.alias/description を組み合わせてハードコード定数 (RETRY_LIMIT=5, FAILED_CMD_TIMEOUT=6s) によって制御される。
