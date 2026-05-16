# community-set — Phase H プラットフォーム差異スキャンノート

## スキャン対象ソース

- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
- `sonic-buildimage/src/sonic-frr-mgmt-framework/templates/bgpd/bgpd.conf.db.comm_list.j2`
- `sonic-buildimage/rules/frr.mk`

## 抽出結果

### 1. FRR バージョン固定

- `rules/frr.mk L3`: `FRR_VERSION = 10.5.1`
- SONiC master は FRR 10.5.1 を pinning。`bgp community-list` / `bgp extcommunity-list` 構文を前提とする。
- 旧形式 `ip community-list`（FRR < 7.5）は非サポート。

### 2. COMMUNITY_SET vs EXTENDED_COMMUNITY_SET コマンド差

- `frrcfgd.py:1974`: `community_set_key_map` → `bgp community-list` を使用
- `frrcfgd.py:1975`: `extcommunity_set_key_map` → `bgp extcommunity-list` を使用
- 両テーブルとも `hdl_com_set()` を共有するが、`extended` フラグ（True/False）で動作を分岐

### 3. EXTENDED_COMMUNITY_SET メンバー変換ロジック

- `frrcfgd.py:797-810`: `CommunityList.parse_ext_community()`
  - `route-target:<val>` → `rt <val>`
  - `route-origin:<val>` → `soo <val>`
  - 上記以外 → `None`（サイレントドロップ）
- `frrcfgd.py:1002-1003`: `extended=True` かつ `set_type=standard` の場合、`{:ext-com-list}` フォーマットを適用

### 4. standard vs expanded の FRR 挙動

- COMMUNITY_SET での `set_type=standard`: FRR `bgp community-list standard` → 完全一致
- COMMUNITY_SET での `set_type=expanded`: FRR `bgp community-list expanded` → 正規表現マッチ
- EXTENDED_COMMUNITY_SET での `set_type=standard`: `rt`/`soo` プレフィックスを自動付与
- EXTENDED_COMMUNITY_SET での `set_type=expanded`: プレフィックス変換なし（正規表現をそのまま渡す）

### 5. 二重経路（起動時 vs ランタイム）

- 起動時: `bgpd.conf.db.comm_list.j2` テンプレートが初期 bgpd.conf を生成
- ランタイム: `frrcfgd` が差分を vtysh 経由で適用
- 両者は同じロジックを実装しているが独立しており、理論上一致するが保証はない

## platform ブロック適用先

`docs/reference/config-db/community-set.md` の `<!-- /handler-branching -->` 直後に `<!-- platform -->` ブロックを追加済み。
