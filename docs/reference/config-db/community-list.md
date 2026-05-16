---
title: SNMP_COMMUNITY テーブル
description: "SNMP_COMMUNITY テーブル — SNMPv1/v2c コミュニティ文字列を CONFIG_DB に登録するテーブル。sonic-snmp.yang の SNMP_COMMUNITY_LIST で定義され、docker-snmp の snmpd.conf.j2 テンプレートが消費する。"
area: reference
verification: code-verified
last_verified: 2026-05-14
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-snmp.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: dockers/docker-snmp/snmpd.conf.j2
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: dockers/docker-snmp/snmp_yml_to_configdb.py
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - SNMP_COMMUNITY
    - SNMP
    - SNMP_AGENT_ADDRESS_CONFIG
    - SNMP_USER
  cli:
    - config snmp community
  yang:
    - sonic-snmp
hard: 0
---

# SNMP_COMMUNITY テーブル

## 概要

[SNMPv1](../../reference/glossary.md#term-snmp)/v2c コミュニティ文字列を [CONFIG_DB](../../reference/glossary.md#term-config_db) に登録するテーブル[^1]。`sonic-snmp.yang` の `SNMP_COMMUNITY_LIST` で定義される。`docker-snmp` コンテナ起動時に `snmpd.conf.j2` テンプレートが本テーブルを読み取り、`rocommunity` / `rwcommunity` / `rocommunity6` / `rwcommunity6` ディレクティブを `snmpd.conf` に生成する。`snmp_yml_to_configdb.py` がブート時に `/etc/sonic/snmp.yml` からもエントリを注入する。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>SNMP_COMMUNITY")]
  DM["snmp-config / snmpd.conf.j2"]
  CDB --> DM
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
SNMP_COMMUNITY|<community_name>
```

`name` が key。YANG 制約: 長さ 4〜32 文字、SPACE / シングルクォート / `@` / `,` / `\` を含む文字列は禁止。

## フィールド

| フィールド | 型 | 説明 |
|-----------|----|------|
| `TYPE` | enum `RO` / `RW` | コミュニティアクセス種別。`RO` = 読み取り専用、`RW` = 読み取り/書き込み |

`name` は key としてのみ存在し、ハッシュフィールドには現れない。

## 制約

- `name` の長さ: 4〜32 文字 (`length "4..32"`)
- 禁止文字: SPACE / `'` (single quote) / `@` / `,` / `\`（YANG `pattern` 制約）
- CLI 側追加検証: `@` と `:` を含む community 名を拒否（`snmp_community_secret_check` 関数）
- `TYPE` は YANG で `mandatory` 宣言なし — CLI 経由では常に指定が必要だが、直接 DB 書き込みでは省略可能

## 購読者

- `docker-snmp` の `snmpd.conf.j2` テンプレート: `SNMP_COMMUNITY` → `rocommunity`/`rwcommunity`/`rocommunity6`/`rwcommunity6` ディレクティブ生成
- `snmp_yml_to_configdb.py`: ブート時に `/etc/sonic/snmp.yml` から注入

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): [`SNMP`](snmp.md)、[`SNMP_AGENT_ADDRESS_CONFIG`](snmp-agent-address-config.md)、`SNMP_USER`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-snmp`
- 関連 CLI: `config snmp community { add | del | replace }`

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-snmp`](../yang/sonic-snmp.md)
- CLI: [`config snmp`](../cli/config-snmp.md)
- 関連ページ: [`SNMP`](snmp.md)、[`SNMP_AGENT_ADDRESS_CONFIG`](snmp-agent-address-config.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: [YANG](../../reference/glossary.md#term-yang) 定義: `sonic-snmp.yang` container `SNMP_COMMUNITY` / list `SNMP_COMMUNITY_LIST`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-snmp.yang>

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `SNMP_COMMUNITY|<name>`。
- `TYPE: RO` で読み取り専用コミュニティ。`TYPE: RW` で読み書き可能コミュニティ。

### よくある誤設定

- `public` / `private` をデフォルトのまま使用すると外部から SNMP アクセスが可能。本番では必ず変更する。
- community 名が 4 文字未満だと YANG バリデーションエラー。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'SNMP_COMMUNITY|*'
show snmp community
```
<!-- /ops-hint -->

<!-- value-behavior -->
## 値依存挙動マトリクス

| フィールド | 値 | 挙動 |
|-----------|-----|------|
| `TYPE` | `RO` | `snmpd.conf` に `rocommunity <name>` / `rocommunity6 <name>` が生成される。読み取り専用アクセスのみ許可。 |
| `TYPE` | `RW` | `snmpd.conf` に `rwcommunity <name>` / `rwcommunity6 <name>` が生成される。読み取り・書き込みアクセスを許可。 |
| `TYPE` | 未設定（省略） | テンプレートは `TYPE` の存在を前提にチェックするため、`TYPE` がない場合は `if SNMP_COMMUNITY[community]['TYPE'] == 'RO'` / `== 'RW'` のどちらにも一致せず、コミュニティ行が生成されない（サイレントスキップ）。 |
| テーブル全体 | エントリなし | テンプレートの `{% if SNMP_COMMUNITY is defined %}` が偽となり、コミュニティ行を一切出力しない。結果として全 SNMP v1/v2c アクセスが拒否される。 |

<!-- /value-behavior -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

- **SNMP_COMMUNITY 未定義時 → 全 v1/v2c アクセス拒否**: テーブルにエントリが 0 件の場合、`snmpd.conf.j2` の `{% if SNMP_COMMUNITY is defined %}` チェックが偽となり、コミュニティ設定行を出力しない。snmpd は community なしで起動し、全 SNMPv1/v2c アクセスを拒否する。<!-- evidence: snmpd.conf.j2 L48-55, L57-64 -->
- **TYPE 省略時のサイレントスキップ**: `TYPE` フィールドが欠如しているエントリは、`RO` / `RW` どちらにも一致しないため、snmpd.conf 行が生成されない。エラーログは出力されない。<!-- evidence: snmpd.conf.j2 L50-52, L59-61 -->
- **設定変更の反映は snmpd 再起動時のみ**: CONFIG_DB への書き込み後、`docker-snmp` コンテナ再起動 or `systemctl restart snmp.service` まで snmpd.conf への反映は行われない。CLI (`config snmp community add`) は変更後に自動で `systemctl restart snmp.service` を発行する。<!-- evidence: sonic-utilities/config/main.py L4398-4402 -->
- **snmp_yml_to_configdb.py の冪等性**: `snmp_yml_to_configdb.py` はブート時に `/etc/sonic/snmp.yml` から `SNMP_COMMUNITY` を注入するが、既存エントリ (`snmp_config_db_communities`) と重複する community は書き込まずスキップする。<!-- evidence: snmp_yml_to_configdb.py L36, L40, L44, L48 -->
- **IPv4 / IPv6 両方自動バインド**: `TYPE: RO` の場合 `rocommunity` と `rocommunity6` の両行が生成される。IPv4 と IPv6 を個別に制御する手段は本テーブルにはない。<!-- evidence: snmpd.conf.j2 L51-52 -->

<!-- cdb-defaults -->

<!-- defaults -->
## 暗黙デフォルト・コード由来挙動 (Phase A)

### `TYPE` フィールド — YANG mandatory なし、実装は値存在前提

- **YANG `mandatory` 宣言なし**: `sonic-snmp.yang` の `SNMP_COMMUNITY_LIST.TYPE` leaf は `mandatory true` を持たない。CLI では引数 `<RO|RW>` を必須として扱うが、direct DB 書き込み（`sonic-db-cli` や JSON 投入）では `TYPE` を省略したエントリを書き込める。<!-- evidence: sonic-snmp.yang L70-76 -->
- **`TYPE` 省略 → サイレントスキップ（コミュニティ行不生成）**: `snmpd.conf.j2` テンプレートは `== 'RO'` / `== 'RW'` の明示比較のみ行い、`TYPE` フィールドの存在チェックを行わない。`TYPE` がない場合は KeyError または比較不成立でコミュニティ行を生成しない。SNMP access は実質的に機能しなくなる（エラーログなし）。<!-- evidence: snmpd.conf.j2 L50-54, L59-63 -->
- **CLI は `TYPE` を自動大文字化**: `config snmp community add` は `string_type = string_type.upper()` で入力を大文字化してから `set_entry` を呼ぶ。直接 DB に `TYPE: ro`（小文字）を書き込んだ場合、テンプレートの `== 'RO'` 比較に不一致となりスキップされる。<!-- evidence: sonic-utilities/config/main.py L4378 -->

### `name` (key) — YANG 制約と CLI 制約の乖離

- **YANG 制約**: 長さ 4〜32 文字、禁止パターン `[^ @,\\']*`（SPACE / `'` / `@` / `,` / `\` を禁止）。YANG バリデーターが有効な場合のみ適用される。<!-- evidence: sonic-snmp.yang L61-65 -->
- **CLI 追加検証（ADHOC_VALIDATION 有効時のみ）**: `snmp_community_secret_check` は `@` と `:` を禁止する（32 文字超過も拒否）。YANG は `:` を明示禁止しておらず、CLI のみの制約。<!-- evidence: sonic-utilities/config/main.py L4309-4324 -->
- **YANG と CLI の禁止文字集合が異なる**: YANG では `,` と `\` を禁止しているが CLI は禁止しない。CLI では `:` を禁止しているが YANG は禁止しない。direct DB 書き込みでは YANG バリデーションのみが適用される。<!-- evidence: sonic-snmp.yang L62; sonic-utilities/config/main.py L4310 -->
- **大文字小文字感知**: community 名はそのまま FRR/snmpd の community-string として使用される。key の大文字/小文字は区別される。<!-- evidence: snmpd.conf.j2 L51 -->

### ブート時注入（snmp_yml_to_configdb.py）のデフォルト挙動

- **snmp.yml が存在しない場合**: `sys.exit(1)` で終了。`SNMP_COMMUNITY` への書き込みは発生しない。テーブルは空のまま。<!-- evidence: snmp_yml_to_configdb.py L25-27 -->
- **snmp_rocommunity / snmp_rwcommunity が snmp.yml に未定義の場合**: ループ条件 `if comm_type in yaml_snmp_info.keys()` で分岐するため、未定義キーはスキップされ対応 community は書き込まれない。<!-- evidence: snmp_yml_to_configdb.py L33 -->
- **既存 DB エントリとの重複時**: `if community not in snmp_config_db_communities` チェックにより、すでに DB に存在する community は上書きしない（冪等性）。`TYPE` の変更も行われない。<!-- evidence: snmp_yml_to_configdb.py L36, L40, L44, L48 -->
- **`snmp_rocommunities`（複数形）と `snmp_rocommunity`（単数形）の評価順**: `full_snmp_comm_list = ['snmp_rocommunity', 'snmp_rocommunities', 'snmp_rwcommunity', 'snmp_rwcommunities']` の順でループするが、コードは `startswith` で分岐するため `snmp_rocommunities` は `snmp_rocommunity` の `startswith` にも一致する。実際には `startswith('snmp_rocommunities')` 条件を先にチェックするため問題なし。<!-- evidence: snmp_yml_to_configdb.py L34-49 -->

### テンプレート生成の前提（IPv4/IPv6 非分離）

- **IPv4 と IPv6 は分離不可**: `TYPE: RO` 時は `rocommunity` と `rocommunity6` が同一コミュニティ名で生成される。IPv4 のみ / IPv6 のみに限定する仕組みは本テーブルにない。ネットワーク分離が必要な場合は snmpd.conf を直接編集する必要があるが、それは CONFIG_DB 管理外となる。<!-- evidence: snmpd.conf.j2 L51-52 -->
<!-- /defaults -->

<!-- ordering -->
## 書込み順依存 (Phase B)

### 1. replace コマンド: 新 community SET → 旧 community DEL（逆順禁止）

`config snmp community replace <current> <new>` は新 community を先に SET してから旧 community を DEL する順序で動作する（`config/main.py:4449-4454`）。

逆順（旧 DEL → 新 SET）にした場合、DEL 直後に snmpd 再起動が走ると新 community がまだ DB に存在しない瞬間が生じ、全 SNMPv1/v2c アクセスが一時的に拒否される。CLI は新旧両方が DB に存在する時間帯を作ることでこのリスクを回避している。

### 2. TYPE は大文字で書き込む（direct DB 書込み時）

`snmpd.conf.j2` は `SNMP_COMMUNITY[community]['TYPE'] == 'RO'` / `== 'RW'` と大文字で比較する（`snmpd.conf.j2:50,59`）。CLI は `string_type.upper()` で自動大文字化するが（`config/main.py:4376`）、`sonic-db-cli` などで直接書き込む場合は `TYPE: ro`（小文字）では比較に失敗し、snmpd.conf の community 行が生成されない（サイレントスキップ）。

### 3. 複数 community を一括 SET してから snmpd を 1 回再起動

CONFIG_DB への SET/DEL は即時反映されず、`docker-snmp` コンテナ再起動（`systemctl restart snmp.service`）後にテンプレートが再生成される。CLI を使うと SET ごとに自動再起動が走るため非効率。direct DB 書込みで複数 community を一括投入する場合はすべての SET を完了してから 1 回の再起動を行うことで snmpd.conf が最終状態を一括生成できる（`config/main.py:4395-4401`）。

### 4. snmp_yml_to_configdb.py の注入順序（RO 単数 → RO 複数 → RW 単数 → RW 複数）

ブート時注入スクリプトは `full_snmp_comm_list = ['snmp_rocommunity', 'snmp_rocommunities', 'snmp_rwcommunity', 'snmp_rwcommunities']` の固定順でループする（`snmp_yml_to_configdb.py:31`）。既存 DB エントリと重複する community は冪等スキップするため、注入順序を変えても上書きは発生しない。

### 5. YANG unique 制約なし: 同一 name への重複 SET は上書き

`SNMP_COMMUNITY_LIST` に `unique` ステートメントなし（`sonic-snmp.yang:52-65`）。同一 `name` key で TYPE を変更したい場合は DEL 不要で上書き SET が可能。`SNMP_AGENT_ADDRESS_CONFIG` の `unique "agent_ip port"` とは異なる。

| # | 依存関係 | 方向 | 違反時の挙動 |
|---|----------|------|------------|
| 1 | replace: 新 community SET → 旧 community DEL | **CLI 固定順** | 逆順時: snmpd 再起動タイミングで全 v1/v2c アクセス一時拒否リスク |
| 2 | TYPE 書込み: 大文字必須（RO / RW） | **書込み前提** | 小文字（ro/rw）→ テンプレート比較失敗 → snmpd 行不生成（サイレント） |
| 3 | 一括 SET 後に snmpd を 1 回再起動 | **推奨順序** | SET ごとの再起動でも機能するが非効率 |
| 4 | snmp_yml_to_configdb.py 注入順序は固定（RO 単→複, RW 単→複） | **実装固定** | 重複 community は冪等スキップ（順序変更で上書き不可） |
<!-- /ordering -->

<!-- runtime-trace -->
## CDB → 実コンテナ動作トレース

### 段階 1: Consumer 登録

- **docker-snmp / snmpd.conf.j2**: コンテナ起動時にテンプレートエンジンが `SNMP_COMMUNITY` テーブル全体を読み取る（イベントドリブンではなくバッチ生成）。

### 段階 2: CFG → APPL 翻訳

- `snmpd.conf.j2` が `SNMP_COMMUNITY` エントリを `rocommunity` / `rwcommunity` / `rocommunity6` / `rwcommunity6` に変換し `/etc/snmp/snmpd.conf` を生成する。
- APP_DB への書き込みなし。

### 段階 3: APPL → SAI

- SAI 経由なし。snmpd が MIB ツリーを通じてスイッチ統計を提供。

### 段階 4: タイミングと副作用

- **適用タイミング**: `docker-snmp` コンテナ再起動 / `systemctl restart snmp.service` 時のみ。実行中の snmpd プロセスはホットリロード不可。
- **副作用**: community 変更中は古い community での SNMP アクセスが継続される（snmpd 再起動まで）。再起動後は旧 community が無効化される。NMS 側の設定変更も必要。

<!-- /runtime-trace -->

<!-- entry-points -->
## 書き込み入り口 (Direction A)

SNMP_COMMUNITY テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

- `config snmp community add <name> <RO|RW>` — `config/main.py` が `set_entry('SNMP_COMMUNITY', community, {'TYPE': string_type})` を呼ぶ (`sonic-utilities/config/main.py:4391`)
- `config snmp community del <name>` — `set_entry('SNMP_COMMUNITY', community, None)` (`sonic-utilities/config/main.py:4419`)
- `config snmp community replace <current> <new>` — 旧 community 削除 + 新 community 追加 (`sonic-utilities/config/main.py:4452-4454`)

### minigraph / sonic-cfggen

`minigraph.py` に `SNMP_COMMUNITY` 生成なし

### REST / gNMI

REST/gNMI 書き込み経路なし（OpenConfig SNMP モデルは本テーブルをサポートしていない）

### db_migrator

`db_migrator.py` での `SNMP_COMMUNITY` マイグレーションなし

### ビルド時デフォルト (init_cfg / j2 テンプレート)

なし（`init_cfg.json` に `SNMP_COMMUNITY` エントリなし）

### ランタイム注入（デーモン自動書き込み）

- `snmp_yml_to_configdb.py`: ブート時に `/etc/sonic/snmp.yml` から `snmp_rocommunity` / `snmp_rocommunities` / `snmp_rwcommunity` / `snmp_rwcommunities` を読み取り `SNMP_COMMUNITY` に注入（`sonic-buildimage/dockers/docker-snmp/snmp_yml_to_configdb.py`）
<!-- /entry-points -->

<!-- derivation -->
## 派生・条件付き登録 (Phase 6/7)

### Phase 6: 値による他フィールド自動派生

| 条件 | 派生先 | evidence |
|---|---|---|
| 派生なし（SNMP_COMMUNITY は CLI / snmp_yml_to_configdb.py でのみ書き込まれる） | — | テンプレートは読み取り専用消費 |

### Phase 7: 条件付き module/manager 登録

| 条件 | 登録 module | evidence |
|---|---|---|
| `docker-snmp` コンテナ稼働時 | `snmpd.conf.j2` が SNMP_COMMUNITY を消費してコミュニティ行を生成 | `snmpd.conf.j2 L48-64` |
| `snmp.yml` が存在する場合 | `snmp_yml_to_configdb.py` がブート時に SNMP_COMMUNITY へ注入 | `snmp_yml_to_configdb.py L25-49` |

<!-- /derivation -->

<!-- handler-branching -->
### Phase 8: Handler メソッド内分岐

| Handler | 分岐条件 | 効果 | evidence |
|---|---|---|---|
| `snmpd.conf.j2` | `SNMP_COMMUNITY is defined` | コミュニティループを実行 | `snmpd.conf.j2 L48, L57` |
| `snmpd.conf.j2` | `SNMP_COMMUNITY[community]['TYPE'] == 'RO'` | `rocommunity` / `rocommunity6` 行を生成 | `snmpd.conf.j2 L50-52` |
| `snmpd.conf.j2` | `SNMP_COMMUNITY[community]['TYPE'] == 'RW'` | `rwcommunity` / `rwcommunity6` 行を生成 | `snmpd.conf.j2 L59-61` |
| `snmp_yml_to_configdb.py` | `community not in snmp_config_db_communities` | 新規 community のみ書き込み（冪等） | `snmp_yml_to_configdb.py L36-49` |

<!-- /handler-branching -->

<!-- glossary-links-injected: placeholder -->
