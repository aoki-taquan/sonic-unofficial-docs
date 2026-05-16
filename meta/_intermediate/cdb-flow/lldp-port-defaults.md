# LLDP_PORT フィールド暗黙デフォルト調査メモ

調査日: 2026-05-15
対象テーブル: CONFIG_DB `LLDP_PORT`

## 調査対象ファイル

- `sonic-buildimage/dockers/docker-lldp/lldpd.conf.j2` (lldpd 起動時 Jinja テンプレート)
- `sonic-buildimage/dockers/docker-lldp/lldpmgrd` (CONFIG_DB を購読し lldpcli に翻訳する Python デーモン)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-lldp.yang` (YANG 定義)

注: ユーザー文脈で言及される `interval` / `ttl` (LLDPDU 送出周期と保持時間) は **per-port ではなく** グローバル `LLDP` テーブルの `hello_time` / `multiplier` で表現される (YANG `lldp_mode_config` 配下ではなく `lldp_config` 配下)。本ページの対象は `LLDP_PORT` (per-port) のため、それらは対象外として整理する。

---

## フィールド別 暗黙デフォルト

### `enabled`

**コード由来デフォルト**: `true` (YANG `default` 文)

```yang
// sonic-lldp.yang:24-31
grouping lldp_mode_config {
    leaf enabled {
        type boolean;
        default true;
        description "Enable LLDP on this port";
    }
```

`LLDP_PORT` は `lldp_mode_config` を `uses` (sonic-lldp.yang:115) しているため、`enabled` フィールド省略時は `true` 扱い。`config lldp interface <port> disable` で `false` に切り替わるまでは LLDP TX/RX が有効。

### `mode`

**コード由来デフォルト**: 未設定 (YANG に `default` なし)

```yang
// sonic-lldp.yang:32-40
leaf mode {
    type enumeration {
        enum RECEIVE;
        enum TRANSMIT;
    }
    description "RX/TX mode for LLDP frames";
}
```

YANG enum は `RECEIVE` と `TRANSMIT` のみで `BOTH` は存在しない。**未設定 = lldpd デフォルトの双方向送受信 (rx+tx)** として扱われる。lldpmgrd は `mode` フィールドを `lldpcli configure ports ... lldp status` に翻訳しないため、`mode` を未指定にすれば lldpd 側の組み込みデフォルト (rx+tx) が有効。

### `portidsubtype` (グローバル + per-port の上書き)

**コード由来デフォルト**:

- **グローバル**: `ifname` (lldpd.conf.j2:31 `configure lldp portidsubtype ifname`)
- **per-port**: lldpmgrd が `local <alias>` で上書き (lldpmgrd:156)

```python
# lldpmgrd:156
lldpcli_cmd = ["lldpcli", "configure", "ports", port_name, "lldp",
               "portidsubtype", "local", port_alias]
```

`PORT.alias` を Port ID subtype `local` として宣言する。`alias` が空/None の場合は port name (例: `Ethernet0`) を fallback として使用 (lldpmgrd:147-150)。

```jinja2
{# lldpd.conf.j2:30-31 #}
{# Use ifname globally to avoid MAC-as-Port-ID; lldpmgrd sets alias per port later. #}
configure lldp portidsubtype ifname
```

起動初期は `ifname` (= linux iface 名)、その後 lldpmgrd が CONFIG_DB の `PORT.alias` を読んで per-port で `local <alias>` に切り替える二段構成。

### `description` (per-port)

**コード由来デフォルト**: なし (空のまま)

```python
# lldpmgrd:152-153
port_desc = port_table_dict.get("description")
# ...
if port_desc:
    lldpcli_cmd += ["description", port_desc]
```

`description` が空/未設定なら `lldpcli` に description 引数を渡さない (lldpmgrd:160-162 のログで明示)。lldpd は description を空のまま送信。

---

## 特殊ポートのスキップ条件

lldpmgrd は次の prefix を持つポートを LLDP 設定対象から除外 (lldpmgrd:141-142):

- `inband_prefix()` (典型: `Ethernet-IB`)
- `recirc_prefix()` (典型: `Ethernet-Rec`)
- `backplane_prefix()` (典型: `Ethernet-BP`)

これらのポートは `LLDP_PORT` エントリがあっても lldpcli に渡らないため、CONFIG_DB には書けるが lldpd には反映されない。

---

## まとめ

| フィールド | コード由来デフォルト | 出典 |
|-----------|----------------------|------|
| `enabled` | `true` | `sonic-lldp.yang:27` |
| `mode` | 未設定 (= lldpd 双方向) | `sonic-lldp.yang:32-40` (default 文なし) |
| portidsubtype (per-port) | `local <PORT.alias>` (alias 空時は port name) | `lldpmgrd:156`, `lldpmgrd:147-150` |
| portidsubtype (起動グローバル) | `ifname` | `lldpd.conf.j2:31` |
| `description` | なし (空) | `lldpmgrd:152-162` |
