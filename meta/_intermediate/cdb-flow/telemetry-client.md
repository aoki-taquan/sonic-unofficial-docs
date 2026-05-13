# TELEMETRY_CLIENT 例外条件調査メモ

ソース: `sonic-gnmi/dialout/dialout_client/dialout_client.go` (SHA: eb635b7679b260c3fd0786a6d0734fc8e82c9a22)

## 抽出した例外条件

1. **`Global` キーの DEL 不可** — `key == "Global"` に対して DEL 操作が来ると
   `"Invalid delete operation for TELEMETRY_CLIENT|Global"` を返す。
   Global 設定はシングルトンで削除不可。

2. **`retry_interval` の型変換失敗** — `retry_interval` を `strconv.ParseUint()` で変換できない場合、
   `"Invalid retry_interval <value> <err>"` をログして `continue` する（フィールドをスキップ）。
   不正値は無視され旧設定が維持される。

3. **DestinationGroup の空名** — `DestinationGroup_` プレフィックスを除いた名前が空文字列のとき
   `"Empty Destination Group name <key>"` を返してエラーにする。

4. **DestinationGroup 使用中の DEL** — `DestGrp2ClientSubMap` に参照があるグループを DEL しようとすると
   `"<destGroupName> is being used: <map>"` を返してエラーにする。
   参照している Subscription を先に削除する必要がある。

5. **`dst_addr` の空エントリ** — `Destination.Validate()` で `Addrs` が空なら
   `"Destination.Addrs is empty"` を返す。
   宛先アドレスが空の DestinationGroup は拒否される。

6. **Subscription の空名** — `Subscription_` プレフィックスを除いた名前が空文字列のとき
   `"Empty Subscription_ name <key>"` を返してエラーにする。

7. **DestinationGroup 未設定の Subscription** — `dest_group` フィールドが設定されていない場合
   `"Destination group is not set for <subscription>"` を返す。

8. **不正な DestinationGroup 名参照** — Subscription が参照する DestinationGroup が存在しない場合
   `"Destination group <name> doesn't exist"` を返す。

9. **redis HGetAll 失敗** — CONFIG_DB へのアクセスが失敗すると
   `"redis HGetAll failed for <key> with error <err>"` を返してエラーにする。
