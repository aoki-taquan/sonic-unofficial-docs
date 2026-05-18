# subscription-config — Phase H プラットフォーム差スキャンノート

生成日: 2026-05-18

## 調査対象

`docs/reference/config-db/subscription-config.md` 対象テーブル
`TELEMETRY_CLIENT|Global` / `TELEMETRY_CLIENT|DestinationGroup_<name>` / `TELEMETRY_CLIENT|Subscription_<name>`
プラットフォーム（multi-ASIC / Chassis / HWSKU）によって挙動が変わる箇所を調査する。

## 走査範囲

- `sonic-gnmi/dialout/dialout_client/dialout_client.go` 全行
- `sonic-gnmi/sonic_db_config/db_config.go` (namespace 解決ロジック)
- `sonic-buildimage/rules/docker-gnmi.mk` (ビルドフラグ)
- `sonic-buildimage/rules/config` (`INCLUDE_SYSTEM_GNMI`)
- `sonic-buildimage/platform/*/` 全 `.mk` (`INCLUDE_SYSTEM_GNMI` 上書き確認)

## 走査結果

### 1. dialout_client.go のプラットフォーム分岐

```bash
grep -n "namespace\|multi_npu\|is_multi\|chassis\|linecard\|asic_id\|platform\|ASIC\|hwsku" \
  sonic-gnmi/dialout/dialout_client/dialout_client.go
```

**結果: 0 件**。`dialout_client.go` 全 746 行においてプラットフォーム固有の分岐は存在しない。

### 2. namespace 解決

`dialout_client.go` が使用する namespace 関連 API:

```
L465: ns, _ := sdcfg.GetDbDefaultNamespace()  # processTelemetryClientConfig
L649: ns, _ := sdcfg.GetDbDefaultNamespace()  # DialOutRun (初期接続)
L650: dbn, err := sdcfg.GetDbId("CONFIG_DB", ns)
```

`GetDbDefaultNamespace()` は `sonic_db_config/db_config.go:28-30` で以下のように実装:

```go
func GetDbDefaultNamespace() (ns string, err error) {
    return SONIC_DEFAULT_NAMESPACE, nil
}
```

`SONIC_DEFAULT_NAMESPACE` は空文字列 (`""`)。**常にホスト/グローバル namespace の CONFIG_DB のみを参照する**。

`GetDbNonDefaultNamespaces()` や `CheckDbMultiNamespace()` は呼ばれていない。

### 3. multi-ASIC への影響

`dialout_client.go` はデフォルト namespace (= ホスト CONFIG_DB) しか参照しない。
multi-ASIC 構成でも `asic0`/`asic1`/... の namespace CONFIG_DB を個別に購読しないため:

- `TELEMETRY_CLIENT` の設定は全 ASIC 共通で 1 つのみ
- per-ASIC CONFIG_DB に `TELEMETRY_CLIENT` を書いても `dialout_client` には届かない
- テレメトリ送信先 (dst_addr) は per-ASIC ではなく全体として 1 つの宛先セット

### 4. INCLUDE_SYSTEM_GNMI ビルドフラグ

`rules/config:160`: デフォルト `INCLUDE_SYSTEM_GNMI = y`

`platform/*/` の全 `.mk` で `INCLUDE_SYSTEM_GNMI` を上書き (`= n`) するプラットフォームは**存在しない**。
全プラットフォームで `docker-sonic-gnmi` はビルド・インストール対象。

### 5. Chassis / Linecard

`dialout_client.go` は `SONIC_DEFAULT_NAMESPACE` のみを使用するため、
Chassis 構成の Supervisor Card でのみ `TELEMETRY_CLIENT` が有効。
Linecard 上では `TELEMETRY_CLIENT` を設定しても `dialout_client` はそれを参照しない
（Linecard 上の `docker-sonic-gnmi` が起動している場合でも、Supervisor の CONFIG_DB を参照する）。

## 結論

| 確認観点 | 結果 | ソース |
|---------|------|--------|
| プラットフォーム固有分岐 (`HWSKU` / `is_multi_npu` 等) | **なし** | `dialout_client.go` 全行 0 ヒット |
| multi-ASIC namespace 分岐 | **なし**（常にデフォルト namespace） | `dialout_client.go:465,649`; `db_config.go:28-30` |
| `INCLUDE_SYSTEM_GNMI` プラットフォーム差 | **なし**（全プラットフォームでデフォルト `y`） | `rules/config:160`; `platform/*/` 0 ヒット |
| Chassis での挙動差 | Supervisor の global CONFIG_DB のみ参照（Linecard 個別設定は無効） | アーキテクチャ上の帰結 |
