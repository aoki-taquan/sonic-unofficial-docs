# queue-state — Phase G 調査証跡 (pubsub)

**対象テーブル**: STATE_DB `QUEUE_COUNTER_CAPABILITIES`
**調査日**: 2026-05-19
**調査ソース**: `sonic-swss/orchagent/portsorch.cpp`、`sonic-utilities/scripts/wredstat`、`sonic-utilities/utilities_common/portstat.py`

---

## Producer 側

`PortsOrch::initCounterCapabilities(gSwitchId)` が使用する書き込みオブジェクトは:

```cpp
// portsorch.cpp:793
m_queueCounterCapabilitiesTable = unique_ptr<Table>(new Table(m_state_db.get(), STATE_QUEUE_COUNTER_CAPABILITIES_NAME));
```

`swss::Table` クラス (`table.cpp`) は `HSET` を使って Redis ハッシュへ直接書き込む。**`ProducerTable`（LPUSH + PUBLISH）は使用しない**。

書き込みのタイミング:
- orchagent 起動時に `PortsOrch::PortsOrch()` コンストラクタ → `init()` → `initCounterCapabilities()` の順で **1 回のみ**呼ばれる
- 実行時の動的更新なし（CONFIG_DB イベントとは無関係）

## Consumer 側

### wredstat (`sonic-utilities/scripts/wredstat`)

```python
self.state_db = SonicV2Connector(use_unix_socket_path=False)
self.state_db.connect(self.state_db.STATE_DB)
```

`SonicV2Connector.get()` で直接 `HGET` を呼ぶ。SUBSCRIBE / keyspace notification は使わない。

### portstat.py (`sonic-utilities/utilities_common/portstat.py:297-312`)

`PORT_COUNTER_CAPABILITIES` (Phase F で記録した副次書き込みテーブル) を参照するが、`QUEUE_COUNTER_CAPABILITIES` への直接参照は portstat.py には存在しない。

## 通知チャネルの有無

| 項目 | 内容 |
|------|------|
| 書き込みクラス | `swss::Table` (`HSET` 直接) |
| keyspace notification | STATE_DB の `notify-keyspace-events` 設定次第だが、orchagent/consumer どちらも使用しない |
| 購読チャネル | なし |
| consumer 読み取り方式 | `SonicV2Connector.get()` → `HGET` (直接 GET) |

## 結論

`QUEUE_COUNTER_CAPABILITIES` は **orchagent 起動時 1 回のみ書き込まれる静的ステータステーブル**であり、Redis Pub/Sub や keyspace notification に依存しない。consumer は都度 `HGET` でポーリングするシンプルな 1 対 N 直接読み出し構造。
