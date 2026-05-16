# NTP_KEY フィールド暗黙デフォルト調査メモ

調査日: 2026-05-15
対象テーブル: CONFIG_DB `NTP_KEY`

## 調査対象ファイル

- `sonic-host-services/scripts/hostcfgd` (`NtpCfg` クラス / `ntp_srv_key_update()`)
- `sonic-buildimage/files/image_config/chrony/chrony.keys.j2` (chrony keyfile テンプレート)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-ntp.yang` (YANG default 宣言)

備考: 独立した `ntp.keys.j2` (ntpd 用) は master では削除済みで、現行は chrony 専用テンプレート (`chrony.keys.j2`) のみが使用される。

---

## フィールド別 暗黙デフォルト

### `type` (NTP_KEY|<id>)

**YANG default**: `md5` (`sonic-ntp.yang` typedef `key-type` の `default md5`)

**コード由来デフォルト挙動**:

`chrony.keys.j2` (`files/image_config/chrony/chrony.keys.j2`) は鍵を出力する直前で `type` と `value` の両方を要求する:

```jinja2
{% for keyid in NTP_KEY if NTP_KEY[keyid].type and NTP_KEY[keyid].value %}
{{ keyid }} {{ NTP_KEY[keyid].type | upper }} {{ keyval }}{{trusted_str}}
{% endfor -%}
```

- `NTP_KEY[keyid].type` が falsy (空文字 / 未設定) の鍵はテンプレ展開でスキップされ、chrony keyfile に出力されない。
- YANG バリデーション経由で書き込まれた場合、`default md5` が補完されて `type` は常に non-empty となる。
- 直接 `redis-cli` で `type` 未設定の鍵を書き込むと chrony keyfile から除外され、ハードウェア (ntpd/chrony) に到達しない (silent drop)。
- `NTP_KEY[keyid].type | upper` で `MD5/SHA1/SHA256/SHA384/SHA512` に正規化されて keyfile に書かれる。

**実質デフォルト**: `md5` (YANG default 経由)、ただし type が空の場合は **テンプレでスキップ** され実装に渡らない。

---

### `trusted` (NTP_KEY|<id>)

**YANG default**: `no` (`sonic-ntp.yang` の `leaf trusted` で `default no`)

**コード由来デフォルト挙動**:

`chrony.keys.j2` 内では `NTP_KEY[*].trusted` は **参照されない**。代わりに `NTP_SERVER[*].trusted` を集約して `trusted_str` を生成し、各 key 行末に同じ trusted server リストを付与している:

```jinja2
{% set trusted_arr = [] -%}
{% for server in NTP_SERVER if NTP_SERVER[server].trusted == 'yes' and
                               NTP_SERVER[server].resolve_as -%}
    {% set _ = trusted_arr.append(NTP_SERVER[server].resolve_as) -%}
{% endfor -%}
{% set trusted_str = ' ' ~ trusted_arr|join(',') -%}
```

- chrony 視点では `NTP_KEY.trusted` は **読み捨て** (dead field 相当)。鍵の trusted 判定は `NTP_SERVER.trusted` のサーバ側に紐付く。
- YANG default `no` は CONFIG_DB に正規化された値を残すのみで、chrony keyfile 生成には影響しない。
- ドキュメント本文の「`trusted=no` のキーで authenticate しようとして時刻同期が失敗する」記述は CLI/UX レベルの話で、テンプレ実装上は trusted=yes/no のどちらでも chrony keyfile 出力は同じになる。

**実質デフォルト**: `no` (YANG default、ただし `chrony.keys.j2` では未参照)。

---

### `value` (NTP_KEY|<id>)

**YANG default**: なし (必須・`length 1..64`)

**コード由来デフォルト挙動**:

`chrony.keys.j2` の `if NTP_KEY[keyid].type and NTP_KEY[keyid].value` で `value` 空はスキップ。`value | b64decode` で base64 デコードしてから書き出される。YANG が `length 1..64` で空を拒否するため、通常経路ではここに到達しない。

---

### `id` (NTP_KEY key)

**YANG default**: なし (key 自体、`range 1..65535`)

key 部分のため暗黙デフォルトは存在しない。`leafref` で `NTP_SERVER_LIST/key` から参照される整合性制約のみ。

---

## 要約表

| フィールド | YANG default | コード由来挙動 | 発生源 |
|---|---|---|---|
| `type` | `md5` | `chrony.keys.j2`: `type` が falsy ならエントリスキップ。`upper` で正規化 | `chrony.keys.j2:15-17` / `sonic-ntp.yang typedef key-type` |
| `trusted` | `no` | `chrony.keys.j2` では **未参照**。trusted 判定は `NTP_SERVER.trusted` 側 | `chrony.keys.j2:8-13` / `sonic-ntp.yang leaf trusted` |
| `value` | なし (必須) | falsy 値はスキップ。`b64decode` 通過 | `chrony.keys.j2:15-16` |
| `id` | なし (key) | leafref 参照整合性のみ | `sonic-ntp.yang typedef key-id` |

---

## hostcfgd 側の挙動

`hostcfgd:1366-1406` `ntp_srv_key_update()`:

- DB から取得した `ntp_keys` をキャッシュ (`self.cache['keys']`) と比較し、同一なら ntp.conf 再生成スキップ (`hostcfgd:1383-1384`)。
- Python レイヤでフィールド単位の default 補完は **しない** (AaaCfg のような `*_default` dict は NTP_KEY には存在しない)。
- そのまま Jinja2 context に渡し、テンプレ側 (`chrony.keys.j2`) で falsy フィルタが効く。

つまり「コード由来の暗黙デフォルト」は **テンプレートの `if` フィルタ** が主体で、Python 側で値を補完するロジックはない。YANG default (`md5` / `no`) が CONFIG_DB に正規化済みであることに依存している。

---

## 証拠リンク

- `sonic-buildimage/files/image_config/chrony/chrony.keys.j2` (commit 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)
- `sonic-host-services/scripts/hostcfgd:1278-1406` (`NtpCfg.load` / `ntp_srv_key_update`)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-ntp.yang` (typedef `key-type` default md5、`leaf trusted` default no)
