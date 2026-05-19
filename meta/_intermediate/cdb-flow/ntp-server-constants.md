# NTP_SERVER — Phase E: ハードコード定数調査

## 調査対象ファイル

- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-ntp.yang`
- `sonic-buildimage/files/image_config/chrony/chrony.conf.j2`
- `sonic-host-services/scripts/hostcfgd`
- `sonic-host-services/scripts/caclmgrd`
- `sonic-buildimage/src/sonic-config-engine/minigraph.py`

---

## 調査結果サマリ

### YANG 定数 (sonic-ntp.yang)

| 定数 | 値 | 行 |
|------|-----|-----|
| NTP_SERVER_LIST max-elements | 10 | L174 |
| association_type default | "server" | L189 |
| iburst default | "on" | L195 |
| admin_state default | "enabled" | L213 |
| trusted default | "no" | L219 |
| version default | 4 | L231 |
| version range | "3..4" | L227-228 |

### chrony.conf.j2 テンプレート定数

#### Jinja2 フォールバック値
- `association_type | d('server')` (L26) — DB キーなし時のフォールバック
- `resolve_as | d(server)` (L27) — DB キーなし時はサーバアドレスをそのまま使用
- pool タイプでは `resolve_as = server` で強制上書き (L49-51)

#### iburst テンプレートバグ
- L37: `{% if config.iburst %}` — truthy 判定のみ。`'off'` も iburst 付与される

#### ハードコードファイルパスと数値定数
- driftfile: `/var/lib/chrony/chrony.drift` (L132)
- ntsdumpdir: `/var/lib/chrony` (L135)
- logdir: `/var/log/chrony` (L141)
- maxupdateskew: `100.0` (L144)
- rtcfile: `/var/lib/chrony/rtc` (L156)
- hwclockfile: `/etc/adjtime` (L157)
- rtcautotrim: `15` (L159)
- leapsectz: `right/UTC` (L170)
- keyfile: `/etc/chrony/chrony.keys` (L127)
- confdir: `/etc/chrony/conf.d` (L10)
- sourcedir (dhcp): `/run/chrony-dhcp` (L119)
- sourcedir (static): `/etc/chrony/sources.d` (L122)

### caclmgrd NTP サービス定義 (L95-100)

```python
ACL_SERVICES = {
    "NTP": {
        "ip_protocols": ["udp"],
        "dst_ports": ["123"],
        "multi_asic_ns_to_host_fwd": False
    },
```

- NTP ポート: UDP 123 (リテラル、変更不可)
- multi_asic_ns_to_host_fwd: False

### hostcfgd コマンド定数

```python
CHRONY_RESTART = ['systemctl', 'restart', 'chrony']  # L1280
```

### minigraph.py 注入定数

```python
results['NTP_SERVER'] = dict((item, {'iburst': 'on'}) for item in ntp_servers)  # L2646
```

ブート時に全 NTP_SERVER エントリに `iburst: 'on'` を一律設定。

### CONFIG_DB で制御不可能な chrony パラメータ

- `minpoll`: YANG/CONFIG_DB フィールドなし → chrony 内部デフォルト 6 (= 64s) を使用
- `maxpoll`: YANG/CONFIG_DB フィールドなし → chrony 内部デフォルト 10 (= 1024s) を使用
