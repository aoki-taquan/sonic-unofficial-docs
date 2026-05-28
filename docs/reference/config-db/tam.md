---
title: TAM テーブル
description: "TAM / IFA (In-band Flow Analyzer) テーブル — デバイス ID 設定・コレクタ宛先・IFA 機能フラグ・フロー定義の 4 コンテナを含む。sonic-mgmt-common の CVL と sonic-swss orchagent が参照する。"
area: reference
verification: code-verified
last_verified: 2026-05-14
sources:
  - repo: sonic-net/sonic-mgmt-common
    path: cvl/testdata/schema/sonic-tam.yang
    ref: HEAD
  - repo: sonic-net/sonic-mgmt-common
    path: cvl/testdata/schema/sonic-ifa.yang
    ref: HEAD
related:
  config_db:
    - TAM_DEVICE_TABLE
    - TAM_COLLECTOR_TABLE
    - TAM_INT_IFA_FEATURE_TABLE
    - TAM_INT_IFA_FLOW_TABLE
    - ACL_TABLE
    - ACL_RULE
  yang:
    - sonic-tam
    - sonic-ifa
---

# TAM テーブル

## 概要

Telemetry and Monitoring ([TAM](../../reference/glossary.md#term-tam)) および In-band Flow Analyzer ([IFA](../../reference/glossary.md#term-ifa)) に関する CONFIG_DB エントリ群。4 つのテーブルで構成される。

- **TAM_DEVICE_TABLE**: デバイス固有の [TAM](../../reference/glossary.md#term-tam) ID（`deviceid`）を保持する。
- **TAM_COLLECTOR_TABLE**: telemetry データの送信先コレクタ（IP アドレス・ポート）を定義する。
- **TAM_INT_IFA_FEATURE_TABLE**: [IFA](../../reference/glossary.md#term-ifa) 機能の有効/無効フラグを保持する。
- **TAM_INT_IFA_FLOW_TABLE**: [ACL](../../reference/glossary.md#term-acl) ルールに紐付いた [IFA](../../reference/glossary.md#term-ifa) フローを定義する。

<!-- defaults -->
### コード由来デフォルト

| テーブル | フィールド | デフォルト | 根拠 |
|---------|-----------|-----------|------|
| `TAM_DEVICE_TABLE\|device` | `deviceid` | `0` | YANG `default 0` (sonic-tam.yang) |
| `TAM_INT_IFA_FEATURE_TABLE\|feature` | `enable` | なし（false 相当） | boolean、DB に存在しない場合は IFA 無効 |
| `TAM_COLLECTOR_TABLE\|<name>` | `port` | なし | inet:port-number、省略可 |
| `TAM_INT_IFA_FLOW_TABLE\|<name>` | `sampling-rate` | なし | uint16 1..10000、省略可 |
| `TAM_INT_IFA_FLOW_TABLE\|<name>` | `collector-name` | なし | string、省略可 |

<!-- /defaults -->

## key / 構造

```text
TAM_DEVICE_TABLE|device              # デバイス TAM 設定（singleton）
TAM_COLLECTOR_TABLE|<name>           # コレクタ定義（名前キー）
TAM_INT_IFA_FEATURE_TABLE|feature    # IFA 機能フラグ（singleton）
TAM_INT_IFA_FLOW_TABLE|<name>        # IFA フロー定義（名前キー）
```

## TAM_DEVICE_TABLE

singleton エントリ。key は固定値 `device`。

| フィールド | 型 | 既定 | 説明 |
|-----------|----|------|------|
| `deviceid` | uint16 | **0** | [TAM](../../reference/glossary.md#term-tam) デバイス識別子。`0` は未設定を意味する。 |

`deviceid` は SAI_TAM_INT_ATTR_DEVICE_ID に渡される（`portsorch.cpp`）。

## TAM_COLLECTOR_TABLE

テレメトリデータの送信先を定義する。名前（`<name>`）をキーとする。

| フィールド | 型 | 既定 | 必須 | 説明 |
|-----------|----|------|------|------|
| `ipaddress-type` | enum `ipv4`/`ipv6` | - | yes | IP アドレスの種別。`must` 制約で `ipaddress` の内容と一致する必要がある。 |
| `ipaddress` | inet:ip-address | - | yes | コレクタの IP アドレス（IPv4/IPv6）。`ipaddress-type` と対で指定。 |
| `port` | inet:port-number (0..65535) | - | no | コレクタの UDP ポート番号。 |

`name` の文字種: `[a-zA-Z0-9]{1}([-a-zA-Z0-9_]{0,32})`（最大 32 文字）。  
`must` 制約: IPv6 アドレス（`:` 含む）なら `ipaddress-type=ipv6`、IPv4（`.` 含む）なら `ipaddress-type=ipv4` でなければ CVL が拒否する。

## TAM_INT_IFA_FEATURE_TABLE

IFA 機能の全体的な有効/無効フラグ。singleton。key は固定値 `feature`。

| フィールド | 型 | 既定 | 説明 |
|-----------|----|------|------|
| `enable` | boolean | なし (false 相当) | IFA を有効化する場合 `true`。DB にエントリが存在しない場合は無効扱い。 |

## TAM_INT_IFA_FLOW_TABLE

特定の [ACL](../../reference/glossary.md#term-acl) ルールに IFA フロー設定を紐付ける。

| フィールド | 型 | 既定 | 必須 | 説明 |
|-----------|----|------|------|------|
| `acl-table-name` | leafref → `ACL_TABLE.aclname` | - | yes | 対象 [ACL](../../reference/glossary.md#term-acl) テーブル名。 |
| `acl-rule-name` | leafref → `ACL_RULE.rulename` | - | yes | 対象 ACL ルール名（`acl-table-name` と対で解決）。 |
| `sampling-rate` | uint16 (1..10000) | - | no | 1/N パケットサンプリングレート。省略時はサンプリングなし。 |
| `collector-name` | string (1..32) | - | no | `TAM_COLLECTOR_TABLE` のエントリ名を参照する（string 型、leafref ではない）。 |

`name` の文字種: `[a-zA-Z0-9]{1}([-a-zA-Z0-9_]{0,32})`（最大 32 文字）。  
`sampling-rate` の範囲外値（0 または 10001+）は YANG 制約 `error-app-tag "Invalid IFA flow sampling rate."` でブロックされる。

## 購読者・処理経路

- `sonic-mgmt-common` CVL: YANG ベースの設定バリデーション（`must` / `mandatory` / `leafref` 制約）
- `sonic-swss/orchagent/portsorch.cpp`: `SAI_TAM_INT_ATTR_DEVICE_ID` に `deviceid` を設定（Path Tracing 機能）
- `sonic-swss/orchagent/high_frequency_telemetry/hftelorch.cpp`: `SAI_TAM_COLLECTOR_ATTR_*` を参照（High Frequency Telemetry）

## 関連 CONFIG_DB / YANG

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `ACL_TABLE`、`ACL_RULE`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-tam`、`sonic-ifa`

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): `sonic-tam`
- [YANG](../../reference/glossary.md#term-yang): `sonic-ifa`
- [CONFIG_DB](../../reference/glossary.md#term-config_db): [`acl-table`](acl-table.md)
- [CONFIG_DB](../../reference/glossary.md#term-config_db): [`acl-rule`](acl-rule.md)

<!-- ref-triangle:end -->

## 引用元

[^3]: [SAI](../../reference/glossary.md#term-sai) 属性参照: `portsorch.cpp:11593-11609`. <https://github.com/sonic-net/sonic-swss/blob/HEAD/orchagent/portsorch.cpp#L11593>

[^5]: CVL must テスト (TAM_COLLECTOR ipaddress-type 不一致): `cvl_must_test.go:443-467`. <https://github.com/sonic-net/sonic-mgmt-common/blob/HEAD/cvl/cvl_must_test.go#L443>

[^6]: CVL leafref テスト (TAM_INT_IFA_FLOW leafref 失敗): `cvl_leafref_test.go:214-260`. <https://github.com/sonic-net/sonic-mgmt-common/blob/HEAD/cvl/cvl_leafref_test.go#L214>

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: Telemetry / SNMP / Observability](../../topics/09-telemetry-snmp/index.md)

<!-- /topics-back-ref -->

<!-- ops-hint -->
## 運用ヒント

### 典型設定手順

```bash
# デバイス ID 設定
sonic-db-cli CONFIG_DB hset 'TAM_DEVICE_TABLE|device' deviceid 12345

# コレクタ登録
sonic-db-cli CONFIG_DB hmset 'TAM_COLLECTOR_TABLE|col1' \
  ipaddress-type ipv4 ipaddress 192.0.2.10 port 9999

# IFA 機能有効化
sonic-db-cli CONFIG_DB hset 'TAM_INT_IFA_FEATURE_TABLE|feature' enable true

# IFA フロー設定（ACL と紐付け）
sonic-db-cli CONFIG_DB hmset 'TAM_INT_IFA_FLOW_TABLE|flow1' \
  acl-table-name MY_ACL acl-rule-name RULE1 \
  sampling-rate 100 collector-name col1
```

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB hgetall 'TAM_DEVICE_TABLE|device'
sonic-db-cli CONFIG_DB hgetall 'TAM_COLLECTOR_TABLE|col1'
sonic-db-cli CONFIG_DB hgetall 'TAM_INT_IFA_FEATURE_TABLE|feature'
sonic-db-cli CONFIG_DB hgetall 'TAM_INT_IFA_FLOW_TABLE|flow1'
```
<!-- /ops-hint -->

<!-- value-behavior -->
## 値依存挙動マトリクス

### `TAM_DEVICE_TABLE.deviceid` 値別挙動

| 値 | 挙動 |
|----|------|
| `0`（デフォルト） | TAM デバイス ID 未設定。SAI_TAM_INT_ATTR_DEVICE_ID に `0` が渡される。 |
| `1..65535` | デバイス固有の ID として [ASIC](../../reference/glossary.md#term-asic) に設定される（Path Tracing で使用）。 |

### `TAM_INT_IFA_FEATURE_TABLE.enable` 値別挙動

| 値 | 挙動 |
|----|------|
| `true` | IFA 機能を有効化。フロー定義（`TAM_INT_IFA_FLOW_TABLE`）が処理される。 |
| `false` / エントリなし | IFA 機能を無効化。フロー設定が存在しても IFA 処理は行われない。 |

### `TAM_INT_IFA_FLOW_TABLE.sampling-rate` 値別挙動

| 値 | 挙動 |
|----|------|
| 省略 | サンプリングなし（全パケット対象、または機能オフ）。 |
| `1` | 1/1 = 全パケットサンプリング。 |
| `100` | 1/100 パケットをサンプリング。 |
| `10000` | 最大間引き（YANG range 上限）。 |

### `TAM_COLLECTOR_TABLE.ipaddress-type` と `ipaddress` の対関係

| `ipaddress-type` | `ipaddress` 形式 | YANG must 結果 |
|-----------------|----------------|----------------|
| `ipv4` | `192.0.2.1`（`.` 含む） | OK |
| `ipv6` | `2001:db8::1`（`:` 含む） | OK |
| `ipv4` | `2001:db8::1` | エラー（`ipaddress-type-mismatch`） |
| `ipv6` | `192.0.2.1` | エラー（`ipaddress-type-mismatch`） |

<!-- /value-behavior -->

<!-- ordering -->
## 書込み順依存 (Phase B)

> 調査証跡: `meta/_intermediate/cdb-flow/tam-ordering.md`

### 1. TAM_COLLECTOR_TABLE → TAM_INT_IFA_FLOW_TABLE

`TAM_INT_IFA_FLOW_TABLE` の `collector-name` フィールドは YANG 上 string 型だが、
CVL（[sonic-mgmt](../../reference/glossary.md#term-sonic-mgmt)-common）が `TAM_COLLECTOR_TABLE` のエントリ存在を検証する
（`cvl_leafref_test.go` 参照）。
コレクタ名が `TAM_COLLECTOR_TABLE` に存在しない状態で IFA フローを書き込むと
CVL バリデーションが失敗する。

```
TAM_COLLECTOR_TABLE|<name>  →  書く  →  TAM_INT_IFA_FLOW_TABLE|<name> (collector-name フィールドあり)
```

### 2. ACL_TABLE / ACL_RULE → TAM_INT_IFA_FLOW_TABLE

`TAM_INT_IFA_FLOW_TABLE` の `acl-table-name` は `leafref → ACL_TABLE.aclname`、
`acl-rule-name` は `leafref → ACL_RULE.rulename` と YANG で明示的に定義されている。
CVL は leafref 解決を行うため、対応する ACL エントリが先に CONFIG_DB に存在していなければならない。

```
ACL_TABLE|<aclname>  →  書く  →  TAM_INT_IFA_FLOW_TABLE|<name> (acl-table-name / acl-rule-name フィールドあり)
```

### 3. TAM_DEVICE_TABLE / TAM_INT_IFA_FEATURE_TABLE は依存なし

どちらも singleton で他テーブルへの leafref 参照を持たない。任意の順序で書ける。

### 4. DEL 時の逆順

ADD と逆順で削除する。`TAM_INT_IFA_FLOW_TABLE` のエントリを削除してから
`TAM_COLLECTOR_TABLE` や `ACL_RULE` を削除する。
参照が残った状態での DEL は CVL が拒否する（leafref / string 参照チェック）。

### 5. orchagent 側の挙動

コミュニティ版 [orchagent](../../reference/glossary.md#term-orchagent) には `TAM_DEVICE_TABLE` / `TAM_COLLECTOR_TABLE` /
`TAM_INT_IFA_*` を直接購読するハンドラが存在しない。
上記の順序制約は主に Management フレームワーク（GNMI/REST）経由での CVL 検証で発生する。
`sonic-db-cli` で直接書き込む場合は YANG 制約チェックが走らないため、
順序違反してもリジェクトされない（ただし IFA 機能は [orchagent](../../reference/glossary.md#term-orchagent) 非実装のため [SAI](../../reference/glossary.md#term-sai) 反映もなし）。

<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

> 調査証跡: `meta/_intermediate/cdb-flow/tam-cross-refs.md`

`TAM_INT_IFA_FLOW_TABLE` の各フィールドは YANG leafref および CVL must 制約によって
以下のテーブルのエントリを**参照**する。CVL ([sonic-mgmt](../../reference/glossary.md#term-sonic-mgmt)-common) が GNMI/REST 経由の
設定適用時にこれらの制約を強制する。

| 参照元フィールド | 参照先テーブル | 参照先キー形式 | 制約種別 | 根拠 |
|---|---|---|---|---|
| `acl-table-name` | `ACL_TABLE` | `ACL_TABLE\|<aclname>` | YANG leafref (mandatory) | `sonic-ifa.yang:58-60` |
| `acl-rule-name` | `ACL_RULE` | `ACL_RULE\|<aclname>\|<rulename>` | YANG leafref (mandatory, 連鎖キー) | `sonic-ifa.yang:65-67` |
| `collector-name` | `TAM_COLLECTOR_TABLE` | `TAM_COLLECTOR_TABLE\|<name>` | CVL must 制約 (string 型) | `cvl_must_test.go:449-461` |

### 解決タイミング

- すべての参照チェックは **CVL バリデーション** (Management Framework が呼び出す) で行われる。
  `sonic-db-cli` の直接書き込み時は CVL をバイパスするため制約は適用されない。
- `acl-rule-name` の leafref は `current()/../acl-table-name` でフィルタされた連鎖 leafref のため、
  `ACL_RULE|<acl-table-name>|<acl-rule-name>` の組み合わせが正確に一致している必要がある。
- `collector-name` は optional のため、省略時は参照チェックが走らない。

### 依存なしのテーブル

- `TAM_DEVICE_TABLE` / `TAM_INT_IFA_FEATURE_TABLE` — 他テーブルへの leafref 参照を持たない。
  任意の順序で書き込み可能。

<!-- /cross-refs -->

<!-- failure -->
## 失敗挙動マトリクス (Phase D)

> 調査証跡: `meta/_intermediate/cdb-flow/tam-failure.md`

TAM テーブル群の失敗経路は **2 つのレイヤ** に分かれる。(1) Management Framework
経由での設定時に CVL が検出する YANG 制約違反、(2) [orchagent](../../reference/glossary.md#term-orchagent)（[portsorch](../../reference/glossary.md#term-portsorch) / HFTelOrch）
が [SAI](../../reference/glossary.md#term-sai) 操作を行う際のランタイム失敗。コミュニティ版 orchagent には
`TAM_DEVICE_TABLE` / `TAM_COLLECTOR_TABLE` / `TAM_INT_IFA_*` を直接 CONFIG_DB から
購読するハンドラが存在しないため、`sonic-db-cli` による直接書き込みは CVL をバイパスし
SAI への反映も起こらない。

### CVL バリデーション失敗（Management Framework 経由）

| # | 操作 | 失敗条件 | エラー種別 | ErrAppTag | 結果 |
|---|------|---------|-----------|-----------|------|
| 1 | `TAM_COLLECTOR_TABLE` CREATE | `ipaddress-type=ipv6` かつ `ipaddress` が IPv4 形式（またはその逆） | `CVL_SEMANTIC_ERROR` | `ipaddres-type-mismatch` | GNMI/REST が `400 Bad Request`。DB への書き込みなし[^5] |
| 2 | `TAM_INT_IFA_FLOW_TABLE` CREATE | `acl-table-name` が `ACL_TABLE` に存在しない、または `acl-rule-name` が対応する `ACL_RULE` に存在しない | `CVL_SEMANTIC_DEPENDENT_DATA_MISSING` | `instance-required` | 同上[^6] |
| 3 | `TAM_INT_IFA_FLOW_TABLE` CREATE | `collector-name` が `TAM_COLLECTOR_TABLE` に存在しない | `CVL_SEMANTIC_ERROR`（must 制約） | — | 同上 |
| 4 | `TAM_INT_IFA_FLOW_TABLE.sampling-rate` | 値が範囲外（0 または 10001+） | `CVL_SYNTAX_RANGE` | `"Invalid IFA flow sampling rate."` | 同上 |

!!! note "CVL は GNMI/REST 専用"
    `sonic-db-cli CONFIG_DB hmset` 等の直接書き込みは CVL を通らないため、上記制約は適用されない。orchagent はこれらのテーブルを購読しないため、不整合なエントリが SAI に伝播することもない（IFA 機能は orchagent 非実装）。

### HFTelOrch 初期化失敗（SAI TAM 能力チェック）

| # | 失敗条件 | 検出箇所 | 結果 | ログ |
|---|---------|---------|------|------|
| 5 | `sai_query_stats_st_capability` が `SUCCESS` / `BUFFER_OVERFLOW` 以外 | `isSupportedHFTel()` | `HFTel disabled`（TAM Collector SAI オブジェクト未作成） | `NOTICE "Streaming stats not supported, HFTel disabled"` |
| 6 | `SAI_OBJECT_TYPE_TAM_COLLECTOR` 属性の capability クエリ失敗 / `create_implemented=false` | `isSupportedHFTel()` | 同上 | `NOTICE "HFTel: <attr> capability query failed, HFTel disabled"` |
| 7 | `SAI_SWITCH_ATTR_TAM_TEL_TYPE_CONFIG_CHANGE_NOTIFY` set 失敗 | `HFTelOrch()` 初期化 | `runtime_error` → orchagent abort → systemd 再起動 | `ERROR "Failed to set SAI_SWITCH_ATTR_TAM_TEL_TYPE_CONFIG_CHANGE_NOTIFY"` |
| 8 | `SAI_SWITCH_ATTR_TAM_OBJECT_ID` set 失敗 | `HFTelOrch()` 初期化 | 同上 | `ERROR "Failed to set SAI_SWITCH_ATTR_TAM_OBJECT_ID"` |

### HFTelOrch doTask() 処理失敗

| 失敗条件 | 結果 | 根拠 |
|---------|------|------|
| 未知のテーブル名 | ERROR ログ → `task_failed`（永続スキップ） | `hftelorch.cpp:623` |
| 未知のオペレーション型 | ERROR ログ → `task_failed`（永続スキップ） | `hftelorch.cpp:598, 618` |
| 処理例外送出 | ERROR ログ → `task_failed`（永続スキップ） | `hftelorch.cpp:628-633` |
| プロファイルが `canBeUpdated()=false`（ストリーム稼働中） | `task_need_retry`（次サイクルで再試行） | `hftelorch.cpp:275` |
| グループのプロファイルが未発見 | `task_need_retry` | `hftelorch.cpp:340-345` |

### portsorch Path Tracing TAM 失敗

`portsorch` は Path Tracing のために SAI TAM オブジェクトを作成する。`SAI_TAM_INT_ATTR_DEVICE_ID` は `TAM_DEVICE_TABLE.deviceid` を読まず固定値 `0` を使用する[^3]。

| # | 失敗条件 | 検出箇所 | 結果 |
|---|---------|---------|------|
| 9 | `create_tam_report()` SAI 失敗 | `createPtTam()` | `createAndSetPortPtTam()` が `false` を返す。当該ポートへの Path Tracing TAM 設定未反映 |
| 10 | `create_tam_int()` SAI 失敗 | `createPtTam()` | 同上 |
| 11 | `create_tam()` SAI 失敗 | `createPtTam()` | 同上 |
| 12 | `SAI_PORT_ATTR_TAM_OBJECT` set 失敗 | `setPortPtTam()` | 当該ポートの TAM オブジェクト未割り当て |

### STATE_DB / ERROR_TABLE への記録

TAM テーブル群に対応する [STATE_DB](../../reference/glossary.md#term-state_db) への書き込みはなし。失敗情報は syslog のみに出力される。CVL エラーは GNMI/REST レスポンスのエラーボディとして呼び出し元に返される。

```bash
# orchagent ログ確認（swss コンテナ内）
docker logs swss 2>&1 | grep -E "TAM|HFTel|Path Tracing"
```

<!-- /failure -->

<!-- constants -->
## ハードコード定数 (Phase E)

> 調査証跡: `meta/_intermediate/cdb-flow/tam-constants.md`

TAM テーブル群に関わる定数は YANG スキーマ由来のバリデーション定数と、orchagent が SAI オブジェクト生成時に使用するランタイム定数の 2 層に存在する。

### YANG スキーマ由来のバリデーション定数

| 定数 | 値 | 宣言箇所 |
|------|----|---------|
| `TAM_DEVICE_TABLE.name` 許容値 | `device`（enum 固定） | `sonic-tam.yang:28-31` |
| `TAM_DEVICE_TABLE.deviceid` YANG デフォルト | `0` | `sonic-tam.yang:36` |
| `TAM_INT_IFA_FEATURE_TABLE.name` 許容値 | `feature`（enum 固定） | `sonic-ifa.yang:28-31` |
| `TAM_COLLECTOR_TABLE.name` 文字パターン | `[a-zA-Z0-9]{1}([-a-zA-Z0-9_]{0,32})` | `sonic-tam.yang:49` |
| `TAM_COLLECTOR_TABLE.name` 最大長 | 32 文字 | `sonic-tam.yang:50` |
| `TAM_INT_IFA_FLOW_TABLE.name` 文字パターン | `[a-zA-Z0-9]{1}([-a-zA-Z0-9_]{0,32})` | `sonic-ifa.yang:46` |
| `TAM_INT_IFA_FLOW_TABLE.name` 最大長 | 32 文字 | `sonic-ifa.yang:47` |
| `TAM_INT_IFA_FLOW_TABLE.sampling-rate` 範囲 | 1〜10000 | `sonic-ifa.yang:64` |
| `TAM_INT_IFA_FLOW_TABLE.sampling-rate` エラータグ | `"Invalid IFA flow sampling rate."` | `sonic-ifa.yang:65` |
| `TAM_COLLECTOR_TABLE.port` 範囲 | 0〜65535 (`inet:port-number`) | `sonic-tam.yang:57` |

!!! warning "`ipaddres-type-mismatch` の typo"
    `TAM_COLLECTOR_TABLE` の `must` 制約 `error-app-tag` は `ipaddres-type-mismatch`（`ipaddress` の `s` が 1 文字欠落、`sonic-tam.yang:62`）。CVL が実際に返すエラータグもこの typo 文字列で固定されているため、GNMI/REST クライアントがエラータグでマッチングする場合はこの文字列をそのまま使用する必要がある。

### portsorch Path Tracing TAM のランタイム定数

`portsorch.cpp:createPtTam()` は `TAM_DEVICE_TABLE.deviceid` を CONFIG_DB から**読まず**、SAI TAM [INT](../../reference/glossary.md#term-int) オブジェクトに以下の固定値を使用する。

| SAI 属性 | 固定値 | 宣言箇所 |
|---------|--------|---------|
| `SAI_TAM_INT_ATTR_DEVICE_ID` | `0`（CONFIG_DB の `deviceid` を無視） | `portsorch.cpp:11597-11598` |
| `SAI_TAM_INT_ATTR_TYPE` | `SAI_TAM_INT_TYPE_PATH_TRACING` | `portsorch.cpp:11593-11594` |
| `SAI_TAM_INT_ATTR_INT_PRESENCE_TYPE` | `SAI_TAM_INT_PRESENCE_TYPE_UNDEFINED` | `portsorch.cpp:11601-11602` |
| `SAI_TAM_INT_ATTR_INLINE` | `false` | `portsorch.cpp:11605-11606` |
| `SAI_TAM_REPORT_ATTR_TYPE` | `SAI_TAM_REPORT_TYPE_VENDOR_EXTN` | `portsorch.cpp:11567-11568` |

!!! warning "TAM_DEVICE_TABLE.deviceid は dead field"
    `SAI_TAM_INT_ATTR_DEVICE_ID` には常に `0` が設定される。CONFIG_DB の `deviceid` フィールドは現在のコードでは Path Tracing TAM に反映されない（`portsorch.cpp:11597-11598`）。

### HFTelOrch TAM のランタイム定数

`hftelorch.cpp:createTAM()` が作成する SAI TAM オブジェクト群はすべてハードコード値を使用する。`TAM_COLLECTOR_TABLE` の CONFIG_DB 設定は HFTel の SAI TAM オブジェクトに**反映されない**（別機構）。

| SAI 属性 | 固定値 | 宣言箇所 |
|---------|--------|---------|
| `SAI_TAM_TRANSPORT_ATTR_TRANSPORT_TYPE` | `SAI_TAM_TRANSPORT_TYPE_NONE` | `hftelorch.cpp:751-752` |
| `SAI_TAM_COLLECTOR_ATTR_SRC_IP` | `0.0.0.0`（固定） | `hftelorch.cpp:766-768` |
| `SAI_TAM_COLLECTOR_ATTR_DST_IP` | `0.0.0.0`（固定、localhost 経由） | `hftelorch.cpp:771-773` |
| `SAI_TAM_COLLECTOR_ATTR_LOCALHOST` | `true` | `hftelorch.cpp:780-781` |
| `SAI_TAM_COLLECTOR_ATTR_DSCP_VALUE` | `0` | `hftelorch.cpp:788-789` |
| `SAI_TAM_ATTR_TAM_BIND_POINT_TYPE_LIST` | `SAI_TAM_BIND_POINT_TYPE_SWITCH` | `hftelorch.cpp:802-807` |

<!-- /constants -->

<!-- side-effects -->
## 副次 DB 書込 (Phase F)

> 調査証跡: `meta/_intermediate/cdb-flow/tam-side-effects.md`

TAM テーブル群（`TAM_DEVICE_TABLE` / `TAM_COLLECTOR_TABLE` / `TAM_INT_IFA_FEATURE_TABLE` / `TAM_INT_IFA_FLOW_TABLE`）に対する主要購読者（`portsorch` および `HFTelOrch`）が副次的に書き込む DB エントリを以下に示す。

| 副次 DB | テーブル/キー形式 | 書込内容 | 根拠 |
|---|---|---|---|
| [STATE_DB](../../reference/glossary.md#term-state_db) | `HIGH_FREQUENCY_TELEMETRY_SESSION_TABLE\|<profile_name>\|<group_type>` | プロファイルグループが SAI 側で ready になった時点で `stream_status` / `session_type=ipfix` / `session_config`（テンプレートバイト列）を SET。グループ DEL 時はキーを DEL | `hftelorch.cpp:308, 432, 557`; 定数: `schema.h:509` |
| [ASIC_DB](../../reference/glossary.md#term-asic_db) | [syncd](../../reference/glossary.md#term-syncd) 経由 SAI オブジェクト | `portsorch.cpp` の `createPtTam()` / `setPortPtTam()` が SAI TAM オブジェクトを作成し [syncd](../../reference/glossary.md#term-syncd) 経由で [ASIC_DB](../../reference/glossary.md#term-asic_db) に反映（`portsorch.cpp:11554-11650`）。ただし `portsorch` は `TAM_DEVICE_TABLE` を CONFIG_DB から購読せず、Path Tracing TAM の設定変更は DEVICE_TABLE 操作と独立している | `portsorch.cpp:11401-11480` |
| [APPL_DB](../../reference/glossary.md#term-appl_db) | なし | TAM テーブル購読者から [APPL_DB](../../reference/glossary.md#term-appl_db) への書込みなし（`ProducerStateTable` / `ResponsePublisher` 参照: 0 件） | — |
| [COUNTERS_DB](../../reference/glossary.md#term-counters_db) | なし | `countersyncd`（Rust）は [STATE_DB](../../reference/glossary.md#term-state_db) の `HIGH_FREQUENCY_TELEMETRY_SESSION_TABLE` 変化を受けて [COUNTERS_DB](../../reference/glossary.md#term-counters_db) に書込むが、これは TAM テーブルへの直接書込みではなく STATE_DB 変化のリアクション | `countersyncd/src/actor/swss.rs:11, 42, 152` |
| [FLEX_COUNTER_DB](../../reference/glossary.md#term-flex_counter_db) / [LOGLEVEL_DB](../../reference/glossary.md#term-loglevel_db) | なし | 参照なし | — |

### HFTelOrch STATE_DB 書込の詳細

`HIGH_FREQUENCY_TELEMETRY_SESSION_TABLE` は `sonic-swss-common/common/schema.h:509` に定数 `STATE_HIGH_FREQUENCY_TELEMETRY_SESSION_TABLE_NAME` として定義される。

```
STATE_DB:HIGH_FREQUENCY_TELEMETRY_SESSION_TABLE|<profile_name>|<group_type>
  stream_status  = <稼働状態文字列>
  session_type   = "ipfix"        # 固定値 (hftelorch.cpp:553)
  session_config = <template bytes as string>
```

このエントリは `HFTelOrch::doTask(NotificationConsumer&)` が SAI TAM 通知を受け取り設定が ready になったときに書き込まれる（`hftelorch.cpp:485-560`）。`portsorch` の Path Tracing TAM は STATE_DB に直接書き込まない。

!!! note "TAM テーブルは間接的にのみ STATE_DB に影響する"
    `TAM_DEVICE_TABLE` / `TAM_COLLECTOR_TABLE` / `TAM_INT_IFA_*` への書込みは orchagent で直接購読されないため、これらの変更が STATE_DB の `HIGH_FREQUENCY_TELEMETRY_SESSION_TABLE` に反映されることは**ない**。STATE_DB 書込は HFTel プロファイル/グループ系テーブルの操作を通じて発生する。

<!-- /side-effects -->

<!-- pubsub -->
## 通信メカニズム (Phase G)

> 調査証跡: `meta/_intermediate/cdb-flow/tam-pubsub.md`

TAM 4 テーブル（`TAM_DEVICE_TABLE` / `TAM_COLLECTOR_TABLE` / `TAM_INT_IFA_FEATURE_TABLE` / `TAM_INT_IFA_FLOW_TABLE`）は **コミュニティ版 orchagent によって購読されない**。`orchdaemon.cpp` に対応する `TableConnector` / `addConsumer` 登録が存在しないため、keyspace 通知・`SubscriberStateTable`・`ConsumerStateTable` のいずれも発生しない。

| 項目 | 値 |
|------|-----|
| orchagent による購読 | **なし**（TableConnector 登録なし） |
| 購読クラス | 該当なし |
| keyspace 通知 | 使用しない（書き手・リスナーともに orchagent 側になし） |
| `ProducerStateTable` / channel PUBLISH | 使用なし |
| アクセス方式 | CVL（[sonic-mgmt](../../reference/glossary.md#term-sonic-mgmt)-common / Management Framework）がオンデマンド polling で HGETALL 読み出し（GNMI/REST リクエスト時のみ） |
| バッチサイズ | 概念なし（polling 読み取りのみ） |
| TTL | 未設定（CONFIG_DB は永続前提） |

`HFTelOrch` が CONFIG_DB から購読するのは `HIGH_FREQUENCY_TELEMETRY_PROFILE` と `HIGH_FREQUENCY_TELEMETRY_GROUP` の 2 テーブルのみ（`orchdaemon.cpp:860-861`）。これら HFTel 系テーブルは TAM 4 テーブルと異なり、`Orch::addConsumer()` 経由で `SubscriberStateTable`（CONFIG_DB 分岐、`DEFAULT_POP_BATCH_SIZE=128`）として購読される。

!!! note "TAM 4 テーブルは CVL 専用スキーマ"
    `sonic-db-cli` 等で直接書き込んだ場合は CVL もバイパスされるため、GNMI/REST 経由のバリデーションも発生しない。orchagent は CONFIG_DB の TAM 4 テーブルをポーリングも購読もしないため、書込みは SAI に一切伝播しない。

<!-- evidence: sonic-net/sonic-swss/orchagent/orchdaemon.cpp:860L (HFTelOrch 購読テーブルは HIGH_FREQUENCY_TELEMETRY_PROFILE / GROUP のみ) -->
<!-- evidence: sonic-net/sonic-swss/orchagent/orch.cpp:1186L (addConsumer CONFIG_DB → SubscriberStateTable 分岐) -->
<!-- evidence: sonic-net/sonic-swss-common/common/schema.h:408L (CFG_HIGH_FREQUENCY_TELEMETRY_PROFILE_TABLE_NAME 定義) -->
<!-- evidence: sonic-net/sonic-swss-common/common/table.h:164L (DEFAULT_POP_BATCH_SIZE = 128) -->
<!-- /pubsub -->

<!-- platform -->
## プラットフォーム差 (Phase H)

> 調査証跡: `meta/_intermediate/cdb-flow/tam-platform.md`

TAM 4 テーブル（`TAM_DEVICE_TABLE` / `TAM_COLLECTOR_TABLE` / `TAM_INT_IFA_FEATURE_TABLE` / `TAM_INT_IFA_FLOW_TABLE`）の処理コードには `getenv("platform")` や `ASIC_VENDOR` 環境変数によるプラットフォーム固有分岐が**存在しない**。ただし TAM に関わる 2 つの主要処理経路はともに **SAI capability query** の結果でランタイムに有効/無効が決まるため、ベンダー SAI 実装によって動作差が生じる。

### 1. Path Tracing TAM — SAI capability による有効/無効判定

`PortsOrch::isPathTracingSupported()`（[portsorch](../../reference/glossary.md#term-portsorch).cpp:576-631）は以下の 4 条件をすべて SAI capability query で確認する。いずれかが不成立の場合は Path Tracing TAM 機能全体を無効化する。

| 条件 | SAI クエリ |
|------|-----------|
| Switch が `SAI_OBJECT_TYPE_TAM` をサポートする | `SAI_SWITCH_ATTR_SUPPORTED_OBJECT_TYPE_LIST` |
| Port が `SAI_PORT_ATTR_PATH_TRACING_INTF` をサポートする | `querySwitchCapability` |
| Port が `SAI_PORT_ATTR_PATH_TRACING_TIMESTAMP_TYPE` をサポートする | `querySwitchCapability` |
| Port が `SAI_PORT_ATTR_TAM_OBJECT` をサポートする | `querySwitchCapability` |

判定結果は STATE_DB `SWITCH_CAPABILITY` テーブルの `PATH_TRACING_CAPABLE` フィールドに書き込まれる（`portsorch.cpp:641,648`）。

```
STATE_DB:SWITCH_CAPABILITY
  PATH_TRACING_CAPABLE = "true"  # SAI がすべての条件を満たす場合
  PATH_TRACING_CAPABLE = "false" # いずれかの SAI capability が不成立の場合
```

Path Tracing をサポートしないプラットフォーム（多くのソフトウェアスイッチ・仮想スイッチ等）では `createPtTam()` が呼ばれず、SAI TAM オブジェクトが作成されない。

### 2. High Frequency Telemetry TAM — SAI capability による有効/無効判定

`HFTelOrch::isSupportedHFTel()`（hftelorch.cpp:168-260）は以下の SAI capability query を実施する。いずれかが失敗した場合は `NOTICE "HFTel disabled"` ログを出して HFTel 機能全体を無効化する。

| チェック内容 | API |
|------------|-----|
| `sai_query_stats_st_capability`（`SAI_OBJECT_TYPE_PORT`）が `SUCCESS` / `BUFFER_OVERFLOW` | `sai_query_stats_st_capability` |
| `SAI_TAM_COLLECTOR_ATTR_SRC_IP` 等 6 属性の create 能力 | `sai_query_attribute_capability` |
| `SAI_SWITCH_ATTR_TAM_TEL_TYPE_CONFIG_CHANGE_NOTIFY` / `SAI_SWITCH_ATTR_TAM_OBJECT_ID` の set 能力 | `sai_query_attribute_capability` |
| `SAI_TAM_TRANSPORT_TYPE_NONE` / `SAI_TAM_BIND_POINT_TYPE_SWITCH` の enum 値サポート | SAI メタデータ確認 |

### 3. CONFIG_DB TAM 4 テーブルとプラットフォームの無関係性

CVL（sonic-mgmt-common / Management Framework）によるバリデーションはプラットフォーム非依存の YANG スキーマ処理であり、プラットフォーム差は生じない。orchagent が TAM 4 テーブルを購読しないため、CONFIG_DB の設定値が SAI 動作に直接影響するパスは存在しない。

### プラットフォーム差サマリ

| 処理経路 | プラットフォーム固有コード分岐 | 有効化条件 |
|---------|--------------------------|---------|
| Path Tracing TAM（[portsorch](../../reference/glossary.md#term-portsorch)） | なし | SAI capability query 4 条件すべて成立 |
| HFTelOrch TAM | なし | SAI capability query（streaming stats + TAM Collector 属性）成立 |
| CVL バリデーション（Management Framework） | なし | プラットフォーム非依存（常に有効） |

<!-- /platform -->

<!-- glossary-links-injected: 14dfe6cfeb3d -->
