# dhcp-server-ipv6 — Phase A: コード由来の暗黙デフォルト調査メモ

調査日: 2026-05-14
対象: `DHCP_SERVER_IPV6` テーブル
主要ソース:
- `src/sonic-yang-models/yang-models/sonic-dhcp-server-ipv4.yang`
- `src/sonic-yang-models/yang-models/sonic-dhcpv6-relay.yang`
- `src/sonic-yang-models/yang-models/sonic-dhcp-server.yang`
- `src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcp_cfggen.py`
- `doc/dhcp_server/port_based_dhcp_server_high_level_design.md`

---

## 調査結果: テーブル未実装

**`DHCP_SERVER_IPV6` テーブルは sonic-net/sonic-buildimage master に存在しない。**

SONiC の組み込み DHCP サーバ機能は 2023-07 にリリースされた **IPv4 専用** 実装のみである。
調査したすべてのソース（YANG モデル、Python デーモン、HLD、sonic-utilities、sonic-swss）において `DHCP_SERVER_IPV6` への参照は一切確認されなかった。

---

## 存在するテーブルとの対比

| テーブル | 説明 | 実装状況 |
|---------|------|---------|
| `DHCP_SERVER_IPV4` | ポートベース DHCPv4 サーバの IF 単位設定 | 実装済み（sonic-dhcp-server-ipv4.yang） |
| `DHCP_SERVER_IPV6` | DHCPv6 サーバの IF 単位設定（仮称） | **未実装** |
| `DHCP_RELAY` | DHCPv6 リレーエージェント設定 | 実装済み（sonic-dhcpv6-relay.yang） |

DHCPv6 に関しては **relay のみ** 実装されている。DHCPv6 サーバ機能（kea-dhcp6 等の管理デーモン含む）は 2026-05-14 時点で SONiC master に存在しない。

---

## YANG モデル確認

```text
sonic-dhcp-server-ipv4.yang  — DHCP_SERVER_IPV4 定義あり
sonic-dhcp-server.yang       — DHCP_SERVER（relay IP リスト）のみ
sonic-dhcpv6-relay.yang      — DHCP_RELAY（DHCPv6 relay）のみ
```

`sonic-dhcp-server-ipv6.yang` に相当するファイルは存在しない。

---

## コード確認

- `sonic-buildimage/src/sonic-dhcp-utilities/` — `dhcpservd.py`、`dhcp_cfggen.py` は IPv4 専用
- `sonic-utilities/config/main.py` 内 `dhcp_server` グループ — IPv4 専用コマンド
- `sonic-swss/` — DHCP_SERVER_IPV6 への参照なし
- `sonic-mgmt-common/` — DHCPv6 server transformer なし

---

## 結論

`DHCP_SERVER_IPV6` テーブルは未実装のため、Phase A の暗黙デフォルト調査の対象となるフィールドが存在しない。
ドキュメントページは `verification: stub` + `monitor: not_implemented` として作成し、実装されたときに更新するプレースホルダーとする。

---

## Evidence

- `sonic-dhcp-server-ipv4.yang` (sonic-buildimage@9ea932ec): DHCP_SERVER_IPV4 定義、IPv6 版なし
- `sonic-dhcpv6-relay.yang` (sonic-buildimage@9ea932ec): DHCP_RELAY (relay only)
- `doc/dhcp_server/port_based_dhcp_server_high_level_design.md`: "IPv4 Port Based DHCP_SERVER" と明記
- `dhcp_cfggen.py`: IPv4 専用実装、IPv6 コードパスなし
