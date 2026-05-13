# BANNER_MESSAGE テーブル — consumer 例外条件分析

## Consumer: hostcfgd / BannerCfg (sonic-host-services/scripts/hostcfgd)

### 処理関数
- `BannerCfg.load(banner_messages_config)` (L2057)
- `BannerCfg.banner_message(key, data)` (L2084)

### 例外条件・特殊挙動

#### 1. data が dict でない → 処理スキップ
`type(data) != dict` の場合は即 return。ログも出さない。
key に無効な値が来ても silent skip となる。

```python
# sonic-host-services/scripts/hostcfgd:2095
if type(data) != dict:
    # Nothing to handle
    return
```

#### 2. キャッシュ差分チェック
各 key-value を前回キャッシュと比較し、変更がない場合は `banner-config` サービス再起動をスキップ。

```python
# sonic-host-services/scripts/hostcfgd:2099
for k,v in data.items():
    if v != self.cache.get(k):
        update_required = True
        break
if update_required == False:
    return
```

#### 3. banner-config 再起動失敗 → syslog ERR & skip (キャッシュ更新なし)
`systemctl restart banner-config` が例外を投げた場合、syslog ERR を出して return。
キャッシュは更新されないため、次回の変更時に再試行が発生する。

```python
# sonic-host-services/scripts/hostcfgd:2111
try:
    run_cmd(["systemctl", "restart", "banner-config"], True, True)
except Exception:
    syslog.syslog(syslog.LOG_ERR, 'BannerCfg: Failed to restart banner-config service')
    return
```

#### 4. banner_messages_config 空/None → 全 key を空 dict で処理
`load()` で config が空の場合は `{}` を代入し、state/login/motd/logout の各 key を空 dict で `banner_message()` に渡す。
空 dict は `type(data) == dict` を満たすが全 key-value が空なため、キャッシュと差分がなければ再起動なし。

#### 5. key は固定 4 種 (state, login, motd, logout)
load() は `banner_messages_config.get("state", {})` のように固定 key のみを読む。
CONFIG_DB に追加フィールドが存在しても読まれない。
