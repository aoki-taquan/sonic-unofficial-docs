# FG_NHG ハードコード定数 (Phase E)

調査日: 2026-05-16
対象ページ: `docs/reference/config-db/fg-nhg.md`

## ソースファイル

| ファイル | 役割 |
|---------|------|
| `sonic-swss/orchagent/fgnhgorch.cpp` | FG ECMP コア実装。bucket_size 検証・match_mode パース・SAI 属性設定 |

## 検出されたハードコード定数

### fgnhgorch.cpp モジュール定数（L12-13）

| 定数名 | 値 | 説明 |
|--------|-----|------|
| `LINK_DOWN` | `0` | `link` フィールドが設定されたメンバの初期 oper-state（DOWN 扱い）。`link` 空文字列時は `LINK_UP` 固定 |
| `LINK_UP` | `1` | `link` フィールド未設定時のデフォルト oper-state 値。リンク状態追跡なしで「常に UP」扱い |

### bucket_size 検証定数（doTaskFgNhg L1685 / L1722-1726）

| 定数 | 値 | 説明 |
|------|----|------|
| `bucket_size` 初期値 | `0` | ローカル変数初期値。未指定時はこのまま 0 で `SWSS_LOG_ERROR` → `return true`（エントリ破棄） |
| `bucket_size == 0` ガード | `0` | ゼロ値を禁止する唯一の検証。上限値チェックなし（YANG の `uint16` による 65535 が実質上限） |

### match_mode デフォルト（doTaskFgNhg L1680）

| 定数 | 値 | 説明 |
|------|----|------|
| `FGMatchMode::ROUTE_BASED` | enum 値（コード定義） | ローカル変数初期値。不正文字列は `SWSS_LOG_WARN` 後にこの値にフォールバック |

### max_next_hops デフォルト（doTaskFgNhg L1681）

| 定数 | 値 | 説明 |
|------|----|------|
| `max_next_hops` 初期値 | `0` | `match_mode==prefix-based` で参照。0 のまま投入すると `SWSS_LOG_ERROR` だが処理継続。SAI 動作不定 |

### SAI 属性 ID（createFineGrainedNhg L265-271）

| SAI 属性 | 使用値 | 説明 |
|----------|--------|------|
| `SAI_NEXT_HOP_GROUP_ATTR_TYPE` | `SAI_NEXT_HOP_GROUP_TYPE_FINE_GRAIN_ECMP` | NHG 作成時に固定設定。通常 ECMP（`ECMP`/`DYNAMIC_UNORDERED_ECMP`）とは別コードパス |
| `SAI_NEXT_HOP_GROUP_ATTR_CONFIGURED_SIZE` | `fgNhgEntry->configured_bucket_size` | CONFIG_DB の `bucket_size` をそのまま渡す。SAI が実際に確保できない場合は `REAL_SIZE` で実値を取得 |
| `SAI_NEXT_HOP_GROUP_ATTR_REAL_SIZE` | ハードウェア返却値 | VS プラットフォーム以外では SAI get で実際のバケット数を確認。VS では `configured_bucket_size` を `real_bucket_size` として使用 |

### NHG メンバ属性（sprayBankNhgMembers L1154-1165）

| SAI 属性 | 使用値 | 説明 |
|----------|--------|------|
| `SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_GROUP_ID` | NHG OID | メンバが属する NHG を指定 |
| `SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_ID` | NH OID | 実際のネクストホップ OID |
| `SAI_NEXT_HOP_GROUP_MEMBER_ATTR_INDEX` | `bucket_idx` | Fine-Grained ECMP のバケットインデックス（0 〜 real_bucket_size-1） |

### hash_bucket 配置アルゴリズム定数（calculateBankHashBucketStartIndices L146-211）

| 定数 | 値 | 説明 |
|------|----|------|
| `buckets_per_nexthop` | `real_bucket_size / num_members` | バンク内の各 NH あたりの基本バケット数（整数除算）。端数は先頭 NH に `+1` で配布 |
| `extra_buckets` | `real_bucket_size - (buckets_per_nexthop * num_members)` | 端数バケット数。先頭 `extra_buckets` 個の NH が 1 バケット多く持つ |

### prefix-based 強制シングルバンク（setFgNhg L1342）

| 定数 | 値 | 説明 |
|------|----|------|
| `bank_member_changes.resize(1, ...)` | `1` | `match_mode==PREFIX_BASED` 時にバンク数を 1 に固定。`FG_NHG_MEMBER` の `bank` フィールドは無視される |
| initial `bank` 値 (prefix-based) | `0` | L1369: `FGNextHopInfo fg_nh_info = {0, "", LINK_DOWN}` — bank=0、link=""、oper=LINK_DOWN で初期化 |

## 特記事項

- `bucket_size` の上限はコード上チェックなし。YANG `uint16` (0-65535) が唯一の制約。実装上は SAI の `REAL_SIZE` がハードウェア上限を返す
- VS（Virtual Switch）プラットフォームでは `SAI_NEXT_HOP_GROUP_ATTR_REAL_SIZE` を取得しない分岐あり（L286-288 の TODO コメント）。`configured_bucket_size` = `real_bucket_size` として扱う
- `LINK_DOWN`/`LINK_UP` はコード内整数定数（0/1）で、SAI や APPL_DB の oper-state 文字列（"up"/"down"）とは別物。`link` フィールド設定時は PORT/PORTCHANNEL の oper-state 変化イベントで更新される
