# SNMP — 値依存挙動分析

## Phase 1: YANG フィールド全列挙

`SNMP|CONTACT`:
- `Contact`: string (1..255 chars、改行不可)

`SNMP|LOCATION`:
- `Location`: string (1..255 chars、改行不可)

## Phase 2: per-value 挙動

### `Contact` / `Location` フィールド挙動
| 状態 | 挙動 |
|------|------|
| 設定済み（1..255 chars） | snmpd.conf の `sysContact` / `sysLocation` 行に展開。`\n` は空白に置換。 |
| 未定義（エントリなし） | テンプレートの `is defined` チェックで該当行を出力しない。snmpd は空の sysContact/sysLocation を使用。 |
| 改行文字を含む | YANG `pattern '[^\n]+'` 制約違反でロード拒否。 |
| 256 chars 以上 | YANG `length "1..255"` 違反でロード拒否。 |

### `SNMP_COMMUNITY` テーブルとの関係
| 状態 | 挙動 |
|------|------|
| SNMP_COMMUNITY 定義済み | snmpd.conf にコミュニティ設定行を出力。 |
| SNMP_COMMUNITY 未定義 | `{% if SNMP_COMMUNITY is defined %}` チェック失敗。全 SNMP アクセスが拒否される。 |
| SNMP_COMMUNITY TYPE `RO` | 読み取り専用コミュニティ。 |
| SNMP_COMMUNITY TYPE `RW` | 読み取り/書き込みコミュニティ。 |

## Phase 3: ソース確認

- `sonic-buildimage/dockers/docker-snmp/snmpd.conf.j2:88-94`: `{% if SNMP is defined and SNMP.LOCATION is defined %}` でガードされた sysLocation 展開。`SNMP.CONTACT.keys() | first` と `values() | first` で Contact を展開。
- キーの大文字/小文字: `SNMP|LOCATION` / `SNMP|CONTACT` と YANG 定義が一致しない場合サイレントスキップ。

## enum 有無

- `Contact` / `Location`: enum なし（文字列）
- `SNMP_COMMUNITY.TYPE`: 実装上 `RO` / `RW` の 2 値（YANG enum としては別テーブル定義）
