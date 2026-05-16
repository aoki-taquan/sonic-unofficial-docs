# SNMP_COMMUNITY — Phase B 書込み順依存 証跡

生成日: 2026-05-16
対象ページ: `docs/reference/config-db/community-list.md`
調査ソース:
- `sonic-buildimage/dockers/docker-snmp/snmp_yml_to_configdb.py`
- `sonic-buildimage/dockers/docker-snmp/snmpd.conf.j2`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-snmp.yang`
- `sonic-utilities/config/main.py` L4370-4460

---

## 1. 書込み経路と順序依存の概要

`SNMP_COMMUNITY` テーブルへの書き込みは 3 経路ある:
1. CLI (`config snmp community add/del/replace`) — ADHOC_VALIDATION → YANG バリデーション → DB 書込み → snmp 再起動
2. `snmp_yml_to_configdb.py` — ブート時に `/etc/sonic/snmp.yml` から注入（冪等）
3. direct DB 書込み (`sonic-db-cli` / JSON)

`snmpd.conf.j2` テンプレートは `SNMP_COMMUNITY` を消費するが、コンテナ起動時にバッチ生成するためリアルタイム同期なし。

---

## 2. 順序依存の詳細

### 2-1. replace コマンド: 新 community SET → 旧 community DEL（逆順禁止）

`config snmp community replace <current> <new>` は次の順序で 2 回 DB 書込みを行う:
1. `set_entry('SNMP_COMMUNITY', new_community, {'TYPE': string_type})` — 新 community を先に SET
2. `set_entry('SNMP_COMMUNITY', current_community, None)` — 旧 community を後に DEL

これにより、snmpd が再起動されるまでの間は新旧両方の community が DB に存在する状態が生じる。
逆順（旧 DEL → 新 SET）にした場合、snmpd 再起動が走ると旧 community が削除済みで新 community が未登録の瞬間が発生し、
SNMP アクセスが一時的に全拒否となる可能性がある。

evidence: `sonic-utilities/config/main.py:4449-4454`

### 2-2. snmp_yml_to_configdb.py: 処理順序は fixed list 順

`full_snmp_comm_list = ['snmp_rocommunity', 'snmp_rocommunities', 'snmp_rwcommunity', 'snmp_rwcommunities']`

RO 単数 → RO 複数 → RW 単数 → RW 複数 の固定順でループする。
`snmp_rocommunities` は `snmp_rocommunity` の `startswith` に一致するが、
コード内では `startswith('snmp_rocommunities')` を先にチェックするため順序は保証される。

evidence: `snmp_yml_to_configdb.py L31-49`

### 2-3. SET 後は snmpd 再起動が必須（反映順序依存）

CONFIG_DB への SET/DEL 後、`docker-snmp` コンテナを再起動するまで `snmpd.conf` は更新されない。
CLI は SET/DEL 直後に自動で `systemctl restart snmp.service` を発行する。
direct DB 書込みの場合は手動で再起動が必要。

複数 community を連続で追加する場合: すべての SET を完了してから 1 回の snmpd 再起動を行うことで
テンプレートが最終状態を一括生成できる。CLI を使うと各 SET ごとに再起動が走るため非効率。

evidence: `config/main.py:4395-4401`

### 2-4. YANG unique 制約なし: 重複 key は上書き

`SNMP_COMMUNITY_LIST` に `unique` ステートメントなし。
同一 `name` key で SET を重複実行した場合、後発の SET がフィールドを上書きする（TYPE 変更が可能）。
SNMP_AGENT_ADDRESS_CONFIG の `unique "agent_ip port"` とは異なり、事前 DEL は不要。

evidence: `sonic-snmp.yang L52-65` (unique ステートメント不在)

---

## 3. 書込み順依存サマリ

| # | 依存関係 | 方向 | 違反時の挙動 |
|---|----------|------|------------|
| 1 | replace コマンド: 新 community SET → 旧 community DEL | **CLI 固定順** | 逆順時: snmpd 再起動タイミングで一時的に全 community 喪失リスク |
| 2 | TYPE 大文字化: CLI 経由は自動変換、direct 書込みは要注意 | **書込み前提** | `TYPE: ro`（小文字）→ テンプレート比較失敗 → snmpd 行不生成（サイレント） |
| 3 | snmpd 再起動は DB 書込み完了後に 1 回実施（一括推奨） | **反映タイミング** | 各 SET 後の即時再起動は可能だが非効率（CLI はこの動作） |
| 4 | snmp_yml_to_configdb.py は RO 単数 → RO 複数 → RW 単数 → RW 複数 の固定順 | **注入順序** | 重複 community は冪等スキップのため順序変更での上書き不可 |

---

## 4. evidence 一覧

- `sonic-buildimage/dockers/docker-snmp/snmpd.conf.j2:48-64` — SNMP_COMMUNITY テンプレートループ
- `sonic-buildimage/dockers/docker-snmp/snmp_yml_to_configdb.py:31-49` — full_snmp_comm_list 固定順ループ
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-snmp.yang:52-65` — SNMP_COMMUNITY_LIST 定義（unique なし）
- `sonic-utilities/config/main.py:4449-4454` — replace コマンド: 新 SET → 旧 DEL 順
- `sonic-utilities/config/main.py:4395-4401` — add コマンド後の snmpd 自動再起動
