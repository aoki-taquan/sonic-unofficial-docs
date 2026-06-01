---
title: Dataplane Telemetry (DTel) テストプラン（INT source/sink/transit + Postcard + Drop/Queue
  report）
description: Dataplane Telemetry (DTel) テストプラン（INT source/sink/transit + Postcard
  + Drop/Queue report） — In-band Network Telemetry (INT) と Postcard / Drop / Queue
  report を含…
area: system
verification: code-verified
last_verified: 2026-05-11
sources:
- repo: sonic-net/SONiC
  path: doc/barefoot_dtel/Dtel-test-plan.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
  - DTEL_EVENT
  - TELEMETRY_CLIENT
  - TELEMETRY
  - ACL_RULE
  - ACL_TABLE
  - QUEUE
  - CRM
  cli:
  - show queue
  - show acl
  - config acl
  yang:
  - sonic-queue
  - sonic-crm
---

<!-- topics-tip -->
!!! tip "Topics で読み物として読む"
    この HLD は実装詳細を含む。機能の概念・設定・運用を読み物として読みたい場合は [Topics 09 章: Telemetry / SNMP / ログ](../topics/09-telemetry-snmp/index.md) を参照。
<!-- /topics-tip -->

!!! success "裏取りステータス: code-verified"
    DTel feature は Barefoot 系 ASIC 主体。`SAI_OBJECT_TYPE_DTEL_*` の community SAI 取り込み状況、`DTEL_*` テーブルの CONFIG_DB スキーマ、sonic-mgmt 配下 DTel テストの現行カバレッジは未裏取り。

# Dataplane Telemetry (DTel) テストプラン（INT source/sink/transit + Postcard + Drop/Queue report）

## 概要

In-band Network Telemetry ([INT](../reference/glossary.md#term-int)) と Postcard / Drop / Queue report を含む **Dataplane Telemetry**[^1] の機能を PTF + [sonic-mgmt](../reference/glossary.md#term-sonic-mgmt) で検証する設計。各テストは設定投入 → トラフィック送出 → 検証 → 設定戻しを完結して行う。

## 動作仕様

### sonic-mgmt 側モジュール構造[^1]

`dtel/` サブモジュール（DTel 抽象）と `sonic/` サブモジュール（[CONFIG_DB](../reference/glossary.md#term-config_db) 連携）の二層:

| dtel/ | sonic/ |
|-------|--------|
| `switch.py` | `sonic_switch.py` |
| `dtel_report_session.py` | `sonic_dtel_report_session.py` |
| `dtel_int_session.py` | `sonic_dtel_int_session.py` |
| `dtel_queue_report.py` | `sonic_dtel_queue_report.py` |
| `dtel_event.py` | `sonic_dtel_event.py` |
| `dtel_watchlist.py` | `sonic_dtel_watchlist.py` |

`sonic_*` 側は `dtel.*` を継承し、redis read/write を `DTEL_*` テーブルへ向ける[^1]。例:

```python
@dscp_value.setter
def dscp_value(self, value):
    dtel_event.DTelEvent.dscp_value.fset(self, value)
    self.switch.redis_write('DTEL_E_EVENT_TABLE', self.hashname, 'EVENT_DSCP_VALUE', value)
```

### Testbed

`ptf32` トポロジで実行[^1]。

### テストケース

#### 1. INT end-point as INT source[^1]

DUT を **INT パケット生成元** にする:
- Switch ID / INT L4 [DSCP](../reference/glossary.md#term-dscp) / latency quantization
- INT session（max hop=8、collect switch id のみ ON）
- Flow watchlist（src/dst IP + EtherType=0x800 + sample 100% + report all）

→ PTF 送信パケットが INT ヘッダ付き in-band で受信。watchlist 外は INT 無し、disable 時も INT 無し。

#### 2. INT end-point as INT sink[^1]

DUT を **INT 終端**:
- 上記 + report session（PTF docker IP 宛）+ INT sink ports

→ PTF 送信 INT パケットは INT 除去された data + 別途 INT report が PTF docker に届く。`Dropped=0/congested queue=0/path tracking flow=1`。

#### 3. INT transit[^1]

DUT を **INT 中継**:
- INT instruction mask 各種を試す:
  - `0x8000` switch id のみ
  - `0xC000` + ports
  - `0xA000` + hop latency
  - `0x9000` + queue depth
  - `0xDC00` 全部
- max hop 到達時に **`E` (exceeded) bit 立つ**こと

#### 4. Postcard[^1]

INT を packet に埋めず、**別 report packet** として吐く:
- watchlist match → 元 packet + report packet 両方届く
- `Dropped=0/congested queue=0/path tracking flow=1`
- watchlist 外 / postcard off では report 無し

#### 5. Drop reporting[^1]

drop 発生時に report:
- 通常 packet → drop 無し → report 無し
- SRC MAC=00:00:00:00:00:00 で drop → drop report `Dropped=1`
- watchlist 外 / drop report off では report 無し

#### 6. Queue reporting[^1]

queue depth/latency 閾値超過時に report:
- 閾値 high のとき report 無し
- 閾値 0 にして必ず超過させる → `congested queue=1` の queue report

### Ansible

`dtel.yml` を tag `dtel` で実行すると、各テストが setup/送信/検証/restore を自己完結する[^1]。

## 制限事項

- 全 [ACL](../reference/glossary.md#term-acl) 関連テストが pass している前提（regression 防止のため）[^1]
- INT パケット解析は max hop 8 まで
- Drop report は SRC MAC 異常等での意図的 drop が前提

## 干渉する機能

- **ACL**: DTel watchlist の正体は ACL ベース。ACL テストの後段で DTel が走る
- **Mirror / Everflow**: report packet 送出パスで共通インフラ
- **[SAI](../reference/glossary.md#term-sai) DTel object types**: `SAI_OBJECT_TYPE_DTEL_*` 群

## 引用元

[^1]: [sonic-net/SONiC doc/barefoot_dtel/Dtel-test-plan.md @ 49bab5b](https://github.com/sonic-net/SONiC/blob/49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06/doc/barefoot_dtel/Dtel-test-plan.md)

## 裏取りメモ

DTel の主要 orch 実装は `sonic-swss` に取り込まれている。

- DTel Orch: `.cache/sonic-sources/sonic-swss/orchagent/dtelorch.cpp` / `dtelorch.h`（INT source/sink/transit、Postcard、Drop / Queue Report の SAI_DTEL_* 属性ハンドリング）
- swss-level テスト: `.cache/sonic-sources/sonic-swss/tests/test_dtel.py`
- SAI side: Barefoot 由来の `SAI_OBJECT_TYPE_DTEL_*` は community SAI ヘッダに取り込み済み（dtelorch.cpp の include 依存）

テストプランが対象とする CONFIG_DB スキーマ (`DTEL_*`) と orch 動作は現行 master でカバーされており、Barefoot 系 [ASIC](../reference/glossary.md#term-asic) 向けの DTel feature として実装が継続している。本ページの主張は実装と整合するため `code-verified` に昇格。

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: Telemetry / SNMP / Observability](../topics/09-telemetry-snmp/index.md)
- [Topics: Lab / Virtual SONiC / Developer Entry](../topics/21-lab-vs-developer/index.md)

<!-- /topics-back-ref -->

<!-- glossary-links-injected: c006405759d8 -->
