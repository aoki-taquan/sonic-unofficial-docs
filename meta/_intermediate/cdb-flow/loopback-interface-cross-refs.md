# LOOPBACK_INTERFACE — Phase C 暗黙参照スキャンノート

対象テーブル: `LOOPBACK_INTERFACE`
Consumer: `intfmgrd` / `orchagent IntfsOrch` (`sonic-swss/cfgmgr/intfmgr.cpp`, `sonic-swss/orchagent/intfsorch.cpp`)
スキャン範囲: `IntfMgr` コンストラクタ、`doIntfGeneralTask()`、`doIntfAddrTask()`、`IntfsOrch::doTask()`、`IntfsOrch::setIntf()` 全行精読
調査日: 2026-05-18

---

## 検出した暗黙参照

### 1. STATE_VRF_TABLE — VRF ready チェック (`intfmgr.cpp:839-842`)

`vrf_name` が非空のとき `isIntfStateOk(vrf_name)` → `m_stateVrfTable.get(vrf_name, temp)` で
STATE_DB `STATE_VRF_TABLE` を読む。エントリがなければ処理を保留してリトライ。
YANG leafref は CONFIG_DB の `VRF` テーブルを指すが、intfmgrd の readiness guard は STATE_DB 側を参照する。

### 2. STATE_INTF_TABLE — VRF 変更禁止チェック (`intfmgr.cpp:846-849`)

既に同 alias の STATE_INTF_TABLE エントリに `vrf` フィールドが書かれている場合、
`isIntfChangeVrf(alias, vrf_name)` が `true` を返し、変更を ERROR ログで拒否する。
CONFIG_DB を書き替えてもこのガードにより STATE_DB と不整合が生じる可能性がある。

### 3. STATE_INTERFACE_TABLE — IP プレフィクスロウの前提 (`intfmgr.cpp:1115`)

`doIntfAddrTask()` SET パスで `isIntfCreated(alias)` → `m_stateIntfTable.get(alias, temp)` を参照。
STATE_DB に属性ロウのエントリがなければ IP プレフィクスロウの処理をスキップしてリトライ。
属性ロウ SET が完了して `m_stateIntfTable.hset(alias, "vrf", …)` が書かれた後でないと
IP アドレス設定が進まない。

### 4. DEVICE_METADATA.switch_type — 起動時 1 回読み (`intfmgr.cpp:70-75`)

`IntfMgr` コンストラクタで `cfgDeviceMetaDataTable.hget("localhost", "switch_type", swtype)` を呼ぶ。
`mySwitchType == "voq"` のとき IPv6 アドレス付与コマンドに `metric 256` を付与。
CONFIG_DB の DEVICE_METADATA が設定前に intfmgrd が起動すると空文字列のまま固定される
（起動後の変更は反映されない）。

### 5. VrfOrch::isVRFexists() — orchagent 側 VRF 存在確認 (`intfsorch.cpp:826-831`)

Loopback ではない SET の場合、orchagent は `m_vrfOrch->isVRFexists(vrf_name)` を確認する。
VRF が orchagent の内部マップ `m_vrfTable` に存在しなければ `it++; continue;` でリトライ。
Loopback の `is_lo == true` パスでは `m_syncdIntfses` への直接書込みで VrfOrch 確認を迂回するが、
`vrf_id` は `m_vrfOrch->getVRFid(vrf_name)` から取得するため VrfOrch への暗黙依存は残る。

### 6. DEVICE_METADATA.mac → gMacAddress (`intfsorch.cpp:1205`)

Loopback IF の `mac_addr` が未設定（`00:00:00:00:00:00`）のとき、orchagent は
グローバル変数 `gMacAddress` をフォールバックとして SAI `SAI_ROUTER_INTERFACE_ATTR_SRC_MAC_ADDRESS` に設定。
`gMacAddress` は orchagent 起動時に `DEVICE_METADATA.localhost.mac` から一度読み込まれる。

### 7. NAT_GLOBAL → gIsNatSupported (`intfsorch.cpp:1287-1294`)

`nat_zone` フィールドが指定されていても `gIsNatSupported == false`（NAT 無効プラットフォーム）の場合、
SAI `SAI_ROUTER_INTERFACE_ATTR_NAT_ZONE_ID` は設定されない。
Loopback に `nat_zone` を設定するユースケースは稀だが、このガードは常時有効。

---

## 暗黙参照サマリ

| # | 参照先 | DB / 場所 | 方向 | 契機 | 根拠コード |
|---|--------|-----------|------|------|-----------|
| 1 | `STATE_VRF_TABLE` | STATE_DB | READ | `vrf_name` 指定時の readiness ガード | `intfmgr.cpp:839-842` |
| 2 | `STATE_INTF_TABLE` | STATE_DB | READ | VRF 変更禁止チェック | `intfmgr.cpp:846-849` |
| 3 | `STATE_INTERFACE_TABLE` | STATE_DB | READ | IP プレフィクスロウ処理の前提確認 | `intfmgr.cpp:1115` |
| 4 | `DEVICE_METADATA.switch_type` | CONFIG_DB | READ (起動時 1 回) | VOQ 判定・IPv6 metric 付与 | `intfmgr.cpp:70-75` |
| 5 | `VrfOrch` 内部マップ (`VRF` 由来) | orchagent memory | READ | orchagent 側 VRF 存在確認 | `intfsorch.cpp:826-831` |
| 6 | `DEVICE_METADATA.mac` → `gMacAddress` | CONFIG_DB (起動時) | READ | `mac_addr` 省略時の SAI MAC フォールバック | `intfsorch.cpp:1205` |
| 7 | `NAT_GLOBAL` → `gIsNatSupported` | CONFIG_DB (起動時) | READ | `nat_zone` 指定時の NAT 有効判定 | `intfsorch.cpp:1287-1294` |
