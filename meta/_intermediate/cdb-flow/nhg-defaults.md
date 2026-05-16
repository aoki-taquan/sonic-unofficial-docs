# NEXTHOP_GROUP_TABLE Phase A — コード由来デフォルト調査メモ

調査対象: `docs/reference/config-db/nhg.md`
調査日: 2026-05-15
ソース:
- `sonic-swss/orchagent/nhgorch.cpp` (`NhgOrch::doTask`)
- `sonic-swss/orchagent/nhgorch.h` (クラス定義・コメント)
- `sonic-swss/orchagent/nhgbase.h` (NhgBase, NhgMember 基底クラス)
- `sonic-swss/orchagent/orchdaemon.cpp` (NhgOrch 生成: `APP_NEXTHOP_GROUP_TABLE_NAME`)
- `sonic-swss/fpmsyncd/routesync.cpp` (`RouteSync::installNextHopGroup`, `updateNextHopGroupDb`, `getNextHopGroupFields`)
- `sonic-swss-common/common/schema.h` (`APP_NEXTHOP_GROUP_TABLE_NAME` 定義)
- `sonic-utilities/dump/plugins/route.py` (APPL_DB 参照確認)

---

## 0. DB 帰属確認

`schema.h` に `#define APP_NEXTHOP_GROUP_TABLE_NAME "NEXTHOP_GROUP_TABLE"` と定義されており、
`APP_` プレフィックスは **APPL_DB** を意味する。`orchdaemon.cpp` の `NhgOrch(m_applDb, APP_NEXTHOP_GROUP_TABLE_NAME)` が確認。

つまり `NEXTHOP_GROUP_TABLE` は **CONFIG_DB ではなく APPL_DB のテーブル**。
書き込み元は `fpmsyncd` の `routesync.cpp` (FRR/Zebra から受信した netlink ECMP ルートを変換)。
消費者は `NhgOrch` (orchagent 内、APPL_DB を購読)。

---

## 1. フィールド列挙

`nhgorch.cpp` `doTask` の SET_COMMAND ブロック (L60-96) より:

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `nexthop` | comma-separated IP addresses | ECMP メンバーのゲートウェイ IP アドレス一覧 |
| `ifname` | comma-separated interface names | 各 nexthop に対応する出力インタフェース名一覧 |
| `weight` | comma-separated integers | ECMP メンバーごとの重み (UCMP 用、省略可) |
| `mpls_nh` | comma-separated MPLS labels or "na" | MPLS ラベルスタック (MPLS 非使用時は "na") |
| `seg_src` | comma-separated IPv6 addresses | SRv6 ソースアドレス (`srv6_nh=true` に自動設定) |
| `nexthop_group` | comma-separated NHG index names | 再帰 NHG: メンバー NHG のインデックス名一覧 |

---

## 2. コード由来デフォルト・暗黙動作

### 2-1. `weight` フィールド省略時

- `weights` は空文字列のまま (`nhgorch.cpp` L62 初期化, L79-80 の `!= ""` ガード)
- `NextHopGroupKey(nhg_str, weights)` に空文字列が渡ると、各メンバーの weight = 1 扱い (均等 ECMP)
- `fpmsyncd` 側でも `weights.empty()` の場合は `fvw.weight` を設定しない (`routesync.cpp` L3415-3418)
- **暗黙デフォルト**: weight 省略 = 全メンバー均等 (weight=1)。ハードコードのフォールバック値は weight=1 相当

### 2-2. `mpls_nh` フィールド省略時 (または "na")

- `mpls_nhv` が空の場合、または `mpls_nhv[i] == "na"` の場合はラベルスタック無しで nhg_str を構築 (`nhgorch.cpp` L230-234)
- MPLS push 動作なし。通常 IP forwarding のみ
- **暗黙デフォルト**: MPLS ラベルなし (通常 IP nexthop)

### 2-3. `seg_src` フィールドの存在 → srv6_nh フラグ自動セット

- `seg_src` フィールドが存在すると `srv6_nh = true` に自動設定 (`nhgorch.cpp` L85-89)
- SRv6 コードパスに分岐: `NextHopGroupKey(nhg_str, overlay_nh, srv6_nh)` で SRv6 NHG キーを生成
- **暗黙動作**: `seg_src` の有無が SRv6 モード判定の唯一の基準

### 2-4. `nexthop_group` フィールドがある場合 → 再帰 NHG

- `is_recursive = true` に設定、通常 nexthop/ifname フィールドと排他 (`nhgorch.cpp` L91-95)
- 両方存在する場合: `SWSS_LOG_ERROR` → `consumer.m_toSync.erase(it)` (エントリ破棄)
- **ハードコード制約**: 再帰 NHG と通常 NHG のフィールドを混在させると silent erase

### 2-5. `nexthop` / `ifname` が空文字列の場合

- `fvField(i) == "nexthop" && fvValue(i) != ""` ガードにより空文字列は無視 (`nhgorch.cpp` L73-74)
- `ipv` / `alsv` が空ベクターのまま NHG 構築が進む → SAI NHG にメンバー0件で sync
- **暗黙動作**: 空 nexthop = 有効なグループとして処理されるが SAI 側で空グループエラーが発生する場合あり

### 2-6. NHG 数上限到達時の temporary group 動作

- `gRouteOrch->getNhgCount() + NextHopGroup::getSyncedCount() >= gRouteOrch->getMaxNhgCount()` 時
- SRv6 NHG でない場合: `createTempNhg` で代替の単一 NH グループを作成 (`nhgorch.cpp` L252-264)
- SRv6 NHG: temp NHG は作成されず `++it` でスキップ (L257-260)
- エントリは `m_toSync` に残り、リソース解放後に自動再試行
- **ハードコード挙動**: temp NHG が使われている間は ECMP 動作せず、代表 1 NH のみに収束

### 2-7. 再帰 NHG のメンバー未存在時

- メンバー NHG がまだ `m_syncdNextHopGroups` に存在しない場合: `non_existent_member = true` + `continue`
- 利用可能なメンバーのみで NHG を構築 (`nhgorch.cpp` L131-153)
- **暗黙動作**: 一部メンバーが未解決でも残りで NHG を即時作成 (partial NHG)。全メンバー未存在の場合は `++it` でスキップ

### 2-8. 再帰 NHG のメンバーが recursive または temporary な場合

- `SWSS_LOG_ERROR("Invalid member nexthop group %s in parent nhg %s", ...)` → `consumer.m_toSync.erase(it)` (エントリ破棄)
- **制約**: 再帰 NHG の 2 段ネストは許可されない。一時的に temporary な NHG がメンバーになっても同様

### 2-9. SRv6 NHG で `seg_src` 数と nexthop 数の不一致

- `ipv.size() != srv6_srcv.size()` の場合: `SWSS_LOG_ERROR("inconsistent number of endpoints and srv6_srcs.")` → `consumer.m_toSync.erase(it)` (エントリ破棄)
- **制約**: SRv6 NHG では nexthop と seg_src の要素数が一致必須

### 2-10. DEL_COMMAND 時の既存 NHG への参照チェック

- `getRefCount() == 0` でないと削除不可 (RouteOrch などからの参照が残っている間はブロック)
- `success = false` → `m_toSync` に残り再試行
- **暗黙動作**: 参照されている NHG は削除できない。参照元ルートを先に削除する必要がある

---

## 3. dead field / dead consumer 検索

- `overlay_nh` フラグはコード内で `bool overlay_nh = false;` に初期化されるが、SET ブロック内でセットする箇所なし (`nhgorch.cpp` L67 のみ定義、L91-95 の `nexthop_group` ブロックで `m_syncdNextHopGroups` から取得)。APPL_DB フィールドとして明示的に `overlay_nh` キーを受け付けるパスは現実装ではない → `overlay_nh` フィールドは **dead field** (コードがセットしないため常に `false`)
- `nhgorch` は APPL_DB を購読し CONFIG_DB を購読しない (正確には APPL_DB テーブル限定)

---

## 4. 書込み元 (fpmsyncd) の動作

`routesync.cpp` `updateNextHopGroupDb` (L3400-3420):
- `nexthop`, `ifname` は常に設定
- `weights` が非空の場合のみ `weight` フィールドを設定
- MPLS/SRv6 の場合は追加フィールドを設定 (VPN SID, seg_src など)

key 形式: `NEXTHOP_GROUP_TABLE|<nh_group_id>` where `<nh_group_id>` は kernel netlink のグループ ID を文字列化したもの

---

## 5. `<!-- defaults -->` ブロック案

```markdown
<!-- defaults -->
## コード由来の暗黙デフォルト (Phase A)

> **注意**: `NEXTHOP_GROUP_TABLE` は **APPL_DB** テーブルである。`APP_NEXTHOP_GROUP_TABLE_NAME` として `schema.h` で定義され、`fpmsyncd` (`routesync.cpp`) が FRR/Zebra から受信した netlink ECMP ルートを変換して書き込む。`NhgOrch` が APPL_DB を購読して SAI next hop group を作成する。CONFIG_DB には存在しない。

| フィールド | 省略/未設定時の実装動作 | コードロケーション |
|-----------|----------------------|------------------|
| `weight` | 省略時は全メンバー均等 (weight=1 相当)。`weights` が空の場合 `NextHopGroupKey` の各メンバーに weight=1 が割り当てられる。 | `nhgorch.cpp` `doTask` L79-80; `routesync.cpp` `updateNextHopGroupDb` L3415-3418 |
| `mpls_nh` | 省略または "na" 指定時は MPLS ラベルなし。通常 IP forwarding 経路として NHG を構築。 | `nhgorch.cpp` L230-234 |
| `seg_src` | 省略時は SRv6 なし (IP NHG)。`seg_src` が存在すると `srv6_nh=true` に自動設定されて SRv6 コードパスへ分岐。 | `nhgorch.cpp` L85-89 |
| `nexthop_group` | 省略時は通常 IP/MPLS NHG。存在すると再帰 NHG モード (`is_recursive=true`)。`nexthop`/`ifname` と混在は `SWSS_LOG_ERROR` → エントリ破棄。 | `nhgorch.cpp` L91-102 |
| NHG 数上限 | `getMaxNhgCount()` 到達時、非 SRv6 NHG は代表 1 NH の temporary group を作成してルートを暫定解決。SRv6 NHG はスキップ。 | `nhgorch.cpp` L252-264 |
| 再帰 NHG の部分メンバー | メンバー NHG の一部が未解決でも利用可能分で即時作成 (partial NHG)。全未解決は skip → 再試行。 | `nhgorch.cpp` L131-163 |
| `seg_src` / nexthop 要素数不一致 | SRv6 NHG で不一致は `SWSS_LOG_ERROR` → エントリ破棄 (再試行なし)。 | `nhgorch.cpp` L209-214 |

### 書込み順依存

- 再帰 NHG のメンバー NHG が `m_syncdNextHopGroups` に存在しない場合はスキップされ、メンバー登録後に部分的に再構築される (完全な再試行ではなく partial NHG として即時適用)。
- NHG を参照するルートが存在する間は DEL_COMMAND で NHG を削除できない (参照カウントチェック)。ルートを先に削除する必要がある。

### 既知の注意点

- `overlay_nh` フラグは `nhgorch.cpp` L67 で `false` に初期化されるが、APPL_DB のフィールドとして明示的にセットするパスは実装にない。再帰 NHG のメンバーから派生する場合のみ使用される。
- `NEXTHOP_GROUP_TABLE` には YANG モデルが存在しない (APPL_DB テーブルのため)。バリデーションはすべて orchagent 側の実装ロジックに依存する。

<!-- /defaults -->
```
