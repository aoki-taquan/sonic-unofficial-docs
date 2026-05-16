# Phase A — BANNER_MESSAGE フィールド暗黙デフォルト調査

## 対象フィールド

| フィールド | YANG default | init_cfg.json.j2 | コード fallback |
|-----------|-------------|-----------------|----------------|
| `state`   | `disabled`  | `"disabled"`    | `.get("state", {})` → `{}` (dict型でなければ silent return) |
| `login`   | `"Debian GNU/Linux 11"` | `"Debian GNU/Linux 11"` | `.get("login", {})` → `{}` (なければ空dict、banner-config.sh では空文字列展開) |
| `motd`    | SONiC ASCII アート文字列 (多行) | 同一内容 (改行を `\n` でエスケープ) | `.get("motd", {})` → `{}` |
| `logout`  | `""` (空文字列) | `""` | `.get("logout", {})` → `{}` |

## 詳細分析

### YANG デフォルト (sonic-banner.yang)

```
leaf state  → default disabled;
leaf login  → default "Debian GNU/Linux 11";
leaf motd   → default "<SONiC ASCII アート + 注意文>";
leaf logout → default "";
```

ソース: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-banner.yang`

### init_cfg.json.j2 ハードコード値

`sonic-buildimage/files/build_templates/init_cfg.json.j2:180-186` に全 4 フィールドを明示:
- `state`: `"disabled"`
- `login`: `"Debian GNU/Linux 11"`
- `motd`: SONiC アスキーアート + 警告文 (改行 `\n` 込み、約 200 文字)
- `logout`: `""`

→ YANG default と完全一致。

### hostcfgd の Python fallback

`sonic-host-services/scripts/hostcfgd:2069-2077` (`BannerCfg.load`):

```python
if not banner_messages_config:
    banner_messages_config = {}

state_data  = banner_messages_config.get("state",  {})
login_data  = banner_messages_config.get("login",  {})
motd_data   = banner_messages_config.get("motd",   {})
logout_data = banner_messages_config.get("logout", {})
```

- CONFIG_DB エントリが存在しない場合、各 `*_data` は `{}` (空 dict)
- `banner_message()` メソッド (`hostcfgd:2096`) で `type(data) != dict` チェックがあるが、`{}` は dict なので通過
- キャッシュ (`self.cache = {}`) と差分なし → `update_required = False` → no-op

つまり CONFIG_DB になければ **何もしない** (既存 `/etc/issue` 等を上書きしない)。

### banner-config.sh の shell fallback

`sonic-buildimage/files/image_config/bannerconfig/banner-config.sh`:

```bash
STATE=$(sonic-db-cli CONFIG_DB HGET 'BANNER_MESSAGE|global' state)
LOGIN=
MOTD=
LOGOUT=
if [[ $STATE == "enabled" ]]; then
    LOGIN=$(...)
    ...
fi
```

- `state` が DB になければ `STATE` は空文字列 → `if` ブランチに入らない → ファイル書き換えなし
- `login`/`motd`/`logout` は `state=enabled` 時のみ読み込まれる。DB になければ空文字列 → `echo -e ""` で空ファイル作成

## 結論: per-field 暗黙デフォルト

| フィールド | 暗黙デフォルト (DB なし) | ソース層 |
|-----------|----------------------|---------|
| `state`   | `{}` → shell では空文字列 → バナー無効化と同等 | hostcfgd `.get("state", {})` / banner-config.sh 空文字列 |
| `login`   | `{}` → no-op (ファイル未書き換え) / `state=enabled` 時は `""` で `/etc/issue` 空白化 | hostcfgd `.get("login", {})` / banner-config.sh `LOGIN=` |
| `motd`    | `{}` → no-op / `state=enabled` 時は `""` で `/etc/motd` 空白化 | 同上 |
| `logout`  | `{}` → no-op / `state=enabled` 時は `""` で `/etc/logout_message` 空白化 | 同上 |

**重要**: YANG の `default` 値は **sonic-cfggen が init_cfg.json.j2 を展開してDBに書く段階**で適用される。
コードレベルの fallback は「DBエントリ自体がない場合の振る舞い」であり、その場合は no-op (既存ファイル維持) となる。
YANG default は runtime fallback ではなく、プロビジョニング時のデフォルト値。
