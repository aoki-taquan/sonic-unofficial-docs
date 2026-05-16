# MACSEC_PROFILE / MACSEC_PORT — Phase A コード由来デフォルト調査

## 調査対象テーブル

- `MACSEC_PROFILE` — MACsec セキュリティプロファイル
- `PORT.macsec` フィールド — MACSEC_PORT に相当するポート側参照

## 調査ソース

| ソース | パス | SHA/Ref |
|--------|------|---------|
| CLI プラグイン | `sonic-buildimage/dockers/docker-macsec/cli/config/plugins/macsec.py` | HEAD |
| Manager ソース | `sonic-swss/cfgmgr/macsecmgr.cpp` | HEAD |
| Manager ヘッダ | `sonic-swss/cfgmgr/macsecmgr.h` | HEAD |
| YANG モデル | `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-macsec.yang` | 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd |

## MACSEC_PROFILE フィールドのデフォルト値

### CLI (`macsec.py`) — `add_profile` コマンドのデフォルト

```python
@click.option('--priority',              default=255)
@click.option('--cipher_suite',          default="GCM-AES-128")
@click.option('--policy',                default="security")
@click.option('--enable_replay_protect', default=False)
@click.option('--replay_window',         default=0)
@click.option('--send_sci',              default=True)
@click.option('--rekey_period',          default=0)
```

注: `primary_cak` と `primary_ckn` は `required=True` — 必須フィールド、デフォルトなし。

### macsecmgr.cpp — GetValue フォールバック (行 365-387)

```cpp
if (!GetValue(ta, enable_replay_protect))
    enable_replay_protect = false;       // false がコードデフォルト
if (!GetValue(ta, replay_window))
    replay_window = 0;                   // 0 がコードデフォルト
if (!GetValue(ta, send_sci))
    send_sci = true;                     // true がコードデフォルト
if (!GetValue(ta, rekey_period))
    rekey_period = 0;                    // 0 がコードデフォルト
if (!GetValue(ta, priority))
    priority = 255;                      // 255 がコードデフォルト
if (!GetValue(ta, policy))
    policy = Policy::SECURITY;           // "security" がコードデフォルト
```

### YANG モデル — `sonic-macsec.yang` の `default` ステートメント

| フィールド | YANG `default` |
|-----------|----------------|
| `priority` | `255` |
| `cipher_suite` | `"GCM-AES-128"` |
| `policy` | `"security"` |
| `enable_replay_protect` | `"false"` |
| `send_sci` | `"true"` |
| `rekey_period` | `0` |

`replay_window` には YANG `default` なし（`when` 条件で `enable_replay_protect = true` 時のみ有効）。
`primary_cak`, `primary_ckn` は YANG `mandatory true`。
`fallback_cak`, `fallback_ckn` はオプション（`default` 宣言なし）。

## まとめ: CLI / コード / YANG 三者一致確認

| フィールド | CLI default | C++ fallback | YANG default | 整合 |
|-----------|------------|-------------|-------------|------|
| `priority` | `255` | `255` | `255` | 一致 |
| `cipher_suite` | `GCM-AES-128` | — (必須扱い) | `GCM-AES-128` | 一致 |
| `policy` | `security` | `SECURITY` | `security` | 一致 |
| `enable_replay_protect` | `false` | `false` | `false` | 一致 |
| `replay_window` | `0` | `0` | なし (when 条件) | 実質一致 |
| `send_sci` | `true` | `true` | `true` | 一致 |
| `rekey_period` | `0` | `0` | `0` | 一致 |
| `primary_cak` | mandatory | mandatory | mandatory | N/A |
| `primary_ckn` | mandatory | mandatory | mandatory | N/A |
| `fallback_cak` | optional | optional | optional | N/A |
| `fallback_ckn` | optional | optional | optional | N/A |

全フィールドでCLI・C++コード・YANGが一致。discrepancy なし。
