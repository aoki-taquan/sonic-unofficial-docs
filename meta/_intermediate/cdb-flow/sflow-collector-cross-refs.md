# SFLOW_COLLECTOR — Phase C 暗黙参照（テーブル間依存）調査ノート

**調査日**: 2026-05-17  
**調査範囲**: `sonic-swss/cfgmgr/sflowmgrd.cpp`, `sflowmgr.cpp`, `sflowmgr.h`, `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-sflow.yang`, `sonic-utilities/config/main.py`, `sonic-utilities/show/sflow.py`

---

## 1. SFLOW_COLLECTOR を直接購読するプロセス

`sflowmgrd.cpp:31-41` で登録される TableConnector リスト:

```cpp
TableConnector conf_port_table(&cfgDb, CFG_PORT_TABLE_NAME);         // PORT
TableConnector state_port_table(&stateDb, STATE_PORT_TABLE_NAME);    // STATE_DB PORT
TableConnector conf_sflow_table(&cfgDb, CFG_SFLOW_TABLE_NAME);       // SFLOW
TableConnector conf_sflow_session_table(&cfgDb, CFG_SFLOW_SESSION_TABLE_NAME); // SFLOW_SESSION
```

**結論**: `SFLOW_COLLECTOR` テーブルは sflowmgrd の TableConnector に含まれていない。sflowmgrd は SFLOW_COLLECTOR を直接購読しない。

---

## 2. YANG レベルの依存

`sonic-sflow.yang:85-97`:

```yang
leaf collector_vrf {
    must "(current() != 'mgmt') or (/mvrf:sonic-mgmt_vrf/mvrf:MGMT_VRF_CONFIG/mvrf:vrf_global/mvrf:mgmtVrfEnabled = 'true')" {
        error-message "Must condition not satisfied. Try enable Management VRF.";
    }
    type string {
        pattern "mgmt|default";
    }
}
```

`collector_vrf = 'mgmt'` を指定する場合は `sonic-mgmt_vrf` モジュール（MGMT_VRF_CONFIG テーブル）の `vrf_global.mgmtVrfEnabled = 'true'` が必須。YANG バリデーション時に評価される。

---

## 3. CLI（config/main.py）での参照

`config/main.py:9352`: `config_db.get_table('SFLOW_COLLECTOR')` でテーブル全体を読み込みエントリ数チェック（上限 2 件）。  
`config/main.py:9359-9361`: `config_db.mod_entry('SFLOW_COLLECTOR', name, {...})` で書き込み。  
`config/main.py:9383`: `config_db.set_entry('SFLOW_COLLECTOR', name, None)` で削除。

---

## 4. show コマンド（show/sflow.py）での参照

`show/sflow.py:89`: `config_db.get_table('SFLOW_COLLECTOR')` で全コレクタ情報を読み取り表示。

---

## 5. hsflowd との関係

hsflowd (sflowd container) は起動時に `/etc/hsflowd.conf` を読み込む。この conf ファイルは CONFIG_DB の SFLOW_COLLECTOR エントリから生成される（起動スクリプトによる変換）。hsflowd 自体は CONFIG_DB に直接アクセスしない。SFLOW_COLLECTOR エントリ変更時は hsflowd 再起動が必要（Phase B で記述済み）。

---

## 6. 暗黙参照サマリ表

| 参照先 | 参照種別 | 条件 | コード箇所 |
|--------|---------|------|-----------|
| `MGMT_VRF_CONFIG\|vrf_global` | YANG must 制約（必須依存） | `collector_vrf = 'mgmt'` のとき | `sonic-sflow.yang:86-88` |
| `SFLOW\|global` | 実装依存（hsflowd 起動制御） | SFLOW_COLLECTOR 変更の実効化に必要 | `sflowmgr.cpp:456-459` |

---

## 7. 注意事項

- sflowmgrd は SFLOW_COLLECTOR を購読しないため、SFLOW_COLLECTOR への書き込みは即座に hsflowd へは伝播しない
- MGMT_VRF_CONFIG への参照は YANG バリデーション時のみ（実装コードに MGMT_VRF_CONFIG 参照なし）
- `show sflow` コマンドは CONFIG_DB の SFLOW_COLLECTOR を直接 read-only 参照する
