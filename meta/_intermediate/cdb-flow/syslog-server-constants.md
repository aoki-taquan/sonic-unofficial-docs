# SYSLOG_SERVER — Phase E: ハードコード定数調査

## 調査対象ファイル

- `sonic-buildimage/files/image_config/rsyslog/rsyslog.conf.j2`
- `sonic-buildimage/files/image_config/rsyslog/rsyslog-config.sh`

---

## ハードコード定数一覧

### ポート・プロトコルデフォルト定数 (rsyslog.conf.j2)

`rsyslog.conf.j2` L84-94 のフィールド取得ロジック:

```jinja2
{% set source = conf.get('source') -%}
{% set port = conf.get('port', 514) -%}
{% set proto = conf.get('protocol', 'udp') -%}
{% set vrf = conf.get('vrf', 'default') -%}
```

| 定数 / 用途 | 値 | ソース行 |
|------------|-----|---------|
| デフォルト UDP ポート | **514** | `rsyslog.conf.j2` L89 |
| デフォルトプロトコル | **`udp`** | `rsyslog.conf.j2` L90 |
| デフォルト VRF | **`default`** | `rsyslog.conf.j2` L91 |

### プロトコル enum 文字列定数

`protocol` フィールドの YANG enum は `tcp` / `udp` の 2 値。Jinja2 テンプレートは値をそのまま `Protocol=` オプションに転写する（`rsyslog.conf.j2` L124）:

```jinja2
action(type="omfwd" Target="{{ server }}" Port="{{ port }}" Protocol="{{ proto }}" ...)
```

| 値 | rsyslog 効果 |
|----|------------|
| `udp` | `Protocol="udp"` — UDP 転送。パケットロスあり |
| `tcp` | `Protocol="tcp"` — TCP 転送。失敗時キュー蓄積 |

### 受信ポート定数 (rsyslog.conf.j2)

| ポート | プロトコル / モジュール | ソース行 |
|-------|----------------------|---------|
| **514** | UDP / imudp | L31 |
| **2514** | RELP / imrelp | L42 |

これらはホスト rsyslog がコンテナ syslog を受け取るためのリスニングポート。CONFIG_DB に対応フィールドなし。

### Action 固定オプション定数 (rsyslog.conf.j2 L124)

```text
action.resumeRetryCount="60" queue.type="LinkedList" queue.size="20000"
```

| オプション | 固定値 |
|-----------|--------|
| `action.resumeRetryCount` | `60` |
| `queue.type` | `LinkedList` |
| `queue.size` | `20000` |

### VRF 判定文字列定数 (rsyslog.conf.j2 L97)

```jinja2
{% set device = vrf if vrf != '' and vrf != 'default' -%}
```

文字列 `'default'` および `''`（空文字列）が「VRF バインドなし」を意味するリテラル定数。

---

## 特記事項

1. **デフォルト port 514** は YANG `default` 宣言なし — テンプレートのみのフォールバック。YANG 定義と実装の間に厳密な同期は存在しない。
2. **デフォルト protocol `udp`** も同様。YANG default なし、テンプレートのみ。
3. **デフォルト vrf `default`** も同様。YANG は union 型（leafref + enum）で default なし。
4. **受信ポート 514/2514** はユーザー設定不可。`DEVICE_METADATA` のフィールドでも変更できない。
5. **action.resumeRetryCount=60** / **queue.size=20000** は既存 `<!-- defaults -->` ブロックにも記載済み（ハードコード固定値セクション）。Phase E 中間ファイルとして再確認・証拠保持。

## evidence

- `rsyslog.conf.j2`: `sonic-buildimage/files/image_config/rsyslog/rsyslog.conf.j2` L31,42,89-92,97,124
- `rsyslog-config.sh`: `sonic-buildimage/files/image_config/rsyslog/rsyslog-config.sh`
