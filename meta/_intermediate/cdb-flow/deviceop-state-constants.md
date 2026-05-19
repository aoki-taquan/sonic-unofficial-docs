# deviceop-state — Phase E: ハードコード定数

## 調査方法

- `pfcwd/main.py` の module-level 定数 (L36-42) および `start_default` 実装 (L404-442)
- `scripts/ecnconfig` のポートソートロジック (L289-293)
- `managers_bgp.py` の `BGPPeerMgrBase.__init__` (L100)

---

## pfcwd start_default — デフォルト値定数

| 定数名 | 値 | 用途 |
|--------|-----|------|
| `DEFAULT_PORT_NUM` | `32` | ポートスケーリング基準 (`multiply = max(1,(port_num-1)//32+1)`) |
| `DEFAULT_POLL_INTERVAL` | `200` ms | POLL_INTERVAL = 200 * multiply (最大 1000 ms) |
| `MAX_POLL_INTERVAL_TIME` | `1000` ms | POLL_INTERVAL の上限クランプ値 |
| `DEFAULT_DETECTION_TIME` | `200` ms | detection_time = 200 * multiply |
| `DEFAULT_RESTORATION_TIME` | `200` ms | restoration_time = 200 * multiply |
| `DEFAULT_ACTION` | `'drop'` | PFC ストーム検出時アクション |
| `DEFAULT_PFC_HISTORY_STATUS` | `"disable"` | pfc_stat_history フィールドのデフォルト |

```python
# pfcwd/main.py:36-42
MAX_POLL_INTERVAL_TIME = 1000
DEFAULT_DETECTION_TIME = 200
DEFAULT_RESTORATION_TIME = 200
DEFAULT_POLL_INTERVAL = 200
DEFAULT_PORT_NUM = 32
DEFAULT_ACTION = 'drop'
DEFAULT_PFC_HISTORY_STATUS = "disable"
```

スケーリング: `multiply = max(1, (port_num-1)//DEFAULT_PORT_NUM+1)`
- port_num は `PORT` テーブルのキー数（DEVICE_NEIGHBOR キー数ではない）
- `pfcwd start_default` は DEVICE_NEIGHBOR キーを外部ポート一覧として取得した後、PORT テーブルのポート総数でスケーリングを計算する

## ecnconfig — バックエンドポートソートオフセット

```python
# scripts/ecnconfig:291-293
self.ports_key.sort(
    key = lambda k: int(k[8:]) if "BP" not in k else int(k[11:]) + 1024
)
```

- オフセット `1024` は無名定数（シンボル化なし）
- `'Ethernet-BPxy'` のポート番号に加算して `'Ethernetxy'` より大きな値にし、末尾ソートを実現

## bgpcfgd — loopbacks ハードコードリスト

```python
# managers_bgp.py:100
self.loopbacks = ["Loopback0"]
```

BGP neighbor 処理でのループバック IP 解決時に使用される固定リスト。

## Evidence

- `sonic-utilities` `pfcwd/main.py:36-42,404-442`
- `sonic-utilities` `scripts/ecnconfig:289-293`
- `sonic-buildimage` `src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:100`
