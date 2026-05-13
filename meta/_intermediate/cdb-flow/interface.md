# CONFIG_DB 例外条件分析: INTERFACE

## Consumer

- `intfmgr` (`sonic-swss/cfgmgr/intfmgr.cpp`): `INTERFACE` テーブルを subscribe し、Linux ネットデバイスへの IP アドレス付与・VRF バインド・MPLS 有効化・Proxy ARP 設定等を行う。

## 例外条件

### 1. IPv6 有効化失敗 → エラーログ（処理継続）
- ソース: `intfmgr.cpp` L122
- `sysctl` で IPv6 を有効化する `ip -6 addr add` 等が失敗した場合 `SWSS_LOG_ERROR("Failed to enable IPv6 on interface %s", alias.c_str())` を出力。エントリは処理済みとはならず再試行される。

### 2. admin_status に不正値 → up にデフォルト
- ソース: `intfmgr.cpp` L867
- `admin_status` が `up`/`down` 以外の場合 `SWSS_LOG_WARN("Got incorrect value for admin_status as %s for intf %s, defaulting as up", ...)` → `up` として扱われる。

### 3. MPLS 状態不正値 → エラーログ + スキップ
- ソース: `intfmgr.cpp` L184
- `mpls` フィールドが `enable`/`disable` 以外の場合 `SWSS_LOG_ERROR("MPLS state is invalid: \"%s\"", mpls.c_str())` → MPLS 設定が適用されない。

### 4. VRF 変更（別 VRF への直接移動）→ エラーログ + スキップ
- ソース: `intfmgr.cpp` L848
- インターフェースが既存 VRF に属している状態で別 VRF に直接変更しようとすると `SWSS_LOG_ERROR("%s can not change to %s directly, skipping", ...)` → VRF の付け替えは「既存 VRF から remove → 再設定」の 2 ステップが必要。

### 5. VRF または interface 未 ready → debug ログ + 延期
- ソース: `intfmgr.cpp` L835, L841
- インターフェースまたは VRF がまだ ready でない場合は `SWSS_LOG_DEBUG("Interface is not ready, skipping %s", ...)` → Consumer キューに残り再試行。

### 6. Proxy ARP / GARP の不正値 → エラーログ
- ソース: `intfmgr.cpp` L590, L632
- `grat_arp` が `enabled`/`disabled` 以外 → `SWSS_LOG_ERROR("GARP state is invalid: \"%s\"", ...)`.
- `proxy_arp` が `enabled`/`disabled` 以外 → `SWSS_LOG_ERROR("Proxy ARP state is invalid: \"%s\"", ...)`.

### 7. サブインターフェース key 不正 → エラーログ
- ソース: `intfmgr.cpp` L759
- サブインターフェース名が `Ethernet<N>.<id>` 形式でない場合 `SWSS_LOG_ERROR("Invalid subnitf: %s", ...)`.

### 8. MTU 設定失敗 → warn（処理継続）
- ソース: `intfmgr.cpp` L455
- `ip link set mtu` が失敗した場合 `SWSS_LOG_WARN("Setting mtu to %s netdev failed ...", ...)` → warn のみで処理は継続、MTU は旧値のまま。
