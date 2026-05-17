# control-plane-acl — Phase G: 通信メカニズム (pub/sub) 中間トレース

調査日: 2026-05-17
対象ファイル:
- sonic-host-services/scripts/caclmgrd (全行読了)
- sonic-swss/orchagent/aclorch.cpp (購読部分確認)

---

## 1. 購読 API の種別

caclmgrd は CONFIG_DB の `ACL_TABLE` / `ACL_RULE` を `swsscommon.SubscriberStateTable` + `swsscommon.Select` で購読する。
`ConfigDBConnector.subscribe()` (keyspace notification) ではなく、swsscommon の低レベル API を直接使用している点が hostcfgd と異なる。

```python
# caclmgrd L1173-1184
acl_db_connector = swsscommon.DBConnector("CONFIG_DB", 0, False, namespace)
subscribe_acl_table = swsscommon.SubscriberStateTable(
    acl_db_connector, swsscommon.CFG_ACL_TABLE_TABLE_NAME)
subscribe_acl_rule_table = swsscommon.SubscriberStateTable(
    acl_db_connector, swsscommon.CFG_ACL_RULE_TABLE_NAME)
sel.addSelectable(subscribe_acl_table)
sel.addSelectable(subscribe_acl_rule_table)
```

- `SubscriberStateTable` は Redis の `__keyspace@<dbId>__:<TABLE>*` パターンの PSUBSCRIBE ではなく、
  CONFIG_DB の `HSET` / `DEL` 操作をトリガーとする **keyspace notification** を内部的に利用する swsscommon 独自 API。
- `sel.select(SELECT_TIMEOUT_MS=1000)` で 1 秒タイムアウトのブロッキングポーリングを行い、
  OBJECT イベント (state=Select.OBJECT) が返った場合にのみ処理する。

## 2. 購読テーブル一覧

| 購読元 DB | テーブル | 購読 API | 購読目的 |
|-----------|---------|---------|---------|
| CONFIG_DB | `ACL_TABLE` (`CFG_ACL_TABLE_TABLE_NAME`) | `SubscriberStateTable` | CTRLPLANE ACL テーブル定義の SET/DEL 検出 |
| CONFIG_DB | `ACL_RULE` (`CFG_ACL_RULE_TABLE_NAME`) | `SubscriberStateTable` | CTRLPLANE ACL ルールの SET/DEL 検出 |
| CONFIG_DB | `VXLAN_TUNNEL` | `SubscriberStateTable` | VxLAN トンネル設定の変更検出 |
| CONFIG_DB | `DPU` | `SubscriberStateTable` | DASH-HA 用 DPU 設定の変更検出 |
| STATE_DB | `BFD_SESSION_TABLE` | `SubscriberStateTable` | BFD セッション存在の初回検出 (SET のみ) |
| STATE_DB | `MUX_CABLE_TABLE` | `SubscriberStateTable` | DualToR 時のみ: MUX ケーブル状態変化 |
| STATE_DB | `DHCP_PACKET_MARK` | `SubscriberStateTable` | DualToR 時のみ: DHCP パケットマーク変化 |

## 3. 購読イベント → 処理のフロー

```
CONFIG_DB ACL_TABLE / ACL_RULE 変更
  ↓ SubscriberStateTable.pop()
  caclmgrd run() L1268-1286
  → ctrl_plane_acl_notification.add(namespace)
  ↓ (namespace ごとに)
  lock 取得 → num_changes++ (L1290-1295)
  → update_thread が未起動なら threading.Thread 生成 (L1299-1303)
    ↓ (別スレッド)
    check_and_update_control_plane_acls(namespace, num_changes)
      ↓ UPDATE_DELAY_SECS=0.5 秒 デバウンス
      → 安定後に update_control_plane_acls(namespace, new_config_db_connector)
        → get_acl_rules_and_translate_to_iptables_commands()
          → CONFIG_DB から ACL_TABLE / ACL_RULE を全量 get_table() で取得
          → iptables / ip6tables を全フラッシュ後に再インストール
```

## 4. デバウンス機構 (UPDATE_DELAY_SECS)

- `check_and_update_control_plane_acls()` は `time.sleep(0.5)` 後に `num_changes[namespace]` を確認。
- スリープ中にさらに変更通知が届いた場合 (`num_changes > 最初の num_changes`) はスリープを繰り返す。
- 0.5 秒間変更通知がない状態になって初めて `update_control_plane_acls()` を実行する。
- これにより連続 SET/DEL (例: minigraph.py の一括投入) の際に iptables の複数回フラッシュを防ぐ。
- evidence: `caclmgrd:123, 943-993`

## 5. イベントループの Select タイムアウト

- `sel.select(SELECT_TIMEOUT_MS=1000)` は 1000ms タイムアウト。
- タイムアウト時は `state != Select.OBJECT` で即 continue。
- メインスレッドは 1 秒ごとに `thread_exceptions` を確認し、子スレッドで例外が発生していれば SIGKILL で自壊する。
- evidence: `caclmgrd:1114, 1190-1202`

## 6. 特殊ケース: BFD セッションの one-shot 購読

```python
# caclmgrd L1221-1224
if op == 'SET' and not self.bfdAllowed:
    self.allow_bfd_protocol(namespace)
    self.bfdAllowed = True
    sel.removeSelectable(subscribe_bfd_session)
```

BFD セッションの最初の SET を検出した後、`sel.removeSelectable()` で購読を解除する。
BFD ルールは一度追加されたら以降の通知に依存しない (全 flush 時に `self.bfdAllowed==True` なら再追加)。

## 7. ConfigDBConnector との差異

| 比較軸 | caclmgrd (SubscriberStateTable) | hostcfgd (ConfigDBConnector.subscribe) |
|--------|--------------------------------|-----------------------------------------|
| 内部 API | swsscommon 低レベル Select + SubscriberStateTable | Python ラッパ ConfigDBConnector.subscribe + listen |
| OBJECT 識別 | `CastSelectableToRedisSelectObj()` で DB ID / Namespace を取得 | テーブル名でコールバックをディスパッチ |
| マルチ namespace | 明示的に namespace ごとに SubscriberStateTable を生成 | 単一 namespace のみ (hostcfgd はホスト名前空間固定) |
| 通知受信後の DB 再取得 | `get_table()` で全量再取得 (スナップショット方式) | pop() で差分取得後 HGETALL で再取得 |

## 8. 証跡

- `caclmgrd:1112-1304` (`run()` メインループ全行)
- `caclmgrd:943-993` (`check_and_update_control_plane_acls()` 全行)
- `caclmgrd:625-901` (`get_acl_rules_and_translate_to_iptables_commands()` — get_table 呼び出し確認)
- `swsscommon.SubscriberStateTable`, `swsscommon.Select` (swsscommon ライブラリ)
