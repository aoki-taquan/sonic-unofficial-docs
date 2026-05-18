# ntp-global — Phase B 調査メモ (ordering)

## 調査対象

- `sonic-host-services/scripts/hostcfgd` (NtpCfg クラス, HcfgDaemon)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-ntp.yang`

## hostcfgd 購読テーブルと処理順序

HcfgDaemon.__init__() が `config_db.subscribe()` を呼ぶ順序 (hostcfgd:2512-2516):

```
CFG_NTP_GLOBAL_TABLE_NAME  -> ntp_global_handler -> NtpCfg.ntp_global_update()
CFG_NTP_SERVER_TABLE_NAME  -> ntp_srv_key_handler -> NtpCfg.ntp_srv_key_update()
CFG_NTP_KEY_TABLE_NAME     -> ntp_srv_key_handler -> NtpCfg.ntp_srv_key_update()
LOOPBACK_INTERFACE         -> lpbk_handler        -> NtpCfg.handle_ntp_source_intf_chg()
```

## 順序依存の詳細

### 1. NTP_SERVER / NTP_KEY → NTP_GLOBAL の推奨先行書き

ntp_srv_key_handler は ntp_srv_key_update() を呼び、このとき `config_db.get_table()` で
NTP_SERVER と NTP_KEY 全体を再取得する (hostcfgd:2389-2391)。
NTP_GLOBAL だけ先に書いて NTP_SERVER が空だと chrony.conf のサーバ定義が空になる。
後から NTP_SERVER を追加すると ntp_srv_key_handler が再度呼ばれて正常状態に自動復旧する。

### 2. src_intf (LOOPBACK_INTERFACE) の先行必須性

handle_ntp_source_intf_chg() は NTP_GLOBAL.src_intf に登録されたインタフェース名を参照し、
その名前が LOOPBACK_INTERFACE の変更イベントと一致したときのみ chrony を restart する
(hostcfgd:1315-1325)。

- NTP_SERVER が空のとき: servers キャッシュが空なので early return (hostcfgd:1315-1316)
- src_intf と一致しない loopback 変更: iptables/aaacfg に転送されるが NTP には影響なし

### 3. MGMT_VRF_CONFIG と NTP_GLOBAL の依存 (YANG must 制約)

sonic-ntp.yang の must 制約により、NTP_GLOBAL.vrf を "mgmt" に設定するには
MGMT_VRF_CONFIG.vrf_global.mgmtVrfEnabled = "true" が事前に必要。
YANG バリデーションは CLI 発行時に評価される。直接 redis-cli で書き込む場合は制約が適用されない。

### 4. diff 検知による冪等性 (ordering への影響)

- ntp_global_update(): cache == data のとき no-op (hostcfgd:1344)
- ntp_srv_key_update(): cache.servers == new_servers かつ cache.keys == new_keys のとき no-op (hostcfgd:1383-1386)
これによりイベント順序が逆でも最終状態は収束するが、中間状態でいったん空設定の chrony が動く。

## 検出された順序依存一覧

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | NTP_SERVER / NTP_KEY → NTP_GLOBAL | 推奨先行 | 後追いで ntp_srv_key_handler が自動復旧 |
| 2 | MGMT_VRF_CONFIG (mgmtVrfEnabled=true) → NTP_GLOBAL (vrf=mgmt) | **必須先行** (YANG must) | CLI が reject; redis 直書きは制約バイパス |
| 3 | LOOPBACK_INTERFACE 存在 → handle_ntp_source_intf_chg() | 推奨先行 | servers 空なら early return、後続 LOOPBACK ADD で自動再試行 |
| 4 | NTP_GLOBAL.src_intf ∈ LOOPBACK_INTERFACE.keys | 推奨先行 | イベントトリガは名前一致のみ; 登録前の loopback 追加は無視 |
