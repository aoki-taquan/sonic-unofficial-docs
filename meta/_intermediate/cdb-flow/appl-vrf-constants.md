# APPL_DB VRF_TABLE — ハードコード定数調査メモ (Task F Phase E)

調査日: 2026-05-15
対象ページ: `docs/reference/config-db/appl-vrf.md`
スコープ: APPL_DB `VRF_TABLE` を扱う `vrfmgrd` (cfgmgr/vrfmgr.cpp) と `VRFOrch` (orchagent/vrforch.cpp) でソース直書きされている定数・固定識別子・固定文字列。CONFIG_DB / YANG 経由で設定可能な値は除外。

## 1. Linux カーネル VRF table_id レンジ (vrfmgr.cpp)

`sonic-swss/cfgmgr/vrfmgr.cpp` 冒頭の `#define` で確定:

```cpp
// vrfmgr.cpp:12-16
#define VRF_TABLE_START      1001
#define VRF_TABLE_END        5097
#define TABLE_LOCAL_PREF     1001 // after l3mdev-table
#define MGMT_VRF_TABLE_ID    6000
#define MGMT_VRF             "mgmt"
```

- `VRF_TABLE_START=1001`〜`VRF_TABLE_END=5097` の半開区間 (`for (i = START; i < END; i++)`、vrfmgr.cpp:28) が data-plane VRF の Linux カーネル `ip route table` ID プール。**同時に存在できる data-plane VRF の上限は実質 `5097 - 1001 = 4096` 個**。
- 上限到達時 `getFreeTable()` は `0` を返し (vrfmgr.cpp:118-121)、`setLink()` がそのまま `false` を返してエントリを拒否する (vrfmgr.cpp:185-189)。CONFIG_DB / YANG 側に制約条件としては露出していない。
- `TABLE_LOCAL_PREF=1001` は VRF Linux 初期化時に `ip rule add pref 1001 table local && ip rule del pref 0` を実行する固定 priority。再起動なしで動的に変更不能。
- `MGMT_VRF_TABLE_ID=6000` は `mgmt` VRF 専用の予約 table_id。data-plane プールとは完全分離 (1001-5097 とは重複しない)。

## 2. `mgmt` 固定識別子 (vrfmgr.cpp)

`MGMT_VRF` マクロ (`"mgmt"`) は VRF 名そのものをハードコード比較に使う:

| 用途 | コード位置 | 挙動 |
|---|---|---|
| 起動時カーネル `ip link show type vrf` 結果からの mgmt VRF 削除スキップ | vrfmgr.cpp:74 (`vrfName.compare("mgmt") == 0`) | hostcfgd が作る既存 `mgmt` device は vrfmgrd 起動時に削除されない |
| `delLink()` 早期 return | vrfmgr.cpp:148 (`if (vrfName == MGMT_VRF)`) | `ip link del mgmt` は実行されない (table_id だけ recycle) |
| `setLink()` 早期 return + 予約 table_id 払い出し | vrfmgr.cpp:176-183 | `mgmt` は `ip link add` を行わず `MGMT_VRF_TABLE_ID=6000` を `m_vrfTableMap` に登録するだけ |
| `MGMT_VRF_CONFIG_TABLE` event での vrfName 上書き | vrfmgr.cpp:262 (`vrfName = MGMT_VRF;`) | CONFIG_DB `MGMT_VRF_CONFIG` のキー (`vrf_global` 等) は無視され、APPL_DB には常に `VRF_TABLE\|mgmt` として書かれる |

「`mgmt`」という文字列は CONFIG_DB / YANG 上の VRF 名制約 (`Vrf[a-zA-Z0-9_-]+`) には適合しない（`Vrf` プレフィクス必須）が、`vrfmgrd` の特別経路により APPL_DB / Linux に書き込まれる**唯一の例外名**。ユーザー側で `Vrf mgmt` のような名前を作ることはできないし、`mgmt` を再利用する別経路もない。

## 3. orchagent 側のハードコード文字列 (vrforch.cpp)

`VRFOrch::addOperation` と `delOperation` から STATE_DB へ書き込む際の固定文字列:

| 定数 | コード位置 | 値 |
|---|---|---|
| STATE フィールド名 | vrforch.cpp:120, 150 | `"state"` (literal、`hset(vrfName, "state", "ok")`) |
| STATE 成功値 | 同上 | `"ok"` (literal) |
| ignore 対象フィールド名 | vrforch.cpp:74 | `"mgmtVrfEnabled"` / `"in_band_mgmt_enabled"` (literal 比較) |
| dead field 名 | vrforch.cpp 全文 | `"fallback"` (vrforch.h:34 で受理宣言、本体で分岐なし → silent drop) |

`STATE_VRF_OBJECT_TABLE_NAME` 自体は `sonic-swss-common/common/schema.h` の `#define` 由来で「ハードコード定数」だが、これはテーブル名スキーマで既に [defaults] / [side-effects] ブロックで言及済み。本 Phase E は VRF 固有の数値・識別子に絞る。

## 4. `fallback` の YANG デフォルト

`fallback` フィールドは `sonic-vrf.yang` で `default false` が宣言されている (page 本体 [defaults] で既述) が、`VRFOrch` 側にはハードコード分岐が存在しないため、CONFIG_DB → APPL_DB pass-through 後に silent drop される。**「APPL_DB 上のハードコード定数値」としては存在しない**（vrfmgrd が CONFIG_DB の文字列をそのまま書くため動的）。

## 5. ハードコード定数を APPL_DB 経由で変更する余地

| 定数 | APPL_DB / CONFIG_DB / YANG で変更可能か | 根拠 |
|---|---|---|
| `VRF_TABLE_START=1001` | 不可 | `#define`、ビルド時固定。CLI / YANG で table_id 指定は不可。`config vrf add` は `vrfmgrd` 内で自動割り当て |
| `VRF_TABLE_END=5097` | 不可 | 同上。上限 4096 VRF も実質固定 |
| `TABLE_LOCAL_PREF=1001` | 不可 | vrfmgrd 起動時に `ip rule add pref 1001` を実行するのみ。実行後に手動で `ip rule` を書き換えれば一時的に変更可能だが、再起動で復元 |
| `MGMT_VRF_TABLE_ID=6000` | 不可 | `#define`。`mgmt` VRF を data-plane プールから分離するためのオフセット予約 |
| `MGMT_VRF="mgmt"` | 不可 | VRF 名そのものがソースに固定。renaming は不可能 |
| STATE フィールド `"state"="ok"` | 不可 | orchagent 内 literal。リーダー側 (`vrfmgrd::isVrfObjExist()`) も同じ literal を使用 |

## 6. ページに反映する `<!-- constants -->` ブロック方針

以下 3 区分で記述する:

1. **Linux カーネル VRF table_id プール** — 1001 / 5097 / TABLE_LOCAL_PREF / MGMT_VRF_TABLE_ID の数値と「同時 4096 VRF が運用上限」という派生事実。
2. **`mgmt` 固定識別子** — `MGMT_VRF` マクロが効く 4 つの分岐ポイント。
3. **STATE_DB 固定 literal** — `"state"="ok"` と `mgmtVrfEnabled` / `in_band_mgmt_enabled` ignore literal。

CONFIG_DB / YANG 側のデフォルト (`fallback default false` 等) は Phase A の [defaults] ブロックで網羅済みなので Phase E では繰り返さない。

## 7. grep 履歴

```text
$ grep -nE '1001|5097|VRF_TABLE_START|VRF_TABLE_END|table_id|MGMT_VRF|mgmt|fallback' \
    .cache/sonic-sources/sonic-swss/cfgmgr/vrfmgr.cpp | head -30
12:#define VRF_TABLE_START 1001
13:#define VRF_TABLE_END 5097
14:#define TABLE_LOCAL_PREF 1001 // after l3mdev-table
15:#define MGMT_VRF_TABLE_ID 6000
16:#define MGMT_VRF          "mgmt"
28:    for (uint32_t i = VRF_TABLE_START; i < VRF_TABLE_END; i++)
73:                    // No deletion of mgmt table from kernel
74:                    if (vrfName.compare("mgmt") == 0)
148:    if (vrfName == MGMT_VRF)
176:    if (vrfName == MGMT_VRF)
180:        uint32_t table_id = MGMT_VRF_TABLE_ID;
```

```text
$ grep -nE 'fallback|"mgmt|state.*ok|mgmtVrfEnabled' \
    .cache/sonic-sources/sonic-swss/orchagent/vrforch.cpp
74:        else if ((name == "mgmtVrfEnabled") || (name == "in_band_mgmt_enabled"))
120:        m_stateVrfObjectTable.hset(vrf_name, "state", "ok");
150:        m_stateVrfObjectTable.hset(vrf_name, "state", "ok");
```
