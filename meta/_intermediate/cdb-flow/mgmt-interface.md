# CONFIG_DB 例外条件分析: MGMT_INTERFACE

## Consumer

- `sonic-utilities` / `config` (`config/main.py`): CLI レイヤで `MGMT_INTERFACE` を読み書き。
- カーネルルーティング: `interfaces.j2` テンプレートが netplan/ifupdown 設定を生成し、eth0 に IP を付与する。

## 例外条件

### 1. ip_prefix と gwaddr のアドレスファミリ不一致 → YANG must 制約違反
- ソース: `sonic-mgmt_interface.yang` — `must "(contains(current(), ':') and contains(../gwaddr, ':')) or (contains(current(), '.') and contains(../gwaddr, '.'))"`。
- IPv4 prefix に IPv6 ゲートウェイを設定する（またはその逆）と YANG バリデーションで拒否。

### 2. forced_mgmt_routes によるルーティングテーブル分岐
- ソース: `sonic-mgmt_interface.yang` / `interfaces.j2` — `forced_mgmt_routes` に追加ルートを列挙すると、Management VRF 有無に応じてデフォルト VRF または mgmt VRF のルーティングテーブルへ追加される。
- Management VRF が未有効化の状態で mgmt VRF 向けルートを設定しても、フォールバックとしてデフォルト VRF に追加される。

### 3. エントリの IP プレフィックス部分が複合キー
- ソース: `sonic-mgmt_interface.yang` — キーは `(eth0, ip_prefix)` の組み合わせ。同一インターフェースに複数プレフィックスを設定可能。
- CLI (`config/main.py`) は既存設定の gwaddr を参照し、新規プレフィックスと矛盾する場合に警告を出す。

### 4. USB ネットワークインターフェース使用時の自動 reset
- ソース: `config/main.py` L1117 `reset_mgmt_interface_if_usb_not_running()` — USB ネットワークが未稼働の場合、mgmt interface エントリを CONFIG_DB から削除して eth0 をリセット。
