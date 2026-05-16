# PORTCHANNEL 暗黙参照調査 (Phase C)

生成日: 2026-05-15  
対象ページ: `docs/reference/config-db/portchannel.md`

## 調査概要

`PORTCHANNEL` テーブルが暗黙的に参照する（または参照される）周辺 CONFIG_DB テーブル・DB テーブルを
ソースコードから列挙した。

---

## A. PORTCHANNEL が参照するテーブル（PORTCHANNEL → X）

### A-1. PORT (CONFIG_DB)

- **経路**: `TeamMgr::addLag()` が `m_cfgPortTable` で PORT エントリの存在を確認する。
- **証跡**: `sonic-swss/cfgmgr/teammgr.cpp:32` `m_cfgPortTable(confDb, CFG_PORT_TABLE_NAME)` および `:212-225`。
- **影響**: PORT エントリが存在しない場合 `task_need_retry` → LAG 作成保留。
- **追加制約**: PORTCHANNEL_MEMBER add 時、member ポートの `tpid` が `0x8100` でなければ拒否（`config/main.py:2993-2996`）。

### A-2. DEVICE_METADATA (CONFIG_DB)

- **経路**: `TeamMgr` コンストラクタが `m_cfgMetadataTable(confDb, CFG_DEVICE_METADATA_TABLE_NAME)` を購読し、`mac` フィールドを読み込んで LAG の hwaddr に使用する。
- **証跡**: `teammgr.cpp:31,56,64` `m_mac = MacAddress(it->second)`.
- **影響**: warm reboot 時は boot 時の LAG MAC を維持するために `mac` を参照（`:574-606`）。

---

## B. PORTCHANNEL を参照するテーブル（X → PORTCHANNEL）

### B-1. PORTCHANNEL_MEMBER (CONFIG_DB)

- **経路**: PORTCHANNEL DEL 前に PORTCHANNEL_MEMBER が空であることを確認する（CLI ガード `config/main.py:2890`）。
- **エラー**: `Failed to remove non-empty LAG %s` (orchagent) / `Error: Portchannel {} contains members.` (CLI)。
- **また**: PORTCHANNEL_MEMBER add 時、member ポートに ACL / PBH バインドがないことを確認 (`main.py:2997-3010`)。
- **doc**: `docs/reference/config-db/portchannel-member.md`

### B-2. PORTCHANNEL_INTERFACE (CONFIG_DB)

- **経路**: PORTCHANNEL DEL 前に L3 interface 設定を削除しなければ `ref_count > 0` エラー。
- **エラー**: `Failed to remove ref count %d LAG %s` (orchagent).
- **doc**: `docs/reference/config-db/portchannel-interface.md`

### B-3. VLAN_MEMBER (CONFIG_DB)

- **経路**: PORTCHANNEL DEL 前に VLAN_MEMBER から当該 LAG の参照を削除する必要がある（CLI ガード `config/main.py:2886-2888`）。
- **エラー**: `Failed to remove LAG %s, it is still in VLAN` (orchagent) / `has vlan {} configured, remove vlan membership to proceed` (CLI)。
- **doc**: `docs/reference/config-db/vlan-member.md`

### B-4. ACL_TABLE (CONFIG_DB)

- **経路**: `config portchannel member add` 時に `get_port_acl_binding()` で member ポートの ACL バインドを確認。バインドがあれば追加拒否。
- **証跡**: `sonic-utilities/config/main.py:2997-3002`.
- **YANG 注記**: `# TODO: MISSING CONSTRAINT IN YANG MODEL` — YANG には対応制約なし。
- **doc**: `docs/reference/config-db/acl-table.md`

### B-5. PBH (PBH_TABLE, CONFIG_DB)

- **経路**: `config portchannel member add` 時に `get_port_pbh_binding()` で member ポートの PBH バインドを確認。バインドがあれば追加拒否。
- **証跡**: `sonic-utilities/config/main.py:3005-3010`.
- **YANG 注記**: `# TODO: MISSING CONSTRAINT IN YANG MODEL`.
- **doc**: `docs/reference/config-db/pbh.md`

### B-6. MCLAG_DOMAIN / MCLAG_INTERFACE (CONFIG_DB)

- **経路**: `config mclag add` の `peer_link` フィールドに PortChannel 名を指定可能。`is_portchannel_name_valid()` で名前バリデーション実施。
  `config mclag member add` で MCLAG_INTERFACE エントリに `if_type=PortChannel` として LAG を登録。
- **証跡**: `sonic-utilities/config/mclag.py:145,293`.
- **影響**: PORTCHANNEL が MCLAG の peer-link または member として使用されている場合、削除順序に注意が必要。
- **doc**: `docs/reference/config-db/mclag-domain.md`

---

## C. STATE_DB 連動（参照・書込み）

### C-1. STATE_PORT_TABLE (STATE_DB)

- **経路**: `TeamMgr` が `m_statePortTable(statDb, STATE_PORT_TABLE_NAME)` を購読 (`teammgr.cpp:37,165`)。
  ポート状態変化（`STATE_PORT_TABLE_NAME` イベント）で LAG メンバーの再評価をトリガー。
- **影響**: ポートが STATE_DB に登録されていないと LAG メンバー追加が保留。

### C-2. STATE_LAG_TABLE (STATE_DB)

- **経路**: `TeamMgr` が `m_stateLagTable(statDb, STATE_LAG_TABLE_NAME)` に LAG 状態を書き込む (`teammgr.cpp:38`)。
- **影響**: `show interfaces portchannel` が STATE_LAG_TABLE を参照して LAG up/down を表示。

### C-3. STATE_MACSEC_INGRESS_SA_TABLE (STATE_DB)

- **経路**: `TeamMgr` が `m_stateMACsecIngressSATable(statDb, STATE_MACSEC_INGRESS_SA_TABLE_NAME)` を保持 (`teammgr.cpp:39`)。
  MACsec が有効な場合に teamd conf で `macsec` オプションを設定 (`:116-117`)。
- **影響**: PORTCHANNEL に `macsec` フィールドが設定されているとき STATE_MACSEC_INGRESS_SA_TABLE と連動。

---

## D. 制約なし確認（明示的に排除したもの）

| テーブル | 判定 | 根拠 |
|---------|------|------|
| STP (PORTCHANNEL_MEMBER → STP_PORT) | 直接参照なし | stp は別経路; PORTCHANNEL は STP_PORT key ではない |
| MIRROR_SESSION | 直接参照なし | ミラーは INTERFACE/PORT 経由 |
| FG_NHG | 直接参照なし | FG_NHG は PORTCHANNEL_INTERFACE 経由で暗黙参照 |

---

## E. 暗黙参照のまとめ（cross-refs ブロック用）

```
PORTCHANNEL → PORT            (addLag 前のポート存在確認)
PORTCHANNEL → DEVICE_METADATA (システム MAC 取得)
PORTCHANNEL ← PORTCHANNEL_MEMBER (非空 LAG 削除ガード)
PORTCHANNEL ← PORTCHANNEL_INTERFACE (ref_count 削除ガード)
PORTCHANNEL ← VLAN_MEMBER    (VLAN 所属 LAG 削除ガード)
PORTCHANNEL ← ACL_TABLE      (メンバー追加前 ACL バインドチェック)
PORTCHANNEL ← PBH            (メンバー追加前 PBH バインドチェック)
PORTCHANNEL ← MCLAG_DOMAIN/MCLAG_INTERFACE (peer-link / MLAG member)
PORTCHANNEL → STATE_PORT_TABLE (ポート初期化待ち)
PORTCHANNEL → STATE_LAG_TABLE  (LAG 状態書込み)
PORTCHANNEL → STATE_MACSEC_INGRESS_SA_TABLE (MACsec 有効時)
```

---

## F. 証跡ソース一覧

| ファイル | 行番号 | 内容 |
|---------|--------|------|
| `sonic-swss/cfgmgr/teammgr.cpp` | 31-39 | Table 初期化: PORT, DEVICE_METADATA, STATE_PORT/LAG/MACSEC |
| `sonic-swss/cfgmgr/teammgr.cpp` | 116-117 | macsec フィールド参照 |
| `sonic-swss/cfgmgr/teammgr.cpp` | 165 | STATE_PORT_TABLE 購読 |
| `sonic-utilities/config/main.py` | 2886-2890 | DEL ガード: VLAN_MEMBER, PORTCHANNEL_MEMBER |
| `sonic-utilities/config/main.py` | 2997-3010 | ADD ガード: ACL_TABLE, PBH |
| `sonic-utilities/config/mclag.py` | 145,293 | MCLAG peer-link / member PortChannel 参照 |
