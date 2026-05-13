# portchannel-interface 例外条件エビデンス

## 調査ソース

- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-portchannel.yang`
- `sonic-swss/orchagent/portsorch.cpp`

## 例外条件まとめ

### スキーマ検証 (YANG)
- `PORTCHANNEL_INTERFACE` の `nat_zone` は range 0..3: `error-message "Invalid nat zone for the portchannel interface."` (sonic-portchannel.yang:191)
- IP prefix は `leafref` 等で参照整合性を確認。

### consumer 例外動作
- PORTCHANNEL が存在しない場合の IP アドレス追加: orchagent は PORTCHANNEL 存在確認後に IP 付与; 存在しなければタスクを保留 (依存関係による遅延処理)。
- VLAN に所属している LAG への IP 追加: portsorch で LAG が VLAN に残っている場合は削除操作に `Failed to remove LAG %s, it is still in VLAN` (portsorch.cpp:8065)。
- TPID 設定失敗: `Failed to set LAG %s TPID 0x%x` → SWSS_LOG_ERROR (portsorch.cpp:6175)
