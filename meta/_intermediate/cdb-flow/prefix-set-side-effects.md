# PREFIX_SET 副作用スキャン証跡 (Phase F)

## 調査対象ファイル

- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`

## 調査日

2026-05-18

## 要旨

PREFIX_SET / PREFIX の変更は frrcfgd 経由で FRR デーモンに即時反映される。
FRR 内で該当 prefix-list を参照している route-map は次の BGP UPDATE サイクルから
フィルタリング結果が変わるため、BGP ピアへのルート広告・受信に波及する。
PREFIX メンバの追加・削除は bgpd だけでなく zebra / ospfd / pimd にも発行される。

## 1. FRR 内部への即時波及

### 1-1. PREFIX_SET DEL → FRR prefix-list 全体削除 → route-map 無効化

`PREFIX_SET|<name>` DEL 時、frrcfgd は:

```
vtysh -c 'configure terminal' -c 'no ip prefix-list <name>'
```

を発行し FRR から prefix-list を削除する（frrcfgd.py:2976-2981）。

これにより、該当 prefix-list を `match ip address prefix-list <name>` で参照している
すべての route-map statement が即座に **条件未一致（= deny）** として動作する。
FRR は参照先不明の prefix-list を deny として評価するため、意図せず
全ルートが拒否される可能性がある。

### 1-2. PREFIX メンバ ADD/DEL → 複数 FRR デーモンへ同時発行

PREFIX テーブル (`PREFIX_LIST` / `PREFIX_NOSEQ_LIST`) の変更時、frrcfgd は
TABLE_DAEMON 定義（frrcfgd.py:87）に従い以下のデーモンすべてに vtysh コマンドを発行する:

| FRR デーモン | 役割 |
|------------|------|
| `bgpd`     | BGP ルーティングポリシーに適用 |
| `zebra`    | カーネル経路フィルタに適用 |
| `ospfd`    | OSPF redistribute フィルタに適用 |
| `pimd`     | PIM SSM レンジ（`ip pim ssm prefix-list`）に適用 |

一方 `PREFIX_SET` 自体の変更は `bgpd` のみへの通知（frrcfgd.py:83）。
PREFIX メンバ変更の方が影響範囲が広い。

## 2. BGP プロトコルへの波及

### 2-1. BGP ROUTE_REFRESH / soft-reconfiguration

frrcfgd は FRR への prefix-list 変更後に明示的な `clear ip bgp` コマンドを発行しない。
FRR bgpd は prefix-list 変更を検知すると **自動的に影響するピアへ soft-reconfiguration** を
行い、ルートフィルタリングを再評価する。これにより:

- 許可 → 拒否 に変わった経路: BGP WITHDRAW が送出される
- 拒否 → 許可 に変わった経路: BGP UPDATE が送出される

ピアへの通知は FRR 内部の非同期処理で行われるため、タイミングはミリ秒〜秒単位の遅延がある。

### 2-2. OSPF redistribute への波及

`ospfd` が `redistribute connected/static route-map <name>` で当該 prefix-list を参照している場合、
PREFIX メンバ変更後の次の OSPF SPF 再計算時に再フィルタリングが適用される。

### 2-3. PIM SSM レンジ変更

`pimd` が `ip pim ssm prefix-list <name>` で参照している場合、PREFIX メンバ変更後に
SSM グループ範囲が即座に変わる。既存の PIM ジョイン状態には影響しないが、
新規グループへの参加可否が変化する。

## 3. CONFIG_DB 内への副作用なし

PREFIX_SET / PREFIX の変更は CONFIG_DB 内の他テーブルを直接書き換えない。
APPL_DB への書き込みもない。副作用はすべて FRR vtysh コマンド経由の FRR 内部状態変更のみ。

## 4. STATE_DB / COUNTERS_DB への副作用なし

frrcfgd は PREFIX_SET / PREFIX 処理の成否を STATE_DB や COUNTERS_DB に記録しない
（Phase D 参照）。

## 証跡

- frrcfgd.py:83 (`TABLE_DAEMON PREFIX_SET`)
- frrcfgd.py:87 (`TABLE_DAEMON PREFIX`)
- frrcfgd.py:2974-2981 (PREFIX_SET DEL → no ip prefix-list)
- frrcfgd.py:2945,2960 (PREFIX ADD/DEL vtysh コマンド生成)
- frrcfgd.py:2931 (af 判定から ip/ipv6 選択)
