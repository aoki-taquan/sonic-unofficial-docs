---
title: Dual-ToR の設定
description: Dual-ToR の設定 — Dual-ToR の設定は、port ごとの MUX_CABLE と peer ToR を表す PEER_SWITCH
  を起点に読みます。
area: topics
verification: meta
last_verified: 2026-05-10
sources:
- docs/reference/cli/config-muxcable.md
- docs/reference/cli/show-muxcable.md
- docs/reference/config-db/mux-cable.md
- docs/reference/config-db/peer-switch.md
related:
  cli:
  - show muxcable
  - config muxcable
  - show ip
  config_db:
  - MUX_CABLE
  - PEER_SWITCH
  - TUNNEL
  - MUX_LINKMGR
  - XCVRD_LOG
  - INTERFACE
  - VLAN_INTERFACE
  yang:
  - sonic-mux-cable
  - sonic-tunnel
---

# Dual-ToR の設定

Dual-ToR の設定は、port ごとの `MUX_CABLE` と peer ToR を表す `PEER_SWITCH` を起点に読みます。CLI の `config muxcable` は便利ですが、何が [CONFIG_DB](../../reference/glossary.md#term-config_db) に残る設定で、何が xcvrd / ycabled への一時的な低レイヤ操作なのかを分けておくと運用しやすくなります。

## 最小単位は server-facing port

`MUX_CABLE|<ifname>` は、サーバに向かう Ethernet port ごとに作ります。最低限見るフィールドは次の通りです。

| フィールド | 使う場面 |
|---|---|
| `cable_type` | `active-standby` または `active-active` を選ぶ |
| `state` | `auto`、`manual`、`active`、`standby`、`detach` の制御 |
| `server_ipv4` / `server_ipv6` | link prober と mux neighbor の対象 |
| `soc_ipv4` / `soc_ipv6` | Active-Active の SoC NIC 制御 |
| `prober_type` | software / hardware prober の選択 |
| `neighbor_mode` | `prefix-route` または `host-route` |

Active-Standby の構成では、peer ToR の情報も `PEER_SWITCH` に置きます。`PEER_SWITCH` は Dual-ToR ペアの相手を 1 つだけ表すメタデータで、MuxTunnel や mux 関連の整合に使われます。

## 典型シナリオ 1: Active-Standby Dual-ToR を初期設定する

「上位 spine と接続済みの 2 台の ToR が用意され、サーバの dual-attached NIC を mux 制御したい」というケース。

### CLI で打つ

```bash
# 1. peer ToR の loopback を登録
# (CLI 直接コマンドは無く JSON で投入するか sonic-cfggen を使う)

# 2. 各サーバ port を mux 配下にする
sudo config muxcable mode auto Ethernet0
sudo config muxcable mode auto Ethernet4

# 3. 状態確認
show muxcable status
show muxcable config Ethernet0
```

`PEER_SWITCH` や `MUX_CABLE` の初期 row 作成は通常 CLI ではなく `config_db.json` への投入 (deployment template) で行われます。CLI は state 操作 (`mode`、`probertype`) が中心です。

### CONFIG_DB JSON

Active-Standby の最小例:

```json
{
  "DEVICE_METADATA": {
    "localhost": {
      "subtype": "DualToR",
      "peer_switch": "tor-peer"
    }
  },
  "PEER_SWITCH": {
    "tor-peer": {
      "address_ipv4": "10.1.0.32"
    }
  },
  "TUNNEL": {
    "MuxTunnel0": {
      "tunnel_type": "IPINIP",
      "src_ip": "10.1.0.33",
      "dst_ip": "10.1.0.32",
      "dscp_mode": "uniform",
      "encap_ecn_mode": "standard",
      "ecn_mode": "copy_from_outer",
      "ttl_mode": "pipe"
    }
  },
  "MUX_CABLE": {
    "Ethernet0": {
      "cable_type": "active-standby",
      "state": "auto",
      "server_ipv4": "192.168.0.2/32",
      "server_ipv6": "fc02:1000::2/128",
      "prober_type": "software",
      "neighbor_mode": "prefix-route"
    }
  }
}
```

`DEVICE_METADATA.subtype = DualToR` は [linkmgrd](../../reference/glossary.md#term-linkmgrd) / mux-related orchestration の有効化フラグです。これが無いと MUX_CABLE row があっても `linkmgrd` は起動しない実装になっています。

`state: auto` により `linkmgrd` が状態遷移を管理します。`neighbor_mode: prefix-route` にすると、サーバ向け neighbor を残したまま route の nexthop を直接 neighbor / tunnel 間で切り替える設計になります。

### show コマンドで確認

```bash
show muxcable status
show muxcable config Ethernet0
show muxcable tunnel_route Ethernet0
show muxcable hwmode muxdirection
```

`show muxcable status` の典型出力:

```text
PORT        STATUS    HEALTH    HWSTATUS
----------  --------  --------  ----------
Ethernet0   active    healthy   active
Ethernet4   standby   healthy   standby
```

`STATUS` (linkmgrd 視点) と `HWSTATUS` (実 hardware mux) がずれている場合は ycabled の状態を疑います。

## 典型シナリオ 2: Active-Active (SoC NIC 連動) を設定する

```json
{
  "MUX_CABLE": {
    "Ethernet0": {
      "cable_type": "active-active",
      "state": "auto",
      "server_ipv4": "192.168.0.2/32",
      "server_ipv6": "fc02:1000::2/128",
      "soc_ipv4": "10.10.0.2/32",
      "soc_ipv6": "fc02:2000::2/128",
      "prober_type": "software",
      "neighbor_mode": "prefix-route"
    }
  }
}
```

Active-Active では SoC NIC と通信するための `soc_ipv4` / `soc_ipv6` が設定の読みどころになります。実際の到達性は gRPC channel、Loopback IP、証明書、NIC 側 service の状態にも依存します。

確認:

```bash
show muxcable grpc muxdirection Ethernet0
show muxcable grpc connection-info Ethernet0
```

`grpc connection-info` で `connection_status: READY` でない場合は SoC NIC との TLS / 経路を確認します。

## 典型シナリオ 3: 障害切替テスト (手動 toggle)

upgrade 前の draining などで、active 側を強制的に standby 化したいケース。

```bash
# 全 port を standby に倒す
sudo config muxcable mode standby all

# 個別 port のみ
sudo config muxcable mode standby Ethernet0

# 完了後 auto に戻す
sudo config muxcable mode auto all
```

`mode standby` は `MUX_CABLE.state` を `standby` に書き、linkmgrd の auto 制御を一時的に上書きします。`mode auto` に戻すと再評価が走ります。

## `config muxcable` で変えるもの

通常の状態制御は次の形で行います。

```bash
config muxcable mode auto Ethernet0
config muxcable mode active Ethernet0
config muxcable mode standby Ethernet0
config muxcable mode detach Ethernet0
config muxcable probertype hardware Ethernet0
```

`mode` は `MUX_CABLE` の状態を書き換えます。`auto` は自動制御、`manual` / `active` / `standby` は運用者が状態を固定したい場面、`detach` は mux 制御から外したい場面で使います。

一方、PRBS、loopback、firmware、FEC、ANLT、packet loss reset などは、CONFIG_DB だけで完結する設定ではなく xcvrd / ycabled への非同期 RPC に近い操作です。低レイヤの保守作業として扱い、通常の mux 状態制御とは分けて記録するのが安全です。

## 設定後に見るもの

```bash
show muxcable config Ethernet0
show muxcable status Ethernet0
show muxcable tunnel_route Ethernet0
show muxcable grpc muxdirection Ethernet0
```

`show muxcable config` は CONFIG_DB の見え方、`status` は動的状態、`tunnel_route` は tunnel 経路、`grpc muxdirection` は Active-Active 側の gRPC キャッシュを確認する入口です。詳細な列や JSON 出力の形は既存の CLI ページを参照してください。

## よくある設定エラーと対処

| 症状 | 原因 | 対処 |
|---|---|---|
| `MUX_CABLE` 書いたが linkmgrd が動かない | `DEVICE_METADATA.subtype != DualToR` | metadata を確認 |
| `state: standby` 固定で戻らない | 過去の手動 toggle 残存 | `config muxcable mode auto <port>` |
| `STATUS` と `HWSTATUS` が永続的にズレる | ycabled crash / cable firmware 異常 | `docker exec pmon supervisorctl status ycabled` |
| MuxTunnel decap が動かない | `PEER_SWITCH.address_ipv4` 不一致 / TUNNEL src_ip 誤り | `show ip route <peer_loopback>` で reachability 確認 |
| Active-Active で grpc `NOT_READY` | SoC NIC IP 未到達 / cert 不整合 | `show muxcable grpc connection-info` でエラー詳細 |
| `prefix-route` モードで standby 時に /32 route の nexthop が tunnel に切り替わる | neighbor entry 自体は削除されず、サーバ IP の `/32` または `/128` route の nexthop だけが直接 neighbor と tunnel の間で切り替わる設計 | 仕様。詳細は internals.md と [MUX_CABLE テーブル](../../reference/config-db/mux-cable.md) を参照 |

`cable_type: active-active` と `cable_type: active-standby` を box 内で混在させる構成は基本的に想定外です。port 単位の混在は controller / linkmgrd の前提を崩します。

## sonic-cfggen で部分パッチを当てる

deployment template (`minigraph.xml` → `sonic-cfggen` 経路) ではなく、運用中に Dual-ToR 関連の row を追加・削除したいときは [sonic-cfggen](../../reference/glossary.md#term-sonic-cfggen) の部分パッチを使います。

```bash
cat > /tmp/mux_patch.json <<'EOF'
{
  "MUX_CABLE": {
    "Ethernet8": {
      "cable_type": "active-standby",
      "state": "auto",
      "server_ipv4": "192.168.0.4/32",
      "server_ipv6": "fc02:1000::4/128",
      "prober_type": "software",
      "neighbor_mode": "prefix-route"
    }
  }
}
EOF
sudo sonic-cfggen -a "$(cat /tmp/mux_patch.json)" --write-to-db
sudo config save -y
```

部分パッチを当てた後は linkmgrd の subscription 経由で自動的に config が読まれます。`docker restart mux` などの強制再起動は通常不要です。

## CONFIG_DB / STATE_DB の関係

`MUX_CABLE` は CONFIG_DB の管理対象ですが、実状態は次の table に分かれます。

| 配置 | テーブル | 内容 |
|---|---|---|
| CONFIG_DB | `MUX_CABLE` | 静的設定 (cable_type, state, server_ip 等) |
| [APPL_DB](../../reference/glossary.md#term-appl_db) | `MUX_CABLE_TABLE` | linkmgrd が反映した動的設定 |
| [STATE_DB](../../reference/glossary.md#term-state_db) | `MUX_CABLE_TABLE` | 現在状態 (active/standby, link prober 状態) |
| STATE_DB | `HW_MUX_CABLE_TABLE` | ycabled が報告する hardware 上の mux 方向 |

`show muxcable status` が混乱した出力をするときは、STATE_DB の `MUX_CABLE_TABLE` と `HW_MUX_CABLE_TABLE` の不一致を `redis-cli -n 6 keys 'MUX*'` で確認します。CONFIG_DB の `state` を変えても hardware が追従していないケース (cable firmware ハング、ycabled デッドロック) はこの 2 table の差分で判別できます。

## YANG を見る場面

Dual-ToR 関連の [YANG](../../reference/glossary.md#term-yang) モジュールは `sonic-mux-cable` (`MUX_CABLE` の型)、`sonic-peer-switch` (`PEER_SWITCH`)、`sonic-tunnel` (`TUNNEL`) の 3 つに分かれます。`cable_type` の enum (`active-standby` / `active-active`) や `state` の許容値はここに定義されています。外部から [gNMI](../../reference/glossary.md#term-gnmi) で設定する場合は値の正規化を YANG 側で確認します。

## 関連ページ

- [MUX_CABLE テーブル](../../reference/config-db/mux-cable.md)
- [PEER_SWITCH テーブル](../../reference/config-db/peer-switch.md)
- [config muxcable サブコマンド](../../reference/cli/config-muxcable.md)
- [show muxcable サブコマンド](../../reference/cli/show-muxcable.md)
- [TUNNEL テーブル](../../reference/config-db/tunnel.md)

<!-- glossary-links-injected: d2689548bde0 -->
