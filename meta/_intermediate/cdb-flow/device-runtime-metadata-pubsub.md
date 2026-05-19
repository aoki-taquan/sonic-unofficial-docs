# device-runtime-metadata pubsub (Phase G — 通信メカニズム / subscribe 経路)

生成日: 2026-05-19
対象: `DEVICE_RUNTIME_METADATA` (CONFIG_DB 仮想テーブル)
手法: sonic-buildimage / sonic-host-services / sonic-py-common ソース全行精読

---

## 概要

`DEVICE_RUNTIME_METADATA` は Redis には永続化されない **仮想テーブル** であり、`device_info.get_device_runtime_metadata()` 呼び出しによってインメモリで生成される。このため、通常の Redis keyspace notification (PSUBSCRIBE) や `SubscriberStateTable` / `ConsumerStateTable` による subscribe は **一切存在しない**。

consumer は次の 3 パターンで値を取得する:

| パターン | 使用箇所 | タイミング |
|---------|---------|---------|
| 直接関数呼び出し | `featured` (起動時 `__init__`) | デーモン起動時に 1 回だけ |
| 直接関数呼び出し | `sysmonitor.py` (`get_service_from_feature_table`) | `config reload` 等のトリガー時に都度呼び出し |
| Jinja2 テンプレート変数展開 | `sonic-cfggen` / `init_cfg.json.j2` | システム起動時の設定生成フェーズ (1 回限り) |

---

## Consumer 詳細

### G-1. featured — 直接関数呼び出し (起動時 1 回)

| 項目 | 詳細 |
|------|------|
| デーモン | ホスト上の `featured` Python スクリプト (`sonic-host-services`) |
| 取得 API | `device_info.get_device_runtime_metadata()` (Python 関数呼び出し) |
| タイミング | `FeatureHandler.__init__()` 内 (`featured:145`) — デーモン起動時に 1 回のみ実行 |
| 格納先 | `self._device_running_config` インスタンス変数 |
| 利用箇所 | `handler()` 内 (`featured:193-195`) で `DEVICE_METADATA` と merge し、FEATURE テーブルの Jinja2 `state` フィールドをレンダリングするコンテキストとして使用 |
| Redis subscribe | なし (`DEVICE_RUNTIME_METADATA` への keyspace 通知購読は実装されていない) |
| evidence | `sonic-host-services/scripts/featured:137-145,193-196` |

### G-2. sysmonitor — 直接関数呼び出し (都度)

| 項目 | 詳細 |
|------|------|
| デーモン | `system-health` コンテナ内 `sysmonitor` Python スクリプト |
| 取得 API | `device_info.get_device_runtime_metadata()` (Python 関数呼び出し) |
| タイミング | `get_service_from_feature_table()` 内 (`sysmonitor.py:220`) — `config reload` 等の CONFIG_DB `FEATURE` テーブル変化検知時に都度呼び出し |
| 格納先 | ローカル変数 `device_config` に update してスコープ内で使用 |
| 利用箇所 | `FEATURE` テーブルの各エントリの `state` フィールド (Jinja2 テンプレート文字列) をレンダリングするコンテキストとして使用 |
| Redis subscribe | なし |
| evidence | `sonic-buildimage/src/system-health/health_checker/sysmonitor.py:217-226` |

### G-3. sonic-cfggen (init_cfg.json.j2) — テンプレート変数展開 (起動時 1 回)

| 項目 | 詳細 |
|------|------|
| ツール | `sonic-cfggen` コマンド (ホスト起動シーケンス中) |
| 取得方法 | `get_device_runtime_metadata()` の返り値が `sonic-cfggen` のテンプレート変数辞書に渡され、Jinja2 の `DEVICE_RUNTIME_METADATA` 変数として参照可能になる |
| タイミング | システム起動時の `rc.local` / `platform-rc` スクリプトから 1 回のみ呼び出される |
| 参照フィールド | `ETHERNET_PORTS_PRESENT`、`MACSEC_SUPPORTED`、`CHASSIS_METADATA.module_type` |
| 効果 | `FEATURE` テーブルの `state`・`has_global_scope`・`has_per_asic_scope` を決定して CONFIG_DB へ書き込む |
| Redis subscribe | なし (テンプレートレンダリング時にインメモリで参照するのみ) |
| evidence | `sonic-buildimage/files/build_templates/init_cfg.json.j2:67,75,90,106-107` |

---

## pub/sub 不在の理由

`DEVICE_RUNTIME_METADATA` は起動時に決定する **ハードウェア由来の静的メタデータ** (プラットフォーム種別・ポート設定ファイルの有無・MACsec 対応) を格納する。  
これらの値はシステム実行中に変化しないことを前提としており、Redis に永続化する設計になっていない。したがって:

- keyspace 通知 (`PSUBSCRIBE __keyspace@*__:DEVICE_RUNTIME_METADATA*`) を発行する consumer は存在しない
- `SubscriberStateTable` / `ConsumerStateTable` でこのテーブルを購読する consumer は存在しない
- runtime 変更通知のユースケース自体が想定されていない

---

## フィールド × consumer マトリクス

| フィールド | featured | sysmonitor | sonic-cfggen |
|---|:---:|:---:|:---:|
| `ETHERNET_PORTS_PRESENT` | ✓ | ✓ | ✓ |
| `MACSEC_SUPPORTED` | ✓ | ✓ | ✓ |
| `CHASSIS_METADATA.module_type` | ✓ | ✓ | ✓ |
