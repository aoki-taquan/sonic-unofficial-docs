# portchannel-status Phase F — side-effects 調査メモ

## 調査対象

- `docs/reference/config-db/portchannel-status.md` (APPL_DB LAG_TABLE)
- Phase F: SET/DEL 副次 DB 書込み

## ソースコード調査結果

### teamsync.cpp (teamsyncd)

- `addLag()`: APPL_DB `LAG_TABLE` 書込み後、`TeamPortSync` 生成成功時のみ STATE_DB `LAG_TABLE` に `state: ok` を書き込む (teamsync.cpp:175, 191-203)
- `delLag()`: STATE_DB `LAG_TABLE` のエントリを削除
- コード明示コメント: "STATE_DB is written only after the team instance is successfully created"

### teammgr.cpp (teammgrd)

- `setLagMtu()` (teammgr.cpp:501-535): APPL_DB `LAG_TABLE` の mtu 更新に加え、`m_cfgLagMemberTable.getKeys()` でメンバーポートを取得し APPL_DB `PORT_TABLE` の各メンバーポートにも同じ mtu を書き込む
- カーネル操作: `ip link set dev <lag> mtu`, `ip link set dev <lag> up/down`, `/usr/bin/teamd` 起動

### portsorch.cpp (orchagent)

- `addLag()` (portsorch.cpp:8022): SAI create_lag 成功後、`COUNTERS_DB COUNTERS_LAG_NAME_MAP` に `<lag_alias>: <sai_oid>` を書き込む
- `removeLag()` (portsorch.cpp:8095): `COUNTERS_DB COUNTERS_LAG_NAME_MAP` から `<lag_alias>` フィールドを削除
- `notify(SUBJECT_TYPE_PORT_CHANGE)` (portsorch.cpp:8015-8017): AclTable, DebugCounterOrch, DtelOrch が連動

### aclorch.cpp

- `AclTable::onUpdate(SUBJECT_TYPE_PORT_CHANGE)`: LAG がバインドされている ACL テーブルの bind port リストを更新 (aclorch.cpp:2866)

## 結論

Phase F に記載した副次効果:
1. STATE_DB LAG_TABLE への state:ok 書込み (teamsyncd, 条件付き)
2. APPL_DB PORT_TABLE へのメンバーポート MTU 伝播 (teammgrd, MTU 変更時)
3. COUNTERS_DB COUNTERS_LAG_NAME_MAP への OID マッピング追加/削除 (portsorch)
4. orchagent 内部 Observer 通知 (AclTable, DebugCounterOrch, DtelOrch)
5. カーネル操作 (teamd 起動/停止, ip link)
