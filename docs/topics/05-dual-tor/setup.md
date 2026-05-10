---
title: Dual-ToR の設定
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/reference/cli/config-muxcable.md
  - docs/reference/cli/show-muxcable.md
  - docs/reference/config-db/mux-cable.md
  - docs/reference/config-db/peer-switch.md
---

# Dual-ToR の設定

Dual-ToR の設定は、port ごとの `MUX_CABLE` と peer ToR を表す `PEER_SWITCH` を起点に読みます。CLI の `config muxcable` は便利ですが、何が CONFIG_DB に残る設定で、何が xcvrd / ycabled への一時的な低レイヤ操作なのかを分けておくと運用しやすくなります。

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

## Active-Standby の例

```json
{
  "PEER_SWITCH": {
    "tor-peer": {
      "address_ipv4": "10.1.0.32"
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

この例では `state: auto` により `linkmgrd` が状態遷移を管理します。`neighbor_mode: prefix-route` にすると、サーバ向け neighbor を残したまま route の nexthop を直接 neighbor / tunnel 間で切り替える設計になります。

## Active-Active の例

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

## 関連ページ

- [MUX_CABLE テーブル](../../reference/config-db/mux-cable.md)
- [PEER_SWITCH テーブル](../../reference/config-db/peer-switch.md)
- [config muxcable サブコマンド](../../reference/cli/config-muxcable.md)
- [show muxcable サブコマンド](../../reference/cli/show-muxcable.md)
