# SFLOW 副次 DB 書込抽出 (Phase F)

## ソース
- `sonic-swss/orchagent/sfloworch.cpp`
- `sonic-swss/cfgmgr/sflowmgr.cpp`

## 調査方針

SFLOW / SFLOW_SESSION テーブルへの書込をトリガーとして、他 DB / テーブルへの副次書込が発生するコード経路を網羅的に調査。

---

## 副次書込 一覧

### 1. sflowmgrd → APPL_DB `SFLOW_TABLE` (APP_SFLOW_TABLE_NAME)

`SflowMgr::doTask()` が `CFG_SFLOW_TABLE_NAME` の SET イベントを受けると、`m_appSflowTable.set(key, values)` で APPL_DB `SFLOW_TABLE` に書き込む (sflowmgr.cpp:468)。DEL 時は `m_appSflowTable.del(key)` で削除 (sflowmgr.cpp:550)。

| トリガー | 対象 DB | テーブル | 書込フィールド | evidence |
|---------|--------|---------|--------------|---------|
| `SFLOW|global` SET (admin_state, polling_interval 等) | APPL_DB | `SFLOW_TABLE` | SET されたフィールドをそのまま転送 | sflowmgr.cpp:468 |
| `SFLOW|global` DEL | APPL_DB | `SFLOW_TABLE` | キー削除 | sflowmgr.cpp:550 |

SflowOrch は APPL_DB `APP_SFLOW_TABLE_NAME` を購読し、`sflowStatusSet()` で `m_sflowStatus` を更新する (sfloworch.cpp:365-368)。APPL_DB への書込が SAI samplepacket 操作の前提条件となる。

### 2. sflowmgrd → APPL_DB `SFLOW_SESSION_TABLE` (APP_SFLOW_SESSION_TABLE_NAME)

`SFLOW_SESSION` テーブルの SET/DEL に応じて `m_appSflowSessionTable.set(port, fvs)` / `.del(port)` を呼び出す。

#### 2a. グローバル admin_state 変更時 (全ポートに一斉書込)

`sflowHandleSessionAll()` (sflowmgr.cpp:220) が全ポートを走査し APPL_DB `SFLOW_SESSION_TABLE` を set/del:

- `admin_state=up` → `m_appSflowSessionTable.set(port, fvs)` でポートごとの `admin_state` / `sample_rate` / `sample_direction` を書き込む (sflowmgr.cpp:246)
- `admin_state=down` → ローカル admin 設定がないポートは `m_appSflowSessionTable.del(port)` (sflowmgr.cpp:250)

#### 2b. per-port `SFLOW_SESSION|<port>` SET 時

`sflowCheckAndFillValues()` でフィールドを補完後、`m_gEnable` が true のときのみ `m_appSflowSessionTable.set(key, fvs)` を呼び出す (sflowmgr.cpp:531-534)。

書込フィールド:

| フィールド | 値 | 条件 |
|-----------|---|------|
| `admin_state` | "up" / "down" | ローカル設定があれば使用、なければグローバルデフォルト |
| `sample_rate` | ポート速度から算出 (findSamplingRate) または明示値 | 常に書込 |
| `sample_direction` | "rx" / "tx" / "both" | ローカル設定があれば使用、なければグローバル方向 |

#### 2c. `SFLOW_SESSION|all` SET 時

key が `all` のとき全ポートに対して `sflowHandleSessionAll()` を呼び出す (sflowmgr.cpp:513)。`m_intfAllConf` / `m_intfAllDir` を更新し APPL_DB に反映。

#### 2d. PORT_TABLE 更新時 (速度変化)

`sflowUpdatePortInfo()` (sflowmgr.cpp:80) が `CFG_PORT_TABLE_NAME` 変更を受け、ポートの速度が変わりかつポートが有効なとき `m_appSflowSessionTable.set(key, fvs)` でサンプリングレートを自動更新 (sflowmgr.cpp:143)。

### 3. SflowOrch → ASIC_DB via SAI `sai_samplepacket_api` (APPL_DB 経由)

SflowOrch が APPL_DB `SFLOW_SESSION_TABLE` を購読し、SAI samplepacket API でハードウェア設定を行う。

#### 3a. `sai_samplepacket_api->create_samplepacket()`

新しいサンプリングレートのセッションを作成 (sfloworch.cpp:29):

```
attr.id    = SAI_SAMPLEPACKET_ATTR_SAMPLE_RATE
attr.value = rate (uint32)
sai_samplepacket_api->create_samplepacket(&session_id, gSwitchId, 1, &attr)
```

#### 3b. `sai_port_api->set_port_attribute()` — ingress / egress サンプリング設定

ポートに samplepacket セッションを紐付け (sfloworch.cpp:119-150):

| 方向 | SAI 属性 | 値 |
|------|---------|---|
| rx / both | `SAI_PORT_ATTR_INGRESS_SAMPLEPACKET_ENABLE` | `session_id` (有効化) / `SAI_NULL_OBJECT_ID` (無効化) |
| tx / both | `SAI_PORT_ATTR_EGRESS_SAMPLEPACKET_ENABLE` | `session_id` (有効化) / `SAI_NULL_OBJECT_ID` (無効化) |

#### 3c. `sai_samplepacket_api->remove_samplepacket()`

セッション削除 (sfloworch.cpp:49): 参照カウント (`ref_count`) がゼロになったとき呼び出す。

### 4. sflowmgrd → OS / hsflowd サービス制御

`sflowHandleService(enable)` (sflowmgr.cpp:51) が SFLOW.admin_state 変更をトリガーにシステムコマンドを発行:

| 条件 | コマンド | 効果 |
|------|---------|------|
| `admin_state=up` | `service hsflowd restart` | hsflowd プロセス起動・再起動 |
| `admin_state=down` | `service hsflowd stop` | hsflowd プロセス停止 |

> hsflowd は sFlow パケットを実際にコレクタへ送信するユーザースペースデーモン。CONFIG_DB の変更が APPL_DB 経由で SAI に到達するハードウェア経路とは独立して動作する。

---

## 副次書込 サマリテーブル

| トリガー | consumer | 対象 DB | テーブル | 書込内容 | evidence |
|---------|---------|--------|---------|---------|---------|
| `SFLOW|global` SET | sflowmgrd | APPL_DB | `SFLOW_TABLE` | フィールドをそのまま転送 | sflowmgr.cpp:468 |
| `SFLOW|global` DEL | sflowmgrd | APPL_DB | `SFLOW_TABLE` | キー削除 | sflowmgr.cpp:550 |
| `SFLOW|global` admin_state=up/down | sflowmgrd | APPL_DB | `SFLOW_SESSION_TABLE` | 全ポートの admin_state/rate/direction | sflowmgr.cpp:246,250 |
| `SFLOW_SESSION|<port>` SET (gEnable=true) | sflowmgrd | APPL_DB | `SFLOW_SESSION_TABLE` | admin_state / sample_rate / sample_direction | sflowmgr.cpp:533 |
| `SFLOW_SESSION|<port>` DEL | sflowmgrd | APPL_DB | `SFLOW_SESSION_TABLE` | キー削除 | sflowmgr.cpp:567 |
| `SFLOW_SESSION|all` SET | sflowmgrd | APPL_DB | `SFLOW_SESSION_TABLE` | 全ポート一斉更新 | sflowmgr.cpp:513 |
| PORT 速度変化 (oper_speed) | sflowmgrd | APPL_DB | `SFLOW_SESSION_TABLE` | sample_rate 自動更新 | sflowmgr.cpp:211 |
| APPL_DB `SFLOW_SESSION_TABLE` SET (SflowOrch) | SflowOrch | ASIC_DB | SAI samplepacket | create_samplepacket + SAI_PORT_ATTR_{INGRESS,EGRESS}_SAMPLEPACKET_ENABLE | sfloworch.cpp:29,122,139 |
| APPL_DB `SFLOW_SESSION_TABLE` DEL (SflowOrch) | SflowOrch | ASIC_DB | SAI samplepacket | remove_samplepacket + SAI_NULL_OBJECT_ID でポート属性リセット | sfloworch.cpp:49,165,183 |
| `SFLOW|global` admin_state 変化 | sflowmgrd | OS | hsflowd service | restart / stop | sflowmgr.cpp:58,62 |

---

## 結論

SFLOW テーブルは `sflowmgrd` 経由で以下の副次書込を発生させる:
1. **APPL_DB `SFLOW_TABLE`**: CONFIG_DB フィールドをそのまま転送
2. **APPL_DB `SFLOW_SESSION_TABLE`**: ポートごとのサンプリング設定（グローバル/ローカル/速度ベース）
3. **ASIC_DB (SAI)**: `sai_samplepacket_api` でハードウェアサンプリングセッションを作成・削除し、`sai_port_api` でポートに SAI_PORT_ATTR_{INGRESS,EGRESS}_SAMPLEPACKET_ENABLE を設定
4. **OS hsflowd サービス**: admin_state 変化時に `service hsflowd restart/stop` を発行
