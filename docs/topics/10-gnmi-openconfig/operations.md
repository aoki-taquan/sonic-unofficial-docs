---
title: 運用
description: 運用 — gNMI を運用する局面では、複数クライアントが同じ device を触る競合制御、再起動を跨いで設定を残す save-on-set、collector
  へ push する dial-out telemetry、subscription の安定性が課題になる。それぞれの HLD を一望できるようにまとめる。
area: topics
verification: code-verified
last_verified: 2026-06-04
sources:
- repo: sonic-net/sonic-gnmi
  path: gnmi_server/server.go
  ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22
- repo: sonic-net/sonic-gnmi
  path: telemetry/telemetry.go
  ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22
- repo: sonic-net/sonic-buildimage
  path: src/sonic-yang-models/yang-models/sonic-telemetry.yang
  ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
- repo: sonic-net/sonic-buildimage
  path: src/sonic-yang-models/yang-models/sonic-telemetry_client.yang
  ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  cli: []
  config_db:
  - TELEMETRY
  - TELEMETRY_CLIENT
  yang:
  - sonic-telemetry
  - sonic-telemetry_client
  _no_related_cli: true
---

# 運用

[gNMI](../../reference/glossary.md#term-gnmi) を運用する局面では、複数クライアントが同じ device を触る競合制御、再起動を跨いで設定を残す save-on-set、collector へ push する dial-out telemetry、subscription の安定性が課題になる。それぞれ [HLD](../../reference/glossary.md#term-hld) が別々に存在するため、ここで一望できるようにまとめる。

## Master arbitration

複数の NMS / 自動化 client が同じ switch に書き込むと、race condition による不整合が起きる。[SONiC](../../reference/glossary.md#term-sonic) は gNMI master arbitration で「現在の writer は 1 つだけ」を強制できる。election ID を交換し、より大きい ID を持つ client が master になる。slave 化された client の Set は失敗で返るため、運用 script 側で master 化失敗時の fallback を書く必要がある。

詳細は [gNMI master arbitration HLD](../../management/gnmi-master-arbitration-hld.md) を参照する。election ID のリセット条件、failover の手順、observability の見方はそのページにまとまっている。

<!-- evidence:
source: sonic-net/sonic-gnmi/gnmi_server/server.go#L1308-L1340 (sha: eb635b7679b260c3fd0786a6d0734fc8e82c9a22)
excerpt: |
  // ReqFromMasterEnabledMA returns true if the request is sent by the master controller.
  func ReqFromMasterEnabledMA(req *gnmipb.SetRequest, masterEID *uint128) error {
      ...
      ma := e.GetMasterArbitration()
      ...
      reqEID = uint128{High: ma.ElectionId.High, Low: ma.ElectionId.Low}
reasoning: gNMI SetRequest の Extension に MasterArbitration を載せ、election_id (uint128) を比較して master 判定をする実装。role は未実装で codes.Unimplemented を返す。
-->


非 master からの Set は次のような応答になるため、client 側で `PermissionDenied` を確実に拾う実装にする。

```text
$ gnmic -a sw01:8080 set --update-path /openconfig-acl:acl/.../config/name --update-value test
target "sw01:8080": rpc error: code = PermissionDenied
  desc = client is not the current master (current_master_election_id=12, your_election_id=10)
```

telemetry container 内の `/var/log/telemetry.log` には次のような行が出るので、誰が master を奪ったかを後追いできる。

```text
INFO master_arbitration: master changed: old_id=10 new_id=12 client=10.1.2.3:54321
```

## Save-on-set による永続化

gNMI Set は [CONFIG_DB](../../reference/glossary.md#term-config_db) を更新するが、CONFIG_DB は memory 上の [Redis](../../reference/glossary.md#term-redis) のため、再起動を跨ぐと失われる可能性がある。SONiC では `config save` 相当の処理を gNMI Set のたびに自動で走らせる save-on-set モードを持つ。

- 有効化すると、Set 完了後に `/etc/sonic/config_db.json` への書き出しが行われる。
- 大量の Set を高頻度で打つ用途では、write amplification によりディスクへの負担が増えるため、明示的な save を使うパターンと使い分ける。

挙動の詳細、エラー処理、`config save` との衝突回避は [Save-on-set HLD](../../management/save-on-set-hld.md) を参照する。

<!-- evidence:
source: sonic-net/sonic-gnmi/telemetry/telemetry.go#L183-L190 (sha: eb635b7679b260c3fd0786a6d0734fc8e82c9a22)
excerpt: |
  WithSaveOnSet: fs.Bool("with-save-on-set", false, "Enables save-on-set."),
reasoning: telemetry プロセスの起動フラグ `--with-save-on-set` で save-on-set が有効化される。default は false。
-->
<!-- evidence:
source: sonic-net/sonic-gnmi/gnmi_server/server.go#L1050-L1068 (sha: eb635b7679b260c3fd0786a6d0734fc8e82c9a22)
excerpt: |
  // saveOnSetEnabled saves configuration to a file
  func SaveOnSetEnabled() error { ... }
  func saveOnSetDisabled() error { return nil }
reasoning: SaveOnSetEnabled / saveOnSetDisabled の 2 関数を Server.SaveStartupConfig に差し込む形で実装されている。
-->


設定の有無は `redis-cli -n 4 hgetall "DEVICE_METADATA|localhost"` または telemetry の起動オプションで確認する。`config_db.json` の更新タイムスタンプを `stat /etc/sonic/config_db.json` で監視すると、Set 後に永続化が走ったかを後追いできる。

## Telemetry: dial-in と dial-out

SONiC telemetry は、collector 側が gNMI Subscribe で switch から pull する **dial-in** が標準だが、firewall / [NAT](../../reference/glossary.md#term-nat) 越しなどで collector へ switch から push する **dial-out** モードも持つ。

| 観点 | Dial-in (subscribe) | Dial-out |
| --- | --- | --- |
| 接続方向 | collector → switch | switch → collector |
| 認証 | switch 側 server cert | collector 側 server cert |
| 適用シナリオ | 通常運用 | NAT 越し、collector 集約 |

dial-out の設計は [Telemetry dial-out mode](../../system/sonic-telemetry-in-dial-out-mode.md) と続編の [Telemetry dial-out mode 2](../../system/sonic-telemetry-in-dial-out-mode-2.md) を参照する。再接続、buffer、batch、TLS 周りの注意点が両方に分散しているため、両方を順に読む。

dial-in での確認:

```bash
gnmic -a sw01:8080 --skip-verify subscribe \
  --path '/openconfig-interfaces:interfaces/interface[name=Ethernet0]/state/counters' \
  --mode stream --stream-mode sample --sample-interval 10s
```

応答 JSON の主要キーは `in-octets`、`out-octets`、`in-errors`、`out-errors` などで、内部的に [COUNTERS_DB](../../reference/glossary.md#term-counters_db) から拾われる。`counterpoll show` で PORT_STAT が enable でないとカウンタが進まないため、Subscribe が空応答ばかりになる場合はまず polling を疑う。

dial-out 側は `/etc/sonic/telemetry/dialout.cfg` 相当の設定を CONFIG_DB の `TELEMETRY_CLIENT` に書く。状態は [STATE_DB](../../reference/glossary.md#term-state_db) の `TELEMETRY_CLIENT_STATE` を確認する。

## クライアントツールでの確認

実機で gNMI を試すときは `gnmic` か `gnmi_cli` を使う。telemetry container 自身に同梱されているのは `gnmi_get` / `gnmi_set` / `gnmi_cli` で、外部からは `gnmic` が読み書きしやすい。

```bash
# Capability (server がどの YANG model に対応しているか)
gnmic -a sw01:8080 --skip-verify capabilities | head -20

# OpenConfig で port の admin-status を読む
gnmic -a sw01:8080 --skip-verify get \
  --path '/openconfig-interfaces:interfaces/interface[name=Ethernet0]/state/admin-status'

# 同じ port を up にする
gnmic -a sw01:8080 --skip-verify set \
  --update '/openconfig-interfaces:interfaces/interface[name=Ethernet0]/config/enabled:::json:::true'

# 装置内から (telemetry container)
docker exec -it telemetry gnmi_get -xpath '/sonic-port:sonic-port/PORT/PORT_LIST'
```

CONFIG_DB を直接弄りたいときは SONiC 拡張の `sonic-*` model (例: `/sonic-port:sonic-port/PORT/...`) を使い、ベンダ間互換性を取りたい場合は OpenConfig (`/openconfig-interfaces:interfaces/...`) を使う、というのが基本方針。

## Subscription の使い方と注意

[YANG](../../reference/glossary.md#term-yang) path に対する Subscribe は SAMPLE / ON_CHANGE / TARGET_DEFINED の 3 モードがある。SONiC では COUNTERS_DB ベースの数値系メトリクスは SAMPLE 向き、CONFIG_DB ベースの状態は ON_CHANGE 向きである。[BGP](../../reference/glossary.md#term-bgp) RIB のように規模が大きいデータを subscribe するときの注意は [gNMI subscription for YANG data](../../routing/gnmi-subscription-for-yang-data.md) にまとまっている。

実運用では次の点を抑える。

- 同じ path に複数 subscribe を重ねない (server 側で重複 stream を持つ)。
- TARGET_DEFINED は SONiC 側の選択に依存するため、明示的に SAMPLE / ON_CHANGE を指定するほうが debug しやすい。
- subscription の停止は client 側で `CancelSubscription` を送る。session を強制切断すると server 側に半開きの subscription が残る場合がある。

## TLS / 認証の確認

telemetry container は `/etc/sonic/telemetry/` 配下の cert / key で TLS する。手元から疎通確認するには:

```bash
# server cert を確認
openssl s_client -connect sw01:8080 -showcerts </dev/null 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates

# mTLS の場合 client cert を渡す
gnmic -a sw01:8080 --tls-cert client.crt --tls-key client.key --tls-ca ca.crt \
  capabilities
```

`certificate verify failed` は CA mismatch、`handshake failure` は cipher / TLS version、`connection refused` は telemetry container が起動していないか listen address が違うケース。

```text
admin@sonic:~$ docker exec telemetry netstat -tlnp 2>/dev/null | grep -E '8080|50051'
tcp 0 0 0.0.0.0:8080  LISTEN  -
tcp 0 0 0.0.0.0:50051 LISTEN  -
```

## 障害切り分け順

gNMI の問題は、layer ごとに切り分ける。

1. **接続**: TLS handshake、認証、ポート開放を確認する。telemetry container のログを最初に見る。
2. **Get / Set の echo**: `gnmi_get` で簡単な OpenConfig path を引き、応答があるかを確認する。
3. **Translib / Transformer**: 期待した YANG path が CONFIG_DB のどのテーブルに落ちるかを Transformer の対応で確認する。詳細は [アーキテクチャ](architecture.md) を参照する。
4. **Validation**: YANG validation エラーが返るときは、依存テーブル (たとえば PORT が存在しない [VLAN](../../reference/glossary.md#term-vlan) member) を疑う。
5. **永続化**: 再起動後に消える場合は save-on-set が有効か、または明示的に `config save` を打ったかを確認する。

### 典型ログ

```text
INFO telemetry: Started gNMI server on 0.0.0.0:8080
INFO translib: Set request for path /openconfig-interfaces:interfaces/interface[name=Ethernet0]/config/description
ERROR translib: validation failed: dependent key PORT|Ethernet0 not found
WARN telemetry: subscription cancelled by client (sid=42 path=/openconfig-platform:components)
```

`validation failed: dependent key ... not found` は典型的な「親が無いところに子を作ろうとした」ケース。VLAN を作る前に member を入れた、[PortChannel](../../reference/glossary.md#term-portchannel) を作る前に member を入れた、などが該当する。

## 対応コマンド早見表

| 症状 | 入口 | 次に見る |
|------|------|---------|
| 接続できない | `docker logs telemetry` | TLS / cert、port 8080 / 50051 |
| Get は通るが Set で `PermissionDenied` | master arbitration | election ID |
| Set 後 reboot で消える | save-on-set | `config save` 履歴、`stat config_db.json` |
| Subscribe が空 | counterpoll show | 該当 DB の polling |
| Set がエラー (`validation failed`) | translib log | 依存 table の存在 |
| dial-out が collector に届かない | telemetry log | TELEMETRY_CLIENT_STATE、route |

## CONFIG_DB / STATE_DB 関連 key

| 機能 | DB | Key |
|------|-----|-----|
| telemetry 設定 | CONFIG_DB | `TELEMETRY` / `TELEMETRY_CLIENT` |
| master 状態 | STATE_DB | `TELEMETRY_MASTER_STATE` |
| dial-out 状態 | STATE_DB | `TELEMETRY_CLIENT_STATE` |
| YANG 検証エラー | telemetry.log | grep `translib` |

## 関連章

- 章 [07 ACL / CoPP / mirror](../07-acl-copp-mirror/operations.md) — gNMI で [ACL](../../reference/glossary.md#term-acl) を投入する場合の確認
- 章 [08 QoS / Buffer](../08-qos-buffer/operations.md) — [QoS](../../reference/glossary.md#term-qos) の宣言的設定
- 章 [09 telemetry / SNMP / observability](../09-telemetry-snmp/operations.md) — system-health / techsupport

## 関連ページ

- [gNMI master arbitration HLD](../../management/gnmi-master-arbitration-hld.md)
- [Save-on-set HLD](../../management/save-on-set-hld.md)
- [Telemetry dial-out mode](../../system/sonic-telemetry-in-dial-out-mode.md)
- [Telemetry dial-out mode 2](../../system/sonic-telemetry-in-dial-out-mode-2.md)
- [gNMI subscription for YANG data](../../routing/gnmi-subscription-for-yang-data.md)

<!-- glossary-links-injected: 8ba32e5aa69d -->
