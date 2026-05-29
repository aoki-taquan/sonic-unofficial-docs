---
title: YANG モデル既知問題と検証
description: >
  sonic-buildimage の YANG モデル実装における既知の問題、検証エラー、
  CONFIG_DB との整合性不具合を issue tracker から収集したリファレンス。
area: system
verification: code-verified
last_verified: 2026-05-13
sources:
  - repo: sonic-net/sonic-buildimage
    ref: master
    note: >
      issues #7076, #7959, #9312, #9611, #9623, #9638, #9746, #9794, #9929,
      #10376, #10386, #10668, #12256, #12397, #12573
related:
  config_db:
    - ACL_TABLE
    - ACL_RULE
    - BGP_PEER_RANGE
    - VLAN
    - VLAN_INTERFACE
    - MIRROR_SESSION
    - SNMP_USER
    - SNMP_TRAP_CONFIG
    - TACPLUS
  yang:
    - sonic-acl
    - sonic-bgp-peerrange
    - sonic-vlan
    - sonic-mirror-session
    - sonic-snmp
---

!!! success "裏取りステータス: code-verified"
    sonic-buildimage issue tracker の実環境報告から抽出。master ブランチ対象。

# YANG モデル既知問題と検証

## 概要

[SONiC](../reference/glossary.md#term-sonic) の [YANG](../reference/glossary.md#term-yang) モデルは `sonic-buildimage/src/sonic-yang-models/yang-models/` 以下に格納され、
[CONFIG_DB](../reference/glossary.md#term-config_db) の検証・管理フレームワーク（mgmt-framework）・[DPB](../reference/glossary.md#term-dpb) の依存解決に使用される。
本ページは issue tracker で報告された YANG モデルの既知問題を整理する。

---

## 1. ビルド時エラー

### 1-1. `yang-models/sonic_yang_tree` が存在しない (#7076)[^7076]

```
[build] error: can't copy './yang-models/sonic_yang_tree': doesn't exist or not a regular file
```

**原因**: YANG ツリーファイルの生成ステップが並列ビルドで skip されることがある。
または初回 `make configure` 後のクリーンビルドで発生。

**対処**:

```bash
# YANG ツリーを手動生成
cd src/sonic-yang-models
python3 -m pytest tests/ -v
# または
make clean && make configure PLATFORM=<target> && make
```

---

### 1-2. libyang バックリンク問題でビルド失敗 (#9312)[^9312]

複数の YANG モジュールを `import` すると libyang のバックリンクコードが
メモリアクセス違反を起こす場合がある。

**歴史的背景**: この問題の回避策として一部の YANG フィールドが
過去にコメントアウトされた。libyang バージョンアップで概ね修正済み。

**確認**:

```bash
pyang --version
python3 -c "import libyang; print(libyang.__version__)"
```

---

## 2. パターン / 型定義の問題

### 2-1. `sonic-scheduler.yang` パターン問題 (#9611)[^9611]

```
[yang-models] sonic-scheduler.yang pattern issue
```

スケジューラー名のパターン正規表現が実際の CLI で許容される値と
一致しないケースがある。

---

### 2-2. `sonic-types.yang` の ACL `ACCEPT` 欠落 (#9638)[^9638]

```
[yang-models] missing ACCEPT in sonic-types.yang which used in ACL
```

`sonic-types.yang` の [ACL](../reference/glossary.md#term-acl) アクション定義に `ACCEPT` が含まれておらず、
`ACCEPT` を指定した ACL ルールが YANG 検証で拒否される。

**対処**: master の `sonic-types.yang.j2` には `ACCEPT` が定義済みのため、
最新版では本問題は解消している[^9638]。

<!-- evidence:
source: sonic-net/sonic-buildimage/src/sonic-yang-models/yang-templates/sonic-types.yang.j2#L81-L84 (sha: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)
excerpt: |
  enum DROP;
  enum ACCEPT;
  enum FORWARD;
reasoning: >
  現行 master の sonic-types.yang.j2 の packet action enum に ACCEPT が含まれることを確認。
  issue #9638 が報告した「ACCEPT 欠落」は master では修正済みであることの裏取り。
-->

---

### 2-3. ACL の `MIRROR_INGRESS_ACTION` / `MIRROR_EGRESS_ACTION` 欠落 (#9929)[^9929]

```
[yang] missing MIRROR_INGRESS_ACTION and MIRROR_EGRESS_ACTION in sonic-acl.yang
```

ACL ルールの `MIRROR_INGRESS_ACTION` / `MIRROR_EGRESS_ACTION` が
YANG モデルに定義されていないため、mgmt-framework 経由での設定時に
検証エラーが発生する。master では `sonic-acl.yang.j2` に両 leaf が追加され解消している[^9929]。

<!-- evidence:
source: sonic-net/sonic-buildimage/src/sonic-yang-models/yang-templates/sonic-acl.yang.j2#L80-L94 (sha: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)
excerpt: |
  leaf MIRROR_INGRESS_ACTION {
  leaf MIRROR_EGRESS_ACTION {
reasoning: >
  現行 master の sonic-acl.yang.j2 に MIRROR_INGRESS_ACTION / MIRROR_EGRESS_ACTION の
  両 leaf が定義されていることを確認。issue #9929 の欠落は master で解消済み。
-->

---

## 3. テーブル YANG モデル欠落

### 3-1. `BGP_PEER_RANGE` テーブル (#9794)[^9794]

```
Need YANG for BGP_PEER_RANGE table
```

[BGP](../reference/glossary.md#term-bgp) 動的ピア（peer-range）のテーブルに YANG モデルがない。
DPB の依存チェックや CONFIG_DB 検証で「未検証テーブル」として警告になる。

---

### 3-2. `MIRROR_SESSION` と CONFIG_DB の不整合 (#12397)[^12397]

```
[yang] sonic-mirror-session.yang does not align with ConfigDb
```

`MIRROR_SESSION` テーブルのフィールド定義が
実際の CONFIG_DB スキーマと乖離している。

**影響**: mgmt-framework 経由でミラーセッションを設定すると
検証エラーになる場合がある。

**ワークアラウンド**: `redis-cli` で直接 CONFIG_DB に書き込む。

```bash
redis-cli -n 4 HMSET "MIRROR_SESSION|mirror1" \
    src_ip 192.0.2.1 \
    dst_ip 192.0.2.2 \
    ttl 255 \
    queue 0
```

---

### 3-3. SNMP 関連テーブルの YANG 欠落 (#12573)[^12573]

```
Need Yang for SNMP_AGENT_ADDRESS_CONFIG, SNMP_USER, SNMP_TRAP_CONFIG tables
```

これらのテーブルに YANG モデルが存在しないため、
mgmt-framework 経由での [SNMP](../reference/glossary.md#term-snmp) 設定に制限がある。

---

## 4. 制約・バリデーション問題

### 4-1. TACPLUS 空の `global` セクション (#9746)[^9746]

```
[yang] validating TACPLUS with empty "global" fails, while non-empty "global" does not fail
```

TACPLUS の `global` セクションが空（`{}`）の場合に YANG 検証が失敗する。
非空の場合は検証が通る非対称な挙動。

**ワークアラウンド**: `global` セクションに最低 1 つのフィールドを設定する。

```bash
config tacacs global timeout 5
```

---

### 4-2. BGP peer-range 重複 IP チェック (#10376)[^10376]

```
[yang] sonic-bgp-peerrange.yang same ip_range is not allowed - sonic yang extension
```

sonic-yang extension で BGP ピア範囲の重複チェックが実装されているが、
エラーメッセージが不明瞭な場合がある。

---

### 4-3. VLAN / VLAN_INTERFACE の制約欠落 (#12256)[^12256]

```
[yang-models] Missing constraints in VLAN, VLAN_INTERFACE yang models
```

[VLAN](../reference/glossary.md#term-vlan) ID の範囲制約（1-4094）や
VLAN インターフェースの必須フィールドチェックが
YANG モデルに反映されていないケースがある。

---

### 4-4. dot1p-tc-map YANG と mgmt-framework (#10386)[^10386]

```
[YANG] sonic-dot1p-tc-map.yang would cause failed deployment via mgmt-framework
```

`sonic-dot1p-tc-map.yang` の定義が mgmt-framework の
OpenAPI スキーマ生成と競合する場合がある。

---

## 5. PORT の lanes 一意性検証 (#9623)[^9623]

```
[yang-models] Verify 'lanes' are unique per entry in 'PORT' table by yang validation extension
```

PORT テーブルで同一の lane 番号を複数ポートに割り当てることを
YANG バリデーションで拒否する拡張が追加された。

**確認**:

```bash
sonic-cfggen -d --print-data | python3 -c "
import json, sys
data = json.load(sys.stdin)
port_data = data.get('PORT', {})
lanes_set = set()
for port, cfg in port_data.items():
    for lane in cfg.get('lanes', '').split(','):
        lane = lane.strip()
        if lane in lanes_set:
            print(f'Duplicate lane {lane} in {port}')
        lanes_set.add(lane)
print('Lane check complete')
"
```

---

## 6. Annotation YANG の xpath 解決エラー (#10668)[^10668]

```
[Yang] Failed to find the xDbSpecMap: xpath for Annotation yang with field-name and table-name
```

mgmt-framework の YANG annotation ファイルで、
フィールド名とテーブル名の xpath が解決できない場合がある。

**確認**:

```bash
docker exec mgmt-framework supervisorctl status
docker logs mgmt-framework | grep -E 'xDbSpecMap|xpath' | tail -20
```

---

## YANG モデル管理のベストプラクティス

| 操作 | コマンド |
|------|---------|
| YANG バリデーション実行 | `python3 -m pytest src/sonic-yang-models/tests/` |
| 特定テーブルのモデル確認 | `find src/sonic-yang-models -name "*.yang" | xargs grep -l "TABLE_NAME"` |
| CONFIG_DB との整合確認 | `sonic-cfggen -d --print-data \| python3 -c "import json,sys; d=json.load(sys.stdin); print(list(d.keys()))"` |
| YANG ツリー生成 | `cd src/sonic-yang-models && python3 setup.py build` |

---

## 参照

- [動的ポートブレイクアウト DPB 既知問題](dynamic-port-breakout-known-issues.md)
- [CONFIG_DB リファレンス](../reference/config-db/index.md)

## 引用元

各項目の一次情報は sonic-buildimage の issue tracker。YANG モデルの現況は `sonic-net/sonic-buildimage` (sha `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`) の `src/sonic-yang-models/` で裏取りした。

[^7076]: [sonic-buildimage #7076](https://github.com/sonic-net/sonic-buildimage/issues/7076) — `sonic_yang_tree` 生成ステップ skip によるビルドエラー。
[^9312]: [sonic-buildimage #9312](https://github.com/sonic-net/sonic-buildimage/issues/9312) — libyang バックリンクのバグで `import` がビルドを壊す件。
[^9611]: [sonic-buildimage #9611](https://github.com/sonic-net/sonic-buildimage/issues/9611) — `sonic-scheduler.yang` のパターン正規表現の不整合。
[^9638]: [sonic-buildimage #9638](https://github.com/sonic-net/sonic-buildimage/issues/9638) — `sonic-types.yang` の ACL アクションに `ACCEPT` が欠落していた件（master で解消）。
[^9794]: [sonic-buildimage #9794](https://github.com/sonic-net/sonic-buildimage/issues/9794) — `BGP_PEER_RANGE` テーブルの YANG モデル追加要望。
[^9929]: [sonic-buildimage #9929](https://github.com/sonic-net/sonic-buildimage/issues/9929) — `sonic-acl.yang` の `MIRROR_INGRESS_ACTION` / `MIRROR_EGRESS_ACTION` 欠落（master で解消）。
[^12397]: [sonic-buildimage #12397](https://github.com/sonic-net/sonic-buildimage/issues/12397) — `sonic-mirror-session.yang` と CONFIG_DB スキーマの不整合。
[^12573]: [sonic-buildimage #12573](https://github.com/sonic-net/sonic-buildimage/issues/12573) — `SNMP_AGENT_ADDRESS_CONFIG` / `SNMP_USER` / `SNMP_TRAP_CONFIG` の YANG モデル追加要望。
[^9746]: [sonic-buildimage #9746](https://github.com/sonic-net/sonic-buildimage/issues/9746) — 空の `global` セクションを持つ TACPLUS の YANG 検証が失敗する非対称挙動。
[^10376]: [sonic-buildimage #10376](https://github.com/sonic-net/sonic-buildimage/issues/10376) — `sonic-bgp-peerrange.yang` の同一 ip_range 重複チェック拡張。
[^12256]: [sonic-buildimage #12256](https://github.com/sonic-net/sonic-buildimage/issues/12256) — VLAN / VLAN_INTERFACE の制約欠落。
[^10386]: [sonic-buildimage #10386](https://github.com/sonic-net/sonic-buildimage/issues/10386) — `sonic-dot1p-tc-map.yang` が mgmt-framework デプロイを失敗させる件。
[^9623]: [sonic-buildimage #9623](https://github.com/sonic-net/sonic-buildimage/issues/9623) — PORT テーブルの `lanes` 一意性を YANG validation extension で検証する件。
[^10668]: [sonic-buildimage #10668](https://github.com/sonic-net/sonic-buildimage/issues/10668) — Annotation YANG の xDbSpecMap xpath 解決エラー。

<!-- glossary-links-injected: 7c25258ad0ca -->
