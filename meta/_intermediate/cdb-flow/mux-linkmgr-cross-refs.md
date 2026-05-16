# MUX_LINKMGR テーブル 暗黙参照スキャン (Phase C)

`docs/reference/config-db/mux-linkmgr.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソースは `sonic-net/sonic-linkmgrd` (DbInterface.cpp, MuxManager.cpp, MuxPort.cpp) および `sonic-net/sonic-swss/orchagent/muxorch.cpp`。`MUX_LINKMGR` パラメータ処理時に `linkmgrd` が直接購読せずに間接参照する CONFIG_DB テーブルを列挙する。

## スキャン手順

```bash
# linkmgrd 内で MUX_LINKMGR 処理後に MUX_CABLE / PEER_SWITCH を参照する箇所
grep -n "MUX_CABLE\|PEER_SWITCH\|MuxPort\|setMuxLinkmgrStateMachineConfig\|setTimeoutIpv4\|setTimeoutIpv6\|processMuxLinkmgrConfig" \
    sonic-linkmgrd/src/DbInterface.cpp sonic-linkmgrd/src/MuxManager.cpp sonic-linkmgrd/src/MuxPort.cpp

# orchagent 側での PEER_SWITCH × TUNNEL 参照
grep -n "handlePeerSwitch\|getDstIpAddresses\|getDscpMode\|getQosMapId" \
    sonic-swss/orchagent/muxorch.cpp
```

## 検出された暗黙参照テーブル

### MUX_CABLE (linkmgrd 経由)

`linkmgrd` は `MUX_LINKMGR` を購読する handler (`processMuxLinkmgrConfigNotification()`, `DbInterface.cpp:1120-1214`) でパラメータを受け取り、その時点で保持している全 `MuxPort` インスタンスに対して適用する。各 `MuxPort` は `MUX_CABLE|<ifname>` エントリに 1:1 対応する。

| 参照方法 | 参照箇所 | 用途 |
|---|---|---|
| `MuxManager::setMuxLinkmgrStateMachineConfig()` 内で全 MuxPort を走査 | `sonic-linkmgrd/src/MuxManager.cpp` | `interval_v4`, `interval_v6`, `positive_signal_count`, `negative_signal_count` を各 MuxPort ステートマシンへ一括適用 |
| `MuxPort::setTimeoutIpv4_msec()` / `setTimeoutIpv6_msec()` | `sonic-linkmgrd/src/MuxPort.cpp` | LINK_PROBER コンテナの interval 変更を受けて各ポートの ICMP heartbeat タイマーを動的更新 |
| `MuxPort::setPositiveStateChangeRetryCount()` / `setNegativeStateChangeRetryCount()` | `sonic-linkmgrd/src/MuxPort.cpp` | active/standby 判定カウンタを更新。MUX_CABLE エントリのないポートには MuxPort が存在しないためスキップ |

> **重要**: `MUX_CABLE` エントリが存在しないインターフェースは `MuxPort` オブジェクトが作成されないため、`MUX_LINKMGR` の設定変更がそのポートに到達しない。DualToR 運用では全 server-facing ポートに `MUX_CABLE` エントリが必要。

### PEER_SWITCH (orchagent 経由 → 間接)

`linkmgrd` は `PEER_SWITCH` を直接 subscribe しない。peer ToR IP は orchagent (`MuxOrch::handlePeerSwitch()`) が `PEER_SWITCH` テーブルを読み取り、`TUNNEL` テーブルの `MuxTunnel0` と組み合わせてデータプレーントンネルを生成した後、STATE_DB / APPL_DB に結果を書き込む。`linkmgrd` はその STATE_DB を介してトンネル状態を把握し、`MUX_LINKMGR|LINK_PROBER` で設定した ICMP probe をそのトンネル経路で送信する。

| 参照方法 | 参照箇所 | 用途 |
|---|---|---|
| `decap_orch_->getDstIpAddresses("MuxTunnel0")` | `muxorch.cpp:2348` | PEER_SWITCH 処理時に TUNNEL.MuxTunnel0 の dst_ip を取得して P2P tunnel を生成 |
| `decap_orch_->getDscpMode("MuxTunnel0")` | `muxorch.cpp:2359` | MuxTunnel0 の dscp_mode を読み取り SAI encap 属性に反映 |
| `decap_orch_->getQosMapId("MuxTunnel0", ...)` | `muxorch.cpp:2367, 2374` | TC→DSCP / TC→Queue QoS マップ OID を取得 |

> `PEER_SWITCH` が未設定だとトンネルが生成されず、`MUX_LINKMGR|LINK_PROBER.interval_v4` 等で設定した ICMP probe が peer ToR に到達しない。結果として Active-Standby の peer リンク品質測定が機能しない。

## 依存関係サマリ

```
MUX_LINKMGR (CONFIG_DB)
  └── linkmgrd: processMuxLinkmgrConfigNotification()
        └── MuxManager::setMuxLinkmgrStateMachineConfig()
              └── 全 MuxPort (= MUX_CABLE エントリ 1:1 対応)
                    ├── setTimeoutIpv4_msec()    ← interval_v4 反映
                    ├── setTimeoutIpv6_msec()    ← interval_v6 反映
                    ├── setPositiveStateChangeRetryCount()  ← positive_signal_count
                    └── setNegativeStateChangeRetryCount()  ← negative_signal_count

PEER_SWITCH (CONFIG_DB) — 間接参照
  └── MuxOrch::handlePeerSwitch() (orchagent)
        └── decap_orch_->getDstIpAddresses/getDscpMode/getQosMapId ← TUNNEL.MuxTunnel0
              └── P2P tunnel 生成 → STATE_DB 反映
                    └── linkmgrd が MUX_LINKMGR.interval_v4 で ICMP probe をトンネル経由送信
```

## まとめ — `mux-linkmgr.md` Phase C 記載対象

| カテゴリ | テーブル | 参照方法 |
|---|---|---|
| プローブパラメータ適用先 (linkmgrd 内) | `MUX_CABLE` | `setMuxLinkmgrStateMachineConfig()` — 全 MuxPort へ一括伝搬 |
| peer ToR リンク品質測定経路 (間接) | `PEER_SWITCH` → `TUNNEL` | orchagent が MuxTunnel0 生成後に linkmgrd が ICMP probe を送信 |

生成日: 2026-05-16 (Phase C / mux-linkmgr)
