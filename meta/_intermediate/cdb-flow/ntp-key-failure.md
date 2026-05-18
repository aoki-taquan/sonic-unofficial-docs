# NTP_KEY テーブル — Phase D 失敗挙動調査メモ

対象テーブル: `NTP_KEY`
調査日: 2026-05-18

## 調査対象ファイル

| ファイル | 役割 |
|---------|------|
| `sonic-host-services/scripts/hostcfgd` | `NtpCfg.ntp_srv_key_update()` — chrony 再起動の失敗ハンドリング |
| `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-ntp.yang` | YANG 制約 — key-id range / leafref 整合性 |

---

## 1. chrony 再起動失敗時の挙動

`hostcfgd` の `ntp_srv_key_update()` (`hostcfgd:1396-1405`):

```python
try:
    run_cmd(self.CHRONY_RESTART, True, True)
except Exception:
    syslog.syslog(syslog.LOG_ERR, f'NtpCfg: Failed to restart '
                                  'chrony service')
    return
```

- `systemctl restart chrony` が失敗した場合、`syslog.LOG_ERR` でログを出力し `return` する
- **キャッシュは更新されない**: `self.cache['keys'] = ntp_keys` の行（`hostcfgd:1405-1406`）に到達しないため、次回変更イベントではキャッシュ不一致を検出して再試行する
- リトライループは存在しない。次の NTP_KEY / NTP_SERVER の DB イベントが発生したときに再実行される

## 2. YANG 制約違反（SET 時のバリデーション失敗）

CONFIG_DB への書き込み時（CLI / gNMI / REST 経由）に YANG バリデーションが実行される。

| 制約 | 違反時の挙動 |
|------|------------|
| `key-id` が 1..65535 範囲外 | YANG `range` 制約で書き込みが拒否される。`error-message "Failed NTP key ID"` |
| `type` が enum 外の値 | YANG `enum { md5; sha1; sha256; sha384; sha512; }` 制約で拒否 |
| `value` が空または 65 文字以上 | YANG `length 1..64` 制約で拒否 |
| `NTP_SERVER.key=<id>` 参照中の NTP_KEY DEL | YANG leafref 整合性チェックで拒否（dangling leafref 防止） |

YANG バリデーション失敗は書き込みが DB に届く前に拒否されるため、hostcfgd への通知は発生しない。

## 3. chrony.keys.j2 テンプレート処理の silent skip

`type` や `value` が falsy（空文字・None）の場合、`chrony.keys.j2` は当該鍵エントリをテンプレート展開からスキップする：

```jinja2
{% for keyid in NTP_KEY if NTP_KEY[keyid].type and NTP_KEY[keyid].value %}
```

- エラーは発生せず、該当鍵が keyfile に出力されない（silent drop）
- chrony は keyfile 再読み込み後、当該鍵 ID を未登録として扱う

## 4. 失敗挙動サマリ

| フェーズ | 失敗条件 | 挙動 | リトライ |
|---------|----------|------|---------|
| YANG バリデーション | key-id 範囲外 / type 不正 / value 長超過 | 書き込み拒否（DB 変更なし） | なし（CLI 再実行が必要） |
| YANG leafref | 参照中 NTP_KEY を DEL | DEL 拒否（DB 変更なし） | なし |
| chrony 再起動 | `systemctl restart chrony` 失敗 | LOG_ERR ログ、return。キャッシュ未更新 | 次回 DB イベントで自動再試行 |
| テンプレート生成 | type / value が falsy | silent skip（鍵が keyfile に出力されない） | 次回 DB イベントで再生成 |
