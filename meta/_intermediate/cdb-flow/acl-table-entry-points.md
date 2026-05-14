# ACL_TABLE — 書き込み入り口 (Direction A)

## 探索サマリー

| ソース種別 | 有無 | 概要 |
|---|---|---|
| CLI (sonic-utilities) | あり | `config acl add table` / `config acl remove table` |
| acl_loader (JSON) | なし | ACL_TABLE は acl_loader では管理しない（ACL_RULE のみ） |
| minigraph | あり | `minigraph.py` で XML→ACL_TABLE 変換 |
| REST/gNMI | あり | `sonic-mgmt-common/translib/acl_app.go` (`/openconfig-acl:acl`) |
| db_migrator | なし | ACL_TABLE の migration ステップなし |
| build-time (j2) | なし | init_cfg.json.j2 / qos_config.j2 には ACL_TABLE なし |
| hard-coded defaults | なし | |
| runtime injection | なし | orchagent は ACL_TABLE を読む側 (購読者) |

---

## CLI

**コマンド**: `config acl add table <table_name> <table_type> [-d desc] [-p ports] [-s stage]`

ソース: `sonic-utilities/config/main.py:8084-8096`

```python
config_db.set_entry("ACL_TABLE", table_name, table_info)
```

`parse_acl_table_info()` (L8041) でフィールドを構築。`stage` 未指定時デフォルト `"ingress"`。ports はカンマ区切りを list に変換。

**削除**: `config acl remove table <table_name>`

```python
config_db.set_entry("ACL_TABLE", table_name, None)
```

ソース: `sonic-utilities/config/main.py:8117-8123`

**対象 DB**: CONFIG_DB

---

## minigraph

ソース: `sonic-buildimage/src/sonic-config-engine/minigraph.py:1102-1249`

- XML `<AclInterface>` 要素を解析
- `<InAcl>` タグ → `stage: ingress`
- `<OutAcl>` タグ → `stage: egress`
- `<AttachTo>` 要素で `erspan` prefix → `type: MIRROR`、`erspanv6` → `type: MIRRORV6`、`erspan_dscp` → `type: MIRROR_DSCP`
- interface list が空 → `type: CTRLPLANE`（CTRLPLANE ACL）
- それ以外: ACL 名に `v6` を含む → `type: L3V6`、含まない → `type: L3`
- `results['ACL_TABLE'] = filter_acl_table_bindings(acls, ...)` (L2671) で CONFIG_DB に書き込み

---

## REST / gNMI

ソース: `sonic-mgmt-common/translib/acl_app.go`

- REST/gNMI path: `/openconfig-acl:acl/acl-sets/acl-set{}{}`
- `AclApp` の `processCreate()` / `processUpdate()` → `d.SetEntry(app.aclTs, ...)` で ACL_TABLE に書き込み (L300, L1512)
- `processCreate` (L154): `translateCRUCommon()` → `processCommon()` → `processCommonToplevelPath()` → ACL_TABLE へ
- OpenConfig type マッピング: `ACL_IPV4` → `L3`、`ACL_IPV6` → `L3V6`、`ACL_L2` → L2 系 (acl_app.go:1614-1618)

---

## db_migrator

なし。ACL_TABLE の migration ステップは db_migrator.py に存在しない。

---

## build-time デフォルト

なし。`init_cfg.json.j2`、`qos_config.j2` いずれにも ACL_TABLE エントリは存在しない。

---

## hard-coded デフォルト

なし。

---

## 死活 (runtime injection)

`orchagent` の `AclOrch` は ACL_TABLE を購読するのみ（読み取り側）。orchagent 自身が ACL_TABLE へ書き込むケースはない。

---

## エビデンス grep カバレッジ

| ソース | パス | hit |
|---|---|---|
| config/main.py | `set_entry("ACL_TABLE", ...)` | 2 |
| minigraph.py | `results['ACL_TABLE']` | 1 |
| acl_app.go | `SetEntry(app.aclTs, ...)` | 5 |
| db_migrator.py | ACL_TABLE | 0 |
| init_cfg.json.j2 | ACL_TABLE | 0 |
| qos_config.j2 | ACL_TABLE | 0 |
