# SNMP_AGENT_ADDRESS_CONFIG / SNMP_USER — Phase H プラットフォーム差調査メモ

対象テーブル: `SNMP_AGENT_ADDRESS_CONFIG`, `SNMP_USER`
調査日: 2026-05-17

## 調査対象ファイル

| ファイル | 役割 |
|---------|------|
| `sonic-buildimage/src/sonic-config-engine/minigraph.py:2308-2324` | SNMP_AGENT_ADDRESS_CONFIG 初期値生成 — multi-ASIC 分岐あり |
| `sonic-buildimage/dockers/docker-snmp/snmpd.conf.j2` | snmpd.conf テンプレート — プラットフォーム分岐なし (汎用) |
| `sonic-buildimage/dockers/docker-snmp/start.sh` | コンテナ起動スクリプト — プラットフォーム分岐なし |
| `sonic-snmpagent/src/sonic_ax_impl/mibs/__init__.py:586-607` | MIB agent DB 接続 — multi-ASIC で database_global.json を使用 |
| `sonic-buildimage/src/sonic-config-engine/tests/test_cfggen.py:1158-1165` | テスト — SNMP_AGENT_ADDRESS_CONFIG キー期待値 (single-ASIC) |

---

## 1. Single-ASIC vs Multi-ASIC: minigraph.py の分岐

### コード

```python
# minigraph.py:2312-2324
if not is_multi_asic() and asic_name is None:
    results['SNMP_AGENT_ADDRESS_CONFIG'] = {}
    port = '161'
    for intf in list(mgmt_intf.keys()) + list(lo_intfs.keys()):
        ip_addr = ipaddress.ip_address(UNICODE_TYPE(intf[1].split('/')[0]))
        if ip_addr.version == 6 and ip_addr.is_link_local:
            agent_addr = str(ip_addr) + '%' + intf[0]
        else:
            agent_addr = str(ip_addr)
        snmp_key = agent_addr + '|' + port + '|'
        results['SNMP_AGENT_ADDRESS_CONFIG'][snmp_key] = {}
else:
    results['SNMP_AGENT_ADDRESS_CONFIG'] = {}
```

### 差異

| 環境 | minigraph 初期値 | スナップショットコメント |
|------|----------------|----------------------|
| **Single-ASIC** (`is_multi_asic() == False && asic_name is None`) | MGMT IP + Loopback IP を自動列挙。`<ip>\|161\|` 形式でエントリを生成 | snmpd.conf.j2 コメント: "Listen on management and loopback0 ips for single asic platform" |
| **Multi-ASIC** (`is_multi_asic() == True` または `asic_name is not None`) | 空辞書 `{}` のみ。SNMP_AGENT_ADDRESS_CONFIG にエントリなし → snmpd はデフォルト agentAddress (`udp:161` / `udp6:161`) で listen | snmpd.conf.j2 コメント: "Listen for connections on all ip addresses, including eth0, ipv4 lo for multi-asic platform" |

**補足**: multi-ASIC では各 ASIC に個別の netns / docker-snmp が存在するのではなく、SNMP は単一の docker-snmp コンテナで動作し、全 ASIC の COUNTERS_DB に接続して MIB を集約する (`sonic_ax_impl/mibs/__init__.py:586-607`)。SNMP_AGENT_ADDRESS_CONFIG を空にすることで snmpd がデフォルトのワイルドカード listen (`0.0.0.0:161` / `[::]:161`) を行い、全インタフェースで到達可能になる。

---

## 2. IPv6 リンクローカルアドレスの特例

```python
# minigraph.py:2317-2318
if ip_addr.version == 6 and ip_addr.is_link_local:
    agent_addr = str(ip_addr) + '%' + intf[0]
```

Management IF / Loopback IF が IPv6 リンクローカルアドレス (`fe80::/10`) を持つ場合、key に `%<intf>` スコープサフィックスを付与する。

例: `fe80::1%Management0|161|`

- テスト期待値 (`test_cfggen.py:1163`): `'fe80::1%Management0|161|'`
- `snmpd.conf.j2` の `protocol()` マクロは `ip_addr.split('%')[0]` で `%` 以降を除いてから IPv6 判定するため、スコープサフィックス付きでも `udp6` が正しく選択される

---

## 3. snmpd.conf.j2 / start.sh: プラットフォーム非依存

`snmpd.conf.j2` はプラットフォーム固有の分岐を一切持たない。プラットフォーム差は上流 (minigraph.py) で吸収済み:

- `agentAddress` 行: `SNMP_AGENT_ADDRESS_CONFIG` テーブルの内容をそのまま展開
- 認証/暗号化 (`CreateUser` / `rouser` / `rwuser`): SNMPv3 の標準プロトコルであり ASIC ベンダー非依存
- MIB 拡張 (`master agentx` / `agentxsocket tcp:localhost:3161`): 全プラットフォーム共通

`start.sh` も platform 環境変数を参照しない。`sonic-cfggen -d` が CONFIG_DB から一括読み取りするだけ。

---

## 4. MIB agent (sonic_ax_impl): multi-ASIC DB 接続

```python
# mibs/__init__.py:586-607
if multi_asic.is_multi_asic():
    SonicDBConfig.load_sonic_global_db_config()  # database_global.json を読む
else:
    SonicDBConfig.load_sonic_db_config()           # database.json を読む
```

| 環境 | DB 設定ファイル | 影響 |
|------|---------------|------|
| Single-ASIC | `database.json` | 単一 DB インスタンス |
| Multi-ASIC | `database_global.json` | 全 namespace の DB インスタンスを列挙・接続 |

SNMP_AGENT_ADDRESS_CONFIG / SNMP_USER テーブル自体は MIB agent (`sonic_ax_impl`) が直接読まない。MIB agent は MIB ツリー用に COUNTERS_DB / STATE_DB / ASIC_DB を参照するのみ。

---

## 5. YANG / CONFIG_DB スキーマ: プラットフォーム非依存

`sonic-snmp.yang` は `type union` で `inet:ip-address-no-zone` と空文字・文字列パターンのみ定義し、プラットフォーム名 / ASIC ベンダーを一切参照しない。スキーマ制約はプラットフォーム共通。

---

## スキャン証跡

- `minigraph.py:2308-2324` — multi-ASIC 分岐コード精読
- `snmpd.conf.j2:16-34` — agentAddress テンプレート + コメント確認
- `start.sh:1-30` — コンテナ起動スクリプト全行確認
- `sonic_ax_impl/mibs/__init__.py:580-630` — multi-ASIC DB 接続初期化確認
- `test_cfggen.py:1158-1165` — single-ASIC テスト期待値確認
- device/ ディレクトリ — SNMP 固有デバイス設定ファイルなし (プラットフォーム非依存を確認)
