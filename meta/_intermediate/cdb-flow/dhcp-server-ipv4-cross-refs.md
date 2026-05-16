# DHCP_SERVER_IPV4 — Phase C 暗黙参照調査メモ

調査日: 2026-05-15  
対象ページ: `docs/reference/config-db/dhcp-server-ipv4.md`  
証拠ソース:
- `src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcp_cfggen.py`（全行精読）
- `dhcp_utilities/dhcprelayd/dhcprelayd.py`（94-98行）
- `dockers/docker-dhcp-server/cli/config/plugins/dhcp_server.py`（全行精読）
- `src/sonic-yang-models/yang-models/sonic-dhcp-server-ipv4.yang`（全行精読）

---

## 発見した暗黙参照一覧

### 1. VLAN / VLAN_INTERFACE

**参照先**: `VLAN|<name>` および `VLAN_INTERFACE|<name>|<ipv4_prefix>`  
**方向**: CONFIG_DB 読み取り  
**条件**: `dhcp_cfggen.generate()` 実行時（常時）  
**証拠**:
- `dhcp_cfggen.py:432-433`: `VLAN_INTERFACE` から IPv4 サブネットを取得し `ip_network()` 変換。未設定だとそのインタフェースをスキップ
- `dhcp_cfggen.py:245-249`: option 54 (dhcp_server_id) 自動注入時に `VLAN_INTERFACE` の IPv4 アドレスを使用
- `dhcp_cfggen.py:258-259`: `--dup_gw_nm` フラグ時に `VLAN_INTERFACE` の IPv4 アドレスを `gateway` として使用
- YANG leafref なし — 実装上の暗黙依存

**影響**: VLAN_INTERFACE が未設定だと kea-dhcp4 設定に subnet 定義が生成されず、DHCP DISCOVER に無応答。

### 2. VLAN_MEMBER

**参照先**: `VLAN_MEMBER|<vlan>|<port>`  
**方向**: CONFIG_DB 読み取り  
**条件**: PORT モードで `_parse_port()` 実行時  
**証拠**:
- `dhcp_cfggen.py:_parse_port()`: ポートが VLAN メンバーとして登録されているか確認。未登録のポートは `"Port %s is not in %s"` LOG_WARNING でスキップ

**影響**: VLAN_MEMBER なしではそのポートへの IP プール割当なし。

### 3. FEATURE

**参照先**: `FEATURE|dhcp_server` の `state` フィールド  
**方向**: CONFIG_DB 読み取り（feature 有効チェック）  
**条件**: CLI `config dhcp_server` グループ入口（常時）; `dhcpservd` 起動時  
**証拠**:
- `dhcp_server.py:54`: `feature_status = db.get_entry("FEATURE", "dhcp_server")["state"]`; `state != "enabled"` なら `ctx.fail()`
- dhcpservd 自体も feature 有効でなければ起動しない

**影響**: `FEATURE|dhcp_server.state=enabled` が設定されていないと、CLI コマンドはすべて失敗し dhcpservd も起動しない。

### 4. DEVICE_METADATA

**参照先**: `DEVICE_METADATA|localhost` の `dhcp_server` フィールド  
**方向**: CONFIG_DB 読み取り（全体有効化スイッチ）  
**条件**: dhcpservd 起動時  
**証拠**:
- ページ本文より: `DEVICE_METADATA.localhost.dhcp_server` で全体有効化が制御される

**影響**: `dhcp_server` フィールドが未設定または `disabled` だと dhcpservd 自体が起動しない。`state` フィールドの設定は無効になる。

### 5. DHCP_RELAY (排他関係)

**参照先**: `DHCP_RELAY` テーブル  
**方向**: 排他的な共存制約（間接的）  
**条件**: 同一 VLAN に DHCP_RELAY と DHCP_SERVER_IPV4 の両方が設定された場合  
**証拠**:
- `dhcprelayd.py:94-98`: `state=enabled` の DHCP_SERVER_IPV4 エントリが存在する VLAN では `dhcrelay` 起動対象から除外する

**影響**: DHCP_SERVER_IPV4 を有効化すると、同一 VLAN の DHCP relay が自動的に無効化される。

### 6. DHCP_SERVER_IPV4_RANGE (サブテーブル leafref)

**参照先**: `DHCP_SERVER_IPV4_RANGE|<name>`  
**方向**: CONFIG_DB 読み取り（leafref 検証）  
**条件**: `DHCP_SERVER_IPV4_PORT` の `ranges` フィールド使用時  
**証拠**:
- `dhcp_cfggen.py:452-454`: range 名が RANGE テーブルに存在しない場合 LOG_WARNING でスキップ

### 7. DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS (サブテーブル leafref)

**参照先**: `DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS|<name>`  
**方向**: CONFIG_DB 読み取り（leafref 検証）  
**条件**: `customized_options` フィールド使用時  
**証拠**:
- `dhcp_cfggen.py:213-215`: option 名が CUSTOMIZED_OPTIONS テーブルに存在しない場合 LOG_WARNING でスキップ

---

## SAI / APPL_DB 参照

なし。`dhcpservd` / `kea-dhcp4` は Linux ユーザー空間の DHCP サーバであり、SAI/ASIC に一切触れない。APPL_DB 中継もない。

---

## 参照関係サマリーテーブル

| 参照先テーブル | DB | 参照方向 | YANG leafref | 実装上の必須度 | 証拠 |
|---|---|---|---|---|---|
| `VLAN\|<name>` | CONFIG_DB | 読み取り | なし | 実質必須 | dhcprelayd.py:97-98 |
| `VLAN_INTERFACE\|<name>\|<prefix>` | CONFIG_DB | 読み取り (subnet/GW取得) | なし | 実質必須 | dhcp_cfggen.py:432-433,245-249,258-259 |
| `VLAN_MEMBER\|<vlan>\|<port>` | CONFIG_DB | 読み取り (ポート検証) | なし | PORT モード必須 | dhcp_cfggen.py:_parse_port() |
| `FEATURE\|dhcp_server` | CONFIG_DB | 読み取り (feature 有効チェック) | なし | 必須 | dhcp_server.py:54 |
| `DEVICE_METADATA\|localhost` (dhcp_server) | CONFIG_DB | 読み取り (全体有効化) | なし | 必須 | dhcpservd 起動条件 |
| `DHCP_RELAY` | CONFIG_DB | 排他制約 | なし | 排他 | dhcprelayd.py:94-98 |
