# community-list Phase A — 暗黙デフォルト調査

調査日: 2026-05-14
対象: `SNMP_COMMUNITY` テーブル (`SNMP_COMMUNITY_LIST` in YANG)
主要ソース:
- `sonic-snmp.yang` L52-78 (container SNMP_COMMUNITY / list SNMP_COMMUNITY_LIST)
- `snmpd.conf.j2` L48-64 (TYPE分岐)
- `snmp_yml_to_configdb.py` L18-56 (ブート時注入)
- `sonic-utilities/config/main.py` L4309-4454 (CLI検証)

## フィールド別 暗黙デフォルト・挙動

### `TYPE`

| 検出種類 | 詳細 | evidence |
|---|---|---|
| YANG mandatory なし | `mandatory true` 宣言なし。省略可能（YANG レベル）。CLI は必須引数として扱う | sonic-snmp.yang L70-76 |
| 省略 → サイレントスキップ | `snmpd.conf.j2` は `== 'RO'` / `== 'RW'` の明示比較のみ。`TYPE` 欠如エントリは両分岐に一致せずコミュニティ行不生成（エラーなし） | snmpd.conf.j2 L50-54, L59-63 |
| CLI が自動大文字化 | `string_type = string_type.upper()` — CLI 経由では小文字入力 `ro`/`rw` が `RO`/`RW` に変換される | config/main.py L4378 |
| 直接 DB に小文字書き込み | `TYPE: ro` だとテンプレート比較に失敗しスキップ。YANG バリデーター通過後もサイレント非機能 | snmpd.conf.j2 L50, L59 |

### `name` (key)

| 検出種類 | 詳細 | evidence |
|---|---|---|
| YANG 制約: 4〜32 文字 | `length "4..32"` | sonic-snmp.yang L61 |
| YANG 禁止文字: SPACE / `'` / `@` / `,` / `\` | `pattern '[^ @,\\']*'` | sonic-snmp.yang L62 |
| CLI 追加制約: `@` / `:` 禁止（32文字超過も拒否） | `snmp_community_secret_check` — YANG にない `:` 禁止が CLI 独自制約 | config/main.py L4309-4324 |
| YANG と CLI の禁止文字集合乖離 | YANG: `,` `\` 禁止。CLI: `:` 禁止。ADHOC_VALIDATION 無効時は CLI チェックもスキップ | — |
| 大文字小文字感知 | key はそのまま snmpd community-string として使用 | snmpd.conf.j2 L51 |

## ブート時注入 (snmp_yml_to_configdb.py)

| 条件 | 挙動 | evidence |
|---|---|---|
| `/etc/sonic/snmp.yml` なし | `sys.exit(1)` で終了。SNMP_COMMUNITY 書き込みなし | snmp_yml_to_configdb.py L25-27 |
| `snmp_rocommunity` / `snmp_rwcommunity` 未定義 | ループスキップ。対応 community 書き込みなし | snmp_yml_to_configdb.py L33 |
| 既存 DB エントリと重複 | 冪等スキップ（上書きなし）。TYPE 変更も不可 | snmp_yml_to_configdb.py L36-49 |
| `snmp_rocommunities` → 複数 community 注入 | `for community in yaml_snmp_info[comm_type]` で複数 community を RO として書き込み | snmp_yml_to_configdb.py L35-37 |

## テンプレート前提（IPv4/IPv6 非分離）

- `TYPE: RO` → `rocommunity <name>` + `rocommunity6 <name>` 両方生成。IPv4/IPv6 を個別制御する手段なし。
- `TYPE: RW` → `rwcommunity <name>` + `rwcommunity6 <name>` 両方生成。

## 設定反映タイミング

- `docker-snmp` コンテナ起動時 / `systemctl restart snmp.service` 時のみ。
- CLI は変更後に自動で `systemctl restart snmp.service` を発行（config/main.py L4398-4402）。
- direct DB 書き込みでは自動再起動なし。手動で `systemctl restart snmp` が必要。

## YANG-実装 discrepancy

1. **YANG mandatory なし × 実装は値前提**: `TYPE` が YANG で mandatory でないため、直接 DB に書き込めるが、テンプレートは TYPE がない場合に KeyError またはサイレントスキップ。
2. **禁止文字集合の乖離**: YANG は `,` `\` を禁止、CLI は `:` を禁止。両者の制約集合が異なる。
3. **IPv4/IPv6 非分離**: YANG モデルは IPv4/IPv6 を区別する仕組みを持たないが、snmpd.conf.j2 は両方を自動生成する。
