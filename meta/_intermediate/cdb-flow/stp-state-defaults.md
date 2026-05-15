# STATE_DB STP_TABLE — Phase A デフォルト調査メモ

## 調査対象テーブル

- `STP_TABLE` (key: `GLOBAL`) — STATE_DB に書かれる STP 最大インスタンス数フィールド

## 主要ソース

- `sonic-swss/orchagent/stporch.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/stporch.h` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/cfgmgr/stpmgr.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/cfgmgr/stpmgr.h` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss-common/common/schema.h` (SHA: 158de8d3463ff4b841653f6d57190bb142b80d9c)

---

## 1. STATE_DB STP_TABLE の役割と書き込み主体

`STATE_STP_TABLE_NAME = "STP_TABLE"` (schema.h:445)

書き込み: `StpOrch::updateMaxStpInstance()` (stporch.cpp:603-617)
読み取り: `StpMgr::getStpMaxInstances()` (stpmgr.cpp:1381-1413)

### 書き込みタイミング

`StpOrch` コンストラクタ初期化時に SAI API `SAI_SWITCH_ATTR_MAX_STP_INSTANCE` から最大インスタンス数を取得し、そこから -1 した値を `STP_TABLE|GLOBAL` に書き込む:

```cpp
// stporch.cpp:603-617
bool StpOrch::updateMaxStpInstance(uint32_t max_stp_instances)
{
    m_maxStpInstance = (sai_uint16_t)max_stp_instances - 1;
    // SAI から取得した最大値 - 1 を上限として格納

    vector<FieldValueTuple> tuples;
    FieldValueTuple tuple("max_stp_inst", to_string(m_maxStpInstance));
    tuples.push_back(tuple);
    m_stpTable->set("GLOBAL", tuples);
    return true;
}
```

### 読み取りタイミングと待機ループ

`stpmgrd` 起動時に `StpMgr::getStpMaxInstances()` が `STATE_DB` の `STP_TABLE|GLOBAL` を最大 60 秒ポーリングして `max_stp_inst` を取得する。取得できない場合は `STP_DEFAULT_MAX_INSTANCES = 255` をフォールバック値として使用:

```cpp
// stpmgr.cpp:1381-1413
uint16_t StpMgr::getStpMaxInstances(void)
{
    // ...
    while(max_delay)  // max_delay = 60
    {
        if (m_stateStpTable.get("GLOBAL", vmEntry))
        {
            for (auto entry : vmEntry)
                if (entry.first == "max_stp_inst")
                    max_stp_instances = (uint16_t)stoi(entry.second.c_str());
            break;
        }
        sleep(1);
        max_delay--;
    }
    if(max_stp_instances == 0)
        max_stp_instances = STP_DEFAULT_MAX_INSTANCES;  // = 255
    return max_stp_instances;
}
```

---

## 2. フィールド詳細

| フィールド | キー | 型 | 書込み主体 | コード由来デフォルト | 説明 |
|---|---|---|---|---|---|
| `max_stp_inst` | `GLOBAL` | uint16 (文字列) | `orchagent/StpOrch` | **HW依存** (`SAI_SWITCH_ATTR_MAX_STP_INSTANCE - 1`) | STP インスタンス最大数 (HW 能力から自動設定); stpmgrd 未受信時は `255` フォールバック |

---

## 3. SAI 由来の値 — ハードウェア依存

`max_stp_inst` はスイッチ ASIC の SAI から `SAI_SWITCH_ATTR_MAX_STP_INSTANCE` 属性として取得する:

```cpp
// stporch.cpp:28-38
attr.id = SAI_SWITCH_ATTR_MAX_STP_INSTANCE;
attrs.push_back(attr);
status = sai_switch_api->get_switch_attribute(gSwitchId, (uint32_t)attrs.size(), attrs.data());
if (status == SAI_STATUS_SUCCESS)
{
    updateMaxStpInstance(attrs[1].value.u32);
}
```

SAI 取得が失敗した場合、`updateMaxStpInstance()` は呼ばれず、`STP_TABLE|GLOBAL` への書き込みも行われない。この場合 `stpmgrd` は 60 秒待機後にフォールバック値 `255` を使用する。

---

## 4. 暗黙制約・注意点

1. **STP_TABLE はスタンドアロン**: CONFIG_DB の `STP`, `STP_VLAN`, `STP_PORT` テーブルとは別で、State DB に 1 エントリ (`GLOBAL`) のみ存在する
2. **HW 能力駆動**: `max_stp_inst` はコードで固定されておらず、ASIC の SAI 属性から動的に決まる
3. **-1 補正**: SAI が返す最大数から -1 した値が格納される (STP インスタンス ID は 0-indexed のため)
4. **stpmgrd の 60 秒タイムアウト**: orchagent が STP_TABLE を書き込む前に stpmgrd が起動した場合、60 秒待機してフォールバック値を使用する (startup race condition)
5. **state フィールド不存在**: `STP_TABLE|GLOBAL` には `state` フィールドはなく、`max_stp_inst` のみ

---

## ソース証跡

| ファイル | 行番号 | 内容 |
|---|---|---|
| `schema.h` | 445 | `STATE_STP_TABLE_NAME = "STP_TABLE"` |
| `stporch.cpp` | 26 | `m_stpTable` を `STATE_STP_TABLE_NAME` で初期化 |
| `stporch.cpp` | 32-38 | `SAI_SWITCH_ATTR_MAX_STP_INSTANCE` 取得 |
| `stporch.cpp` | 603-617 | `updateMaxStpInstance()` — STATE_DB への書き込み |
| `stpmgr.cpp` | 33 | `m_stateStpTable` を `STATE_STP_TABLE_NAME` で初期化 |
| `stpmgr.cpp` | 1381-1413 | `getStpMaxInstances()` — 60 秒ポーリング読み取り |
| `stpmgr.h` | 38 | `STP_DEFAULT_MAX_INSTANCES = 255` |
