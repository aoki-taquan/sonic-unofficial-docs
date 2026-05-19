# NEXTHOP_GROUP_TABLE (APPL_DB) — Platform Phase H 調査メモ

## 調査対象ソース

- `sonic-swss/orchagent/routeorch.cpp` (L37-124): RouteOrch コンストラクタ。ECMP グループ上限算出とプラットフォーム補正
- `sonic-swss/orchagent/nhgorch.cpp` (L245-283): NhgOrch::doTask() — NHG 上限到達時の temp NHG 作成ロジック
- `sonic-swss/orchagent/orch.h` (L42): `MLNX_PLATFORM_SUBSTRING "mellanox"` 定数定義

## プラットフォーム差の主軸

### 1. Mellanox — ECMP グループ数補正 (routeorch.cpp:83-87)

`SAI_SWITCH_ATTR_NUMBER_OF_ECMP_GROUPS` は Mellanox の場合、ECMP グループサイズ=1 前提の最大値を返す。
実際の ECMP グループ数上限は `DEFAULT_MAX_ECMP_GROUP_SIZE = 32` で除算して算出:

```cpp
char *platform = getenv("platform");
if (platform && strstr(platform, MLNX_PLATFORM_SUBSTRING))
{
    m_maxNextHopGroupCount /= DEFAULT_MAX_ECMP_GROUP_SIZE;
}
```

算出値は STATE_DB `SWITCH_CAPABILITY|switch:MAX_NEXTHOP_GROUP_COUNT` に書き込まれ (routeorch.cpp:90)、
NhgOrch::doTask() が NHG 上限判定に使用する (nhgorch.cpp:252)。

### 2. VOQ スイッチ — MAX_ECMP_MEMBER_COUNT を 128 に上書き (routeorch.cpp:95-124)

`gMySwitchType == "voq"` かつ SAI 取得値が 128 以上の場合、
`SAI_SWITCH_ATTR_ECMP_MEMBER_COUNT` を 128 に強制設定する。
これは VOQ アーキテクチャでの ECMP メンバー数制約を満たすためのプラットフォーム固有処理。

### 3. SRv6 NHG — 上限到達時に temp NHG をスキップ (nhgorch.cpp:256-261)

通常の ECMP NHG は上限到達時に 1 メンバーの temp NHG を作成してフォールバックするが、
SRv6 NHG (`nhg_key.is_srv6_nexthop()` が真) は temp NHG を作成せず、そのままスキップ (`continue`) する:

```cpp
// don't create temp nhg for srv6
if (nhg_key.is_srv6_nexthop())
{
    ++it;
    continue;
}
```

SRv6 NHG はリソース回復まで未登録のまま待機し続ける。SRv6 サポート自体も ASIC ベンダー実装依存。

### 4. VS プラットフォーム

Virtual Switch (VS) では SAI シムが ECMP create/member create を SUCCESS で返すが実 ASIC 転送はない。
CRM 統計はダミー値。テスト・CI 用途のみ。

### 5. Broadcom / Marvell / その他

SAI 戻り値をそのまま使用する (補正なし)。ECMP グループ数は SAI 問い合わせ値のまま上限として使用。

## NEXTHOP_GROUP_TABLE フィールドとプラットフォーム差

NEXTHOP_GROUP_TABLE 自体のフィールド構造はプラットフォーム共通。ただし:

| フィールド | プラットフォーム差 |
|-----------|----------------|
| `weight` | SAI UCMP サポートが必要。UCMP 非対応 ASIC では weight が無視される可能性がある |
| `seg_src` | SRv6 ASIC サポートが必要。非対応 ASIC では NHG 作成が失敗する |
| `mpls_nh` | MPLS ASIC サポートが必要。非対応 ASIC では NHG 作成が失敗する |
| `nexthop`/`ifname` | 全プラットフォームで共通 |

## 結論

NEXTHOP_GROUP_TABLE 自体のスキーマはプラットフォーム非依存だが、
NhgOrch が行う SAI next hop group 作成は以下の 3 点でプラットフォーム差が発生する:
1. ECMP グループ数上限 (Mellanox のみ補正)
2. VOQ での ECMP メンバー数上限固定
3. SRv6 NHG の temp NHG 作成不可
