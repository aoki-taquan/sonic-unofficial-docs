# VLAN_MEMBER — Phase A コード由来の暗黙デフォルト調査

調査日: 2026-05-14
対象ソース:
- sonic-swss/cfgmgr/vlanmgr.cpp
- sonic-swss/orchagent/portsorch.cpp
- sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vlan.yang
- sonic-utilities/config/vlan.py
- sonic-buildimage/src/sonic-config-engine/minigraph.py

## フィールド一覧と暗黙デフォルト

### `tagging_mode`

| 検出種別 | 詳細 |
|---------|------|
| **暗黙デフォルト (code fallback)** | vlanmgr.cpp:648 `string tagging_mode = "untagged"` — フィールドが CONFIG_DB に存在しない場合に両 consumer がそれぞれ独立に `"untagged"` を補完 |
| **同上 (orchagent)** | portsorch.cpp:5916 `string tagging_mode = "untagged"` — APP_DB 受信側でも同じ fallback |
| **YANG-実装乖離** | YANG は `mandatory true` (sonic-vlan.yang:314)。cvl を通過しない warm-restart / 直接注入エントリは YANG 検証なしで受理され、実装側の `"untagged"` fallback が発動する |
| **priority_tagged CLI 死路** | CLI (config/vlan.py:407) は `"untagged"` / `"tagged"` のみ書込み。`"priority_tagged"` は CLI から設定不可能 |
| **priority_tagged bridge/SAI 乖離** | vlanmgr.cpp:238: `priority_tagged` は `untagged` と同一の bridge コマンド (`pvid untagged`) を使用。orchagent portsorch.cpp:7546 は `SAI_VLAN_TAGGING_MODE_PRIORITY_TAGGED` (独立モード) を設定 — Linux ホスト転送と HW 転送で動作が異なる |
| **ハードコード注入 (members@ 経路)** | vlanmgr.cpp:573: `VLAN` エントリに `members@` フィールドがある場合 (minigraph 互換)、`processUntaggedVlanMembers()` が `tagging_mode = "untagged"` をハードコードした合成エントリを注入。ユーザー制御不可 |
| **PAC 経路ハードコード** | vlanmgr.cpp:873: `doVlanPacVlanMemberTask()` 内で `string tagging_mode = "untagged"` をハードコード。PAC 経由の VLAN_MEMBER は常に `untagged` として登録される |

## silent drop / 書込み順依存

| 検出種別 | 詳細 |
|---------|------|
| **silent drop (不正値)** | vlanmgr.cpp:658-663: `untagged`/`tagged`/`priority_tagged` 以外は `SWSS_LOG_ERROR("Wrong tagging_mode")` で silent drop。エラーはログのみ |
| **書込み順依存** | `isVlanStateOk()` と `isMemberStateOk()` が false の場合 `doVlanMemberTask` はエントリを保留 (it++)。VLAN テーブルと PORT テーブルの事前処理が前提 |
| **APP_DB フィールド欠落伝播** | vlanmgr.cpp:672: `m_appVlanMemberTableProducer.set(key, kfvFieldsValues(t))` — CONFIG_DB の raw フィールド列をそのまま転送。`tagging_mode` が CONFIG_DB にない場合、APP_DB にも書かれないが orchagent が再び `"untagged"` を補完 |

## PAC 経路での非公式フィールド注入

| フィールド | 詳細 |
|-----------|------|
| `dynamic` | vlanmgr.cpp:887: PAC 経路のみ `{"dynamic": "yes"}` を APP_DB に注入。YANG 定義なし、CONFIG_DB には書かれない隠しフィールド |

## dead consumer / dead field

| 検出種別 | 詳細 |
|---------|------|
| **priority_tagged 設定経路なし** | CLI は `priority_tagged` を書かない。minigraph.py も `tagged`/`untagged` のみ。YANG typedef では列挙されているが実際の設定経路がない — dead enum value (CLI 観点) |

## 結論

VLAN_MEMBER の field は実質 `tagging_mode` の 1 フィールドのみ。
- YANG は `mandatory true` だが実装は `"untagged"` fallback を持ち、cvl バイパス経路で乖離が顕在化する。
- `priority_tagged` はコードでは処理されるが CLI / minigraph から設定できず、かつ bridge コマンドレベルでは `untagged` と同一動作になる (SAI レベルは異なる)。
- PAC 経路は `tagging_mode` と `dynamic` を独自にハードコードし、通常の CONFIG_DB 設定経路とは独立した動作をする。
