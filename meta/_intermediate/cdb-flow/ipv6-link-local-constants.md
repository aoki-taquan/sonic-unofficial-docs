# ipv6-link-local — Phase E: ハードコード定数

調査日: 2026-05-19

ソース:
- `sonic-swss/cfgmgr/intfmgr.cpp`
- `sonic-swss/neighsyncd/neighsync.cpp`
- `sonic-utilities/config/main.py`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-interface.yang`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-types.yang`

## 抽出した定数

### 1. フィールド名文字列 (コードリテラル)

| 定数 | 値 | 用途 | ソース |
|------|-----|------|--------|
| フィールド名 | `"ipv6_use_link_local_only"` | CONFIG_DB フィールド名。`intfmgr.cpp:817` でパース、`intfmgr.cpp:926` で APP_DB fvTuple に渡す。`neighsync.cpp:227` で検索キー。`config/main.py:9453` で DB get/set。 | intfmgr.cpp:817,926; neighsync.cpp:227; config/main.py:9453 |
| 有効値 | `"enable"` | `ipv6_use_link_local_only` の有効化値。ランタイムで `== "enable"` リテラル比較 | intfmgr.cpp:915; neighsync.cpp:230; config/main.py:9461 |
| 無効値 | `"disable"` | `ipv6_use_link_local_only` の無効化値。YANG `default disable` と一致 | intfmgr.cpp:920; config/main.py:9482 |

### 2. インターフェース名プレフィクス文字列 (neighsync.cpp)

`isLinkLocalEnabled()` (neighsync.cpp:193-243) はインターフェース名プレフィクスによって参照先 CONFIG_DB テーブルを振り分ける。

| プレフィクス文字列 | 参照テーブル | ソース |
|---|---|---|
| `"Vlan"` | `VLAN_INTERFACE` テーブル | neighsync.cpp:197 |
| `"PortChannel"` | `PORTCHANNEL_INTERFACE` テーブル | neighsync.cpp:205 |
| `"Ethernet"` | `INTERFACE` テーブル | neighsync.cpp:213 |

上記以外のプレフィクス (`eth0`, `lo`, `docker0` 等) はサポート外として `false` 返却。

### 3. アドレス判定定数

`delIpv6LinkLocalNeigh()` (intfmgr.cpp:712-740) は NEIGH_TABLE エントリをループし、
`IpAddress::AddrScope::LINK_SCOPE` で link-local アドレスを判定して `ip neigh del` コマンドを実行する。

| 定数 | 値の意味 | ソース |
|------|---------|--------|
| `IpAddress::AddrScope::LINK_SCOPE` | IPv6 link-local アドレス (FE80::/10) のスコープ | intfmgr.cpp:727 |

### 4. sysctl キー (enableIpv6Flag)

`enableIpv6Flag()` (intfmgr.cpp:1272-1280) はインターフェースの IPv6 を有効化するために
`sysctl -w net.ipv6.conf.<alias>.disable_ipv6=0` を実行する。
このカーネルパラメータ名はコードに直接リテラルとして埋め込まれている。

| sysctl キー | 値 | 用途 | ソース |
|---|---|---|---|
| `net.ipv6.conf.<alias>.disable_ipv6` | `0` (有効化) | IPv6 を無効化されたインターフェースで再有効化する | intfmgr.cpp:1276 |

### 5. YANG スキーマ定数

| 定数 | 値 | ソース |
|------|-----|--------|
| YANG default | `disable` | sonic-interface.yang:99 (`default disable;`) |
| YANG type | `stypes:mode-status` → `enum enable` / `enum disable` | sonic-types.yang (mode-status typedef) |

### 6. CONFIG_DB テーブル名文字列

intfmgr と CLI は `INTERFACE` / `PORTCHANNEL_INTERFACE` / `VLAN_INTERFACE` の 3 テーブルを文字列リテラルで指定する。
コード側では `get_interface_table_name(interface_name)` (config/main.py) でインターフェース名から判定する。
