# dhcp-server-ipv4 Phase E — ハードコード定数 調査証跡

調査日: 2026-05-16  
対象ページ: `docs/reference/config-db/dhcp-server-ipv4.md`  
調査ソース: `sonic-buildimage/src/sonic-dhcp-utilities/`, `sonic-buildimage/dockers/docker-dhcp-server/`

## 調査ファイル一覧

| ファイル | 行番号 | 内容 |
|---------|--------|------|
| `src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcp_cfggen.py` | 25 | `DEFAULT_LEASE_TIME = 900` |
| `src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcp_cfggen.py` | 26 | `DEFAULT_LEASE_PATH = "/var/lib/kea/kea-lease.csv"` |
| `src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcp_cfggen.py` | 19 | `MID_PLANE_BRIDGE_SUBNET_ID = 10000` |
| `src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcp_cfggen.py` | 30 | `SUPPORT_DHCP_OPTION_TYPE = ["binary", "boolean", "ipv4-address", "string", "uint8", "uint16", "uint32"]` |
| `src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcp_cfggen.py` | 31 | `OPTION_DHCP_SERVER_ID = "54"` |
| `src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcp_cfggen.py` | 199 | `if "state" not in dhcp_config or dhcp_config["state"] != "enabled":` (state判定ロジック) |
| `dockers/docker-dhcp-server/cli/config/plugins/dhcp_server.py` | 70 | `@click.option("--lease_time", required=False, default="900")` |
| `dockers/docker-dhcp-server/cli/config/plugins/dhcp_server.py` | 105 | `"state": "disabled"` (add コマンド初期値) |
| `dockers/docker-dhcp-server/cli/config/plugins/dhcp_server.py` | 175 | `dbconn.set("CONFIG_DB", key, "state", "enabled")` |
| `dockers/docker-dhcp-server/kea-dhcp4.conf.j2` | 1 | `{%- set default_lease_time = 900 -%}` |
| `dockers/docker-dhcp-server/kea-dhcp4.conf.j2` | 37 | `"lfc-interval": 3600` |
| `dockers/docker-dhcp-server/kea-dhcp4-init.conf` | 全体 | ポート番号明示なし → kea-dhcp4 デフォルト UDP 67 |
| `src/sonic-yang-models/yang-models/sonic-dhcp-server-ipv4.yang` | 105 | `type stypes:admin_mode;` (state フィールド型) |
| `src/sonic-yang-models/yang-models/sonic-dhcp-server-ipv4.yang` | 141-148 | `type enumeration { enum string; enum ipv4-address; enum uint8; enum uint16; enum uint32; }` |

## state enum 詳細

`stypes:admin_mode` は sonic-types モジュールで定義される。値は `"enabled"` / `"disabled"` の 2 値。  
実装上は `dhcp_config["state"] != "enabled"` の判定で `"enabled"` 以外は全て disabled 扱い。

## lease_time デフォルト値の三重定義

1. Python定数: `DEFAULT_LEASE_TIME = 900` (`dhcp_cfggen.py:25`)
2. CLI オプションデフォルト: `default="900"` (`dhcp_server.py:70`)
3. Jinja2テンプレート変数: `default_lease_time = 900` (`kea-dhcp4.conf.j2:1`)

三箇所で独立して定義されており、変更時に全ファイル更新が必要。

## kea-dhcp4 ポート 67

kea-dhcp4 は IETF RFC 2131 に従い UDP ポート 67 でクライアントからの DHCP DISCOVER/REQUEST を受信する。  
SONiC の設定ファイル (`kea-dhcp4.conf.j2`, `kea-dhcp4-init.conf`) にはポートのオーバーライド設定が存在せず、kea-dhcp4 のビルトインデフォルト (67) が使用される。

## CUSTOMIZED_OPTIONS type enum の YANG-実装 乖離

YANG定義 (`sonic-dhcp-server-ipv4.yang:141-148`) では `binary` / `boolean` が未定義だが、  
`SUPPORT_DHCP_OPTION_TYPE` リスト (`dhcp_cfggen.py:30`) にはこれら2型が含まれる。  
→ 直接 DB 書込みで `binary` / `boolean` を指定した場合、実装は処理するが YANG バリデーションで reject される可能性がある（YANG-実装 discrepancy）。

## ip_type について

調査範囲 (`src/sonic-dhcp-utilities/`, `dockers/docker-dhcp-server/`, `sonic-dhcp-server-ipv4.yang`) で  
`ip_type` という名前のフィールドや定数は発見されなかった。  
タスク仕様の `ip_type enum` は `DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS.type` フィールドを指している可能性が高いため、そちらを抽出した。
