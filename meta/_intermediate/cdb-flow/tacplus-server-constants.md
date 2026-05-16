# TACPLUS_SERVER — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-net/sonic-host-services/scripts/hostcfgd` (TACACS+ モジュール定数 L86-89、グローバルデフォルト L366-370、ソートロジック L665)
- `sonic-net/sonic-utilities/config/aaa.py` (CLI `tacacs add` デフォルト L266-267、`auth_type` 選択肢 L229/L265)

---

## 1. モジュール定数 (hostcfgd L86-89)

| 定数名 | 値 | 型 | 用途 | ソース行 |
|--------|----|----|------|---------|
| `TACPLUS_SERVER_PASSKEY_DEFAULT` | `""` (空文字列) | str | `TACPLUS\|global.passkey` / `TACPLUS_SERVER.passkey` 未設定時のフォールバック。空文字列が pam_tacplus に渡され、サーバ側に共有秘密なし設定と一致しない限り認証失敗 (silent) | L87 |
| `TACPLUS_SERVER_TIMEOUT_DEFAULT` | `"5"` | str (秒) | `TACPLUS\|global.timeout` 未設定時のデフォルト応答タイムアウト。全サーバに適用される | L88 |
| `TACPLUS_SERVER_AUTH_TYPE_DEFAULT` | `"pap"` | str | `TACPLUS\|global.auth_type` 未設定時のデフォルト認証プロトコル | L89 |

---

## 2. グローバルデフォルト辞書 (hostcfgd L366-370)

```python
self.tacplus_global_default = {
    'auth_type': TACPLUS_SERVER_AUTH_TYPE_DEFAULT,  # "pap"
    'timeout': TACPLUS_SERVER_TIMEOUT_DEFAULT,       # "5"
    'passkey': TACPLUS_SERVER_PASSKEY_DEFAULT        # ""
}
```

`modify_conf_file()` の冒頭でこの辞書を `copy()` し `TACPLUS|global` 取得値で `update()` する。`TACPLUS|global` テーブル自体が存在しない場合でも上記 3 値が必ず補完される。

---

## 3. TCP ポートデフォルト (CLI / YANG)

TACACS+ の標準 TCP ポートは **49** (IANA well-known)。

| 定義箇所 | 値 | 備考 |
|---------|----|----|
| `aaa.py L266` | `default=49` | `config tacacs add` CLI オプション `--port` のデフォルト値 |
| `sonic-system-tacacs.yang` | `default 49` | YANG モデル `tcp_port` leaf のデフォルト |
| `hostcfgd` 内部 | 定数定義なし | `CONFIG_DB.TACPLUS_SERVER.tcp_port` の値をそのままテンプレートに渡す。49 のリテラルは出現しない |

`tacplus_nss.conf.j2` テンプレート:
```
server={{ server.ip }}:{{ server.tcp_port }},secret={{ server.passkey }},timeout={{ server.timeout }}
```

---

## 4. priority レンジ (CLI / YANG)

| 定義箇所 | 範囲 | デフォルト | 備考 |
|---------|------|-----------|------|
| `aaa.py L267` | `IntRange(1, 64)` | `1` | `config tacacs add --pri` の受け付けレンジ |
| `sonic-system-tacacs.yang` | `uint8 1..64` | `1` | YANG `priority` leaf |
| `hostcfgd L665` | — | — | `sorted(..., key=lambda t: int(t['priority']), reverse=True)` で降順ソート（大きいほど先に PAM 設定へ記載） |

> **注意**: `priority` が CONFIG_DB に存在しない場合、`int(t['priority'])` で `KeyError` → `TypeError` が発生し `modify_conf_file()` が中断する。CLI は常に `priority=1` を書くが、直接 DB 操作では要注意。

---

## 5. auth_type 列挙値

| 値 | 定義箇所 | 説明 |
|----|---------|------|
| `pap` | `aaa.py L229/L265`、`hostcfgd L89` | PAP (Password Authentication Protocol)。デフォルト。最広互換 |
| `chap` | `aaa.py L229/L265` | CHAP (Challenge Handshake Authentication Protocol) |
| `mschap` | `aaa.py L229/L265` | MS-CHAP (Microsoft CHAP) |
| `login` | `aaa.py L229/L265` | ASCII ログインシーケンス |

YANG モデル (`sonic-system-tacacs.yang`) でも同じ 4 値を列挙型 (`auth_type_enumeration`) として定義する。

---

## 6. グローバル → per-server 継承ロジック (hostcfgd L660-665)

```python
server = tacplus_global.copy()   # グローバル設定をベースにコピー
server['ip'] = addr
server.update(self.tacplus_servers[addr])  # per-server 設定で上書き
```

`TACPLUS|global.auth_type` / `timeout` / `passkey` が、`TACPLUS_SERVER.<ip>` で未設定のフィールドに自動継承される。per-server で明示設定した値がグローバルより優先される。

---

## 7. 特記事項

1. **TCP ポート 49 はホスト定数としては定義されていない**: `hostcfgd` 内に TACACS+ ポート定数（`TACPLUS_SERVER_TCP_PORT_DEFAULT` 等）は存在しない。CLI 書き込み時に `49` が CONFIG_DB に格納され、それをそのままテンプレートに渡す設計。
2. **`auth_type=mschap` の実装状況**: CLI/YANG では `mschap` を受け付けるが、`pam_tacplus` ライブラリ側が MS-CHAP に対応しているかはディストリビューション依存。
3. **グローバル `timeout` 範囲**: YANG は `1..60` (uint16)。CLI `tacacs timeout` は `click.IntRange(0, 60)` で `0` を許容するが、実質的に `0` は「タイムアウトなし」ではなく即タイムアウトになる可能性がある。

---

## 出典

- `sonic-net/sonic-host-services/scripts/hostcfgd` L86-89, L366-370, L648-665
- `sonic-net/sonic-utilities/config/aaa.py` L229, L263-267, L283-286
- `sonic-net/sonic-buildimage/src/sonic-yang-models/yang-models/sonic-system-tacacs.yang`
- `sonic-net/sonic-host-services/data/templates/tacplus_nss.conf.j2` L46-50
