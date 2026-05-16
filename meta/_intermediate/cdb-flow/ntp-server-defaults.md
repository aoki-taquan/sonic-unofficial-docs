# NTP_SERVER フィールド暗黙デフォルト調査メモ

調査日: 2026-05-15
対象テーブル: CONFIG_DB `NTP_SERVER`

## 調査対象ファイル

- `sonic-host-services/scripts/hostcfgd` (`NtpCfg` クラス、`ntp_srv_key_update()`)
- `sonic-buildimage/files/image_config/chrony/chrony.conf.j2` (chrony 設定生成テンプレート)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-ntp.yang` (YANG 既定値 — 参考)
- `sonic-buildimage/src/sonic-config-engine/minigraph.py` (minigraph 由来の自動投入)

---

## 重要な前提

`NtpCfg` 自体は `authentication_default` のような Python 側デフォルト dict を保持しない。
DB から読み出した `ntp_servers` dict をそのまま `chrony.conf.j2` テンプレートに渡し、chrony.conf を再生成する (`hostcfgd:1366-1401`)。

**結論: NTP_SERVER の「コード由来デフォルト」は `chrony.conf.j2` 内の Jinja2 `| d(...)` フィルタ (Jinja2 default フィルタ) によって決まる。**

---

## フィールド別 コード由来デフォルト

### `association_type`

**コード由来デフォルト**: `'server'`

```jinja
{# chrony.conf.j2:26 #}
{% set association_type = config.association_type | d('server') -%}
```

DB に `association_type` キーが無い場合、Jinja2 の `default('server')` フィルタにより `server` ディレクティブが chrony.conf に書き込まれる。
YANG `default server` (sonic-ntp.yang) と同値だが、テンプレート側でも独立してフォールバックを担保している。

### `resolve_as`

**コード由来デフォルト**: `<server_address>` (テーブル key そのもの)

```jinja
{# chrony.conf.j2:27 #}
{% set resolve_as = config.resolve_as | d(server) -%}
```

ここで `server` は `for server in NTP_SERVER` のループ変数 = NTP_SERVER のテーブル key (=入力されたサーバアドレス) である。
DB に `resolve_as` (名前解決済み IP) が無い場合、テンプレートに渡されている key そのものを `chrony.conf` の host フィールドに使う。

**さらに**、`association_type == 'pool'` の場合は `resolve_as` の値に関わらず `resolve_as = server` で上書きされる (chrony.conf.j2:49-51)。pool は FQDN のまま使うのが意図。

### `iburst`

**コード由来デフォルト**: キー不在 → Jinja2 で falsy → `iburst` オプション**付与なし**

```jinja
{# chrony.conf.j2:37-39 #}
{% if config.iburst -%}
    {% set soptions = soptions ~ ' iburst' -%}
{% endif -%}
```

`config.iburst` を **truthy 判定**（`| d(...)` フィルタなし）するため:

- DB キー不在 → Jinja2 `undefined` → falsy → `iburst` オプション無し
- DB 値 `'on'` (文字列非空) → truthy → `iburst` 付与
- DB 値 `'off'` (文字列非空) → **truthy → `iburst` 付与される**(!)

つまり `chrony.conf.j2` 単体では「値が `off`」でも `iburst` が付く実装上の癖がある。
ただし運用上は minigraph.py が `iburst: 'on'` を自動投入し (`minigraph.py:2646`)、YANG `default on` (sonic-ntp.yang) も on を強制するため、実害は出にくい。

YANG の `default on` とテンプレート挙動の不整合は留意事項。

### `version`

**コード由来デフォルト**: キー不在 → `version` オプション付与なし

```jinja
{# chrony.conf.j2:42-44 #}
{% if config.version -%}
    {% set soptions = soptions ~ ' version ' ~ config.version -%}
{% endif -%}
```

YANG `default 4` で DB 投入時に 4 が埋まる前提だが、テンプレート単体ではキー不在時に何も付与せず chrony 側のデフォルト (NTPv4) に任せる。

### `key`

**コード由来デフォルト**: キー不在 → `key` オプション付与なし。
かつ `global.authentication == 'enabled'` の場合のみ参照される (chrony.conf.j2:30-34)。
DB に `key` があっても authentication が disabled なら chrony.conf に書かれない。

### `admin_state`

**コード由来デフォルト**: キー不在 → エントリ採用（disabled でない限り含める）

```jinja
{# chrony.conf.j2:20 #}
{% for server in NTP_SERVER if NTP_SERVER[server].admin_state != 'disabled' -%}
```

`admin_state` キーが DB に無い場合 `!= 'disabled'` が真 → エントリは chrony.conf に含まれる。
YANG `default enabled` と同じ運用効果。

### `minpoll` / `maxpoll`

**コード由来デフォルト**: **未実装**（テンプレートも YANG も持たない）

`chrony.conf.j2` には `minpoll` / `maxpoll` への参照が無い。`sonic-ntp.yang` の `NTP_SERVER_LIST` にも当該 leaf 無し。
SONiC の NTP_SERVER モデルでは `minpoll`/`maxpoll` を CONFIG_DB から制御できない。chrony 側のデフォルト (`minpoll 6 / maxpoll 10` = 64s〜1024s) がそのまま使われる。

---

## 要約表

| フィールド | コード由来デフォルト | 源 | YANG default との関係 |
|-----------|--------------------|----|--------------------|
| `association_type` | `'server'` | `chrony.conf.j2:26` `\| d('server')` | YANG `default server` と同値 |
| `resolve_as` | テーブル key (=サーバアドレス) | `chrony.conf.j2:27` `\| d(server)` | YANG default 無し — テンプレート専用 |
| `iburst` | キー不在 → 付与なし／値あれば全て付与 | `chrony.conf.j2:37-39` (truthy 判定のみ) | YANG `default on` — テンプレートは off でも付与する不整合あり |
| `version` | キー不在 → 付与なし | `chrony.conf.j2:42-44` | YANG `default 4` で投入される前提 |
| `key` | キー不在 → 付与なし | `chrony.conf.j2:30-34` (auth=enabled 時のみ) | YANG default 無し |
| `admin_state` | キー不在 → 採用 | `chrony.conf.j2:20` (`!= 'disabled'`) | YANG `default enabled` と同等 |
| `minpoll` / `maxpoll` | **モデル未実装** | テンプレート/YANG 双方に無し | — |

---

## 証拠リンク

- `sonic-host-services/scripts/hostcfgd:1272-1401` — `NtpCfg` クラス全体（デフォルト dict は持たず、DB→テンプレート直結）
- `sonic-buildimage/files/image_config/chrony/chrony.conf.j2:20-55` — NTP_SERVER ループとフィールド既定値
- `sonic-buildimage/src/sonic-config-engine/minigraph.py:2646` — `iburst: 'on'` 自動投入（Phase 6 派生で記録済み）
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-ntp.yang` — YANG `default` 句（参考）
