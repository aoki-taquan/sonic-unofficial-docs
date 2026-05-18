# LLDP / LLDP_PORT ハードコード定数調査 (Phase E)

調査対象: `sonic-buildimage/dockers/docker-lldp/lldpmgrd`, `lldpd.conf.j2`, `lldpdSysDescr.conf.j2`

## lldpmgrd 定数 (Python)

| 定数名 | 値 | ファイル:行 | 用途 |
|-------|----|-----------|------|
| `PORT_INIT_TIMEOUT` | `300` 秒 | `lldpmgrd:33` | PortInitDone / PortConfigDone 待機上限。超過すると強制 `lldpcli resume` |
| `FAILED_CMD_TIMEOUT` | `6` 秒 | `lldpmgrd:34` | lldpcli 失敗時の再試行間隔 |
| `RETRY_LIMIT` | `5` 回 | `lldpmgrd:35` | ポート設定 lldpcli の最大再試行回数。超過で silent drop |
| `SELECT_TIMEOUT_MS` | `10000` ms (10 秒) | `lldpmgrd:291` | Redis select ループのタイムアウト。pending_cmds 処理周期を兼ねる |
| `REDIS_TIMEOUT_MS` | `0` | `lldpmgrd:50` | DBConnector タイムアウト (0 = ブロッキング) |

## lldpd.conf.j2 ハードコード設定

| 設定 | 値 | 説明 |
|-----|-----|------|
| グローバル portidsubtype | `ifname` | 起動時全ポートに適用。lldpmgrd が後で `local <alias>` に上書き |
| lldpd 起動状態 | `pause` | コンテナ起動直後は LLDP PDU 送出停止。lldpmgrd の `lldpcli resume` まで停止継続 |
| eth0 portidsubtype | `local <MGMT_PORT.alias>` (alias 未設定時 `local eth0`) | MGMT_PORT に alias がある場合のみ上書き |
| 管理 IP | IPv4 優先、次点 IPv6 (MGMT_INTERFACE から) | `configure system ip management pattern <ip>` |

## lldpdSysDescr.conf.j2 ハードコード

| 設定 | テンプレート | 説明 |
|-----|------------|------|
| system description | `SONiC Software Version: SONiC.<build_version> - HwSku: <hwsku> - Distribution: Debian <debian_version> - Kernel: <kernel_version>` | ビルド時展開。CONFIG_DB `LLDP|GLOBAL.system_description` は無視される |

## 暗黙デフォルト (lldpd 組み込み)

| 設定 | 値 | ソース |
|-----|-----|-------|
| hello_time (LLDP PDU 送出間隔) | 30 秒 | lldpd ハードコード (YANG `default 30` と一致) |
| hold multiplier (ttl = hello × mult) | 4 | lldpd ハードコード (YANG `default 4` と一致) |
| LLDP 双方向動作 | rx+tx | mode 未設定時の lldpd デフォルト |

## 証跡

- lldpmgrd L33-35: `PORT_INIT_TIMEOUT`, `FAILED_CMD_TIMEOUT`, `RETRY_LIMIT`
- lldpmgrd L50: `REDIS_TIMEOUT_MS`
- lldpmgrd L291: `SELECT_TIMEOUT_MS`
- lldpd.conf.j2 L31: `configure lldp portidsubtype ifname`
- lldpd.conf.j2 L33: `pause`
- lldpdSysDescr.conf.j2 L1: system description テンプレート
