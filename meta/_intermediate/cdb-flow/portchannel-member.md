# portchannel-member 例外条件エビデンス

## 調査ソース

- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-portchannel.yang`
- `sonic-swss/orchagent/portsorch.cpp`
- `sonic-swss/cfgmgr/teammgr.cpp`

## 例外条件まとめ

### スキーマ検証 (YANG)
- `PORTCHANNEL_MEMBER` の key は `(name, port)` — PORTCHANNEL と PORT への leafref。参照先が存在しない場合は YANG validate で reject。

### consumer (portsorch / teammgr) 例外動作
- メンバーポートが PHY/SYSTEM 型以外: `LAG member port has to be of type PHY or SYSTEM` → SWSS_LOG_ERROR (portsorch.cpp:6292)
- chassis 環境で switch id ミスマッチ: `System lag switch id mismatch. Lag %s switch id: %d, Member %s switch id: %d` → SWSS_LOG_ERROR (portsorch.cpp:6311)
- DEL で存在しないメンバー: `Member %s not found in LAG %s` → SWSS_LOG_WARN (portsorch.cpp:6401)
- SAI LAG member add 失敗: `Failed to add member %s to LAG %s` → SWSS_LOG_ERROR (portsorch.cpp:8176)
- SAI LAG member remove 失敗: `Failed to remove member %s from LAG %s` → SWSS_LOG_ERROR (portsorch.cpp:8225)
- teamd でポート未発見: `Unable to find port %s` → SWSS_LOG_WARN (teammgr.cpp:743)
- teamd メンバー追加失敗: `Failed to add %s to port channel %s` → SWSS_LOG_ERROR (teammgr.cpp:785)
