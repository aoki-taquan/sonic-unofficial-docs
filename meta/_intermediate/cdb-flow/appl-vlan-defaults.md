# APPL_DB VLAN_TABLE / VLAN_MEMBER_TABLE フィールドのコード由来デフォルト (Phase A)

調査対象: `docs/reference/config-db/appl-vlan.md`

## ソース

- `sonic-swss/cfgmgr/vlanmgr.cpp` — 書き込み主体 (vlanmgrd)
- `sonic-swss/orchagent/portsorch.cpp` — APPL_DB 読み取り / consumer 側
- `sonic-swss-common/common/schema.h` — テーブル名定数定義

sha: sonic-swss master (local shallow clone)

---

## VLAN_TABLE フィールドとデフォルト

`vlanmgr.cpp` L354-L437 の `doVlanTask()` 書き込みロジックから:

| フィールド | C++ 初期値 | 条件 | 出典 |
|-----------|-----------|------|------|
| `admin_status` | `""` (空) | CONFIG_DB に存在する場合上書き。**省略時は fvVector 空ガード** (L421-L426) で `"up"` を強制挿入 | vlanmgr.cpp:424 |
| `mtu` | `DEFAULT_MTU_STR` = `"9100"` | CONFIG_DB に `mtu` フィールドがあれば上書き (L400)。APPL_DB には常に書かれる (L428) | vlanmgr.cpp:19,357,428 |
| `mac` | `gMacAddress.to_string()` | CONFIG_DB に `mac` フィールドがあれば上書き (L411)。APPL_DB には常に書かれる (L431) | vlanmgr.cpp:358,431 |
| `host_ifname` | `""` (空文字列) | CONFIG_DB に `host_ifname` があれば上書き (L418)。常に APPL_DB に書かれる (L434) | vlanmgr.cpp:359,434 |
| `members@` | (CONFIG_DB のみ、未転送) | APPL_DB には書かれない。`processUntaggedVlanMembers()` 経由で VLAN_MEMBER_TABLE に反映 | vlanmgr.cpp:451-453 |

### 注記

- `admin_status` 省略時: `fvVector.empty()` 判定 (L421) で `"up"` が APPL_DB に強制注入される。
- `mtu` 省略時: 変数初期化値 `DEFAULT_MTU_STR = "9100"` (L357) がそのまま APPL_DB に書かれる。
- `mac` 省略時: `gMacAddress`（スイッチ MAC）がそのまま APPL_DB に書かれる。`gMacAddress` が未初期化の場合 vlanmgrd はタスク全体を保留する (L316-L321)。
- `host_ifname` 省略時: 空文字列 `""` が APPL_DB に書かれる。portsorch.cpp:5820 でチェック → `createVlanHostIntf()` は空文字列の場合スキップ。

---

## VLAN_MEMBER_TABLE フィールドとデフォルト

`vlanmgr.cpp` L593-L724 の `doVlanMemberTask()` 書き込みロジックから:

| フィールド | C++ 初期値 | 条件 | 出典 |
|-----------|-----------|------|------|
| `tagging_mode` | `"untagged"` | CONFIG_DB フィールドが存在する場合上書き (L648-L655)。`processUntaggedVlanMembers()` 経由 (L573) では常に `"untagged"` ハードコード | vlanmgr.cpp:648 |
| `dynamic` | 存在しない | 通常経路では注入されない。PAC 経路 (`doVlanPacVlanMemberTask()`) のみ `"yes"` を注入 | vlanmgr.cpp:887 |

### VLAN_MEMBER_TABLE 書き込みロジック

```cpp
// vlanmgr.cpp:672
m_appVlanMemberTableProducer.set(key, kfvFieldsValues(t));
```

CONFIG_DB の生フィールドをそのまま APPL_DB に転送する。`tagging_mode` が CONFIG_DB に存在しない場合 APPL_DB にも書かれないが、
portsorch 側 (portsorch.cpp:5916) が再度 `"untagged"` で fallback するため二重の暗黙補完が発生する。

---

## orchagent (portsorch) consumer 側デフォルト

`portsorch.cpp` L5760-L5830 の VLAN_TABLE 処理:

```cpp
uint32_t mtu = 0;         // フィールド不在 → 0 (mtu 更新なし)
MacAddress mac;            // フィールド不在 → 空 MAC (mac 更新なし)
string hostif_name = "";   // フィールド不在 → 空 → createVlanHostIntf() スキップ
```

`portsorch.cpp` L5915-L5928 の VLAN_MEMBER_TABLE 処理:

```cpp
string tagging_mode = "untagged";  // フィールド不在 → "untagged" fallback
```

---

## テーブル名定数

`sonic-swss-common/common/schema.h`:

```
#define APP_VLAN_TABLE_NAME        "VLAN_TABLE"
#define APP_VLAN_MEMBER_TABLE_NAME "VLAN_MEMBER_TABLE"
```

---

## key 構造

```
VLAN_TABLE|<vlan_name>                         (例: VLAN_TABLE|Vlan100)
VLAN_MEMBER_TABLE|<vlan_name>|<port_alias>     (例: VLAN_MEMBER_TABLE|Vlan100|Ethernet0)
```

`<vlan_name>` は `Vlan<id>` 形式。`Vlan` プレフィクスがない場合 vlanmgrd がエントリを破棄する (vlanmgr.cpp:332-336)。

---

## PAC 経路の hidden フィールド

`doVlanPacVlanMemberTask()` (vlanmgr.cpp:887) は PAC 制御の VLAN_MEMBER_TABLE エントリに
`{"dynamic": "yes"}` を注入する。このフィールドは:

- YANG 定義なし
- CONFIG_DB には存在しない
- APPL_DB VLAN_MEMBER_TABLE のみに存在する隠しフィールド
