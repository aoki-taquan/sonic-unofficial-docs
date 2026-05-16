# STATIC_ROUTE — ハードコード定数 (Phase E)

ソース: `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_static_rt.py`、`static_rt_timer.py`

## StaticRouteMgr クラス定数

| 定数名 | 値 | 用途 |
|--------|-----|------|
| `OP_DELETE` | `'DELETE'` | 差分演算での削除操作識別子 |
| `OP_ADD` | `'ADD'` | 差分演算での追加操作識別子 |
| `ROUTE_ADVERTISE_ENABLE_TAG` | `'1'` | BGP 広告有効時に FRR へ付与する route-map tag 値 |
| `ROUTE_ADVERTISE_DISABLE_TAG` | `'2'` | BGP 広告無効時に FRR へ付与する route-map tag 値 |

## IpNextHop デフォルト値

| フィールド | デフォルト値 | コード根拠 |
|-----------|------------|-----------|
| `distance` | `0` | `self.distance = 0 if dist is None else int(dist)` |
| `blackhole` | `'false'` | `self.blackhole = 'false' if blackhole is None or blackhole == '' else blackhole` |
| `ip` (IPv4 ゼロ) | `'0.0.0.0'` | `zero_ip = lambda af: '0.0.0.0' if af == socket.AF_INET else '::'` |
| `ip` (IPv6 ゼロ) | `'::'` | 同上 |

## プロトコル enum（FRR コマンド文字列）

| AF | FRR コマンドプレフィクス | 判定ロジック |
|----|----------------------|------------|
| IPv4 | `'ip'` | `ip_nh.af == socket.AF_INET` |
| IPv6 | `'ipv6'` | `ip_nh.af == socket.AF_INET6` |

## アドレスファミリ enum（redistribute 対象）

```python
for af in ["ipv4", "ipv6"]:
    cmd_list.append(" address-family %s" % af)
    cmd_list.append("  redistribute static route-map STATIC_ROUTE_FILTER")
```

両 AF に対して `redistribute static route-map STATIC_ROUTE_FILTER` を発行する。

## StaticRouteTimer 定数

| 定数名 | 値 | 単位 | 用途 |
|--------|-----|------|------|
| `DEFAULT_TIMER` | `180` | 秒 | APPL_DB 未更新 static route を削除するデフォルト有効期間 |
| `DEFAULT_SLEEP` | `60` | 秒 | タイマーループのポーリング間隔 |
| `MAX_TIMER` | `172800` | 秒 (48h) | カスタム expiry time の上限値 |

## 引用元

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_static_rt.py` (L30–33, L265, L312)
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/static_rt_timer.py` (L13–16)
