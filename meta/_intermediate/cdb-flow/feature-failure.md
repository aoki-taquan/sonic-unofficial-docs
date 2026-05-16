# FEATURE 失敗挙動 (Phase D)

intermediate for `docs/reference/config-db/feature.md` Phase D block.

## 調査対象ソース

- `sonic-host-services/scripts/featured` (全 692 行精読)
  - `Feature.__init__()` L67-86: フィールド初期化・バリデーション
  - `FeatureHandler.handler()` L186-217: メインディスパッチャ
  - `FeatureHandler.update_feature_state()` L242-287: enable/disable 状態遷移
  - `FeatureHandler.enable_feature()` L468-514: systemd enable + start
  - `FeatureHandler.disable_feature()` L516-548: systemd stop + disable + mask
  - `FeatureHandler.sync_feature_scope()` L311-355: multi-asic スコープ同期
  - `FeatureHandler.set_feature_state()` L585-590: STATE_DB への状態書き込み
  - `FeatureHandler.update_systemd_config()` L357-406: auto_restart.conf 更新
  - `FeatureHandler.get_multiasic_feature_instances()` L408-424: インスタンス名計算
  - `run_cmd()` L27-39: subprocess 実行・エラーハンドリング

---

## 失敗パス一覧

### 1. `has_timer` フィールド存在 → `ValueError` raise → feature 全体を拒絶

`featured:75-78`:

```python
if 'has_timer' in feature_cfg:
    err_str = "Invalid obsolete field 'has_timer' in FEATURE table. Please update configuration schema version"
    syslog.syslog(syslog.LOG_ERR, err_str)
    raise ValueError(err_str)
```

`Feature.__init__()` で `ValueError` が raise される。`handler()` は `feature = Feature(...)` を呼び出すが try/except はない。例外は `FeatureDaemon.start()` のイベントループまで伝播し、デーモン全体がクラッシュする可能性がある。

**retry なし。CONFIG_DB 値は残る。STATE_DB への書き込みなし（set_feature_state 未到達）。デーモン終了リスクあり。**

---

### 2. `state` の Jinja2 テンプレートが不正値を render → `ValueError` raise → feature 全体を拒絶

`featured:112-113` (`_get_feature_table_key_render_value()`):

```python
if target_value not in expected_values:
    raise ValueError('Invalid value rendered for feature {}: {}'.format(self.name, target_value))
```

`expected_values` は `['enabled', 'disabled', 'always_enabled', 'always_disabled']`。CONFIG_DB の `state` フィールドが Jinja2 テンプレート（例: `{{ device_type }}`）として保存されており、render 後の値がこれら以外になると `ValueError`。`has_timer` と同様にデーモンクラッシュリスク。

**retry なし。CONFIG_DB 値は残る。STATE_DB 書き込みなし。デーモン終了リスクあり。**

---

### 3. `enable_feature()` systemd start/unmask コマンド失敗 → STATE_DB に "failed" 記録・False 返却

`featured:506-511`:

```python
except Exception as err:
    syslog.syslog(syslog.LOG_ERR, "Feature '{}.{}' failed to be enabled and started"
                  .format(feature.name, feature_suffixes[-1]))
    self.set_feature_state(feature, self.FEATURE_STATE_FAILED)
    return False
```

`systemctl unmask` / `systemctl start` が非ゼロ終了した場合（`run_cmd(..., raise_exception=True)`）。`systemctl enable` のみ `raise_exception=False` で失敗を無視（/run 配下の生成サービスファイルへの enable 非対応を考慮）。

`set_feature_state()` が `STATE_DB` の `FEATURE|<name>` テーブルに `state=failed` を書き込む。`handler()` は `update_feature_state()` の False 返却を受け `resync_feature_state()` を呼び出し、CONFIG_DB を現在の cached_feature.state（変更前の値）に戻す（`featured:216-217`）。

**retry なし。CONFIG_DB は変更前状態に resync。STATE_DB に "failed" 記録。ハードウェア影響なし（systemd unit が起動していない）。**

---

### 4. `disable_feature()` systemd stop/disable/mask コマンド失敗 → STATE_DB に "failed" 記録・False 返却

`featured:539-545`:

```python
except Exception as err:
    syslog.syslog(syslog.LOG_ERR, "Feature '{}.{}' failed to be stopped and disabled"
                  .format(feature.name, feature_suffixes[-1]))
    self.set_feature_state(feature, self.FEATURE_STATE_FAILED)
    return False
```

`wait_for_service_stable()` で最大 60 秒待機後 (`featured:436`)、`systemctl stop` / `systemctl disable` / `systemctl mask` のいずれかが失敗すると `FEATURE_STATE_FAILED`。

停止処理は **reversed order** (`reversed(feature_suffixes)`) で実行され、service suffix 順に stop → disable → mask を実施。コマンドは for ループ内で逐次実行されるため、最初の失敗で `return False` となり以降のコマンドは実行されない（中途状態になりうる）。

**retry なし。CONFIG_DB は変更前状態に resync（handler:216-217）。STATE_DB に "failed"。コンテナが稼働中のまま残るリスクあり。**

---

### 5. `sync_feature_scope()` 内 multi-asic scope 停止失敗 → STATE_DB に "failed"・即 return

`featured:342-345`:

```python
except Exception as err:
    syslog.syslog(syslog.LOG_ERR, "Feature '{}.{}' failed to be stopped and disabled"
                  .format(feature_name, feature_suffixes[-1]))
    self.set_feature_state(feature_config, self.FEATURE_STATE_FAILED)
    return
```

multi-ASIC 環境で `has_per_asic_scope` / `has_global_scope` が False に変化した場合、対象インスタンスを stop → disable → mask するが、いずれかが失敗すると即 `return`（False でなく `None`）。スコープ更新後の `_conditional_update_scope()` による CONFIG_DB 書き込みがスキップされる。

**retry なし。CONFIG_DB の scope フィールドは古い値のまま（DB と実状態が乖離）。STATE_DB に "failed"。**

---

### 6. `get_multiasic_feature_instances()` でインスタンス名空 → syslog ERR のみ（続行）

`featured:418-420`:

```python
if not feature_names:
    syslog.syslog(syslog.LOG_ERR, "Feature '{}' service not available"
                  .format(feature.name))
```

`has_global_scope=False` / `has_per_asic_scope=False` かつ non-multi-ASIC 環境では `feature_names=[]`。ログのみで継続し、`enable_feature()` / `disable_feature()` はループを0回実行して `True` を返す（実質 no-op）。STATE_DB は "enabled" / "disabled" に更新されるが、実際の systemd 操作はゼロ。

**retry なし。STATE_DB は "enabled"/"disabled" に更新（実態と乖離）。syslog ERR のみ。**

---

### 7. `update_systemd_config()` の `daemon-reload` 失敗 → syslog ERR のみ（続行）

`featured:401-406`:

```python
try:
    run_cmd(["sudo", "systemctl", "daemon-reload"], raise_exception=True)
except Exception as err:
    syslog.syslog(syslog.LOG_ERR, "Failed to reload systemd configuration files!")
```

`auto_restart.conf` ファイル書き込みは成功しても `daemon-reload` が失敗した場合、古い systemd 設定が使用され続ける（`Restart=` フィールドが未反映）。例外を捕捉して **続行**するため、`handler()` は auto_restart 更新済みとして `cached_config` を更新する。

**retry なし。CONFIG_DB / STATE_DB への影響なし。systemd の Restart= 設定が古いまま残る。syslog ERR のみ。**

---

### 8. `handler()` でのキャッシュミス (空の feature_cfg) → deregister

`featured:186-191`:

```python
def handler(self, feature_name, op, feature_cfg):
    if not feature_cfg:
        syslog.syslog(syslog.LOG_INFO, "Deregistering feature {}".format(feature_name))
        self._cached_config.pop(feature_name, None)
        self._feature_state_table._del(feature_name)
        return
```

`DEL` op または空の feature_cfg が届いた場合、`_cached_config` からエントリを削除し STATE_DB の `FEATURE|<name>` エントリも削除する。systemd unit への stop/disable はなし（STATE_DB 削除のみ）。

**retry なし。CONFIG_DB は操作なし（書き戻しなし）。STATE_DB エントリ削除。systemd unit はそのまま稼働継続。**

---

### 9. `state` 不正な状態遷移 → syslog ERR + False 返却

`featured:264-266` (`update_feature_state()`):

```python
else:
    syslog.syslog(syslog.LOG_INFO, "Feature {} service is {}".format(feature.name, cached_feature.state))
    return False
```

`cached_feature.state` が `None` / `always_enabled` / `always_disabled` / `enabled` / `disabled` 以外の値（例: "failed"、カスタム文字列）の場合、`update_feature_state()` は False を返す。`handler()` は `resync_feature_state()` を呼び出す。

**retry なし。STATE_DB への書き込みなし。CONFIG_DB は resync（旧状態を書き戻し）。**

---

## STATE_DB への障害記録

`FeatureHandler.set_feature_state()` (`featured:585-590`) が `STATE_DB` の `FEATURE|<name>` テーブルに `state` フィールドを書き込む:

| `FEATURE_STATE_*` 定数 | STATE_DB 値 | 発生ケース |
|---|---|---|
| `FEATURE_STATE_ENABLED` = `"enabled"` | `"enabled"` | enable_feature() 正常完了 |
| `FEATURE_STATE_DISABLED` = `"disabled"` | `"disabled"` | disable_feature() 正常完了 |
| `FEATURE_STATE_FAILED` = `"failed"` | `"failed"` | enable_feature() / disable_feature() / sync_feature_scope() コマンド失敗 |

multi-ASIC では各 namespace の STATE_DB にも同時書き込み (`ns_feature_state_tbl[ns].set(...)`)。

確認コマンド: `sonic-db-cli STATE_DB hgetall 'FEATURE|<feature_name>'`

ERROR_TABLE への書き込みはなし。syslog (`syslog.LOG_ERR`) のみ。

---

## handler() での失敗 → resync パターン

`featured:212-217`:

```python
if self._cached_config[feature_name].state != feature.state:
    if self.update_feature_state(feature):
        self.sync_feature_scope(feature)
        self._cached_config[feature_name] = feature
    else:
        self.resync_feature_state(self._cached_config[feature_name])
```

`update_feature_state()` が False を返した場合、`resync_feature_state()` が CONFIG_DB の `state` フィールドを `_cached_config` の値（変更前の値）に書き戻す。ただし `_feature_state_is_immutable()` または `_feature_state_is_template()` の条件が成立する場合のみ書き戻し実行（`featured:567-568`）。

---

## retry パターンサマリ

| パターン | 対象ケース | 挙動 | STATE_DB |
|---|---|---|---|
| `ValueError` raise (デーモンクラッシュリスク) | `has_timer` フィールド存在 / `state` render 不正値 | 例外がイベントループに伝播 | 書き込みなし |
| `return False` + resync | enable/disable 失敗 / 不正状態遷移 | CONFIG_DB を旧状態に書き戻し | "failed" / 変更なし |
| `return` (None) + DB 乖離 | multi-asic scope stop 失敗 | scope フィールド未更新 | "failed" |
| syslog のみ・続行 | daemon-reload 失敗 / instance 名空 | systemd 設定未反映 / no-op 続行 | "enabled"/"disabled" (乖離あり) |
| deregister | 空 feature_cfg (DEL op) | STATE_DB エントリ削除、systemd 操作なし | エントリ削除 |

---

## rollback 挙動まとめ

- CONFIG_DB のエントリは featured が削除しない（deregister 時も CONFIG_DB は操作なし）
- enable/disable 失敗時は `resync_feature_state()` が CONFIG_DB の `state` を変更前値に書き戻す（条件付き）
- `"failed"` 状態になった後、CLI で `config feature state <name> enabled/disabled` を再実行すれば featured が再試行
- `has_timer` / 不正 state render による `ValueError` はデーモン再起動（`systemctl restart featured`）が必要
