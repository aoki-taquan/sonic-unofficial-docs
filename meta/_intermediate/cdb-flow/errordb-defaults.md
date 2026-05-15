# ERROR_DB フィールド暗黙デフォルト調査メモ

調査日: 2026-05-15
対象テーブル: ERROR_DB `ERROR_ROUTE_TABLE` / `ERROR_NEIGH_TABLE`

## 調査対象ファイル

- `SONiC/doc/error-handling/error_handling_design_spec.md` (HLD Rev 0.1, 2019-05-06)
- `sonic-swss-common/common/status_code_util.h` (SWSS_RC enum 定義)
- `SONiC/doc/bgp_error_handling/BGP_Route_Error_Handling_Arlo.md` (BGP ユースケース HLD)
- `sonic-swss/orchagent/lagid.h` / `lagid.cpp` (LAG_ID_ALLOCATOR_ERROR_DB_ERROR 定数 — 本 DB とは別)

---

## 調査結果: ERROR_DB の実装状況

**重要**: HLD (2019-05-06) に記載の ERROR_DB / ErrorReporter / ErrorListener クラス / CLI (`show error-database` / `sonic-clear error-database`) は **現行 master に未マージ**。  
`SWSS_RC_*` enum (`sonic-swss-common/common/status_code_util.h`) のみが採用済み。

→ フィールドのデフォルト値の根拠は HLD スキーマ定義から取る (コード実装不在のため)。

---

## テーブル別フィールド定義と暗黙デフォルト

### ERROR_ROUTE_TABLE

キー: `ERROR_ROUTE_TABLE|<prefix>`  
格納先: ERROR_DB (Redis DB, 別 ID — database_config.json には未登録、実装時に追加予定)

HLD スキーマ (Section 3.4.3.2):

```
key       = ERROR_ROUTE_TABLE|prefix
operation = opcode      ; CREATE / SET / DELETE
nexthop   = *prefix,    ; カンマ区切り IP アドレス列
intf      = ifindex,    ; カンマ区切り、0 個以上
rc        = SWSS Code   ; status code (SWSS_RC_* 文字列)
```

**フィールド別デフォルト**:

| フィールド | デフォルト | 根拠 |
|-----------|-----------|------|
| `operation` | デフォルトなし (必須) | OrchAgent が SAI opcode から翻訳して書き込む — HLD Section 3.3.1 |
| `nexthop` | `""` (空文字列可) | `*prefix,` 構文 — 0 個以上許容。HLD Section 3.4.3.2 |
| `intf` | `""` (空文字列可) | `ifindex,` 構文 — 0 個以上許容 (`zero or more`). HLD Section 3.4.3.2 |
| `rc` | デフォルトなし (必須) | SAI → SWSS_RC マッピング済みの文字列。失敗時のみエントリが存在 |

実際の書き込み例 (HLD Section 4.1):
```
"ERROR_ROUTE_TABLE:20.20.20.0/24"
1) "opcode"  2) "CREATE"
3) "nexthop" 4) "10.10.10.2"
5) "intf"    6) "Vlan10"
7) "rc"      8) "SWSS_RC_TABLE_FULL"
```
→ フィールド名は `opcode` (HLD Section 3.4.3.1) と `operation` (Section 3.4.3.2) が混在。実際の redis キーは `opcode`。

### ERROR_NEIGH_TABLE

キー: `ERROR_NEIGH_TABLE|<intf>|<prefix>`  
`<intf>` は `INTF_TABLE.name` / `VLAN_INTF_TABLE.name` / `LAG_INTF_TABLE.name` のいずれか。

HLD スキーマ (Section 3.4.3.2):

```
key       = ERROR_NEIGH_TABLE|INTF_TABLE.name / VLAN_INTF_TABLE.name / LAG_INTF_TABLE.name|prefix
operation = opcode      ; CREATE / SET / DELETE
neigh     = 12HEXDIG    ; mac address
family    = "IPv4" / "IPv6"
rc        = SWSS code   ; status code
```

**フィールド別デフォルト**:

| フィールド | デフォルト | 根拠 |
|-----------|-----------|------|
| `operation` | デフォルトなし (必須) | SAI opcode から翻訳 |
| `neigh` | デフォルトなし (必須) | MAC アドレス — ネイバー一意識別のため必須 |
| `family` | デフォルトなし (必須) | `"IPv4"` または `"IPv6"` のみ許容 — enum 制約 |
| `rc` | デフォルトなし (必須) | SWSS_RC_* 文字列 |

---

## SWSS_RC コード一覧 (status_code_util.h 実装済み)

`sonic-swss-common/common/status_code_util.h` に定義:

```
SWSS_RC_SUCCESS, SWSS_RC_INVALID_PARAM, SWSS_RC_DEADLINE_EXCEEDED,
SWSS_RC_UNAVAIL, SWSS_RC_NOT_FOUND, SWSS_RC_NO_MEMORY, SWSS_RC_EXISTS,
SWSS_RC_PERMISSION_DENIED, SWSS_RC_FULL, SWSS_RC_IN_USE, SWSS_RC_INTERNAL,
SWSS_RC_UNIMPLEMENTED, SWSS_RC_NOT_EXECUTED, SWSS_RC_FAILED_PRECONDITION,
SWSS_RC_UNKNOWN
```

HLD (2019) が定義した 8 コードから実装では 15 コードに拡張済み (`SWSS_RC_DEADLINE_EXCEEDED`, `SWSS_RC_PERMISSION_DENIED`, `SWSS_RC_INTERNAL`, `SWSS_RC_UNIMPLEMENTED`, `SWSS_RC_NOT_EXECUTED`, `SWSS_RC_FAILED_PRECONDITION`, `SWSS_RC_UNKNOWN` が追加)。

---

## エントリ ライフサイクル (暗黙動作)

| イベント | DB への影響 | デフォルト動作 |
|---------|-----------|--------------|
| CREATE 失敗 | エントリ追加 | デフォルト: failure のみ通知 (HLD 1.1.2: "By default, only failed operations are notified") |
| UPDATE 失敗 | 既存エントリ更新 (last-known error 保持) | — |
| DELETE 失敗 | エントリ除去 + 通知 | — |
| CREATE 成功後 | DB には保存しない (通知のみ) | 成功エントリは ERROR_DB に残存しない |
| clear コマンド | アプリへの通知なしで削除 | HLD Section 3.3.3 |

---

## 要約表 (Phase A)

| テーブル | フィールド | コード由来デフォルト | fallback 源 |
|---------|-----------|-------------------|------------|
| ERROR_ROUTE_TABLE | `operation` | なし (必須) | OrchAgent が SAI opcode から書き込む |
| ERROR_ROUTE_TABLE | `nexthop` | `""` (空可) | HLD `*prefix,` = 0 個以上 |
| ERROR_ROUTE_TABLE | `intf` | `""` (空可) | HLD `zero or more separated by ","` |
| ERROR_ROUTE_TABLE | `rc` | なし (必須) | SWSS_RC_* 文字列 (status_code_util.h) |
| ERROR_NEIGH_TABLE | `operation` | なし (必須) | — |
| ERROR_NEIGH_TABLE | `neigh` | なし (必須) | — |
| ERROR_NEIGH_TABLE | `family` | なし (必須) | `"IPv4"` / `"IPv6"` のみ |
| ERROR_NEIGH_TABLE | `rc` | なし (必須) | SWSS_RC_* 文字列 |

---

## 証拠リンク

- `SONiC/doc/error-handling/error_handling_design_spec.md` Section 3.4.3 — ERROR テーブル定義・スキーマ
- `SONiC/doc/error-handling/error_handling_design_spec.md` Section 4.1 — 実際の redis キー・値例
- `SONiC/doc/error-handling/error_handling_design_spec.md` Section 1.1.2 — デフォルト通知種別 (failure only)
- `SONiC/doc/error-handling/error_handling_design_spec.md` Section 3.3.3 — clear コマンド動作
- `sonic-swss-common/common/status_code_util.h` — SWSS_RC enum (実装済み 15 コード)
- `SONiC/doc/bgp_error_handling/BGP_Route_Error_Handling_Arlo.md` Section 3.4.1 — fpmsyncd の ERROR_ROUTE_TABLE 購読
