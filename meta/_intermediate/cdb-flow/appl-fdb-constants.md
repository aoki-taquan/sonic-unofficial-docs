# APPL_DB FDB_TABLE — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-swss/orchagent/fdborch.cpp` (FDB type 文字列、フィールド名、SAI mapping、saved_fdb キー)
- `sonic-swss/orchagent/fdborch.h` (`FdbOrigin` 列挙、`fdborch_pri`、`type` × `origin` 組合せコメント)
- `sonic-swss/orchagent/orchdaemon.cpp` (STATE_DB テーブル名の bind)
- `sonic-swss-common/common/schema.h` (テーブル名マクロの実値)

---

## 1. テーブル名マクロの実値

| マクロ | 値 (実文字列) | 用途 | ソース |
|--------|--------------|------|--------|
| `APP_FDB_TABLE_NAME` | `"FDB_TABLE"` | APPL_DB の動的/静的 FDB テーブル名 | schema.h L52 |
| `APP_VXLAN_FDB_TABLE_NAME` | `"VXLAN_FDB_TABLE"` | VXLAN_ADVERTIZED origin の入力テーブル | schema.h L87 |
| `APP_MCLAG_FDB_TABLE_NAME` | `"MCLAG_FDB_TABLE"` | MCLAG_ADVERTIZED origin の入力テーブル | schema.h L118 |
| `STATE_FDB_TABLE_NAME` | `"FDB_TABLE"` | STATE_DB 側ローカル MAC 書き戻し (`m_fdbStateTable`) | schema.h L426 |
| `STATE_MCLAG_REMOTE_FDB_TABLE_NAME` | `"MCLAG_REMOTE_FDB_TABLE"` | STATE_DB 側 MCLAG advertise 用 (`m_mclagFdbStateTable`) | schema.h L443 |

bind 箇所: `orchdaemon.cpp:233-235` で `TableConnector stateDbFdb(m_stateDb, STATE_FDB_TABLE_NAME)` / `TableConnector stateMclagDbFdb(m_stateDb, STATE_MCLAG_REMOTE_FDB_TABLE_NAME)` として渡される。

---

## 2. FDB type 文字列 (リテラル定数)

`fdborch.cpp` 内に enum 化されておらず、文字列リテラルで比較される。

| 値 | 出現箇所 (代表) | 意味 |
|----|----------------|------|
| `"dynamic"` | L288, L389, L408, L770 (default), L830 assert, L1395, L1431, L1435, L1442, L1489, L1562, L1579 | カーネル学習 / `swssconfig` の動的 MAC |
| `"static"` | L446, L448, L830 assert, L1359, L1370, L1383, L1431, L1750 | 静的 MAC (CONFIG_DB `FDB` / VlanMgr 由来) |
| `"dynamic_local"` | L830 assert, L875, L1395, L1431, L1552, L1572, L1578 | MCLAG ピア由来のローカル aging 用内部値 |

入力検証は `fdborch.cpp:830` の単一 `assert`:

```cpp
assert(type == "dynamic" || type == "dynamic_local" || type == "static" );
```

無効値は debug ビルドでクラッシュ、NDEBUG では `1431/1435` の三項演算子で `SAI_FDB_ENTRY_TYPE_STATIC` にフォールバック。

---

## 3. FdbOrigin 列挙 (`fdborch.h:9-15`)

```cpp
enum FdbOrigin {
    FDB_ORIGIN_INVALID = 0,
    FDB_ORIGIN_LEARN = 1,
    FDB_ORIGIN_PROVISIONED = 2,
    FDB_ORIGIN_VXLAN_ADVERTIZED = 4,
    FDB_ORIGIN_MCLAG_ADVERTIZED = 8
};
```

| 値 | 数値 | 意味 | 設定箇所 |
|----|-----|------|---------|
| `FDB_ORIGIN_INVALID` | `0` | 初期値・未確定 | L78, L1330 |
| `FDB_ORIGIN_LEARN` | `1` | SAI ハードウェア学習通知 | L113 (`fdbdata.origin = FDB_ORIGIN_LEARN`), L1561 (dynamic_local → LEARN 格上げ) |
| `FDB_ORIGIN_PROVISIONED` | `2` | APP_FDB_TABLE 直書込 (default) | L716 (`doTask()` 冒頭 default), `removeFdbEntry` default 引数 |
| `FDB_ORIGIN_VXLAN_ADVERTIZED` | `4` | `APP_VXLAN_FDB_TABLE` 由来 | L719-721 |
| `FDB_ORIGIN_MCLAG_ADVERTIZED` | `8` | `APP_MCLAG_FDB_TABLE` 由来 | L724-726 |

フラグ値だが、現コードでは bit-OR せず単一値として比較される (将来拡張用に 2 のべき)。

### type × origin 有効組合せ (`fdborch.h:53-61` コメント)

| type | origin | 妥当性 |
|------|--------|-------|
| `"dynamic"` | `LEARN` | dynamically learnt |
| `"dynamic"` | `PROVISIONED` | swssconfig 経由の動的投入 |
| `"dynamic"` | `VXLAN_ADVERTIZED` | VXLAN 動的 advertise |
| `"static"` | `LEARN` | **Invalid** (コメントで明示) |
| `"static"` | `PROVISIONED` | static 投入 |
| `"static"` | `VXLAN_ADVERTIZED` / `MCLAG_ADVERTIZED` | EVPN/MCLAG advertise |
| `"dynamic_local"` | `MCLAG_ADVERTIZED` | MCLAG aging 用 |

---

## 4. APPL_DB フィールド名 (リテラル)

`doTask()` L779-822 で `fvField(i)` と文字列比較される。

| フィールド名 | 出現箇所 | 適用 origin |
|-------------|---------|-----------|
| `"port"` | L779, L133 (state 書き戻し fvs) | 全 origin |
| `"type"` | L784, L134, L1579 | 全 origin |
| `"discard"` | L788 | 全 origin (PAC/802.1X 用) |
| `"remote_vtep"` | L795 | `VXLAN_ADVERTIZED` のみ |
| `"esi"` | L811 | `VXLAN_ADVERTIZED` のみ |
| `"vni"` | L816 | `VXLAN_ADVERTIZED` のみ |

`"discard"` の真偽値: `"true"` / `"false"` 文字列比較 (L1497 `fdbData.discard == "true"` → `SAI_PACKET_ACTION_DROP`)。

---

## 5. saved_fdb_entries キャッシュキー

`fdborch.h` で宣言 (型: `map<string, vector<SavedFdbEntry>>`)。**キーはポート別名 (`Port::m_alias`)** であり、VLAN や MAC は値側 vector の `SavedFdbEntry` フィールドに保持される。

| 操作 | コード位置 |
|------|----------|
| push (PORT 未準備) | L1301 `saved_fdb_entries[port_name].push_back(...)` |
| push (VLAN メンバー未満足) | L1316 同上 |
| move + clear (replay 起動時) | L1254-1255 `auto fdb_list = std::move(...)` |
| 個別 erase | L1271 push back (replay 失敗時の再保留) |
| 全 port 走査削除 | `deleteFdbEntryFromSavedFDB()` L1743 以降 (port 名空文字なら全 port) |

`SavedFdbEntry` 構造体 (`fdborch.h`):

```cpp
struct SavedFdbEntry {
    MacAddress mac;
    unsigned short vlanId;
    FdbData fdbData;
};
```

- replay 時に `SavedFdbEntry::fdbData.type` が見られるため、push 時に正しい type を入れる必要がある。
- `deleteFdbEntryFromSavedFDB()` L1750 は比較時のダミーで `entry.fdbData.type = "static"` を入れているが、コメント `/* Below members are unused during delete compare */` の通り **比較ではなく vector iteration 上の placeholder**。

---

## 6. SAI 列挙マッピング (orchagent 内固定)

| `type` × `origin` | SAI 型 | コード位置 |
|-------------------|--------|----------|
| `"dynamic_local"` + `MCLAG_ADVERTIZED` | `SAI_FDB_ENTRY_TYPE_DYNAMIC` (aging 効かせるため) | L1431 三項 |
| 上記以外で `MCLAG_ADVERTIZED` | `SAI_FDB_ENTRY_TYPE_STATIC` | L1431 三項 false 側 |
| `"dynamic"` (LEARN / PROVISIONED / VXLAN) | `SAI_FDB_ENTRY_TYPE_DYNAMIC` | L1435 三項 |
| `"static"` | `SAI_FDB_ENTRY_TYPE_STATIC` | L1435 三項 false 側 |
| `discard == "true"` | `SAI_PACKET_ACTION_DROP` | L1497 |
| `discard == "false"` (or 不在) | `SAI_PACKET_ACTION_FORWARD` | L1497 |

### flush 系 SAI attr (隠れ定数)

| attr id | value | コード位置 |
|---------|------|----------|
| `SAI_FDB_FLUSH_ATTR_ENTRY_TYPE` | `SAI_FDB_FLUSH_ENTRY_TYPE_DYNAMIC` | L949-950, L1122-1123, L1161-1162 |
| `SAI_FDB_FLUSH_ATTR_BRIDGE_PORT_ID` | port OID | L1109 |
| `SAI_FDB_FLUSH_ATTR_BV_ID` | vlan OID | L1116, L1159 |

flush は **動的エントリのみ**対象 (STATIC は flush 不可) という暗黙の制約がコードに焼き付いている。

---

## 7. その他の固定値

| 値 | 名前 | 用途 | ソース |
|----|-----|------|--------|
| `20` | `FdbOrch::fdborch_pri` | Orch スケジューラ優先度 (PortsOrch などより低い) | fdborch.cpp L25 (`const int FdbOrch::fdborch_pri = 20;`) |
| `SUBJECT_TYPE_FDB_FLUSH_CHANGE` | notify subject | flush 発生時の observer 通知 | L1199 |
| `SUBJECT_TYPE_VLAN_MEMBER_CHANGE` | 購読 subject | VLAN_MEMBER 変化で `updateVlanMember()` | L655 (Phase B でも参照) |

---

## 8. YANG / CONFIG_DB で管理されない箇所

- `"dynamic_local"` という type 値は YANG `sonic-fdb` には存在しない (`static`/`dynamic` のみ)。orchagent 内で MCLAG ピア由来 MAC のために**動的に追加生成**される内部値である。
- `FDB_ORIGIN_*` の数値表現は orchagent プロセス内のみで使用され、Redis 経路で外部に露出しない。
- `fdborch_pri = 20` は他 Orch との相対値で hard-coded。CONFIG_DB から変更不可。

---

## 9. 観測手段

```bash
# 起動時に bind した STATE_DB テーブル名を確認
docker exec swss redis-cli -n 6 KEYS 'FDB_TABLE|*'
docker exec swss redis-cli -n 6 KEYS 'MCLAG_REMOTE_FDB_TABLE|*'

# 入力 APP_DB テーブル
docker exec swss redis-cli -n 0 KEYS 'FDB_TABLE:*'
docker exec swss redis-cli -n 0 KEYS 'VXLAN_FDB_TABLE:*'
docker exec swss redis-cli -n 0 KEYS 'MCLAG_FDB_TABLE:*'
```

すべての定数は schema.h マクロまたは fdborch.cpp 内リテラルで定義されており、CONFIG_DB / YANG での変更経路は存在しない。
