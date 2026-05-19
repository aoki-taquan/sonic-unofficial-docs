# NAT_POOL — Phase E ハードコード定数調査メモ

## 調査対象ソース

- `sonic-swss/cfgmgr/natmgr.h`
- `sonic-swss/cfgmgr/natmgr.cpp`
- `sonic-swss/orchagent/natorch.h`
- `sonic-swss/orchagent/natorch.cpp`

---

## 1. バリデーション上限値 (natmgr.h)

| マクロ名 | 値 | 用途 |
|---------|-----|------|
| `L4_PORT_MIN` | `1` | `nat_port` range 下限チェック (0 を拒否) |
| `L4_PORT_MAX` | `65535` | `nat_port` range 上限チェック |
| `POOL_TABLE_KEY_SIZE` | `1` | key セグメント数 (= key に `|` が含まれないことを確認) |
| `TWICE_NAT_ID_MIN` | `1` | `NAT_BINDINGS.twice_nat_id` 下限 (NAT_POOL に直接は関係しないが同一ヘッダ定義) |
| `TWICE_NAT_ID_MAX` | `9999` | 同上 |
| pool 名最大長 | `32` (リテラル) | `natmgr.cpp:6563` `if (key.length() > 32)` — マクロ化なし |

---

## 2. NAT タイムアウトデフォルト (natmgr.h)

これらは `NAT_GLOBAL` テーブルで上書き可能なデフォルト値であり、`NAT_POOL` に直接設定する項目ではないが、`NAT_POOL` による dynamic NAT セッションの寿命に影響する。

| マクロ名 | 値 | 用途 |
|---------|-----|------|
| `NAT_TIMEOUT_DEFAULT` | `600` 秒 | dynamic NAT generic セッションのデフォルトタイムアウト |
| `NAT_TIMEOUT_MIN` | `300` 秒 | `NAT_GLOBAL.nat_timeout` の下限 |
| `NAT_TIMEOUT_MAX` | `432000` 秒 (= 5 日) | `NAT_GLOBAL.nat_timeout` の上限 / static conntrack エントリ保存用に使用 |
| `NAT_TCP_TIMEOUT_DEFAULT` | `86400` 秒 (= 1 日) | TCP セッションのデフォルトタイムアウト |
| `NAT_TCP_TIMEOUT_MIN` | `300` 秒 | TCP タイムアウト下限 |
| `NAT_TCP_TIMEOUT_MAX` | `432000` 秒 | TCP タイムアウト上限 |
| `NAT_UDP_TIMEOUT_DEFAULT` | `300` 秒 | UDP セッションのデフォルトタイムアウト |
| `NAT_UDP_TIMEOUT_MIN` | `120` 秒 | UDP タイムアウト下限 |
| `NAT_UDP_TIMEOUT_MAX` | `600` 秒 | UDP タイムアウト上限 |

---

## 3. 内部タイマー周期 (natmgr.h, natorch.h)

| マクロ名 | 定義場所 | 値 | 用途 |
|---------|---------|-----|------|
| `NAT_ENTRY_REFRESH_PERIOD` | `natmgr.h:125` | `86400` 秒 (= 1 日) | static conntrack エントリを kernel に再書き込みする周期 (`NAT_ENTRY_REFRESH_TIMER`) |
| `NAT_HITBIT_N_CNTRS_QUERY_PERIOD` | `natorch.h:37` | `5` 秒 | NatOrch が SAI hit-bit / カウンタを取得する周期 (`NAT_HITBIT_N_CNTRS_QUERY_TIMER`) |
| `NAT_CONNTRACK_TIMEOUT_PERIOD` | `natorch.h:38` | `86400` 秒 (= 1 日) | NatOrch が `SETTIMEOUTNAT` 通知で natmgrd に conntrack タイムアウト更新を要求する周期 |
| `NAT_HITBIT_QUERY_MULTIPLE` | `natorch.h:39` | `6` (= 30 秒) | hit-bit クエリはカウンタクエリの 6 回に 1 回。実効周期 = 5 × 6 = 30 秒 |

---

## 4. YANG max-elements (sonic-nat.yang)

| コンテナ/リスト | max-elements | 場所 |
|--------------|-------------|------|
| `NAT_POOL` list | `16` | `sonic-nat.yang:213` |
| `NAT_BINDINGS` list | `16` | `sonic-nat.yang:251` |

---

## 5. SAI 依存の動的上限

`NatOrch` コンストラクタ (`natorch.cpp:108-127`) が `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` を照会して `maxAllowedSNatEntries` を取得する。この値はハードウェア依存 (ASIC vendor が決定) であり、コードにリテラルはない。SNAT エントリ数がこの値に達すると新規エントリは作成されない。

---

## 6. iptables 関連固定値

| 定数 | 値 | 用途 |
|------|----|------|
| `REDIRECT_TO_DEV_NULL` | `" &> /dev/null"` | iptables コマンドのエラー抑制サフィックス |
| ACL ゾーン対応プロトコル | TCP / UDP / ICMP (プロトコル番号 6 / 17 / 1) | dynamic NAT iptables -j SNAT ルールを生成する 3 プロトコル固定 |
| iptables target | `MASQUERADE` (port 省略時) / `SNAT --to-source ip:port_range` (port 指定時) | `nat_port` 省略時は MASQUERADE、指定時は SNAT —— コードで分岐 |

---

## 7. その他のハードコードリテラル

- pool 名最大長: `32` 文字 (マクロなし、`natmgr.cpp:6563` にリテラル)
- `NAT_BINDINGS` で参照する pool 名最大長: `32` 文字 (`natmgr.cpp:7023` にも同じチェック)
- `STATIC_NAT_KEY_SIZE`: `1` (key セグメント数)
- `POOL_TABLE_KEY_SIZE`: `1` (key セグメント数)
