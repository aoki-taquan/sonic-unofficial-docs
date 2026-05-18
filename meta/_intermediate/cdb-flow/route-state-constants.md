# route-state constants (Phase E)

## 調査対象

- `orchagent/routeorch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `orchagent/response_publisher.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `common/schema.h` (ref: 158de8d3463ff4b841653f6d57190bb142b80d9c)

## ハードコード定数一覧

### テーブル名定数 (schema.h:494, 47)

```c
#define STATE_ROUTE_TABLE_NAME  "ROUTE_TABLE"   // schema.h:494
#define APP_ROUTE_TABLE_NAME    "ROUTE_TABLE"   // schema.h:47
```

STATE_DB と APPL_STATE_DB のテーブル名はいずれも `"ROUTE_TABLE"` に固定されている。

### `state` フィールド値 (routeorch.cpp:290)

```cpp
string state = add ? "ok" : "na";
```

- `"ok"` — デフォルト経路が SAI に登録された状態
- `"na"` — デフォルト経路が SAI から削除された状態

いずれも変数・設定値ではなくソースコード直書きリテラル。

### `state` フィールドキー名 (routeorch.cpp:291)

```cpp
FieldValueTuple tuple("state", state);
```

フィールドキー名 `"state"` はリテラルで固定。

### `protocol` フィールドキー名 (routeorch.cpp:3196)

```cpp
fvs.emplace_back("protocol", ctx.protocol);
```

フィールドキー名 `"protocol"` はリテラルで固定。

### `err_str` フィールドキー名と prefix (response_publisher.cpp:18-19, 102)

```cpp
constexpr char *kOrchagentComponent = "[OrchAgent] ";
constexpr char *kSaiComponent = "[SAI] ";
// ...
swss::FieldValueTuple err_str("err_str", PrependedComponent(status) + status.message());
```

- フィールドキー名 `"err_str"` はリテラルで固定
- 成功時: prefix なし → `"SWSS_RC_SUCCESS"` (ReturnCode::ok().message())
- SAI エラー時: `"[SAI] "` + SAI エラーメッセージ
- OrchAgent エラー時: `"[OrchAgent] "` + エラーメッセージ

## 変更可能な定数は存在しない

これらの定数はすべてソースコードにハードコードされており、設定ファイル・環境変数・DEVICE_METADATA 等で上書きする手段は提供されていない。テーブル名・フィールド名・フィールド値のすべてが固定で、バイナリの再ビルドなしに変更できない。
