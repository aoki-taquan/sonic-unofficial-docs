# sflow-collector-failure — Phase D: SFLOW_COLLECTOR 失敗挙動

対象ページ: `docs/reference/config-db/sflow-collector.md`
調査ソース:
- `sonic-swss/cfgmgr/sflowmgr.cpp` (全行)
- `sonic-swss/cfgmgr/sflowmgrd.cpp` (全行)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-sflow.yang` (全行)
- `sonic-utilities/config/main.py` (sflow collector add/del 周辺)
- `sonic-mgmt-common/translib/transformer/xfmr_sflow.go` (全行)
生成日: 2026-05-17

---

## SET 処理における失敗経路

### F1: collector_vrf='mgmt' + MGMT_VRF 無効時の YANG must 制約違反

**根拠**: `sonic-sflow.yang:86-88`

```yang
must "(current() != 'mgmt') or
     (/mvrf:sonic-mgmt_vrf/mvrf:MGMT_VRF_CONFIG/mvrf:vrf_global/mvrf:mgmtVrfEnabled = 'true')" {
    error-message "Must condition not satisfied. Try enable Management VRF.";
}
```

`collector_vrf = 'mgmt'` を指定した際に `MGMT_VRF_CONFIG.vrf_global.mgmtVrfEnabled` が `'true'` でない場合、YANG バリデーションが失敗する。`ValidatedConfigDBConnector` 経由 (`config sflow collector add --vrf mgmt`) では書き込みが拒否されるが、直接 `sonic-db-cli` や `ConfigDBConnector` (ADHOC バイパス) 経由で書き込んだ場合は CONFIG_DB に入ってしまう（実行時には hsflowd が VRF なし経路でコレクタに接続しようとし、接続失敗の可能性がある）。

| 検出箇所 | 結果 | エラーメッセージ |
|---------|------|----------------|
| YANG `must` 制約 (`sonic-sflow.yang:86-88`) | YANG バリデーション失敗 → CONFIG_DB 書き込み拒否 | `"Must condition not satisfied. Try enable Management VRF."` |

---

### F2: コレクタ名が 16 文字超え（CLI バリデーション）

**根拠**: `config/main.py:9316`

```python
if len(name) > 16:
    click.echo("Collector name must not exceed 16 characters")
    return False
```

`config sflow collector add` で 16 文字を超えるコレクタ名を指定すると CLI が即座に拒否。YANG の `length 1..64` 制約より厳しい CLI 制限（CLI と YANG の不整合）。`sonic-db-cli` / REST 直接書き込みでは YANG 制限 (64 文字) まで許容。

| 検出箇所 | 結果 | エラーメッセージ |
|---------|------|----------------|
| `config/main.py:9316` (CLI) | CLI 拒否・CONFIG_DB 書き込みなし | `"Collector name must not exceed 16 characters"` |
| REST/gNMI 経由 | YANG `length 1..64` まで許容 | なし (CLI 不整合) |

---

### F3: 3 つ目以降のコレクタ追加（上限 2 件）

**根拠**: `config/main.py:9352-9355` + `sonic-sflow.yang:61 max-elements 2`

```python
if (collector_tbl and name not in collector_tbl and len(collector_tbl) == 2):
    click.echo("Only 2 collectors can be configured, please delete one")
    return
```

既に 2 件のコレクタが登録済みで、かつ新規名の場合に CLI が拒否。既存コレクタを削除せずに 3 件目の追加はできない。YANG `max-elements 2` でも同様の制限が保証される。

| 検出箇所 | 結果 | エラーメッセージ |
|---------|------|----------------|
| `config/main.py:9352-9355` (CLI) | CLI 拒否・CONFIG_DB 書き込みなし | `"Only 2 collectors can be configured, please delete one"` |
| YANG `max-elements 2` | バリデーション拒否 | YANG エラー |

---

### F4: 無効な IP アドレス（CLI バリデーション）

**根拠**: `config/main.py:9321-9323`

```python
if not clicommon.is_ipaddress(ip):
    click.echo("Invalid IP address")
    return False
```

`collector_ip` に IPv4/IPv6 として解析できない文字列を指定した場合、CLI が拒否。YANG `inet:ip-address` 型でも同様のバリデーション。

| 検出箇所 | 結果 | エラーメッセージ |
|---------|------|----------------|
| `config/main.py:9321-9323` (CLI) | CLI 拒否 | `"Invalid IP address"` |
| YANG `inet:ip-address` 型 | バリデーション拒否 | YANG 型エラー |

---

### F5: サポート外 VRF 名（CLI バリデーション）

**根拠**: `config/main.py:9325-9327`

```python
if vrf_name != 'default' and vrf_name != 'mgmt':
    click.echo("Only 'default' and 'mgmt' VRF are supported")
    return False
```

`--vrf` オプションに `'default'` / `'mgmt'` 以外の文字列を指定した場合、CLI が拒否。YANG `pattern "mgmt|default"` でも同様。

| 検出箇所 | 結果 | エラーメッセージ |
|---------|------|----------------|
| `config/main.py:9325-9327` (CLI) | CLI 拒否 | `"Only 'default' and 'mgmt' VRF are supported"` |
| YANG `pattern "mgmt\|default"` | バリデーション拒否 | YANG 型エラー |

---

## DEL 処理における失敗経路

### F6: 存在しないコレクタの削除（ADHOC バリデーション時のみ）

**根拠**: `config/main.py:9374-9378`

```python
if ADHOC_VALIDATION:
    collector_tbl = config_db.get_table('SFLOW_COLLECTOR')
    if name not in collector_tbl:
        click.echo("Collector: {} not configured".format(name))
        return
```

`ADHOC_VALIDATION` が有効な場合のみ CLI が存在チェックを実施。無効の場合は `set_entry('SFLOW_COLLECTOR', name, None)` が呼ばれ、Redis の DEL コマンドが発行されるが存在しないキーに対する DEL は Redis 上エラーなし（silent no-op）。

---

## hsflowd サービス起動失敗

### F7: hsflowd サービス起動・停止コマンド失敗

**根拠**: `sflowmgr.cpp:67-70`

```cpp
int ret = swss::exec(cmd.str(), res);
if (ret)
{
    SWSS_LOG_ERROR("Command '%s' failed with rc %d", cmd.str().c_str(), ret);
}
```

`service hsflowd restart` / `service hsflowd stop` の実行が失敗した場合、`SWSS_LOG_ERROR` を出力するが例外は発生しない。CONFIG_DB の状態と実際の hsflowd 稼働状態がずれる。SFLOW_COLLECTOR を追加してもコレクタへのサンプル転送が行われない状態になる可能性がある。

**重要**: sflowmgrd は SFLOW_COLLECTOR テーブルを購読していない（`sflowmgrd.cpp:31-41`）。SFLOW_COLLECTOR の変更に対して hsflowd の再起動が自動でトリガーされないため、コレクタ追加・変更後に hsflowd が動的にコレクタを追加することはない。

---

## REST/gNMI 経由の失敗経路

### F8: collector/config サブツリーの DELETE 非サポート

**根拠**: `xfmr_sflow.go:283-284`

```go
if strings.HasPrefix(targetUriPath, SAMPLING_SFLOW_COLS_COL_CONFIG) {
    return res_map, errors.New("Delete operation not supported for this xpath")
}
```

REST/gNMI で `/openconfig-sampling-sflow:sampling/sflow/collectors/collector/config` への DELETE を試みると `"Delete operation not supported for this xpath"` エラーが返る。コレクタ全体の削除は `/collectors/collector` レベルで行う必要がある。

---

## サマリ表

| ID | 失敗条件 | 検出層 | 結果 | 自動回復 |
|----|---------|-------|------|---------|
| F1 | `collector_vrf=mgmt` + MGMT_VRF 無効 | YANG must | CONFIG_DB 書き込み拒否 | MGMT_VRF 有効化後に再試行 |
| F2 | コレクタ名 > 16 文字 | CLI バリデーション | CLI 拒否 (YANG は 64 文字まで許容) | なし |
| F3 | 3 件目以降のコレクタ追加 | CLI + YANG max-elements | 書き込み拒否 | 既存コレクタ削除後に再追加 |
| F4 | 無効な IP アドレス | CLI + YANG 型 | CLI 拒否 | なし |
| F5 | mgmt/default 以外の VRF | CLI + YANG pattern | CLI 拒否 | なし |
| F6 | 非存在コレクタの DEL | CLI (ADHOC のみ) | 警告表示・Redis silent no-op | なし |
| F7 | hsflowd start/stop 失敗 | sflowmgr.cpp:70 | LOG_ERROR のみ・設定状態乖離 | 手動で `service hsflowd restart` |
| F8 | REST DELETE on /config subpath | xfmr_sflow.go:284 | エラー返却・操作失敗 | /collector レベルで DELETE |
