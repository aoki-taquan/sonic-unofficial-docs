# CONFIG_DB 例外条件分析: LLDP_PORT

## Consumer

- `lldpmgrd` (`sonic-buildimage/dockers/docker-lldp/lldpmgrd`): lldpd コンテナ内の管理スクリプトが CONFIG_DB の `LLDP_PORT` を読んで `lldpcli` コマンドでポート単位の LLDP 設定を反映する。
- `lldpd`: 実際の LLDP フレーム送受信デーモン。

## 例外条件

### 1. admin_status に不正値 → lldpcli が拒否
- `admin_status` として `rx_and_tx` / `rx_only` / `tx_only` / `disabled` 以外の値が設定された場合、`lldpcli configure ports <port> lldp status <value>` が失敗する。エラーは lldpmgrd のシェルスクリプト返り値で検知されるが、CONFIG_DB 自体にはバリデーション無しで書ける。

### 2. disabled ポートは DEVICE_NEIGHBOR に学習されない
- `admin_status=disabled` を設定したポートは LLDP フレームを送受信しないため、`DEVICE_NEIGHBOR` テーブルへのネイバー情報書き込みが発生しない。minigraph と実態が乖離する原因になる。

### 3. 存在しないポート名 → lldpcli が無視
- CONFIG_DB に実在しないインターフェース名（`Ethernet999` 等）でエントリを投入しても lldpd に対応ポートが存在しないため設定は無視される。エラーログは lldpmgrd レベルで出るが CONFIG_DB にはエントリが残る。

### 4. description フィールドは lldpd に非同期反映
- `description` は lldpd の `system description` ではなくポート固有の description として扱われる。反映は lldpmgrd のポーリング周期（デフォルト数秒）に依存。
