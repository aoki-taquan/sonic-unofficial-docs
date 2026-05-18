# vlan-state Phase E — hardcoded-constants 調査メモ

調査日: 2026-05-18
対象: `STATE_DB VLAN_TABLE` の書き込み主体 `vlanmgrd`
ソース: `sonic-net/sonic-swss cfgmgr/vlanmgr.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## 発見したハードコード定数

### vlanmgr.cpp 上部 #define

| 定数名 | 値 | 用途 |
|--------|-----|------|
| `DOT1Q_BRIDGE_NAME` | `"Bridge"` | Linux の dot1q bridge デバイス名。全 VLAN が所属する親ブリッジ |
| `VLAN_PREFIX` | `"Vlan"` | Linux VLAN インタフェース名プレフィックス（`Vlan100` など） |
| `DEFAULT_VLAN_ID` | `"1"` | dot1q bridge 作成時に削除する PVID（デフォルト VLAN ID 1 をブリッジから除去する） |
| `DEFAULT_MTU_STR` | `"9100"` | ブリッジ作成時の初期 MTU (bytes)。CONFIG_DB `PORT.mtu` とは独立したハードコード値 |
| `VLAN_HLEN` | `4` | VLAN ヘッダ長 (bytes)。コード中で直接利用箇所は少ないが定義されている |

出典: `vlanmgr.cpp:15-20`

### DEFAULT_MTU_STR = "9100" の影響

`addHostVlan()` 内で `/sbin/ip link set Bridge mtu 9100` を実行する (vlanmgr.cpp:96)。
これはブリッジ自体の MTU であり、個々の `Vlan<N>` インタフェースの MTU は CONFIG_DB `PORT.mtu` から orchagent → SAI → カーネルの経路で設定される（別経路）。

したがって、**STATE_DB への書き込みに直接影響するパラメータではない**が、VLAN 作成コマンドの一部として埋め込まれている。

### DOT1Q_BRIDGE_NAME = "Bridge" の唯一性

SONiC では全 VLAN が `Bridge` という名前の単一の dot1q ブリッジに所属する。
このブリッジ名はコード中でリテラルとして多用されており、変更不可（設定化されていない）。

### DEFAULT_VLAN_ID = "1" の削除

dot1q ブリッジ作成直後に `bridge vlan del vid 1 dev Bridge self` を実行して PVID=1 を明示的に除去する。
これにより、VLAN 1 へのフォールスルーを防ぐ（SONiC は VLAN 1 をデフォルト VLAN として使用しない設計）。

### VLAN ID 検証の非明示的な範囲

`doVlanTask()` L342: `vlan_id = stoi(key.substr(4))` — 数値であること以外の範囲チェックはコードに存在しない。
Linux カーネルの dot1q は 2–4094 の範囲を有効とするため、`0`, `1`, `4095` を渡すとカーネルコマンドが失敗して `addHostVlan()` が例外を throw する。
**STATE_DB VLAN_TABLE のキーが `Vlan1` や `Vlan0` になることはない** — カーネルが拒否して vlanmgrd が再起動するため。

## STATE_DB 書き込み時のハードコード文字列

`doVlanTask()` L443: `m_stateVlanTable.set(key, {{"state","ok"}})` — `"state"` と `"ok"` の両方がコード中のリテラル。
YANG 定義は存在しないため、フィールド名・値ともに YANG スキーマによる検証外。
