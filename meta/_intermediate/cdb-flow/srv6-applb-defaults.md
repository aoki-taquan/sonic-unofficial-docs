# Phase A 解析メモ: APPL_DB SRV6_MY_SID_TABLE / SRV6_SID_LIST_TABLE フィールドデフォルト

対象ページ: `docs/reference/config-db/srv6-applb.md`
作成日: 2026-05-15

## 解析対象ソース

| ソース | パス | 用途 |
|--------|------|------|
| `routesync.cpp` | `sonic-swss/fpmsyncd/routesync.cpp` | fpmsyncd が FRR netlink から APPL_DB へ書き込む |
| `srv6orch.cpp` | `sonic-swss/orchagent/srv6orch.cpp` | Srv6Orch が APPL_DB を読み取って SAI へ転送 |
| `schema.h` | `sonic-swss-common/common/schema.h` | テーブル名定義 |
| `test_srv6.py` | `sonic-swss/tests/test_srv6.py` | フィールド値の実例 |

## SRV6_SID_LIST_TABLE (APP_SRV6_SID_LIST_TABLE_NAME)

### フィールド

| フィールド | 型 | 省略時挙動 | コード根拠 |
|-----------|-----|-----------|-----------|
| `path` | string (comma-sep IPv6 list) | 必須: 省略時 segment_list.count=0 でスキップ (`srv6orch.cpp:1052-1055`) | `routesync.cpp:1196-1200` で path のみ set |
| `type` | enum (`insert`/`insert.red`/`encaps`/`encaps.red`) | デフォルト `encaps.red` | `srv6orch.cpp:1080-1083`: `sidlist_type_map` に不一致 → `SAI_SRV6_SIDLIST_TYPE_ENCAPS_RED` |

### 書き込みフロー

fpmsyncd の `Srv6SidListTableFieldValueTupleWrapper::fieldValueTupleVector()` は
`path` フィールドのみを設定し `type` は設定しない（`routesync.cpp:1189-1203`）。
FRR 経由で登録される SID リストは常に `type` フィールドなし = `encaps.red` 相当。

test_srv6.py の `create_sidlist` では `type=None` 時に `path` のみの fvs を使用し、
`type` 指定時のみ両フィールドを設定する（`test_srv6.py:466-474`）。

### key 構造

```
SRV6_SID_LIST_TABLE|<sid_name>
```

`<sid_name>` は通常 VPN SID の IPv6 アドレス文字列 (`routesync.cpp:1408`)。

---

## SRV6_MY_SID_TABLE (APP_SRV6_MY_SID_TABLE_NAME)

### フィールド

| フィールド | 型 | 省略時挙動 | コード根拠 |
|-----------|-----|-----------|-----------|
| `action` | string (endpoint behavior) | 省略時 `end_action=""` → `sidEntryEndpointBehavior` が false 返却でエントリ拒否 (`srv6orch.cpp:1473-1477`) | `routesync.cpp:1174-1176`: non-ZMQ では空文字の場合は push しない |
| `vrf` | string (VRF 名) | 省略時 `dt_vrf=""` → VRF 属性未設定（`mySidVrfRequired` が偽なら不要） | `routesync.cpp:1177-1179` |
| `adj` | string (IPv4/IPv6 アドレス) | 省略時 `adj=""` → nexthop 属性未設定（`mySidNextHopRequired` が偽なら不要） | `routesync.cpp:1180-1182` |

### ZMQ モードでの差異

NB-ZMQ 有効時 (`nbZmqEnabled=true`) は `action`/`vrf`/`adj` を常に全フィールド push する
（空文字列でも）— `routesync.cpp:1169-1172`。
これは ZMQ 側の冪等更新のために明示的に空値を送る設計。

### Orch 側での vrf="default" の扱い

`srv6orch.cpp:1484`:
```cpp
if (dt_vrf == "default")
{
    dt_vrf_id = gVirtualRouterId;
}
```
`vrf` フィールド自体はデフォルト値を持たない（書き込み側が省略可能）が、
Orch は `vrf=""` を `mySidVrfRequired` が真のエンドポイント行動に限り参照し、
空文字列のまま受け取ると VRF 未解決でエラー。
従って VRF が必要な行動（`end.dt*`/`udt*`）では `vrf` フィールド省略は orch エラーになる。

### key 構造

```
SRV6_MY_SID_TABLE|<block_len>:<node_len>:<func_len>:<arg_len>:<sid_ipv6>
```

例: `32:16:16:0:fc00:0:1:64::` (`test_srv6.py:837`)

---

## サポート action 値

### SRV6_MY_SID_TABLE

`end_behavior_map` (`srv6orch.cpp:41-62`) に収録:
`end`, `end.x`, `end.t`, `end.dx6`, `end.dx4`, `end.dt4`, `end.dt6`, `end.dt46`,
`end.b6.encaps`, `end.b6.encaps.red`, `end.b6.insert`, `end.b6.insert.red`,
`udx6`, `udx4`, `udt6`, `udt4`, `udt46`, `un`, `ua`

fpmsyncd `mySidAction2Str` でカバー: `end`, `end.x`, `end.t`, `end.dx6`, `end.dx4`,
`end.dt6`, `end.dt4`, `end.dt46`, `un`, `ua`, `udx6`, `udx4`, `udt6`, `udt4`, `udt46`

### SRV6_SID_LIST_TABLE

`sidlist_type_map` (`srv6orch.cpp:73-79`):
`insert`, `insert.red`, `encaps`, `encaps.red`

---

## まとめ（実効デフォルト表）

### SRV6_MY_SID_TABLE

| フィールド | 実効デフォルト | 備考 |
|-----------|--------------|------|
| `action` | **省略不可** | 空文字列だと orch が `Invalid my_sid action` でエントリ拒否 |
| `vrf` | **行動依存** | VRF 不要な行動（`end`, `un` 等）では省略可。`end.dt*`/`udt*` では省略不可 |
| `adj` | **行動依存** | 隣接不要な行動（`end`, `un`, `end.dt*` 等）では省略可。`end.x`/`ua` 等では省略不可 |

### SRV6_SID_LIST_TABLE

| フィールド | 実効デフォルト | 備考 |
|-----------|--------------|------|
| `path` | **省略不可** | 0要素だと orch が `segment list count is zero, skip` でスキップ（エラーにならずサイレント） |
| `type` | `encaps.red` | fpmsyncd は type を書かない。orch が sidlist_type_map miss → SAI_SRV6_SIDLIST_TYPE_ENCAPS_RED |
