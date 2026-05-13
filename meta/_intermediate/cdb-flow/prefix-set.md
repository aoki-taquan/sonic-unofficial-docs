# PREFIX_SET 例外条件抽出 (cdb-batch-7)

## ソース
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-routing-policy-sets.yang`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py` (bgpcfgd - 直接の consumer なし)

## 抽出した例外条件

1. **bgpcfgd は直接購読しない**: PREFIX_SET は YANG の leafref 制約を APPL_DB を介して bgpcfgd が参照する形式ではなく、CONFIG_DB の宣言テーブルとして存在する。専用の consumer manager が sonic-swss / sonic-bgpcfgd にないため、エントリ変更はリアルタイムに FRR へプッシュされない。FRR テンプレート展開時に sonic-cfggen が CONFIG_DB を読み込む起動時適用のみ。

2. **YANG leafref 違反**: `PREFIX` list の `set_name` leafref が存在しない `PREFIX_SET.name` を指す場合、sonic-yang バリデーションエラー (`leafref`) になり CONFIG_DB へのロードが拒否される。

3. **ip_prefix の型バリデーション**: sonic-bgp-community-set / sonic-routing-policy-sets 等の union 型は `sonic-ip4-prefix` / `sonic-ip6-prefix` の入力文字列が不正なとき YANG の `pattern` 制約違反でロード拒否。

4. **PREFIX エントリの set_name 参照**: `PREFIX|<set>|<seq>` において `<set>` が `PREFIX_SET` に未定義の名前でも CONFIG_DB レベルでは保存されてしまう (sonic-yang leafref はロード時バリデーションのみ、実行時の整合性検査なし)。FRR 側では未定義の prefix-set を参照している policy は `inactive` 状態になる。
