# LOOPBACK_INTERFACE — Phase H: Platform / 環境差異

調査日: 2026-05-16  
調査対象:
- `sonic-swss/cfgmgr/intfmgr.cpp`
- `sonic-swss/orchagent/intfsorch.cpp`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`
- `sonic-utilities/scripts/ipintutil`

---

## 概要

`LOOPBACK_INTERFACE` テーブルの処理は環境（`switch_type` / VOQ シャーシ / NAT サポート）によって
挙動が分岐する。

---

## 1. switch_type == "voq" 時の差異 (intfmgr.cpp)

`DEVICE_METADATA.localhost.switch_type` を起動時に読み取り `mySwitchType` に保持
（`intfmgr.cpp:70-75`）。

| 挙動 | 非 VOQ | VOQ (`mySwitchType == "voq"`) |
|------|-------|-------------------------------|
| IPv6 アドレス付与コマンド | `ip -6 address add <prefix> dev <lo>` | `ip -6 address add <prefix> dev <lo> metric 256` |
| metric 付与理由 | — | 連結経路と static 経路を同一 metric にして eBGP / iBGP ECMP を成立させるため（コメント L98-102） |

コード根拠: `intfmgr.cpp:103-111`

---

## 2. VOQ 環境固有: Loopback4096 (bgpcfgd)

VOQ 構成では `bgpcfgd` が internal BGP peer の依存として
`LOOPBACK_INTERFACE|Loopback4096` を要求する
（`managers_bgp.py:145-146`）。

- `peer_type == 'internal'` のとき `deps` に `Loopback4096` を追加。
- `Loopback4096` が CONFIG_DB に存在しない限り internal BGP peer の設定がブロックされる。
- `Loopback4096` は Voq Inband interface として使われ、
  通常の管理ツール（`show ip interfaces` / `ipintutil`）からは **非表示** にされる
  （`ipintutil:68-69`: `Loopback4096` で始まるインターフェースを `skip_ip_intf_display` でスキップ）。

---

## 3. VOQ 環境固有: CHASSIS_APP_DB 連携 (orchagent IntfsOrch)

`isChassisDbInUse()` が true（VOQ シャーシ構成）の場合、
SAI RIF 作成後に `voqSyncAddIntf(alias)` が呼ばれ
`CHASSIS_APP_DB.SYSTEM_INTERFACE_TABLE|<system_alias>` に `oper_status` を書く
（`intfsorch.cpp:1314-1317`）。

通常の非 VOQ 環境では CHASSIS_APP_DB への書込みは一切発生しない。

| 環境 | CHASSIS_APP_DB 書込み | コード根拠 |
|------|----------------------|-----------|
| 非 VOQ | なし | `isChassisDbInUse() == false` |
| VOQ シャーシ（ローカル port/LAG/Lo） | `SYSTEM_INTERFACE_TABLE|<system_alias>.oper_status` | `intfsorch.cpp:1314-1318` |
| VOQ シャーシ（リモート port） | なし（`SAI_SYSTEM_PORT_TYPE_REMOTE` チェックでスキップ） | `intfsorch.cpp:1689-1692` |

---

## 4. NAT サポート有無の差異 (orchagent IntfsOrch)

`gIsNatSupported` フラグにより SAI RIF 作成時の属性が変わる
（`intfsorch.cpp:1287-1294`）。

| 環境 | SAI 属性 | 効果 |
|------|---------|------|
| NAT 非サポート（`gIsNatSupported == false`） | `SAI_ROUTER_INTERFACE_ATTR_NAT_ZONE_ID` **未設定** | SAI 実装デフォルトの zone_id（通常 0）が使われる |
| NAT サポート（`gIsNatSupported == true`） | `SAI_ROUTER_INTERFACE_ATTR_NAT_ZONE_ID = port.m_nat_zone_id` | CONFIG_DB の `nat_zone` 値（デフォルト 0）が SAI に通知される |

> Loopback の `nat_zone` は natmgrd が mangle ルールを生成しないため実効 NAT 効果はゼロ（`natmgr.cpp:7526-7549`）。
> ただし SAI RIF 属性は NAT サポート環境で設定される。

---

## 5. Cold restart vs Warm restart (intfmgr.cpp)

| 起動モード | `flushLoopbackIntfs()` | `buildIntfReplayList()` | 効果 |
|-----------|----------------------|------------------------|------|
| Cold restart | **実行** | — | カーネルから全 dummy デバイス (`Loopback<N>`) を削除後に CONFIG_DB から再作成 |
| Warm restart | — | **実行** | CONFIG_DB から既存 Loopback キーを収集してリプレイリストを構築。カーネルの dummy デバイスは保持 |

コード根拠: `intfmgr.cpp:55-68`

Cold restart の `flushLoopbackIntfs()` は `ip link show type dummy | grep -o 'Loopback[^:]*'` で
全 dummy デバイスを列挙して `delLoopbackIntf()` を呼ぶ（`intfmgr.cpp:222-242`）。

---

## 6. VoqInband Interface の特別扱い (intfmgr.cpp / intfsorch.cpp)

`CFG_VOQ_INBAND_INTERFACE_TABLE_NAME` テーブルへの SET は `doIntfGeneralTask` を**バイパス**して
APPL_DB に直接リレーする（`intfmgr.cpp:1195-1204`）。
これは `Loopback4096` など inband 専用インターフェースが通常の L3 有効化フローを必要としないためである。

orchagent 側では `inband_type` フィールドを受け取り `gPortsOrch->setVoqInbandIntf(alias, inband_type)` を呼ぶ
（`intfsorch.cpp:895-901`）。

---

## まとめ表

| 差異要因 | 非デフォルト挙動 | コード根拠 |
|---------|----------------|-----------|
| `switch_type == "voq"` | IPv6 アドレスに `metric 256` を付与 | `intfmgr.cpp:103-106` |
| VOQ + internal BGP peer | `Loopback4096` 必須依存 | `managers_bgp.py:146` |
| VOQ シャーシ (isChassisDbInUse) | SAI RIF 作成後に CHASSIS_APP_DB へ oper_status を同期 | `intfsorch.cpp:1314-1317` |
| `gIsNatSupported == true` | SAI RIF に `NAT_ZONE_ID` 属性を設定 | `intfsorch.cpp:1287-1294` |
| Cold restart | `flushLoopbackIntfs()` でカーネルの全 dummy デバイスを削除後再作成 | `intfmgr.cpp:55-57, 222-242` |
| Warm restart | `buildIntfReplayList()` でリプレイ。dummy デバイスは保持 | `intfmgr.cpp:61-67` |
| VoqInband (Loopback4096 等) | `doIntfGeneralTask` バイパス → APPL_DB 直接リレー | `intfmgr.cpp:1195-1204` |
