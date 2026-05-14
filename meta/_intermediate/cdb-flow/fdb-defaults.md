# FDB — Phase A コード由来の暗黙デフォルト (grep 証跡)

生成日: 2026-05-14

## 対象テーブル

CONFIG_DB `FDB` テーブル (`CFG_FDB_TABLE_NAME = "FDB"`, sonic-swss-common/common/schema.h:358)

キー形式: `FDB|<VlanName>|<MAC>` (例: `FDB|Vlan100|00:01:02:03:04:05`)

## 探索対象 field 一覧

CONFIG_DB FDB テーブルの fields: `port`, `type`

---

## field: port

**探索コマンド**:
```
grep -n "fvField.*port\|\"port\"" fdborch.cpp fdbsync.cpp pac_authmgrcfg.cpp
```

**結果**:
- `sonic-swss/orchagent/fdborch.cpp:779`: `if (fvField(i) == "port")` → `port = fvValue(i);`
  - 変数 `port` は `string port = "";` で初期化 (L769)
- `sonic-swss/fdbsyncd/fdbsync.cpp:157`: `if(fvField(i) == "port")` → `info.port_name = fvValue(i);`
- `sonic-buildimage/src/sonic-pac/paccfg/pac_authmgrcfg.cpp:180`: `if (fvField(i) == "port")` で送信先ポートを取り出す

**code fallback**: `port` フィールドが省略された場合、`port = ""` (空文字) のまま `addFdbEntry()` に渡される。空ポートの場合 `m_portsOrch->getPort(port, ...)` が失敗し FDB エントリが追加されない (事実上必須フィールド)。YANG での mandatory 宣言は確認できなかったが、実装上は必須。

**デフォルト値**: なし (省略すると FDB エントリが登録されない)

---

## field: type

**探索コマンド**:
```
grep -n "\"type\"\|type.*dynamic\|type.*static" fdborch.cpp fdbsync.cpp
```

**結果**:
- `sonic-swss/orchagent/fdborch.cpp:770`: `string type = "dynamic";` — フィールド未指定時のデフォルト初期値
- `sonic-swss/orchagent/fdborch.cpp:784-786`: `if (fvField(i) == "type") { type = fvValue(i); }`
- `sonic-swss/orchagent/fdborch.cpp:830`: `assert(type == "dynamic" || type == "dynamic_local" || type == "static");`
  - 有効値: `"dynamic"`, `"dynamic_local"`, `"static"`
- `sonic-swss/fdbsyncd/fdbsync.cpp:162-170`: `if(fvField(i) == "type") { if(fvValue(i) == "dynamic") { info.type = FDB_TYPE_DYNAMIC; } else if (fvValue(i) == "static") { info.type = FDB_TYPE_STATIC; } }`
- `sonic-buildimage/src/sonic-pac/paccfg/pac_authmgrcfg.cpp:73`: PAC モジュールは常に `"static"` を使用して書き込む

**code fallback**: `type` フィールド省略時は `"dynamic"` がデフォルト (fdborch.cpp:770 の初期化)。

**YANG default**: 確認できなかった（sonic-swss-common に YANG 定義なし）。

**デフォルト値**: `"dynamic"` (コード由来, fdborch.cpp:770)

---

## SAI 型マッピング

| type 値 | SAI 値 |
|---------|-------|
| `"static"` | `SAI_FDB_ENTRY_TYPE_STATIC` |
| `"dynamic"` | `SAI_FDB_ENTRY_TYPE_DYNAMIC` |
| `"dynamic_local"` | `SAI_FDB_ENTRY_TYPE_DYNAMIC` (MCLAG ローカル扱い) |

ソース: fdborch.cpp の `addFdbEntry()` 内での SAI 属性設定 (L1430-L1475)

---

## 0-hit フィールド (fallback なし)

CONFIG_DB FDB テーブルには `port` と `type` の 2 フィールドのみ。他に追加フィールドなし。

---

## YANG-コード 乖離サマリ

| フィールド | YANG default | コード fallback | 乖離 |
|-----------|-------------|-----------------|------|
| `port` | 不明 (YANG 定義未確認) | `""` (空) — 実質必須 | 不明 |
| `type` | 不明 (YANG 定義未確認) | `"dynamic"` (fdborch.cpp:770) | 不明 — コードは常に dynamic をデフォルトとする |

---

## 書き込み元サマリ

| 書き込み元 | テーブル | type 値 | 用途 |
|-----------|---------|---------|------|
| ユーザー / swssconfig | CONFIG_DB:FDB | `"static"` | 静的 MAC プロビジョニング |
| PAC (Port Access Control) | CONFIG_DB:FDB → STATE_OPER_FDB | `"static"` | 802.1X 認証後の静的 MAC 追加 |
| 自動学習 (kernel netlink) | APPL_DB:FDB_TABLE | `"dynamic"` | カーネル FDB 学習イベント |

CONFIG_DB FDB テーブルは主に**静的 MAC エントリ**のプロビジョニング用。動的学習エントリは APPL_DB の `FDB_TABLE` に書かれ、CONFIG_DB には書かれない。
