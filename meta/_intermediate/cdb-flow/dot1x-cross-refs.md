# DOT1X / PAC テーブル 暗黙参照スキャン (Phase C)

`docs/reference/config-db/dot1x.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソースは `sonic-net/sonic-buildimage/src/sonic-pac/` 以下の `pacmgr/pacmgr.cpp`、`hostapdmgr/hostapdmgr.cpp`、および `mabmgr/mabmgr.cpp`。

## スキャン手順

```bash
grep -n "m_conf\|addSelectable\|getSelectables\|m_vlan\|RADIUS\|MAB" \
    .cache/sonic-sources/sonic-buildimage/src/sonic-pac/pacmgr/pacmgr.cpp

grep -n "m_conf\|m_radius\|RADIUS\|MAB\|m_confHostapd" \
    .cache/sonic-sources/sonic-buildimage/src/sonic-pac/hostapdmgr/hostapdmgr.cpp
```

## 検出された暗黙参照テーブル

### pacmgrd が購読するテーブル (pacmgr.cpp:63-88)

`PacMgr::PacMgr()` のコンストラクタと `getSelectables()` で登録される購読テーブル:

| テーブル | DB | 参照箇所 | 用途 |
|---------|-----|---------|------|
| `PAC_PORT_CONFIG_TABLE` | CONFIG_DB | `m_confPacTbl` / pacmgr.cpp:64,82 | ポートごとの認証設定。主要購読テーブル |
| `PAC_GLOBAL_CONFIG_TABLE` | CONFIG_DB | `m_confPacGblTbl` / pacmgr.cpp:65,82 | PAC グローバル設定 |
| `HOSTAPD_GLOBAL_CONFIG_TABLE` | CONFIG_DB | `m_confPacHostapdGblTbl` / pacmgr.cpp:66,82 | dot1x グローバル enable/disable |
| `VLAN_TABLE` | CONFIG_DB | `m_confVlanTbl` / pacmgr.cpp:67,85 | VLAN 設定変化を authmgr に通知 |
| `VLAN_MEMBER_TABLE` | CONFIG_DB | `m_confVlanMemTbl` / pacmgr.cpp:68,86 | VLAN メンバー変化を authmgr に通知 |
| `VLAN_TABLE` (State) | STATE_DB | `m_vlanTbl` / pacmgr.cpp:69,83 | VLAN 作成/削除イベント (`VLAN_ADD_NOTIFY` / `VLAN_DELETE_PENDING_NOTIFY`) |
| `VLAN_MEMBER_TABLE` (State) | STATE_DB | `m_vlanMemTbl` / pacmgr.cpp:70,83 | VLAN ポートメンバー追加/削除イベント |

> `PAC_PORT_CONFIG_TABLE` 処理時に `fpGetIntIfNumFromHostIfName()` でインタフェース番号を取得する。この関数はプラットフォームインフラ (`fpinfra`) の内部テーブルを参照するため、**物理インタフェースの存在が前提条件**となる。インタフェース未登録の場合は `SWSS_LOG_NOTICE` 後 `continue` でスキップされ、リトライ機構はない。

### hostapdmgrd が購読するテーブル (hostapdmgr.cpp:43-70)

`HostapdMgr::HostapdMgr()` が購読するテーブル:

| テーブル | DB | 参照箇所 | 用途 |
|---------|-----|---------|------|
| `PAC_PORT_CONFIG_TABLE` | CONFIG_DB | `m_confHostapdPortTbl` / hostapdmgr.cpp:43 | ポートの `capabilities`/`control_mode`/`link_status` を読んで hostapd conf 生成可否を判断 |
| `HOSTAPD_GLOBAL_CONFIG_TABLE` | CONFIG_DB | `m_confHostapdGlobalTbl` / hostapdmgr.cpp:44 | `dot1x_system_auth_control` enable 時に全ポートの conf 生成を走査 |
| `RADIUS_SERVER` | CONFIG_DB | `m_confRadiusServerTable` / hostapdmgr.cpp:45 | RADIUS サーバ IP / ポート / key を `hostapd.conf` に埋め込む |
| `RADIUS` | CONFIG_DB | `m_confRadiusGlobalTable` / hostapdmgr.cpp:46 | RADIUS global key / NAS 設定 |

**RADIUS 依存の詳細**: `hostapdmgr.cpp:293, 169, 199` で `m_radiusServerInUse != ""` チェックを行い、RADIUS サーバが未設定の場合は `createConfFile()` を呼ばない。つまり `RADIUS_SERVER` テーブルが空の間は `dot1x_system_auth_control=true` を設定しても hostapd が起動しない。

### MAB 固有テーブル (mabmgr.cpp:35)

`mabmgrd` は `MAB_PORT_CONFIG_TABLE` を独立して購読する。PAC_PORT_CONFIG_TABLE / HOSTAPD_GLOBAL_CONFIG_TABLE とは**別プロセス**が管理する。

| テーブル | DB | 参照箇所 | 用途 |
|---------|-----|---------|------|
| `MAB_PORT_CONFIG_TABLE` | CONFIG_DB | `m_confMabPortTbl` / mabmgr.cpp:35 | MAB 有効化・認証タイプの設定 |

## 暗黙参照マップ (cross-refs ブロック記載内容)

| 参照方向 | このテーブル | 相手テーブル | 条件 / 説明 |
|---------|------------|------------|------------|
| PAC_PORT_CONFIG_TABLE → | `VLAN_TABLE` / `VLAN_MEMBER_TABLE` | `VLAN` / `VLAN_MEMBER` | pacmgrd が VLAN 変化を authmgr に通知するため間接依存 |
| PAC_PORT_CONFIG_TABLE → | `RADIUS_SERVER` / `RADIUS` | `RADIUS` 系 | hostapdmgrd が RADIUS 未設定時は hostapd を起動しない |
| PAC_PORT_CONFIG_TABLE → | `MAB_PORT_CONFIG_TABLE` | `MAB_PORT_CONFIG` | MAB 有効化は別テーブル／別プロセス (mabmgrd) が管理 |
| YANG | `sonic-pac` YANG なし | — | YANG モデル未定義。REST/gNMI 経路なし |

## 検証コマンド

```bash
grep -n "m_conf\|addSelectable\|getSelectables" \
    .cache/sonic-sources/sonic-buildimage/src/sonic-pac/pacmgr/pacmgr.cpp

grep -n "m_radiusServerInUse\|createConfFile\|m_conf" \
    .cache/sonic-sources/sonic-buildimage/src/sonic-pac/hostapdmgr/hostapdmgr.cpp

grep -n "m_confMabPortTbl\|MAB_PORT_CONFIG" \
    .cache/sonic-sources/sonic-buildimage/src/sonic-pac/mabmgr/mabmgr.cpp
```

Evidence: `sonic-pac/pacmgr/pacmgr.cpp:63-88`; `sonic-pac/hostapdmgr/hostapdmgr.cpp:43-70,145-170,285-300`; `sonic-pac/mabmgr/mabmgr.cpp:35`
