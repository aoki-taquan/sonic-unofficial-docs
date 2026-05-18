# DOT1X / PAC テーブル — Phase F 副次 DB 書込スキャンノート

生成日: 2026-05-18 (q67-f-batch243-next)
対象テーブル: `PAC_PORT_CONFIG_TABLE`, `HOSTAPD_GLOBAL_CONFIG_TABLE`
Consumer: `pacmgrd` (`sonic-pac/pacmgr/pacmgr.cpp`), `hostapdmgrd` (`sonic-pac/hostapdmgr/hostapdmgr.cpp`)

---

## 副次 DB 書込調査

### pacmgrd — APPL_DB / STATE_DB 書込み

`pacmgr.cpp` 全体を `Producer`/`set(`/`hset(`/`Table.set(` で検索した結果、pacmgrd は CONFIG_DB の `PAC_PORT_CONFIG_TABLE` / `HOSTAPD_GLOBAL_CONFIG_TABLE` を読み取り **authmgr ライブラリ API (`authmgr*Set()`) に直接渡す**だけで、APPL_DB / STATE_DB / COUNTERS_DB への書き込みは行わない。

| 副次 DB | 書込有無 | 根拠 |
|---|---|---|
| APPL_DB | なし | `pacmgr.cpp` に `ProducerStateTable`/`ProducerTable` のインスタンス化なし |
| STATE_DB | なし | `m_stateDb` が constructor で受け取られるが `processPacPortConfTblEvent` / `processPacHostapdConfGlobalTblEvent` の内部では read-only 参照なし |
| COUNTERS_DB | なし | `pacmgr.cpp` に COUNTERS_DB 接続コードなし |
| ASIC_DB | なし | SAI 非経由。authmgr ライブラリは FDB/VLAN 操作を別経路で行う |

### hostapdmgrd — APPL_DB / STATE_DB 書込み

`hostapdmgr.cpp` 全体を `Producer`/`Table.set(` で検索した結果、hostapdmgrd も DB への書き込みは行わない。副作用はファイルシステムへの conf 生成と hostapd プロセスへの通知に閉じる。

| 副次 DB | 書込有無 | 根拠 |
|---|---|---|
| APPL_DB | なし | `hostapdmgr.cpp` に DB 書き込みコードなし |
| STATE_DB | なし | 同上 |

---

## 設定変更時の実行時副作用（非 DB）

CONFIG_DB の変更は以下の実行時副作用を引き起こす。DB への書込みではないが運用上重要。

### `dot1x_system_auth_control=true` 設定時 (HOSTAPD_GLOBAL_CONFIG_TABLE)

**pacmgrd 側**:
- `authmgrPortClientAuthStatusUpdate(ALL_INTERFACES, AUTHMGR_METHOD_8021X, AUTHMGR_METHOD_CHANGE, ...)` は呼ばれない（`true` 設定時は internal state をセットするのみ、`pacmgr.cpp:1160-1163`）

**hostapdmgrd 側**:
- `m_intf_info` を走査し、`capabilities=authenticator` かつ `control_mode=auto` かつ `link_status=true` かつ `config_created=false` かつ `m_radiusServerInUse != ""` なポートすべての hostapd conf ファイルを生成 (`createConfFile()`)
- `informHostapd("new", interfaces)` を呼び hostapd プロセスに新規インタフェース群を通知
- evidence: `hostapdmgr.cpp:285-307`

### `dot1x_system_auth_control=false` 設定時 (HOSTAPD_GLOBAL_CONFIG_TABLE)

**pacmgrd 側**:
- `authmgrPortClientAuthStatusUpdate(ALL_INTERFACES, AUTHMGR_METHOD_8021X, AUTHMGR_METHOD_CHANGE, {enableStatus=FALSE})` を呼び出し、**全ポートの 802.1x 認証セッションを即時終了**させる
- evidence: `pacmgr.cpp:1172-1176`

**hostapdmgrd 側**:
- `m_intf_info` を走査し `config_created=true` なポートの hostapd conf ファイルをすべて削除 (`deleteConfFile()`)
- `informHostapd("deleted", interfaces)` を呼び hostapd プロセスに全インタフェース削除を通知
- evidence: `hostapdmgr.cpp:312-335`

### `port_control_mode` 変更時 (PAC_PORT_CONFIG_TABLE)

- `authmgrPortControlModeSet(intIfNum, newMode)` を呼び出し。authmgr ライブラリが当該ポートの認証状態マシンに変更を通知
- `force-unauthorized` に変更した場合、既存認証済みクライアントのトラフィックがブロックされる
- evidence: `pacmgr.cpp:452-460`

### `port_pae_role` 変更時 (PAC_PORT_CONFIG_TABLE)

- `authmgrDot1xCapabilitiesUpdate(intIfNum, newRole)` を呼び出し、EAPoL 送受信の有効/無効を即座に切り替える
- `none` に変更すると実行中の EAPoL 認証セッションが中断される
- evidence: `pacmgr.cpp:551-563`

---

## 証跡

`sonic-buildimage/src/sonic-pac/pacmgr/pacmgr.cpp:63-89,1160-1177`
`sonic-buildimage/src/sonic-pac/hostapdmgr/hostapdmgr.cpp:260-346`
