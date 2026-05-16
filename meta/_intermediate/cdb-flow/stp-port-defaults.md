# STP_PORT — Phase A コード由来デフォルト調査メモ

## 調査対象テーブル

- `STP_PORT` (key: `<intf_name>`) — インタフェースごとの STP 設定 (guard, portfast, path_cost 等)

## 主要ソース

- `sonic-utilities/config/stp.py` (SHA: 39732bceb8bdefe706518ab40623bbbba6ff33b9)
- `sonic-swss/cfgmgr/stpmgr.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)

---

## 1. PVST 有効化時の STP_PORT 初期書き込み

`interface_enable_stp()` (config/stp.py:292-301) および `enable_stp_for_interfaces()` (config/stp.py:361-379) で
VLAN メンバのインタフェースに対して以下が書き込まれる:

```python
fvs = {
    'enabled': 'true',
    'root_guard': 'false',
    'bpdu_guard': 'false',
    'bpdu_guard_do_disable': 'false',
    'portfast': 'false',
    'uplink_fast': 'false'
}
```

- `path_cost` および `priority` は **書き込まれない** (明示 CLI 設定が必要)
- PVST 時の `path_cost` デフォルト: `STP_INTERFACE_DEFAULT_COST = 0` (config/stp.py:1584) — ただし書き込みなし
- PVST 時の `priority` はデフォルト値の定数定義なし (CLI で 0-240 を指定)

---

## 2. MST 有効化時の STP_PORT 初期書き込み

`enable_mst_for_interfaces()` (config/stp.py:441-470) で書き込まれる:

```python
fvs_port = {
    'edge_port': 'false',
    'link_type': 'auto',           # MST_AUTO_LINK_TYPE = 'auto' (config/stp.py:110)
    'enabled': 'true',
    'bpdu_guard': 'false',
    'bpdu_guard_do': 'false',      # PVST の bpdu_guard_do_disable とは別フィールド名
    'root_guard': 'false',
    'path_cost': 1,                # MST_DEFAULT_PORT_PATH_COST (config/stp.py:108)
    'priority': 128                # MST_DEFAULT_PORT_PRIORITY (config/stp.py:92)
}
```

定数定義 (config/stp.py:90-110):
```python
MST_MIN_PORT_PRIORITY = 0
MST_MAX_PORT_PRIORITY = 240
MST_DEFAULT_PORT_PRIORITY = 128

MST_MIN_PORT_PATH_COST = 1
MST_MAX_PORT_PATH_COST = 200000000
MST_DEFAULT_PORT_PATH_COST = 1

MST_AUTO_LINK_TYPE = 'auto'
MST_P2P_LINK_TYPE = 'p2p'
MST_SHARED_LINK_TYPE = 'shared'
```

---

## 3. フィールド別デフォルト比較表

| フィールド | PVST デフォルト | MST デフォルト | 有効範囲 | 備考 |
|---|---|---|---|---|
| `enabled` | `"true"` | `"true"` | `true`/`false` | 初期書き込みあり |
| `root_guard` | `"false"` | `"false"` | `true`/`false` | |
| `bpdu_guard` | `"false"` | `"false"` | `true`/`false` | |
| `bpdu_guard_do_disable` | `"false"` | — | `true`/`false` | PVST のみ |
| `bpdu_guard_do` | — | `"false"` | `true`/`false` | MST のみ |
| `portfast` | `"false"` | — | `true`/`false` | PVST のみ |
| `uplink_fast` | `"false"` | — | `true`/`false` | PVST のみ |
| `edge_port` | — | `"false"` | `true`/`false` | MST のみ |
| `link_type` | — | `"auto"` | `auto`/`p2p`/`shared` | MST のみ |
| `path_cost` | **未設定** | `1` | 1–200,000,000 | PVST は明示設定が必要 |
| `priority` | **未設定** | `128` | 0–240 | PVST は明示設定が必要 |

---

## 4. stpmgr.cpp でのフィールド処理

`processStpPortAttr()` (stpmgr.cpp:519-624) がフィールドを解析し IPC メッセージに変換する:

- `enabled`, `root_guard`, `bpdu_guard`, `bpdu_guard_do_disable`: 文字列 `"true"`/`"false"` → uint8_t
- `path_cost`: `stoi()` で int に変換
- `priority`: `stoi()` で int に変換 (デフォルト sentinel: `-1`)
- `portfast`, `uplink_fast`: `L2_PVSTP` モード時のみ処理
- `edge_port`: `L2_MSTP` モード時のみ処理
- `link_type`: `L2_MSTP` モード時のみ処理するが `stoi(field)` を誤って使用 (value ではなく field のキー文字列を int 変換しているバグの疑い)
- 未知フィールドはサイレントに無視

```cpp
// stpmgr.cpp:611-613
else if (field== "link_type" && l2ProtoEnabled == L2_MSTP)
    msg->link_type = static_cast<LinkType>(stoi(field.c_str()));
    //                                           ^^^^^ バグ疑い: field でなく value を使うべき
```

---

## 5. 暗黙制約・注意点

1. **PVST `path_cost` 未初期化**: PVST 有効化時に `path_cost` は書き込まれない。`STP_INTERFACE_DEFAULT_COST = 0` は無効値 (range: 1-200000000) であり、明示設定前はフィールドが存在しない。
2. **bpdu_guard_do_disable vs bpdu_guard_do**: PVST/MST でフィールド名が異なる。stpmgrd の `processStpPortAttr()` は `bpdu_guard_do_disable` のみ処理するため、MST の `bpdu_guard_do` は IPC に変換されない可能性がある (discrepancy)。
3. **link_type の stoi バグ**: `stoi(field.c_str())` は文字列キー `"link_type"` を int 変換しようとして例外が発生する (実装上の潜在バグ)。
4. **MST `path_cost = 1`**: MST 有効化時に `1` が書き込まれるが、実際のリンク速度に基づく自動計算はなく固定値。

---

## ソース証跡

| ファイル | 行番号 | 内容 |
|---|---|---|
| `config/stp.py` | 90-112 | MST ポート定数定義 |
| `config/stp.py` | 1580-1584 | PVST `STP_INTERFACE_DEFAULT_COST = 0` |
| `config/stp.py` | 292-301 | `interface_enable_stp()` PVST |
| `config/stp.py` | 361-379 | `enable_stp_for_interfaces()` PVST |
| `config/stp.py` | 441-470 | `enable_mst_for_interfaces()` MST |
| `stpmgr.cpp` | 519-624 | `processStpPortAttr()` フィールド処理 |
