# Phase G 通信メカニズム抽出: KDUMP

## 対象ページ
`docs/reference/config-db/kdump.md`

## 調査ソース

- `sonic-host-services/scripts/hostcfgd` (L1163-1270, L2393-2395, L2456-2468)
- `sonic-utilities/scripts/sonic-kdump-config` (L640-718, L749-851)

## CONFIG_DB Subscribe (hostcfgd Python)

`hostcfgd` は `swsscommon.ConfigDBConnector.subscribe()` で `KDUMP` テーブルを購読する。

```python
# hostcfgd:2468
self.config_db.subscribe('KDUMP', make_callback(self.kdump_handler))
```

`make_callback` wrapper がテーブルイベントを `(key, op, data)` に変換し、
`kdump_handler(key, op, data)` → `KdumpCfg.kdump_update(key, data)` と転送する。

## ハンドラ分岐

`kdump_update()` は `key == "config"` の場合のみ有効（単一 container なので実質常時）。

データフィールドごとに `sonic-kdump-config` サブコマンドを個別に呼び出す順次実行。
`enabled` の true/false で `--enable` / `--disable` を切り替える分岐のみ存在。

## grub-mkconfig 経路

`sonic-kdump-config --enable/--disable` は `/host/grub/grub.cfg` を直接書き換える (`rewrite_cfg()`)。
SONiC では `grub-mkconfig` を呼ばず、grub.cfg を直接パッチする独自方式を採用。

- `crashkernel=` パラメータが存在しない行に追記、または既存値を置換
- `/proc/cmdline` にすでに `crashkernel=` がある場合は `/usr/sbin/kdump-config load` でオンラインリロード

## systemctl 制御

`kdump-tools` サービスの `systemctl restart` は hostcfgd から呼ばれない。
設定ファイル書き換え後、次回 reboot でカーネルへ反映される。

例外: `crash_kernel_in_cmdline is not None` の場合のみ `/usr/sbin/kdump-config load` 呼び出し。

## 起動時初期化

1. `init_kdump_config_from_cmdline()` で `/proc/cmdline` の `crashkernel=` を確認
2. 存在する場合は `KDUMP|config` の `enabled`/`memory` を強制上書き (`mod_entry()`)
3. `KdumpCfg.load()` で未設定フィールドをハードコードデフォルトで補完
4. `kdump_update()` で初回 `sonic-kdump-config` 実行
5. `register_callbacks()` で subscribe 登録、以降はイベント駆動

## イベント経路図

```
KDUMP|config 変更
  → ConfigDBConnector subscribe
  → kdump_handler(key, op, data)
  → KdumpCfg.kdump_update(key, data)
  → sonic-kdump-config --enable/--disable  → /host/grub/grub.cfg
  → sonic-kdump-config --memory            → /etc/default/kdump-tools
  → sonic-kdump-config --num_dumps         → /etc/default/kdump-tools
  → sonic-kdump-config --ssh_string        → /etc/default/kdump-tools
  → sonic-kdump-config --ssh_path          → /etc/default/kdump-tools
  → sonic-kdump-config --remote            → /etc/default/kdump-tools
  (次回 reboot でカーネル反映)
```

## 特記事項

- `grub-mkconfig` は使用しない。SONiC 独自の grub.cfg 直接書き換え方式
- `systemctl` 制御なし（kdump-tools は reboot 依存）
- `/proc/cmdline` の `crashkernel=` が CONFIG_DB 設定より優先される起動時上書きあり
- APPL_DB / SAI 非経由（ホスト OS 設定ファイル直接更新）
