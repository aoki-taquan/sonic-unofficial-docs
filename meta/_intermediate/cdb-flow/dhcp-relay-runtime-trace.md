# DHCP_RELAY — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/dhcp-relay.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `dhcrelay` Docker コンテナ / `dhcp_relay` サービス |
| 2. CFG→APPL 翻訳 | なし (APPL_DB 中継なし) |
| 3. APPL→SAI | なし (SAI 非経由 — Linux カーネルの L4 DHCP relay) |
| 4. タイミング+副作用 | `dhcrelay` サービスが CONFIG_DB の `DHCP_RELAY` を読み込んで起動パラメータを決定。設定変更はサービス再起動が必要。... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`dhcrelay` Docker コンテナ / `dhcp_relay` サービス が CONFIG_DB の `DHCP_RELAY` テーブルを購読する。

`DHCP_RELAY` の key は `<vlan_intf>` (例: `Vlan1000`)。複数 server を `dhcp_servers` フィールドでリスト。

### 段階 2 — CFG→APPL 翻訳

なし (APPL_DB 中継なし)

### 段階 3 — APPL→SAI

なし (SAI 非経由 — Linux カーネルの L4 DHCP relay)

### 段階 4 — タイミングと副作用

**適用タイミング**: `dhcrelay` サービスが CONFIG_DB の `DHCP_RELAY` を読み込んで起動パラメータを決定。設定変更はサービス再起動が必要。

**副作用**: DHCP server アドレスの変更は relay 転送先を変更。サービス再起動中 DHCP relay が一時停止する。
<!-- /runtime-trace -->
```
