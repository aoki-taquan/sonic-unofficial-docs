---
title: 運用
area: topics
verification: meta
last_verified: 2026-05-10
sources: []
---

# 運用

gNMI を運用する局面では、複数クライアントが同じ device を触る競合制御、再起動を跨いで設定を残す save-on-set、collector へ push する dial-out telemetry、subscription の安定性が課題になる。それぞれ HLD が別々に存在するため、ここで一望できるようにまとめる。

## Master arbitration

複数の NMS / 自動化 client が同じ switch に書き込むと、race condition による不整合が起きる。SONiC は gNMI master arbitration で「現在の writer は 1 つだけ」を強制できる。election ID を交換し、より大きい ID を持つ client が master になる。slave 化された client の Set は失敗で返るため、運用 script 側で master 化失敗時の fallback を書く必要がある。

詳細は [gNMI master arbitration HLD](../../management/gnmi-master-arbitration-hld.md) を参照する。election ID のリセット条件、failover の手順、observability の見方はそのページにまとまっている。

## Save-on-set による永続化

gNMI Set は CONFIG_DB を更新するが、CONFIG_DB は memory 上の Redis のため、再起動を跨ぐと失われる可能性がある。SONiC では `config save` 相当の処理を gNMI Set のたびに自動で走らせる save-on-set モードを持つ。

- 有効化すると、Set 完了後に `/etc/sonic/config_db.json` への書き出しが行われる。
- 大量の Set を高頻度で打つ用途では、write amplification によりディスクへの負担が増えるため、明示的な save を使うパターンと使い分ける。

挙動の詳細、エラー処理、`config save` との衝突回避は [Save-on-set HLD](../../management/save-on-set-hld.md) を参照する。

## Telemetry: dial-in と dial-out

SONiC telemetry は、collector 側が gNMI Subscribe で switch から pull する **dial-in** が標準だが、firewall / NAT 越しなどで collector へ switch から push する **dial-out** モードも持つ。

| 観点 | Dial-in (subscribe) | Dial-out |
| --- | --- | --- |
| 接続方向 | collector → switch | switch → collector |
| 認証 | switch 側 server cert | collector 側 server cert |
| 適用シナリオ | 通常運用 | NAT 越し、collector 集約 |

dial-out の設計は [Telemetry dial-out mode](../../system/sonic-telemetry-in-dial-out-mode.md) と続編の [Telemetry dial-out mode 2](../../system/sonic-telemetry-in-dial-out-mode-2.md) を参照する。再接続、buffer、batch、TLS 周りの注意点が両方に分散しているため、両方を順に読む。

## Subscription の使い方と注意

YANG path に対する Subscribe は SAMPLE / ON_CHANGE / TARGET_DEFINED の 3 モードがある。SONiC では COUNTERS_DB ベースの数値系メトリクスは SAMPLE 向き、CONFIG_DB ベースの状態は ON_CHANGE 向きである。BGP RIB のように規模が大きいデータを subscribe するときの注意は [gNMI subscription for YANG data](../../routing/gnmi-subscription-for-yang-data.md) にまとまっている。

実運用では次の点を抑える。

- 同じ path に複数 subscribe を重ねない (server 側で重複 stream を持つ)。
- TARGET_DEFINED は SONiC 側の選択に依存するため、明示的に SAMPLE / ON_CHANGE を指定するほうが debug しやすい。
- subscription の停止は client 側で `CancelSubscription` を送る。session を強制切断すると server 側に半開きの subscription が残る場合がある。

## 障害切り分け順

gNMI の問題は、layer ごとに切り分ける。

1. **接続**: TLS handshake、認証、ポート開放を確認する。telemetry container のログを最初に見る。
2. **Get / Set の echo**: `gnmi_get` で簡単な OpenConfig path を引き、応答があるかを確認する。
3. **Translib / Transformer**: 期待した YANG path が CONFIG_DB のどのテーブルに落ちるかを Transformer の対応で確認する。詳細は [アーキテクチャ](architecture.md) を参照する。
4. **Validation**: YANG validation エラーが返るときは、依存テーブル (たとえば PORT が存在しない VLAN member) を疑う。
5. **永続化**: 再起動後に消える場合は save-on-set が有効か、または明示的に `config save` を打ったかを確認する。

## 関連ページ

- [gNMI master arbitration HLD](../../management/gnmi-master-arbitration-hld.md)
- [Save-on-set HLD](../../management/save-on-set-hld.md)
- [Telemetry dial-out mode](../../system/sonic-telemetry-in-dial-out-mode.md)
- [Telemetry dial-out mode 2](../../system/sonic-telemetry-in-dial-out-mode-2.md)
- [gNMI subscription for YANG data](../../routing/gnmi-subscription-for-yang-data.md)
