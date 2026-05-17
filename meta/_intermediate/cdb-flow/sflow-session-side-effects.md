# SFLOW_SESSION 副次 DB 書込抽出 (Phase F)

## ソース
- `sonic-swss/cfgmgr/sflowmgr.cpp`
- `sonic-swss/orchagent/sfloworch.cpp`

## 調査方針

`SFLOW_SESSION` テーブルへの書込をトリガーとして他 DB・テーブルへ副次的に書き込まれる経路を `sflowmgr.cpp` / `sfloworch.cpp` から網羅調査。

---

## 副次書込 一覧

### 1. sflowmgrd → APPL_DB `SFLOW_SESSION_TABLE` (APP_SFLOW_SESSION_TABLE_NAME)

`SFLOW_SESSION` の SET/DEL イベントを受けた `SflowMgr::doTask()` が `m_appSflowSessionTable.set()` / `.del()` を呼び出す。

#### 1a. `SFLOW_SESSION|<port>` SET 時

`sflowCheckAndFillValues()` でフィールドを補完後、グローバル admin_state が有効（`m_gEnable=true`）の場合のみ APPL_DB に書き込む (sflowmgr.cpp:531-534)。

| フィールド | 書込値 | evidence |
|-----------|-------|---------|
| `admin_state` | ローカル設定値、なければグローバルデフォルト `"up"` | sflowmgr.cpp:361-369 |
| `sample_rate` | ローカル設定値、なければ `findSamplingRate()` 結果 | sflowmgr.cpp:345-358 |
| `sample_direction` | ローカル設定値、なければ `m_gDirection` ("rx") | sflowmgr.cpp:373-382 |

#### 1b. `SFLOW_SESSION|<port>` DEL 時

`m_appSflowSessionTable.del(key)` でポートエントリを削除 (sflowmgr.cpp:567)。続いて `m_intfAllConf=true` であれば `sflowGetGlobalInfo()` でグローバル設定を再投入する (sflowmgr.cpp:576-581)。

| トリガー | 副次書込 | evidence |
|---------|--------|---------|
| `SFLOW_SESSION\|<port>` DEL | `SFLOW_SESSION_TABLE` キー削除 | sflowmgr.cpp:567 |
| DEL 後 `m_intfAllConf=true` の場合 | グローバル設定で同ポートを再 SET | sflowmgr.cpp:578-580 |

#### 1c. `SFLOW_SESSION|all` SET 時

`m_intfAllConf` / `m_intfAllDir` を更新し、`m_gEnable=true` のとき `sflowHandleSessionAll()` を呼び出して全ポートの `SFLOW_SESSION_TABLE` を一斉更新 (sflowmgr.cpp:511-514)。

- ポートに local_rate_cfg / local_admin_cfg / local_dir_cfg がある場合は `sflowGetPortInfo()` でローカル設定を優先 (sflowmgr.cpp:228-243)
- ローカル設定がないポートは `sflowGetGlobalInfo()` でグローバル値を使用 (sflowmgr.cpp:244)

#### 1d. `SFLOW_SESSION|all` DEL 時

`m_intfAllConf=false` だった場合のみ、`m_gEnable=true` であれば `sflowHandleSessionAll(true, m_gDirection)` で全ポートを再有効化 (sflowmgr.cpp:558-563)。その後 `m_intfAllConf=true` にリセット (sflowmgr.cpp:563)。

### 2. SflowOrch → ASIC_DB via SAI (APPL_DB `SFLOW_SESSION_TABLE` 経由)

`SFLOW_SESSION_TABLE` の書込をトリガーに SflowOrch が SAI API を呼び出す。

#### 2a. `sai_samplepacket_api->create_samplepacket()`

新レートのセッション作成 (sfloworch.cpp:29)。セッションは `m_sflowRateSampleMap[rate]` で参照カウント管理し、同レートのポートがセッションを共有する。

```
attr.id = SAI_SAMPLEPACKET_ATTR_SAMPLE_RATE
attr.value.u32 = rate
sai_samplepacket_api->create_samplepacket(&session_id, gSwitchId, 1, &attr)
```

#### 2b. `sai_port_api->set_port_attribute()` — ポート samplepacket 設定

| 方向 | SAI 属性 | 有効化時 | 無効化時 |
|------|---------|--------|--------|
| `rx` / `both` | `SAI_PORT_ATTR_INGRESS_SAMPLEPACKET_ENABLE` | `session_id` | `SAI_NULL_OBJECT_ID` |
| `tx` / `both` | `SAI_PORT_ATTR_EGRESS_SAMPLEPACKET_ENABLE` | `session_id` | `SAI_NULL_OBJECT_ID` |

evidence: sfloworch.cpp:119–150 (`sflowAddPort`), sfloworch.cpp:161–195 (`sflowDelPort`)

#### 2c. `sai_samplepacket_api->remove_samplepacket()`

参照カウントがゼロになったとき呼び出す (sfloworch.cpp:49)。レート変更時は旧セッション destroy → 新セッション create の順で実行 (sfloworch.cpp:95-106)。

---

## 副次書込 サマリテーブル

| トリガー | consumer | 対象 DB | テーブル | 書込内容 | evidence |
|---------|---------|--------|---------|---------|---------|
| `SFLOW_SESSION\|<port>` SET (gEnable=true) | sflowmgrd | APPL_DB | `SFLOW_SESSION_TABLE` | admin_state / sample_rate / sample_direction | sflowmgr.cpp:533 |
| `SFLOW_SESSION\|<port>` DEL | sflowmgrd | APPL_DB | `SFLOW_SESSION_TABLE` | キー削除 | sflowmgr.cpp:567 |
| DEL 後 intfAllConf=true | sflowmgrd | APPL_DB | `SFLOW_SESSION_TABLE` | グローバル設定で再 SET | sflowmgr.cpp:578-580 |
| `SFLOW_SESSION\|all` SET (gEnable=true) | sflowmgrd | APPL_DB | `SFLOW_SESSION_TABLE` | 全ポート一斉更新 | sflowmgr.cpp:513 |
| `SFLOW_SESSION\|all` DEL | sflowmgrd | APPL_DB | `SFLOW_SESSION_TABLE` | 全ポート再有効化 (条件付) | sflowmgr.cpp:558-563 |
| APPL_DB `SFLOW_SESSION_TABLE` SET | SflowOrch | ASIC_DB | SAI samplepacket | create_samplepacket + INGRESS/EGRESS 属性 SET | sfloworch.cpp:29,122,139 |
| APPL_DB `SFLOW_SESSION_TABLE` DEL | SflowOrch | ASIC_DB | SAI samplepacket | remove_samplepacket + SAI_NULL_OBJECT_ID でポートリセット | sfloworch.cpp:49,165,183 |

---

## 結論

SFLOW_SESSION テーブルは `sflowmgrd` 経由で以下の副次書込を発生させる:

1. **APPL_DB `SFLOW_SESSION_TABLE`**: per-port の admin_state / sample_rate / sample_direction を転送・補完して書込む。DEL 後はグローバル設定が再投入される場合がある
2. **ASIC_DB (SAI)**: SflowOrch が `sai_samplepacket_api` でハードウェアサンプリングセッションを管理し、`sai_port_api` で `SAI_PORT_ATTR_{INGRESS,EGRESS}_SAMPLEPACKET_ENABLE` を設定する
