# PORT テーブル — Phase B: 書込み順依存調査メモ

調査日: 2026-05-14
対象: `docs/reference/config-db/port.md`

---

## 1. 先行必須テーブル (SET 時)

### BUFFER_POOL / BUFFER_PG が先行必須
- `portsorch.cpp:4779` — `gBufferOrch->isPortReady(pCfg.key)` が false の間、PORT の SET 処理を中断 (`m_pendingPortSet` に保留)。
- `bufferorch.cpp:254-274` — `BufferOrch::isPortReady()` は `m_ready_list` で per-port のバッファ設定完了フラグを管理。
- **結論**: BUFFER_POOL → BUFFER_PG が CONFIG_DB に書き込まれ BufferOrch が ready と判定するまで、PORT テーブルの SET はハードウェアに反映されない。

### portsyncd が CONFIG_DB を読む前提
- `portsyncd.cpp:179-216` — portsyncd 起動時に CONFIG_DB の PORT テーブルを全件読み込んで APP_PORT_TABLE に書き込み、その後 `PortConfigDone` を通知する。
- **boot order**: `portsyncd` が CONFIG_DB の PORT を読み出す → `PortConfigDone` 通知 → `PortsOrch` が `PORT_CONFIG_DONE` 状態へ → SAI `create_port()` → `PortInitDone` 通知 → `allPortsReady()=true` → 他 orch がアンブロック。
- MACSEC_PROFILE、VLAN、INTERFACE などは `allPortsReady()` 後にしか処理されない (`portsorch.cpp:6513-6517`)。

### MACSEC_PROFILE が先行 (論理的依存)
- `PORT.macsec` は YANG leafref で `MACSEC_PROFILE.name` を参照。
- macsec フィールドを PORT に SET する前に MACSEC_PROFILE エントリが存在しないと YANG バリデーション失敗。
- 実行時は `macsecmgrd` が参照を確認してセッション確立するため、MACSEC_PROFILE が先行必須。

---

## 2. SET → SET 順 (フィールド適用順)

`PortsOrch::doTask()` 内の適用順序（`portsorch.cpp:4800` 以降）:

1. `autoneg` — 変更時はまず `setPortAdminStatus(p, false)` でポートを一時 down にする (`portsorch.cpp:4827`)
2. `link_training`
3. `speed` — autoneg=off かつ admin_status=up 時はポートを一時 down にしてから変更 (`portsorch.cpp:5034-5050`)
4. `adv_speeds` / `adv_interface_types` / `interface_type`
5. `fec` — `auto` モードは `SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE` 未サポートプラットフォームで `task_failed`
6. `mtu`
7. `pfc_asym`
8. `tpid`
9. `admin_status` — **最後**に適用。speed/fec/autoneg 完了後に CONFIG_DB の値に戻す (`portsorch.cpp:5500-5529`)

**重要**: speed / autoneg / link_training を変更すると一時リンクフラップが発生する。対向装置との事前調整が必要。

---

## 3. DEL 順 (先に削除が必要なエントリ)

PORT を DEL するには `m_port_ref_count[alias] == 0` が必要 (`portsorch.cpp:5649-5653`)。

ref_count を増加させるもの (DEL 前に先に削除が必要):
- `INTERFACE` テーブル (`intfsorch.cpp:498`) — L3 インタフェースが残っていると ref_count > 0
- `BUFFER_PG` / `BUFFER_QUEUE` (`bufferorch.cpp:1175,1546`) — バッファ設定が残っていると ref_count > 0
- VLAN メンバシップ — `bridge_port_oid != SAI_NULL_OBJECT_ID` の場合は DEL 拒否 (`portsorch.cpp:5661-5669`)
- LAG メンバシップ — PORTCHANNEL_MEMBER を先に削除する必要あり
- `PORT_SERDES` — removePort() 実行前に `removePortSerdesAttribute()` が呼ばれる (内部自動処理)

**DEL の正しい順序**:
1. VLAN_MEMBER DEL (VLAN からポートを除外)
2. PORTCHANNEL_MEMBER DEL (LAG からポートを除外)
3. INTERFACE DEL (L3 設定を削除)
4. BUFFER_PG / BUFFER_QUEUE DEL (バッファ設定を削除)
5. PORT DEL

---

## 4. restart / warm-reboot 影響

### cold reboot / daemon restart
- portsyncd 再起動時は CONFIG_DB を再読み込みして `PortConfigDone` を再送信。orcahgent が重複通知を検出して無視 (`portsorch.cpp:4589-4596`)。
- portmgrd は stateless であり再起動後に CONFIG_DB を再購読して全設定を再適用。

### warm reboot
- `portsyncd.cpp:82,205,211` — `WarmStart::isWarmStart()` が true の場合、portsyncd は CONFIG_DB から読んでも APP_PORT_TABLE に書き込まない（`p.set(k, attrs)` をスキップ）し `PortConfigDone` も送信しない。
- `portsorch.cpp:4342-4396` — warm reboot 時は APP_DB の `PortConfigDone` / `PortInitDone` の有無で既存ポートテーブルを再利用。見つからない場合は `cleanPortTable()` して cold start にフォールバック。
- `portsorch.cpp:6609` — warm reboot 復元時にポートの `oper_status` / `flap_count` を STATE_DB から引き継ぐ。
- **結論**: warm reboot 中は PORT テーブルへの新規書き込みは処理保留になる。フラップなしで復元が完了した後に通常の subscribe 処理が再開される。

### fast reboot
- fast reboot では kernel / hardware の状態を保持したまま再起動するため、portsyncd は cold start と同じ手順で PORT テーブルを処理する（特別分岐なし）。

---

## 5. boot order 依存 (起動時シーケンス)

```
[起動時]
platform プロセス (pmon) が port_config.ini / minigraph を読んで CONFIG_DB|PORT を生成
  ↓
portsyncd 起動 → CONFIG_DB|PORT 全件読み → APP|PORT 書込み → PortConfigDone
  ↓
PortsOrch (orchagent) が PortConfigDone を受信 → SAI create_port() bulk → PORT_CONFIG_DONE
  ↓
netdev が kernel に生成される → PortInitDone (portsyncd が netlink で検出)
  ↓
PortsOrch が PortInitDone を受信 → m_initDone=true
  ↓
gBufferOrch->isPortReady() が true になる (BufferOrch が BUFFER_PG 処理完了後)
  ↓
allPortsReady() = true → VLAN/LAG/INTERFACE/ACL などの他 orch がアンブロック
```

**重要**: orchList の先頭は `gSwitchOrch`, `gCrmOrch`, `gPortsOrch`, `gBufferOrch` の順 (`orchdaemon.cpp:500`)。PortsOrch は 3 番目だが、BufferOrch が ready を返すまで PORT の最終反映は保留される。

---

## 6. PORT 作成時 CreateOnly 属性順序 (addPortBulk)

`PortsOrch::addPortBulk()` (`portsorch.cpp:1248-`) で SAI `create_port()` に渡す属性は以下の順序で `attrList` に積まれる。CreateOnly 属性のためポート作成後は変更不可。

1. `SAI_PORT_ATTR_HW_LANE_LIST` (`lanes.is_set` が true のとき) — `portsorch.cpp:1292`
2. `SAI_PORT_ATTR_SPEED` (`speed.is_set` が true のとき) — `portsorch.cpp:1300`
3. `SAI_PORT_ATTR_AUTO_NEG_MODE` (`autoneg.is_set` が true のとき) — `portsorch.cpp:1308`
4. `SAI_PORT_ATTR_FEC_MODE` + `SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE` (`fec.is_set` のとき) — `portsorch.cpp:1318`
5. `SAI_PORT_ATTR_TPID` (`tpid != 0x8100` のとき) — `portsorch.cpp:1337-1344`

HW_LANE_LIST と SPEED は SAI mandatory 属性。lanes/speed なしで create_port() するとエラー。tpid=0x8100(デフォルト)は属性リストに追加しない。

---

## 7. Dynamic Port Breakout (DPB) シーケンス

PORT テーブルの再書き込みにより breakout を実現する。`doTask()` が PORT_CONFIG_RECEIVED を受信したとき:

1. `removePortBulk()` — `m_portListLaneMap` から消えたレーン構成を持つポートを一括削除 (`portsorch.cpp:4703-4718`)
2. `addPortBulk()` — `m_lanesAliasSpeedMap` に新規追加されたレーン構成のポートを一括作成 (`portsorch.cpp:4725-4748`)
3. `initPortsBulk()` — バッファカウンタ・PG・serdes などを初期化

DEL が ADD より先に実行される。同一 doTask() 内でアトミックに処理される。

**副作用**: `addSubPort()` は最初のサブポート追加時に親 hostif の VLAN tag を変更 (`portsorch.cpp:2059`)、最後のサブポート削除時に復元 (`portsorch.cpp:2122`)。

---

## 8. host_tx_ready 同期メカニズム

STATE_DB の `PORT_TABLE|<alias>.host_tx_ready` フィールド管理:

### 初期化
- `initPortsBulk()` → `initHostTxReadyState()` が STATE_DB に `host_tx_ready` がなければ `"false"` で初期化 (`portsorch.cpp:5494`)。

### レガシーモード (`m_cmisModuleAsicSyncSupported == false`)
`setPortAdminStatus()` 内で同期的に更新 (`portsorch.cpp:2213-2274`):
- admin_status=down 設定前: `"false"` に設定
- SAI/gearbox エラー時: `"false"` に設定
- admin_status=up かつ SAI/gearbox 成功後: `"true"` に設定

### CMIS Async モード (`m_cmisModuleAsicSyncSupported == true`)
SAI コールバック `on_port_host_tx_ready` が非同期通知 → `setHostTxReady()` で STATE_DB 更新 (`portsorch.cpp:9709-9724`)。admin_status 変更時は `host_tx_ready` を直接変更しない。両モードの切り替えは `SAI_SWITCH_ATTR_RW_HW_TX_SIGNAL_SUPPORT` と `SAI_SWITCH_ATTR_PORT_HOST_TX_READY_NOTIFY` 両属性のサポート有無で決まる (`portsorch.cpp:969-980`)。

---

## ソース証跡

| 知見 | ファイル | 行 |
|------|---------|-----|
| gBufferOrch->isPortReady() ブロック | `portsorch.cpp` | 4779 |
| m_port_ref_count DEL ガード | `portsorch.cpp` | 5649 |
| bridge_port_oid DEL ガード | `portsorch.cpp` | 5661 |
| admin_status 最後に適用 | `portsorch.cpp` | 5500-5529 |
| autoneg 変更時一時 down | `portsorch.cpp` | 4827 |
| allPortsReady() ブロック | `portsorch.cpp` | 6514 |
| warm reboot APP_DB チェック | `portsorch.cpp` | 4342-4396 |
| portsyncd warm skip | `portsyncd.cpp` | 205,211 |
| orchList 順序 | `orchdaemon.cpp` | 500 |
| intfsOrch ref_count 増加 | `intfsorch.cpp` | 498 |
| bufferOrch ref_count 増加 | `bufferorch.cpp` | 1175,1546 |
| addPortBulk CreateOnly attrs 順序 | `portsorch.cpp` | 1292-1344 |
| DPB removePortBulk → addPortBulk 順序 | `portsorch.cpp` | 4703-4748 |
| addSubPort hostif vlan tag 変更 | `portsorch.cpp` | 2059,2122 |
| initHostTxReadyState (false 初期化) | `portsorch.cpp` | 5494 |
| host_tx_ready admin_status 連動 | `portsorch.cpp` | 2213-2274 |
| host_tx_ready CMIS async コールバック | `portsorch.cpp` | 9709-9724 |
| CMIS Async モード判定 | `portsorch.cpp` | 969-980 |
