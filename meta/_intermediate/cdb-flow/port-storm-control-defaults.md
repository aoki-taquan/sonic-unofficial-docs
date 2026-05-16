# PORT_STORM_CONTROL — Phase A 暗黙デフォルト調査

対象: `docs/reference/config-db/port-storm-control.md`  
調査日: 2026-05-14  
証跡: `sonic-swss/orchagent/policerorch.cpp`, `sonic-utilities/config/main.py`, `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-storm-control.yang`

---

## フィールド一覧と暗黙デフォルト

### kbps (唯一のフィールド)

- YANG: `uint64`, range `0..100000000`, **YANG default 宣言なし**
- CLI: `click.IntRange(0, 100000000)` — required=True でデフォルト値なし。省略不可
- orchagent: `kbps` が存在しない場合、`cir = false` のまま `task_failed` を返す（line 195-200 policerorch.cpp）
  - エラーログ: `Failed to create storm control policer %s, missing mandatory fields`
- **結論**: kbps はコード上必須フィールド。デフォルト値なし。未指定は task_failed で silent drop ではなく SWSS_LOG_ERROR

---

## ハードコードされた暗黙属性 (YANG に存在しない)

以下は CONFIG_DB エントリに書くフィールドではないが、orchagent が **常に** 固定値で SAI policer に設定する:

| SAI 属性 | ハードコード値 | コード箇所 |
|---|---|---|
| `SAI_POLICER_ATTR_METER_TYPE` | `BYTES` (= `SAI_METER_TYPE_BYTES`) | `policerorch.cpp:157-159` |
| `SAI_POLICER_ATTR_MODE` | `STORM_CONTROL` (= `SAI_POLICER_MODE_STORM_CONTROL`) | `policerorch.cpp:162-164` |
| `SAI_POLICER_ATTR_RED_PACKET_ACTION` | `DROP` (= `SAI_PACKET_ACTION_DROP`) | `policerorch.cpp:167-169` |
| `SAI_POLICER_ATTR_GREEN_PACKET_ACTION` | 設定なし → SAI デフォルト依存 | — |
| `SAI_POLICER_ATTR_YELLOW_PACKET_ACTION` | 設定なし → SAI デフォルト依存 | — |
| `SAI_POLICER_ATTR_CBS` | 設定なし → SAI デフォルト依存 | — |
| `SAI_POLICER_ATTR_CIR` | kbps × 1000 ÷ 8 (kbps → bps → bytes/s 変換) | `policerorch.cpp:181-184` |

### kbps → CIR 変換式

```cpp
attr.value.u64 = (stoul(value)*1000/8);
```

- kbps をバイト/秒に変換して SAI CIR に設定
- 整数演算: `kbps * 1000 / 8` — kbps が 8 の倍数でない場合は切り捨て (silent rounding)
- 例: `kbps=1` → CIR = 125 bytes/s

---

## 暗黙動作・経路依存

### 1. update 時の remove-then-reapply 動作

既存 policer を更新する際、orchagent は:
1. ポートの当該 SAI 属性を `SAI_NULL_OBJECT_ID` に set（実質 detach）
2. CIR のみ update（METER_TYPE / MODE / RED_ACTION は更新しない = 作成時ハードコードのまま固定）
3. 新 oid を再 attach

→ **更新中の瞬間、storm control が外れる**（ミリ秒オーダー）

証跡: `policerorch.cpp:273-288`

### 2. allPortsReady ガード

`gPortsOrch->allPortsReady()` が false の間、`doTask()` は即座 return。
全 PORT の init 完了前は PORT_STORM_CONTROL エントリは処理されない (silent defer)。

証跡: `policerorch.cpp:379-382`

### 3. SAI policer 名前空間

内部 policer 名は `_<ifname>_<storm_type>` (アンダースコアプレフィックス付き)。  
通常の POLICER テーブルエントリとは名前空間が分離されている。衝突なし。

証跡: `policerorch.cpp:146`

### 4. SAI set_port_attribute 失敗時のロールバック (部分的)

- 新規作成時: set_port_attribute 失敗 → policer を remove → m_syncdPolicers から削除 → task_need_retry
- 更新時: detach (set NULL) 失敗 → task_need_retry (既存 policer は残存)
- **TODO コメントあり** (`policerorch.cpp:298`): cleanup が不完全であることをコード自身が認めている

### 5. 非 Ethernet インタフェースのサイレント成功

`if (strncmp(...ETHERNET_PREFIX...))` で非 Ethernet を検出時、`task_success` を返す。  
→ エラーログは出るが、エントリは erase される (silent drop + not retried)。

証跡: `policerorch.cpp:132-137`

### 6. ポート未発見のサイレント成功

ポートが見つからない場合も `task_success` を返す。コメント: "continue here as there can be more interfaces"  
→ エントリは erase される (silent drop)。

証跡: `policerorch.cpp:138-144`

### 7. BUM_STORM_CAPABILITY チェック (CLI 側)

CLI が `STATE_DB:BUM_STORM_CAPABILITY|<storm_type>` の `supported` フィールドをチェック。  
`0` の場合は CONFIG_DB への書き込みをスキップ。orchagent は capability チェックをしない。  
→ CLI 経由とは別に、直接 DB 書き込みをした場合は capability 不問で orchagent が処理を試みる。

証跡: `config/main.py:806-814`

### 8. validate_kbps は常に True を返す (dead validation)

`storm_control.py` の `validate_kbps()` は `return True` のみ。値の検証は行わない。  
実際のバリデーションは YANG + `ValidatedConfigDBConnector` に依存。

証跡: `storm_control.py:68-69`

### 9. CBS / Green / Yellow action は設定不可

YANG にも CLI にも CBS / Green action / Yellow action フィールドは存在しない。  
SAI デフォルトに完全依存。プラットフォームにより挙動が変わる可能性あり。

---

## dead consumer / dead field

| 分類 | 内容 |
|---|---|
| dead field | CBS, Green/Yellow packet action — YANG に存在せず、orchagent でも設定されない (SAI デフォルト依存) |
| dead validation | `validate_kbps()` in storm_control.py — 常に True を返す |
| dead consumer | なし — PolicerOrch が唯一の consumer で正常稼働 |

---

## YANG-実装 discrepancy

| 項目 | YANG | 実装 |
|---|---|---|
| `kbps` mandatory | mandatory 宣言なし (optional に見える) | コード上必須、欠如は task_failed |
| `kbps=0` の意味 | range 0..100000000 で 0 を許容 | CIR=0 として SAI に渡す。SAI/HW がどう扱うかはプラットフォーム依存 |
| `storm_type` の `_` vs `-` | YANG enum: `unknown-unicast`, `unknown-multicast` | orchagent 定数: `storm_unknown_unicast = "unknown-unicast"` — 一致 |
| METER_TYPE | YANG 定義なし | 常に BYTES (ハードコード) |
| MODE | YANG 定義なし | 常に STORM_CONTROL (ハードコード) |
| RED_ACTION | YANG 定義なし | 常に DROP (ハードコード) |
