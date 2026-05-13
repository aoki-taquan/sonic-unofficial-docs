# 値依存挙動分析: NTP_KEY

## Phase 1: YANG フィールド全列挙

- `id` (uint16, key): typedef `key-id`, range 1..65535
- `type` (enum): `md5`/`sha1`/`sha256`/`sha384`/`sha512`, default `md5`
- `value` (string): length 1..64
- `trusted` (yes-no): default `no`

## Phase 2: per-value explicit grep

- `sonic-ntp.yang`: `key-type` typedef — `enum { md5; sha1; sha256; sha384; sha512; }` / default `md5`
- `sonic-ntp.yang`: `trusted` default `no`
- `NTP_SERVER_LIST.key` leafref → `NTP_KEY_LIST.id` — 参照中は削除不可

## Phase 3: 専用ファイル確認

- `sonic-host-services/scripts/hostcfgd`: NTP_KEY 変更 → `systemctl restart chrony`
- chrony keyfile (`/etc/chrony/chrony.keys`) へ `<id> <type> <value>` 形式で書き込み

## Phase 5: 値依存挙動マトリクス

| フィールド | 値 | 挙動 |
|-----------|-----|------|
| `type` | `md5` (default) | MD5 ハッシュで NTP パケット認証。セキュリティ強度低 |
| `type` | `sha1` | SHA-1 ハッシュで認証 |
| `type` | `sha256` | SHA-256 ハッシュで認証 (推奨最低ライン) |
| `type` | `sha384`/`sha512` | 高強度 SHA 認証 |
| `trusted` | `no` (default) | chrony の `trustedkey` 指定なし。認証有効時でも検証のみで同期はしない |
| `trusted` | `yes` | chrony の `trustedkey` に追加。当該鍵のサーバのみで時刻同期を許可 |
| `value` | 1..64字 | chrony keyfile に鍵本体として書き込み |
| `id` | 1..65535 | chrony keyfile の鍵 ID として使用。NTP_SERVER.key からの leafref 参照元 |

enum: `type`=md5/sha1/sha256/sha384/sha512、`trusted`=yes/no。
