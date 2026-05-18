# nat_zone フィールド — Phase E ハードコード定数スキャンノート

対象ページ: `docs/reference/config-db/nat-zone.md`
対象フィールド: `INTERFACE / VLAN_INTERFACE / PORTCHANNEL_INTERFACE / LOOPBACK_INTERFACE` テーブルの `nat_zone` フィールド
スキャン範囲:
- `sonic-swss/cfgmgr/natmgr.h`: マクロ定数
- `sonic-swss/cfgmgr/natmgr.cpp`: `doNatZoneIntfTask()` / `setMangleIptablesRules()` 全行精読
- `sonic-swss/cfgmgr/shellcmd.h`: コマンドパス定数
- `sonic-swss/orchagent/intfsorch.cpp`: `doIntfTask()` / `setRouterIntfsNatZoneId()` 全行精読
- `sonic-swss/orchagent/orchdaemon.cpp`: グローバル変数初期値
- `sonic-swss/orchagent/main.cpp`: `gIsNatSupported` 初期化

---

## 検出したハードコード定数

### natmgr.h — キーサイズ・プレフィックス定数

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `NAT_ZONE` | `"nat_zone"` | CONFIG_DB フィールド名 (ループ内照合) | `natmgr.h:60` |
| `L3_INTERFACE_KEY_SIZE` | `2` | `INTERFACE\|<port>\|<ip_prefix>` の有効キーサイズ | `natmgr.h:74` |
| `L3_INTERFACE_ZONE_SIZE` | `1` | `INTERFACE\|<port>` のゾーン単位エントリキーサイズ | `natmgr.h:75` |
| `IP_PREFIX_SIZE` | `2` | IP プレフィックス (アドレス+マスク長) の分割後サイズ | `natmgr.h:104` |
| `IP_ADDR_MASK_LEN_MIN` | `1` | 有効 IPv4 マスク長の最小値 | `natmgr.h:105` |
| `IP_ADDR_MASK_LEN_MAX` | `32` | 有効 IPv4 マスク長の最大値 | `natmgr.h:106` |

### natmgr.h — インタフェースプレフィックス定数

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `VLAN_PREFIX` | `"Vlan"` | Vlan インタフェース判定 | `natmgr.h:76` |
| `LAG_PREFIX` | `"PortChannel"` | PortChannel 判定 | `natmgr.h:77` |
| `ETHERNET_PREFIX` | `"Ethernet"` | Ethernet ポート判定 | `natmgr.h:78` |
| `LOOPBACK_PREFIX` | `"Loopback"` | Loopback 判定（iptables スキップ分岐） | `natmgr.h:79` |

### shellcmd.h — iptables コマンドパス

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `IPTABLES_CMD` | `"/sbin/iptables"` | mangle MARK ルール操作コマンド (`setMangleIptablesRules`) | `shellcmd.h:15` |

### natmgr.cpp — iptables mangle テンプレート

`setMangleIptablesRules()` は以下のテンプレートを文字列連結で生成する (`natmgr.cpp:912-913`)。

```
/sbin/iptables -t mangle -{A|D} PREROUTING  -i <port> -j MARK --set-mark <nat_zone+1>
/sbin/iptables -t mangle -{A|D} POSTROUTING -o <port> -j MARK --set-mark <nat_zone+1>
```

コマンドの各要素のうち `"-t mangle"` / `"PREROUTING"` / `"POSTROUTING"` / `"-j MARK"` / `"--set-mark"` はすべて文字列リテラルとして `natmgr.cpp` 内にハードコードされており、設定変更はできない。

### natmgr.cpp — iptables mark オフセット

`nat_zone_value++` が `natmgr.cpp:7513` に固定実装されており、DB 値に常に +1 してから mark 値として使用する。これはカーネル mangle MARK=0 がデフォルト動作と衝突する問題を回避するためのハードコードオフセット。YANG や CONFIG_DB には反映されない定数。

### orchagent — gIsNatSupported グローバル変数

| 定数/変数 | 初期値 | 確定タイミング | ソース |
|----------|--------|--------------|--------|
| `gIsNatSupported` | `false` | orchagent 起動時 `main.cpp` で `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` をクエリし、`attr.value.u32 != 0` なら `true` に確定 | `orchdaemon.cpp:78` / `main.cpp:935-947` |

この変数はプロセスライフタイムを通じて不変（再クエリなし）。`false` のプラットフォームでは `setRouterIntfsNatZoneId()` が決して呼ばれない。

### SAI 属性定数

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `SAI_ROUTER_INTERFACE_ATTR_NAT_ZONE_ID` | SAI 仕様値 | RIF に zone_id を設定する SAI 属性 ID | `intfsorch.cpp:285` / `intfsorch.cpp:1289` |
| `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` | SAI 仕様値 | NAT サポート有無をクエリする SAI スイッチ属性 | `main.cpp:936` |

---

## ページ反映方針

- `<!-- constants -->` ブロックを `<!-- /failure -->` と `<!-- entry-points -->` の間に挿入する。
- 主要定数: キーサイズ / プレフィックス文字列 / iptables コマンドパス / mark オフセット (+1) / `gIsNatSupported` 初期化ロジックの 5 グループ。
- mark オフセット (+1) は既存 `<!-- defaults -->` ブロックでも言及しているが、constants では「定数として固定された値」として独立した表で示す。
