# portchannel-state ordering 調査ノート

## 調査対象
- `sonic-swss/teamsyncd/teamsync.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/cfgmgr/teammgr.cpp`
- `sonic-swss/cfgmgr/intfmgr.cpp`
- `sonic-swss/cfgmgr/vlanmgr.cpp`
- `sonic-swss/cfgmgr/stpmgr.cpp`

## 調査日
2026-05-18

## 概要

STATE_DB `LAG_TABLE` は **teamsyncd** が書き込む（CONFIG_DB → teamd → カーネル → teamsyncd → STATE_DB の流れ）。
複数のデーモンがこのテーブルを readiness ガードとして参照し、`state=ok` が存在するまで後続処理を保留する。

## 書き込みシーケンス（teamsyncd が LAG_TABLE を書く前に必要な事前条件）

1. **CONFIG_DB `PORTCHANNEL` エントリが存在すること**
   - `TeamMgr::doLagTask()` (`teammgr.cpp:L157-`) が `PORTCHANNEL` SET を受信
2. **`teammgrd` が `addLag()` を実行して teamd プロセスを起動すること**
   - `TeamMgr::addLag()` (`teammgr.cpp:L564-`) が `teamd` を `exec()` で起動
   - 失敗時は `task_need_retry` → STATE_DB 未書き込みのまま
3. **Linux カーネルが `RTM_NEWLINK` を発行すること**
   - teamd が `/sys/class/net/PortChannelN` を作成するとカーネルが RTM_NEWLINK を送信
4. **`teamsyncd` が `RTM_NEWLINK` を受信すること**
   - `TeamSync::onMsg()` → `addLag()` → `m_stateLagTable.set(lagName, fvVector)` で `state=ok` を書き込む

## warm-restart 時の特例

- `m_warmstart == true` の場合、`m_stateLagTable.set()` を直接呼ばず `m_stateLagTablePreserved` に一時保存
- `applyState()` (`teamsync.cpp:L84-98`) が設定済みタイムアウト経過後に一括書き込み
- warm-restart 中は `state=ok` が遅延して書き込まれるため、読み取り側デーモンはより長く待機することになる

## 読み取り側デーモン一覧（LAG_TABLE を readiness ガードとして使用）

| デーモン | 関数 | 参照箇所 | 用途 |
|---------|------|---------|------|
| `intfmgrd` | `IntfMgr::isIntfStateOk(alias)` | `intfmgr.cpp:L661-668` | `PORTCHANNEL_INTERFACE` / `LAG_INTERFACE` SET 前に LAG readiness 確認 |
| `teammgrd` | `TeamMgr::isLagStateOk(alias)` | `teammgr.cpp:L89-103` | `PORTCHANNEL_MEMBER` SET 前に LAG readiness 確認 |
| `vlanmgrd` | `VlanMgr::isMemberStateOk(alias)` | `vlanmgr.cpp:L490-510` | VLAN_MEMBER に LAG を追加する前に readiness 確認 |
| `stpmgrd` | `StpMgr::isLagStateOk(alias)` | `stpmgr.cpp:L1292-1304` | STP ポート処理前に LAG readiness 確認 |

## DEL の連鎖

teamsyncd が `RTM_DELLINK` を受信すると `removeLag()` を呼び `m_stateLagTable.del(lagName)` でエントリを削除する (`teamsync.cpp:L228-255`)。
その後、`isIntfStateOk()` / `isLagStateOk()` を呼ぶすべてのデーモンが依存処理を停止する。
`PORTCHANNEL_INTERFACE` や `VLAN_MEMBER` に対応するエントリが残存している場合、該当デーモンは SET を永続的にキューに積んだままとなる（手動再設定が必要）。
