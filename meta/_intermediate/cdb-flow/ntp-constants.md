# NTP テーブル群 — Phase E: ハードコード定数調査

## 調査対象ファイル

- `sonic-host-services/scripts/caclmgrd` — ACL サービス定義
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-ntp.yang` — YANG 型定義

---

## ハードコード定数一覧

### NTP UDP ポート定数 (caclmgrd)

`caclmgrd:95-100` の `ACL_SERVICES` 定義:

```python
ACL_SERVICES = {
    "NTP": {
        "ip_protocols": ["udp"],
        "dst_ports": ["123"],
        "multi_asic_ns_to_host_fwd": False
    },
```

| 定数 / 用途 | 値 | ソース行 |
|------------|-----|---------|
| NTP サービスポート (UDP) | **123** | `caclmgrd:98` |
| プロトコル | **`udp`** | `caclmgrd:97` |
| multi_asic_ns_to_host_fwd | **`False`** | `caclmgrd:99` |

`dst_ports: ["123"]` は CONFIG_DB の NTP テーブルから読まず、コードにリテラルとして埋め込まれている。ユーザーが NTP ポートを変更する CONFIG_DB フィールドは存在しない。

### NTP_KEY.type デフォルト定数 (sonic-ntp.yang)

`sonic-ntp.yang:66-73, 268`:

```yang
typedef key-type {
    description "NTP key encryption type";
    type enumeration {
        enum md5;
        enum sha1;
        enum sha256;
        enum sha384;
        enum sha512;
    }
}
...
leaf type {
    type key-type;
    default md5;
    description "NTP authentication key type";
}
```

| 定数 / 用途 | 値 | ソース行 |
|------------|-----|---------|
| `NTP_KEY.type` YANG default | **`md5`** | `sonic-ntp.yang:268` |
| key-type enum 値 (全) | `md5 / sha1 / sha256 / sha384 / sha512` | `sonic-ntp.yang:66-73` |

`chrony.keys.j2:17` は `NTP_KEY[keyid].type | upper` でキーファイルに書き出す（例: `MD5`, `SHA1`, `SHA256`）。

### minpoll / maxpoll 非存在

chrony のポーリング間隔 (`minpoll` / `maxpoll`) に対応する CONFIG_DB フィールドは存在しない。YANG にも定義なし。chrony のデフォルト（minpoll 6 = 64s、maxpoll 10 = 1024s）がそのまま使用される。

### keyfile パス定数 (chrony.conf.j2)

`chrony.conf.j2:127` でハードコード:

```jinja2
keyfile /etc/chrony/chrony.keys
```

| 定数 / 用途 | 値 | ソース行 |
|------------|-----|---------|
| chrony keyfile パス | **`/etc/chrony/chrony.keys`** | `chrony.conf.j2:127` |

CONFIG_DB の NTP テーブルでキーファイルパスを変更するフィールドはない。

---

## 特記事項

1. **NTP ポート 123** は `caclmgrd` にリテラルでハードコード。iptables のフィルタルール生成に使用される。CONFIG_DB の `NTP` テーブルに対応フィールドなし。
2. **NTP_KEY.type default `md5`** は RFC 8573 で非推奨。SHA-1 以上が推奨されるが、YANG default は歴史的経緯で md5 のまま。
3. **minpoll / maxpoll** は CONFIG_DB / YANG いずれにも定義なし。chrony 内部デフォルト（64s / 1024s）が使用される。

## evidence

- `caclmgrd`: `sonic-host-services/scripts/caclmgrd` L95-100
- `sonic-ntp.yang`: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-ntp.yang` L66-73, L266-270
- `chrony.conf.j2`: `sonic-buildimage/files/image_config/chrony/chrony.conf.j2` L127
