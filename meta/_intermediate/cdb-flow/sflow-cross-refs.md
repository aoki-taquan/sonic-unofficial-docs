# SFLOW テーブル 暗黙参照スキャン (Phase C)

`docs/reference/config-db/sflow.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソースは:

- `sonic-net/sonic-swss/cfgmgr/sflowmgr.cpp` (`SflowMgr` クラス, `doTask`)
- `sonic-net/sonic-swss/orchagent/sfloworch.cpp` (`SflowOrch` クラス, `doTask`)

`SFLOW` / `SFLOW_SESSION` / `SFLOW_COLLECTOR` テーブル変更時に各デーモンが間接的に参照する **他 CONFIG_DB / STATE_DB テーブルへの暗黙依存** を列挙する。

## スキャン手順

```bash
# 1. sflowmgr.cpp が CFG_PORT_TABLE_NAME / STATE_PORT_TABLE_NAME を購読するか確認
grep -n "CFG_PORT_TABLE_NAME\|STATE_PORT_TABLE_NAME\|PORT_TABLE" \
    .cache/sonic-sources/sonic-swss/cfgmgr/sflowmgr.cpp

# 2. sfloworch.cpp が gPortsOrch を通じて PORT を参照するか確認
grep -n "gPortsOrch\|getPort\|allPortsReady" \
    .cache/sonic-sources/sonic-swss/orchagent/sfloworch.cpp

# 3. SFLOW_COLLECTOR 参照の調査
grep -n "SFLOW_COLLECTOR\|collector_ip\|collector_vrf" \
    .cache/sonic-sources/sonic-swss/cfgmgr/sflowmgr.cpp \
    .cache/sonic-sources/sonic-swss/orchagent/sfloworch.cpp
```

## 検出された暗黙参照テーブル

### PORT テーブル (CONFIG_DB) — 実質必須

`SflowMgr` は `doTask()` 内で `table == CFG_PORT_TABLE_NAME` を明示的に処理する (sflowmgr.cpp:409)。コンストラクタで `CFG_PORT_TABLE_NAME` を consumer として登録し、ポート speed フィールドを読み取ってデフォルトサンプリングレートを算出する (`findSamplingRate()`, sflowmgr.cpp:385-401)。

- `sflowmgr.cpp:26`: `m_consumerMap.find(CFG_PORT_TABLE_NAME)` で consumer 登録確認
- `sflowmgr.cpp:34`: `SWSS_LOG_ERROR("Consumer object for PORT_TABLE not found")` — 未登録時はエラー
- `sflowmgr.cpp:115-118`: `fvField(i) == "speed"` でポート速度を取得
- `sflowmgr.cpp:409`: `if (table == CFG_PORT_TABLE_NAME)` で `sflowUpdatePortInfo()` を呼ぶ
- **YANG leafref なし**。実装上 CONFIG_DB `PORT` を暗黙参照して初期サンプリングレートを決定する。

### STATE_DB PORT_TABLE — oper_speed フィードバック

`SflowMgr` は `STATE_PORT_TABLE_NAME` も consumer として購読し、oper speed 変化時にサンプリングレートを更新する (sflowmgr.cpp:414, `sflowProcessOperSpeed()`).

- `sflowmgr.cpp:414`: `else if (table == STATE_PORT_TABLE_NAME)` で `sflowProcessOperSpeed()` を呼ぶ
- `sflowmgr.cpp:184`: `fvField(i) == "speed"` — STATE_DB から oper_speed を取得
- `sflowmgr.cpp:195`: `m_sflowPortConfMap[alias].oper_speed != oper_speed` — 変化時にレート更新
- **YANG leafref なし**。実装上 STATE_DB `PORT_TABLE` を暗黙参照して oper_speed 変化をトリガーに使う。

### PORT テーブル参照 (orchagent) — gPortsOrch 経由

`SflowOrch` は `gPortsOrch->allPortsReady()` (sfloworch.cpp:370) および `gPortsOrch->getPort(alias, port)` (sfloworch.cpp:382) を呼び出し、ポート OID を取得して SAI `sai_port_api` に渡す。

- `sfloworch.cpp:11`: `extern PortsOrch* gPortsOrch;`
- `sfloworch.cpp:370`: `if (!gPortsOrch->allPortsReady()) return;` — 全ポート準備完了待ち
- `sfloworch.cpp:382`: `gPortsOrch->getPort(alias, port)` — ポート名 → Port OID 変換
- **YANG leafref なし**。`SFLOW_SESSION` の key (`SFLOW_SESSION|<port>`) が指すポートが `PORT` テーブルに存在する前提が実装上必須。

### MGMT_VRF_CONFIG テーブル (YANG must 制約)

`SFLOW_COLLECTOR.collector_vrf = 'mgmt'` は `YANG must 制約` で `MGMT_VRF_CONFIG.vrf_global.mgmtVrfEnabled = 'true'` のときのみ許容される (sonic-sflow.yang)。これは実装コードではなく YANG バリデーション層で強制される暗黙依存。

- **YANG leafref あり** (must 制約)。mgmt VRF が有効でない状態で `collector_vrf=mgmt` を設定しようとすると YANG バリデーションエラー。

## 暗黙参照サマリ

| 参照先 | DB | 参照方向 | YANG leafref | 実装上の必須度 | 証拠 |
|---|---|---|---|---|---|
| `PORT\|<name>` | CONFIG_DB | 読み取り (speed → デフォルトサンプリングレート算出) | なし | 実質必須 | sflowmgr.cpp:26,34,115-118,409 |
| `PORT_TABLE\|<name>` | STATE_DB | 読み取り (oper_speed → サンプリングレート更新) | なし | 実質必須 | sflowmgr.cpp:414,184,195 |
| `PORT\|<name>` (gPortsOrch) | CONFIG_DB 経由 | 読み取り (ポート OID → SAI samplepacket 設定) | なし | 実質必須 | sfloworch.cpp:370,382 |
| `MGMT_VRF_CONFIG\|vrf_global` | CONFIG_DB | 読み取り (mgmtVrfEnabled チェック) | must 制約 | `collector_vrf=mgmt` 時必須 | sonic-sflow.yang must 制約 |

## SFLOW_COLLECTOR への暗黙参照

`sflowmgr.cpp` / `sfloworch.cpp` を grep した結果、C++ レベルで `SFLOW_COLLECTOR` を直接参照するコードはなかった。`SFLOW_COLLECTOR` テーブルは **`hsflowd`** (sFlow エージェントデーモン、ユーザー空間) が CONFIG_DB を直接読んで宛先 IP / ポート / VRF を設定ファイルに反映する経路で参照される。`sflowmgrd` は hsflowd の設定ファイル生成のトリガー役で、SFLOW_COLLECTOR の内容を読むのは hsflowd 側。

## 範囲外 (誤解されやすい隣接テーブル)

- **`PORTCHANNEL` / `MGMT_PORT`** — YANG の `related` には記載があるが、`sflowmgr.cpp` / `sfloworch.cpp` では直接参照なし。PORT_TABLE 経由のポート解決のみ。
- **`APP_SFLOW_TABLE` / `APP_SFLOW_SESSION_TABLE`** — APPL_DB への **書き込み** (出力) であり暗黙参照ではない。

## 検証コマンド

```bash
grep -n "PORT_TABLE\|STATE_PORT\|CFG_PORT" \
    .cache/sonic-sources/sonic-swss/cfgmgr/sflowmgr.cpp

grep -n "gPortsOrch\|getPort\|allPortsReady" \
    .cache/sonic-sources/sonic-swss/orchagent/sfloworch.cpp
```

このスキャン結果から派生して `docs/reference/config-db/sflow.md` の `<!-- cross-refs -->` ブロックを生成する。
