# BGP_GLOBALS_AF_NETWORK テーブル — Phase E: ハードコード定数 詳細トレース

生成日: 2026-05-16
対象ページ: `docs/reference/config-db/bgp-globals-af-network.md`

## 目的

`frrcfgd.py` が `BGP_GLOBALS_AF_NETWORK` ハンドラで使用するハードコード定数（FRR vtysh コマンドリテラル、フォーマッタ文字列、syslog メッセージ、デーモン名マッピング）をソースコードから抽出し、evidence 行付きで一覧化する。

## 訪問ファイル

| ファイル | 内容 |
|---------|------|
| `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` | BGP_GLOBALS_AF_NETWORK ハンドラ、`af_network_key_map`、フォーマッタ、TABLE_DAEMON マッピング |

## 1. TABLE_DAEMON マッピング (`frrcfgd.py:99`)

| テーブル | デーモン | 意味 |
|---------|---------|------|
| `'BGP_GLOBALS_AF_NETWORK'` | `['bgpd']` | vtysh コマンドは `bgpd` プロセスのみに送信 |

ハードコード文字列: `'BGP_GLOBALS_AF_NETWORK'`（キー）、`'bgpd'`（値リスト要素）。

## 2. `af_network_key_map` FRR コマンドテンプレート (`frrcfgd.py:1985`)

```python
af_network_key_map = [(['ip_prefix', '++policy', '+backdoor'],
                        '{no:no-prefix}network {2} {3:network-policy} {4:network-backdoor}')]
```

### フォーマットトークン分解

| トークン | 意味 | 出力例 |
|---------|------|--------|
| `{no:no-prefix}` | 削除時 `"no "` 前置、追加時 `""` | `no network ...` / `network ...` |
| `network` | FRR vtysh コマンドキーワード（ハードコード） | `network` |
| `{2}` | `ip_prefix` の値（正規化済み prefix） | `10.1.0.0/16` |
| `{3:network-policy}` | `policy` フィールドを `network-policy` フォーマッタで変換 | `route-map MYRMAP` または空文字列 |
| `{4:network-backdoor}` | `backdoor` フィールドを `network-backdoor` フォーマッタで変換 | `backdoor` または空文字列 |

### 生成コマンド全パターン

| `policy` | `backdoor` | 生成 FRR コマンド |
|---------|---------|----------------|
| なし | なし/false | `network <prefix>` |
| `MYRMAP` | なし/false | `network <prefix> route-map MYRMAP` |
| なし | true | `network <prefix> backdoor` |
| `MYRMAP` | true | `network <prefix> route-map MYRMAP backdoor` |
| (DEL) なし | なし | `no network <prefix>` |
| (DEL) `MYRMAP` | true | `no network <prefix> route-map MYRMAP backdoor` |

## 3. `network-policy` フォーマッタ (`frrcfgd.py:922-924`)

```python
elif format == 'network-policy':
    if len(self.value) > 0:
        self.value = 'route-map %s' % self.to_str()
```

ハードコード文字列:
- `'network-policy'` — フォーマッタ識別子
- `'route-map %s'` — FRR vtysh キーワード `route-map` を prefix として付加するリテラル

空文字列（`len == 0`）の場合は変換なし → FRR コマンド出力から省略される。

## 4. `network-backdoor` フォーマッタ (`frrcfgd.py:811-814`)

```python
bool_format = {
    ...
    'network-backdoor': 'backdoor',
    ...
}
```

ハードコード文字列:
- `'network-backdoor'` — フォーマッタ識別子
- `'backdoor'` — FRR vtysh キーワード（`true` 時に出力）

`false` または欠如の場合は `''`（空文字列）→ FRR コマンド出力から省略される。

## 5. `no-prefix` フォーマッタ (`frrcfgd.py:827-828`)

```python
if format == 'no-prefix':
    return 'no ' if not self.enabled else ''
```

ハードコード文字列:
- `'no-prefix'` — フォーマッタ識別子
- `'no '` — FRR `no` コマンド前置子（削除時に `network` → `no network` へ変換）
- `''` — 追加時の空文字列（前置なし）

## 6. vtysh コマンドプレフィクス (`frrcfgd.py:3179-3181`)

```python
cmd_prefix = ['configure terminal',
              'router bgp {} vrf {}'.format(local_asn, vrf),
              'address-family {} {}'.format(af, ip_type)]
```

ハードコード文字列:
- `'configure terminal'` — FRR vtysh セッション開始コマンド
- `'router bgp {} vrf {}'` — フォーマット文字列（`local_asn`, `vrf` を展開）
- `'address-family {} {}'` — フォーマット文字列（`af`, `ip_type` を展開）

`af` は `af_type.lower().split('_')[0]`（例: `'ipv4'`, `'ipv6'`）、
`ip_type` は `af_type.lower().split('_')[1]`（例: `'unicast'`）。

## 7. syslog メッセージリテラル (`frrcfgd.py:3174-3176, 3184-3185`)

| 行 | ログレベル | メッセージ |
|----|-----------|-----------|
| 3174 | `LOG_ERR` | `'invalid IP prefix format %s for af %s'` |
| 3176 | `LOG_INFO` | `'Set address family for IP prefix {} to {} {}'` |
| 3185 | `LOG_ERR` | `'failed running BGP IP prefix AF config command'` |

これらは固定文字列リテラル。オペレーター向け調査時の検索キーワードとして機能する。

## 8. IP prefix 正規化に使用するソケット定数 (`frrcfgd.py:3172`)

```python
norm_ip_prefix = MatchPrefix.normalize_ip_prefix(
    (socket.AF_INET if af == 'ipv4' else socket.AF_INET6), ip_prefix)
```

ハードコード条件:
- `'ipv4'` — IPv4 アドレスファミリの識別文字列（`af_type.lower().split('_')[0]` の期待値）
- `socket.AF_INET` / `socket.AF_INET6` — Python `socket` モジュール定数（`2` / `10`）

## まとめ

ページ `bgp-globals-af-network.md` 本文の `<!-- constants -->` ブロックでは以下を網羅する:

1. `af_network_key_map` FRR コマンドテンプレート文字列（`network`、`no network`、`route-map %s`、`backdoor`）
2. `network-policy` フォーマッタ: `'route-map %s'` リテラル（`frrcfgd.py:924`）
3. `network-backdoor` フォーマッタ: `'backdoor'` キーワード（`frrcfgd.py:814`）
4. `no-prefix` フォーマッタ: `'no '` 前置子（`frrcfgd.py:828`）
5. vtysh コマンドプレフィクス 3 種（`'configure terminal'`, `'router bgp {} vrf {}'`, `'address-family {} {}'`）
6. TABLE_DAEMON マッピング: `'bgpd'`（`frrcfgd.py:99`）
7. syslog メッセージ 3 種（ERR×2, INFO×1）
8. IP prefix 正規化: `'ipv4'` 文字列比較と `socket.AF_INET` / `socket.AF_INET6`
