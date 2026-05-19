# fips — side-effects scan notes

## 対象ファイル

- `sonic-host-services/scripts/hostcfgd` — `FipsCfg` クラス (L1753-1846)

## 検出された副作用

### 1. `/etc/fips/fips_enable` への書込み

`update_noneenforce_config()` (hostcfgd:1795-1809) が `FipsCfg.enable` の値に応じて
`/etc/fips/fips_enable` に `"0"` または `"1"` を書き込む。

```python
if cur_fips_enabled != expected_fips_enabled:
    os.makedirs(os.path.dirname(OPENSSL_FIPS_CONFIG_FILE), exist_ok=True)
    with open(OPENSSL_FIPS_CONFIG_FILE, 'w') as f:
        f.write(expected_fips_enabled)
```

- ディレクトリが存在しない場合は自動作成される
- このファイルは OpenSSL の FIPS provider ロードに影響するが、**既存プロセスには即座に伝播しない**

### 2. systemd サービス再起動

`restart()` (hostcfgd:1811-1835) が以下の条件で実行される:

条件チェック:
1. `cur_enforced=True` の場合: **スキップ**（FIPS enforce 中はサービス再起動不要）
2. `FIPS_STATS|state.config_datetime` > `/etc/fips/fips_enable` の mtime の場合: **スキップ**（二重再起動防止）

再起動対象:
- デフォルト: `['ssh', 'telemetry.service', 'restapi']`（`DEFAULT_FIPS_RESTART_SERVICES` = hostcfgd:103）
- `/etc/sonic/fips.json` の `restart_services` キーで上書き可能（hostcfgd:1766-1769）
- `systemctl -t service --state=running` で running 状態のサービスのみ再起動

```python
for service in self.restart_services:
    if service in services or service + '.service' in services:
        run_cmd(['sudo', 'systemctl', 'restart', service])
```

### 3. ブートローダー FIPS enforce 設定変更

`update_enforce_config()` (hostcfgd:1837-1846):

```python
loader = bootloader.get_bootloader()
image = loader.get_next_image()
next_enforced = loader.get_fips(image)
if next_enforced == self.enforce:
    return  # 変更不要
loader.set_fips(image, self.enforce)
```

- 次回起動イメージのブートローダー設定を変更する
- **再起動後**に `sonic_fips=1` カーネルパラメータが有効化/無効化される
- 副作用 1（OpenSSL ファイル書込み）より先に実行される

### 4. STATE_DB タイムスタンプ更新

`update()` (hostcfgd:1792):

```python
self.state_db_conn.hset('FIPS_STATS|state', 'config_datetime', datetime.utcnow().isoformat())
```

- `update()` 呼出しごとに必ず実行される
- `restart()` の二重再起動防止チェックにも使用される

## 実行順序

```
update()
├── update_enforce_config()   [副作用 3: bootloader 設定変更]
├── update_noneenforce_config()
│   ├── /etc/fips/fips_enable 書込み [副作用 1]
│   └── restart()             [副作用 2: サービス再起動]
└── state_db_conn.hset(...)   [副作用 4: STATE_DB 更新]
```

## 非一貫状態リスク

- `update_enforce_config()` 失敗時: OpenSSL FIPS（副作用 1）は変わるがブートローダーには反映されない
- `restart()` の `run_cmd` 失敗: 例外ハンドリングなし → 後続サービスが再起動されない可能性

## evidence

- `hostcfgd:1753-1846` — FipsCfg クラス全体
- `hostcfgd:1788-1793` — update() 呼出しシーケンス
- `hostcfgd:1795-1809` — update_noneenforce_config
- `hostcfgd:1811-1835` — restart()
- `hostcfgd:1837-1846` — update_enforce_config()
- `hostcfgd:103` — DEFAULT_FIPS_RESTART_SERVICES
