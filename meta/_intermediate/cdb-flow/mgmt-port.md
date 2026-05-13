# CONFIG_DB 例外条件分析: MGMT_PORT

## Consumer

- カーネル / netplan: `MGMT_PORT` エントリは `interfaces.j2` テンプレートが読み取り、eth0 ポートの速度・MTU・admin_status 等を netdev 設定へ反映する。
- `sonic-utilities` の `show management_interface address` がステータス表示に使用。

## 例外条件

### 1. speed が 10/100/1000 Mbps 以外 → YANG が拒否
- ソース: `sonic-mgmt_port.yang` — `range "10|100|1000"` で速度を制約。それ以外の値は YANG バリデーションで拒否。

### 2. autoneg が "on" / "off" 以外 → YANG が拒否
- ソース: `sonic-mgmt_port.yang` — `pattern "on|off"` による制約。

### 3. MTU が 1500-9216 以外 → YANG が拒否 (デフォルト 1500)
- ソース: `sonic-mgmt_port.yang` — `range "1500..9216"` / `default 1500`。

### 4. admin_status のデフォルト = "up"
- ソース: `sonic-mgmt_port.yang` — `default up`。フィールドを省略すると管理ポートは有効状態として扱われる。

### 5. インターフェース名は eth0 形式のみ許可
- ソース: `sonic-mgmt_port.yang` — `pattern 'eth([1-3][0-9]{3}|[1-9][0-9]{2}|[1-9][0-9]|[0-9])'`。
- eth0 以外のインターフェース名 (例: eth1000 以上) は YANG バリデーションで拒否。

### 6. MGMT_PORT エントリが存在しない場合の動作
- `interfaces.j2` はデフォルト値 (MTU=1500, speed=1000, admin=up) でカーネル設定を生成するが、CONFIG_DB にエントリがなければ上書きは行わない。
