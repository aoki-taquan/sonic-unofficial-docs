# BMP — Phase B 書込み順依存スキャンノート

対象テーブル: `BMP`
Consumer: `bmpcfgd` (`sonic-buildimage/src/sonic-bmpcfgd/bmpcfgd/bmpcfgd.py`)
FRR 設定注入: `bgpd.main.conf.j2` (コンテナ起動時の静的テンプレート)
スキャン範囲: `bmpcfgd.py` 全 98 行精読 + `supervisord.conf.j2` (docker-fpm-frr) + `bgpd.main.conf.j2` L94-139

---

## 検出した順序依存・タイミング依存

### 1. `BGP_GLOBALS` / `DEVICE_METADATA.bgp_asn` 先行必須（FRR テンプレート経路）

`bgpd.main.conf.j2` L94-139 において `router bmp` / `bmp targets sonic-bmp` ブロックは  
**`router bgp {{ DEVICE_METADATA['localhost']['bgp_asn'] }}` 宣言の内側**（インデント）に配置される。

```
router bgp <asn>          ← L95: DEVICE_METADATA.bgp_asn が確定していないと bgpd 設定全体が生成されない
  ...
  bmp targets sonic-bmp  ← L132: router bgp コンテキスト内でのみ有効
  bmp connect 127.0.0.1 port 5000 ...
```

- `DEVICE_METADATA.localhost.bgp_asn` が未設定または `"none"` / `"null"` の場合、テンプレート L94 の条件分岐 (`bgp_asn.lower() != 'none'`) により `router bgp` ブロック全体が生成されない。その結果 `bmp targets sonic-bmp` も FRR に投入されず、BMP セッションが確立しない。
- evidence: `bgpd.main.conf.j2:94-139`

### 2. bgpd プロセス起動が bmpcfgd・bgpcfgd の前提

`supervisord.conf.j2` (docker-fpm-frr) の依存チェーン:

```
rsyslogd (priority=1)
  └─ zebra (priority=4, wait_for=rsyslogd:running)
       └─ bgpd (priority=5, wait_for=zsocket:exited)
            ├─ bgpcfgd / frrcfgd (priority=6, wait_for=bgpd:running)
            └─ fpmsyncd (priority=6, wait_for=bgpd:running)
```

- `bgpcfgd`（および `frrcfgd`）は `dependent_startup_wait_for=bgpd:running` で bgpd の起動完了を待ってから起動する（L179）。
- `bgpcfgd/main.py` L47 でも `frr.wait_for_daemons(seconds=20)` により bgpd の応答を能動的に確認してから Manager 登録を開始する。
- **BMP 関連順序への影響**: `BMP` テーブルへの書き込みが bgpd 起動前に CONFIG_DB に存在しても、`bmpcfgd` は `config_db.listen(init_data_handler=self.bmpcfg.load)` (`bmpcfgd.py:89`) で起動後に初回ロードする。ただし `bmpcfgd` は docker-sonic-bmp の `supervisord.conf` で管理され（priority=3）、docker-fpm-frr とは別コンテナであるため、`bmpcfgd` 自身の起動順は bgpd とは独立している。
- evidence: `supervisord.conf.j2:100-179`、`bmpcfgd.py:89`、`bgpcfgd/main.py:47`

### 3. `router bmp` CLI コマンドの内部順序（vtysh）

`bgpd.main.conf.j2` L130-136 で FRR に注入される BMP 設定の順序は固定:

```
bmp mirror buffer-limit 4294967214   ← 先にバッファ制限設定
bmp targets sonic-bmp                ← target station 宣言
bmp stats interval 1000
bmp monitor ipv4 unicast pre-policy
bmp monitor ipv6 unicast pre-policy
bmp connect 127.0.0.1 port 5000 min-retry 10000 max-retry 15000  ← 最後に接続設定
```

- `bmp targets sonic-bmp` を宣言してから `bmp connect` を設定する順序が FRR の vtysh CLI 上の階層順に準拠する。逆順（`bmp connect` → `bmp targets`）は FRR CLI では不可。
- この設定は **コンテナ起動時に静的注入**される。`bmpcfgd` は実行中に vtysh へ BMP 設定を発行しない（`bmpcfgd.py` 全 98 行: vtysh 呼び出しゼロ、supervisorctl のみ）。
- evidence: `bgpd.main.conf.j2:130-136`

### 4. openbmpd の stop → クリア → start 順序

`bmpcfgd.py` L47-49:
```python
self.stop_bmp()      # supervisorctl stop openbmpd
self.reset_bmp_table()  # BMP_STATE_DB の BGP_NEIGHBOR* / BGP_RIB_* を削除
self.start_bmp()     # supervisorctl start openbmpd
```

- `BMP` テーブルの**フィールド変更ごとに必ずこの 3 ステップが順序通りに実行**される（部分更新なし）。
- stop 前に reset を行うと、動作中の openbmpd が BMP_STATE_DB に書き込み中に削除が走る競合が発生する。stop → reset → start の順はこれを防ぐ。
- `supervisorctl stop` が失敗した場合（例: openbmpd がすでに停止済み）、例外の catch がないため `bmpcfgd` プロセスが異常終了する可能性がある（`bmpcfgd.py:58`）。
- evidence: `bmpcfgd.py:47-49, 56-70`

### 5. BMP 機能フラグ（FEATURE テーブル）と bgpd の `-M bmp` 起動オプション

`supervisord.conf.j2` L101-107:
```
{% if FEATURE.frr_bmp.state == "enabled" or FEATURE.bmp.state == "enabled" %}
command=/usr/lib/frr/bgpd -A 127.0.0.1 -P 0 -M snmp -M bmp
{% else %}
command=/usr/lib/frr/bgpd -A 127.0.0.1 -P 0 -M snmp
```

- `FEATURE|bmp.state=enabled` または `FEATURE|frr_bmp.state=enabled` がコンテナ生成時に確定していないと、bgpd が `-M bmp` モジュールなしで起動し、FRR の BMP プラグイン自体が無効化される。
- `BMP` テーブルへの書き込みは CONFIG_DB レベルでは受理されるが、bgpd に `-M bmp` がない場合は `bmp targets` コマンドが vtysh で無効（unknown command）となり BMP セッションが確立しない。
- **順序依存**: `FEATURE|bmp.state=enabled` → コンテナ再起動（bgpd 再起動） → `BMP|table` 書き込み。フラグ変更後のコンテナ再起動なしで `BMP|table` だけを変更しても BMP は機能しない場合がある。
- evidence: `supervisord.conf.j2:101-107`, `bgpd.main.conf.j2:126-139`

---

## まとめ — 推奨書込み順

1. `FEATURE|bmp.state=enabled` または `FEATURE|frr_bmp.state=enabled`（コンテナ起動前に設定必須）
2. `DEVICE_METADATA|localhost.bgp_asn`（FRR bgpd.main.conf.j2 テンプレート条件のため）
3. bgpd + docker-fpm-frr コンテナ起動（`-M bmp` フラグ付き bgpd が `router bgp` + `bmp targets` を静的注入）
4. `BMP|table`（`bgp_neighbor_table` / `bgp_rib_in_table` / `bgp_rib_out_table` の各フィールド）— bmpcfgd が検知して `stop_bmp → reset_bmp_table → start_bmp` を実行

DEL / 無効化操作: `BMP|table` フィールドを `false` に変更 → bmpcfgd が openbmpd を stop → BMP_STATE_DB クリア → openbmpd を start（フラグ `false` の状態で再起動するため実質停止状態）。BMP 機能全体を無効化する場合は `FEATURE|bmp.state=disabled` → コンテナ再起動の順。
