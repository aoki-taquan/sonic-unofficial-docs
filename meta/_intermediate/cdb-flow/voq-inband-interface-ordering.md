# VOQ_INBAND_INTERFACE テーブル — 書込み順依存調査メモ (Phase B)

調査日: 2026-05-16
調査対象:
- `sonic-swss/cfgmgr/intfmgr.cpp`
- `sonic-swss/cfgmgr/intfmgrd.cpp`
- `sonic-swss/orchagent/voqorch.cpp`

---

## 1. 他テーブル先行必須

### VOQ_INBAND_INTERFACE は直接 APP_DB へ relay

`intfmgrd` は `VOQ_INBAND_INTERFACE` を購読する（`intfmgrd.cpp:34`）が、単一キー（属性ロウ）の SET は `doIntfGeneralTask()` を呼ばず**即 APP_DB に relay** する（`intfmgr.cpp:1195-1204`）。

```cpp
// intfmgr.cpp:1195-1203
if((table_name == CFG_VOQ_INBAND_INTERFACE_TABLE_NAME) &&
        (op == SET_COMMAND))
{
    //No further processing needed. Just relay to orchagent
    m_appIntfTableProducer.set(keys[0], data);
    m_stateIntfTable.hset(keys[0], "vrf", "");
    it = consumer.m_toSync.erase(it);
    continue;
}
```

この直接 relay パスでは `isIntfStateOk()` を呼ばないため、PORT / LAG / VLAN の STATE_DB ready は**不要**。

### IP プレフィクスロウは通常パス

2-key（`<alias>|<ip_prefix>`）は `doIntfAddrTask()` を経由する（`intfmgr.cpp:1216-1224`）。このパスは `isIntfCreated(alias)` を確認するため、属性ロウの STATE_DB 書込みが先に必要。

| 先行テーブル / 条件 | 依存の内容 | コード根拠 |
|------------------|-----------|-----------|
| VOQ 環境有効（`switch_type == "voq"`） | `VoqOrch` が起動し APP_DB を処理する | `orchagent/voqorch.cpp` |
| 属性ロウの STATE_INTERFACE_TABLE エントリ | `isIntfCreated()` が false → IP prefix ロウをスキップ | `intfmgr.cpp:1115` |

---

## 2. VOQ_INBAND_INTERFACE 設定順序

```
1. CONFIG_DB に VOQ_INBAND_INTERFACE|<alias> (属性ロウ) 投入
   → intfmgrd が即 APP_DB INTF_TABLE に relay
   → STATE_INTERFACE_TABLE に hset(alias, "vrf", "")
2. CONFIG_DB に VOQ_INBAND_INTERFACE|<alias>|<ip_prefix> (IP prefix ロウ) 投入
   → doIntfAddrTask() パス (isIntfCreated 確認後)
   → ip address add ... dev <alias>
   → APP_DB INTF_TABLE に relay
3. VoqOrch (orchagent) が APP_DB INTF_TABLE を購読し SAI RIF を作成
```

---

## 3. non-VOQ 環境での動作

`switch_type != "voq"` の環境では `VoqOrch` が起動しない（または処理をスキップする）ため、APP_DB に relay されても SAI 処理は発生しない。MGMT 環境への誤投入は無害だが無効。

---

## 4. まとめ（書込み順依存一覧）

| 依存カテゴリ | 必須順序 | ソース |
|------------|---------|-------|
| PORT / LAG / VLAN → VOQ_INBAND | **依存なし**（属性ロウは直接 relay） | `intfmgr.cpp:1195-1204` |
| 属性ロウ → IP prefix | 属性ロウ SET → STATE_INTF 反映後に IP prefix SET | `intfmgr.cpp:1115` |
| VOQ 環境前提 | `switch_type == "voq"` でのみ VoqOrch が SAI RIF 作成 | `orchagent/voqorch.cpp` |
