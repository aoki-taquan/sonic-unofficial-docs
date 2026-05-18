# NTP_KEY — Phase E: ハードコード定数調査

対象テーブル: `NTP_KEY`
調査日: 2026-05-18

## 調査対象ファイル

| ファイル | 役割 |
|---------|------|
| `sonic-host-services/scripts/hostcfgd` | `NtpCfg` クラス — `CHRONY_RESTART` 定数、ログマスク |
| `sonic-buildimage/files/image_config/chrony/chrony.keys.j2` | chrony.keys 生成テンプレート — ファイルパス、フォーマット |
| `sonic-buildimage/files/image_config/chrony/chrony.conf.j2` | chrony.conf 生成テンプレート — keyfile パス |
| `sonic-buildimage/files/image_config/chrony/chrony-config.sh` | ビルド時 ExecStartPre — テンプレート展開先パス、chmod 定数 |
| `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-ntp.yang` | YANG スキーマ — `key-id` range、`key-type` enum |

---

## 1. systemd ユニット名 (hostcfgd L1280)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `NtpCfg.CHRONY_RESTART` | `['systemctl', 'restart', 'chrony']` | `NTP_KEY` / `NTP_SERVER` / `NTP` 変更時の chrony 再起動コマンド。リスト形式で `run_cmd()` に渡す | `hostcfgd:1280` |

---

## 2. chrony.keys ファイルパス (chrony-config.sh L10-11)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| chrony.keys 出力先 | `/etc/chrony/chrony.keys` | `chrony-config.sh` が `sonic-cfggen` でテンプレートを展開して書き出すパス | `chrony-config.sh:10` |
| chmod 値 | `o-r` (others から read 権を除去) | 鍵ファイルへのアクセスを chrony ユーザに限定するための固定 chmod | `chrony-config.sh:11` |
| chrony.keys テンプレートパス | `/usr/share/sonic/templates/chrony.keys.j2` | `sonic-cfggen -d -t <このパス>` で DB から生成 | `chrony-config.sh:10` |

---

## 3. chrony.conf の keyfile 行 (chrony.conf.j2 L127)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| keyfile パス (chrony.conf 中) | `/etc/chrony/chrony.keys` | `global.authentication == 'enabled'` のとき chrony.conf に `keyfile /etc/chrony/chrony.keys` を出力。chrony はこのパスからのみ鍵を読み込む | `chrony.conf.j2:127` |

---

## 4. YANG スキーマ定数 (sonic-ntp.yang)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `key-id` の range | `1..65535` | NTP_KEY テーブルキー (`id`) の有効範囲。0 および 65536 以上は YANG が拒否する (`error-message "Failed NTP key ID"`) | `sonic-ntp.yang` typedef `key-id` |
| `key-type` enum | `md5` / `sha1` / `sha256` / `sha384` / `sha512` | `NTP_KEY.type` の有効値セット。YANG default は `md5` | `sonic-ntp.yang` typedef `key-type` |
| `value` の length | `1..64` | `NTP_KEY.value` の有効文字列長。空文字列と 65 文字以上は拒否 | `sonic-ntp.yang` leaf `value` |
| `NTP_SERVER` max-elements | `10` | NTP サーバの最大登録数。`NTP_KEY` 自体の最大数制限は YANG に存在しない | `sonic-ntp.yang` list `NTP_SERVER_LIST` |

---

## 5. chrony.keys.j2 テンプレート固定値 (chrony.keys.j2)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| キー行フォーマット | `<keyid> <TYPE> <value><trusted_str>` | chrony keyfile の 1 エントリ形式。`<TYPE>` は `type \| upper` で大文字正規化 | `chrony.keys.j2:17` |
| value デコード方式 | `b64decode` フィルタ | `NTP_KEY.value` は base64 エンコード済み前提。`\| b64decode` でデコードして keyfile に書き出す | `chrony.keys.j2:16` |
| type 正規化フィルタ | `\| upper` | `md5` → `MD5`、`sha256` → `SHA256` のように uppercase 変換 (chrony が大文字アルゴリズム名を要求する) | `chrony.keys.j2:17` |

---

## 特記事項

1. **`NTP_KEY` 個数上限の YANG 制約なし**: `NTP_SERVER_LIST` は `max-elements 10` を持つが、`NTP_KEY_LIST` には max-elements 制約がなく、chrony / ntpd の内部制限のみが上限となる。
2. **`chrony.keys` の権限 (o-r)**: `chrony-config.sh:11` で `chmod o-r /etc/chrony/chrony.keys` をハードコード実行。root 以外のユーザが鍵ファイルを読めないように固定化されている。この権限は `hostcfgd` の再起動処理では更新されない（`chrony-config.sh` の ExecStartPre でのみ設定）。
3. **value の base64 デコードはテンプレートに固定**: `NTP_KEY.value` が base64 以外の形式で格納された場合、Jinja2 の `b64decode` フィルタがエラーを発生させ chrony.keys 生成が失敗する。YANG スキーマは `length 1..64` のみ検証し、エンコード形式は検証しない。
4. **CHRONY_RESTART は `chrony` ユニット名のみ**: `ntpd` (NTPd) 用の定数は存在せず、SONiC の NTP 実装は chrony に固定されている。

---

## 出典

- `sonic-net/sonic-host-services/scripts/hostcfgd` L1280
- `sonic-net/sonic-buildimage/files/image_config/chrony/chrony-config.sh` L10-11
- `sonic-net/sonic-buildimage/files/image_config/chrony/chrony.keys.j2` L15-17
- `sonic-net/sonic-buildimage/files/image_config/chrony/chrony.conf.j2` L124-127
- `sonic-net/sonic-buildimage/src/sonic-yang-models/yang-models/sonic-ntp.yang` (typedef `key-id`、`key-type`、leaf `value`)
