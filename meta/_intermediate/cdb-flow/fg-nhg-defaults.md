# FG_NHG フィールド暗黙デフォルト調査メモ

調査日: 2026-05-15
対象テーブル: CONFIG_DB `FG_NHG` / `FG_NHG_PREFIX` / `FG_NHG_MEMBER`

## 調査対象ファイル

- `sonic-swss/orchagent/fgnhgorch.cpp` (`FgNhgOrch::doTaskFgNhg` / `doTaskFgNhgMember`)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-fine-grained-ecmp.yang`

---

## フィールド別 暗黙デフォルト

### `match_mode` (FG_NHG)

**コード由来デフォルト**: `route-based` (`FGMatchMode::ROUTE_BASED`)

```cpp
// fgnhgorch.cpp:1680
FGMatchMode match_mode = FGMatchMode::ROUTE_BASED;
```

ループでフィールドが見つからない場合はこのローカル変数の初期値がそのまま採用される。さらに `match_mode` キーが存在しても `nexthop-based` / `prefix-based` / `route-based` 以外の値だった場合は `SWSS_LOG_WARN` を出して `route-based` のままになる (fgnhgorch.cpp:1703-1707)。

→ YANG にも default 指定なし。値が無ければ orchagent 側で `route-based` に固定される。

---

### `bucket_size` (FG_NHG)

**コード由来デフォルト**: なし (`0` 初期化 → エラーで破棄)

```cpp
// fgnhgorch.cpp:1685
uint32_t bucket_size = 0;
...
// fgnhgorch.cpp:1722-1726
if (bucket_size == 0)
{
    SWSS_LOG_ERROR("Received bucket_size which is 0 for key %s", ...);
    return true;          // 再試行なし、エントリ破棄
}
```

DB に `bucket_size` フィールドが無い／`0` の場合、`SWSS_LOG_ERROR` を出してエントリは登録されずに破棄される。`return true` のため Consumer キューにも残らず再試行されない。

→ 実質的に **必須フィールド**。デフォルトは無く、未指定はエラー。

---

### `max_next_hops` (FG_NHG)

**コード由来デフォルト**: `0`

```cpp
// fgnhgorch.cpp:1681
uint32_t max_next_hops = 0;
```

- `match_mode != prefix-based` の場合: `0` のまま使われ、`prefix-based` 以外のモードでは未参照（無視）。
- `match_mode == prefix-based` かつ `0`: `SWSS_LOG_ERROR` (fgnhgorch.cpp:1717-1720)。`return` せず処理は継続するが、後段の SAI 動作が不定になる。

---

### `bank` (FG_NHG_MEMBER)

**コード由来デフォルト**: `0` (uint32_t 初期化)

```cpp
// fgnhgorch.cpp:1981
uint32_t bank = 0;
...
// fgnhgorch.cpp:2025-2026
FGNextHopInfo fg_nh_info = {};
fg_nh_info.bank = bank;
```

DB に `bank` フィールドが無い場合、ローカル変数初期値 `0` がそのまま `FGNextHopInfo.bank` に格納される。

→ `bank` 未指定のメンバは **全て bank 0** に集約される。

---

### `link` (FG_NHG_MEMBER)

**コード由来デフォルト**: `""` (空文字列) → link 追跡なし

```cpp
// fgnhgorch.cpp:1982
string link = "";
...
// fgnhgorch.cpp:2028
if (!link.empty())
{
    // PORT/PORTCHANNEL の oper-state を見て LINK_UP/LINK_DOWN を判定
}
```

`link` が空文字列の場合は port-down 連動が働かず、`link_oper_state` は初期値 `LINK_UP` (fgnhgorch.cpp:1976) のまま固定される。

---

### `FG_NHG` (FG_NHG_MEMBER フィールド)

**コード由来デフォルト**: なし (空文字列で必須チェック)

```cpp
// fgnhgorch.cpp:1980, 1998-2002
string fg_nhg_name = "";
...
if (fg_nhg_name.empty())
{
    SWSS_LOG_ERROR("Received FG_NHG with empty name for key %s", ...);
    return true;
}
```

`FG_NHG` フィールドが無いメンバはエラーで破棄。

---

## 要約表

| テーブル | フィールド | YANG default | コード実効デフォルト | 出典 |
|---------|-----------|--------------|----------------------|------|
| `FG_NHG` | `bucket_size` | なし | **なし**（0 で `SWSS_LOG_ERROR` → 破棄、再試行なし） | fgnhgorch.cpp:1685, 1722-1726 |
| `FG_NHG` | `match_mode` | なし | `route-based` (ローカル変数初期値、不正値もここにフォールバック) | fgnhgorch.cpp:1680, 1703-1707 |
| `FG_NHG` | `max_next_hops` | なし | `0` (prefix-based 時は `SWSS_LOG_ERROR`、他モードでは無視) | fgnhgorch.cpp:1681, 1717-1720 |
| `FG_NHG_MEMBER` | `bank` | なし | `0` (uint32_t 初期化値) | fgnhgorch.cpp:1981 |
| `FG_NHG_MEMBER` | `link` | なし | `""` 空文字列 → port-down 連動なし、`link_oper_state=LINK_UP` 固定 | fgnhgorch.cpp:1976, 1982, 2028 |
| `FG_NHG_MEMBER` | `FG_NHG` | なし | **なし**（空で `SWSS_LOG_ERROR` → 破棄） | fgnhgorch.cpp:1980, 1998-2002 |
| `FG_NHG_PREFIX` | `FG_NHG` | なし | **なし**（leafref 必須） | YANG `mandatory true` |

---

## 注意点

- `bucket_size==0` / `FG_NHG_MEMBER.FG_NHG==""` は `return true` のため Consumer キューに残らない（再試行なし）。設定ミスは即座に検知が必要。
- `match_mode` の不正値は `WARN` で `route-based` にフォールバックするため、タイポは静かに `route-based` 動作になる点に注意。
- `bank` 未指定はエラーにならず全メンバが bank 0 に集約され、Fine-Grained ECMP のバンク再分配メカニズムが事実上無効化される。
