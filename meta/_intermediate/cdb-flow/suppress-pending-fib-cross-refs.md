# suppress-fib-pending フィールド 暗黙参照スキャン (Phase C)

`DEVICE_METADATA|localhost|suppress-fib-pending` フィールドの Phase C (暗黙参照) ブロック裏付け資料。

対応ドキュメントページは `docs/reference/config-db/suppress-pending-fib.md` として独立ページ化される予定だが、
現時点では当該フィールドは `docs/reference/config-db/device-metadata.md` の `<!-- cross-refs -->` ブロック
(L955-L1025) 内に包含されている。本ファイルはその根拠スキャン記録。

ソースは `sonic-swss/fpmsyncd/fpmsyncd.cpp` および
`sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`、
`sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/bgpd.main.conf.j2`。

## スキャン手順

```bash
grep -n "suppress.fib\|suppress_fib\|suppress-fib-pending" \
    .cache/sonic-sources/sonic-swss/fpmsyncd/fpmsyncd.cpp

grep -n "suppress.fib\|suppress_fib\|suppress-fib-pending" \
    .cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py

grep -n "suppress" \
    .cache/sonic-sources/sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/bgpd.main.conf.j2
```

## 検出された暗黙参照

### fpmsyncd — 起動時 hget + ランタイム SubscriberStateTable

| 参照種別 | コード箇所 | 用途 | evidence |
|---------|-----------|------|---------|
| 起動時 `hget` | `fpmsyncd.cpp:113` | `deviceMetadataTable.hget("localhost", "suppress-fib-pending", suppressionEnabledStr)` — `"enabled"` の場合のみ `NotificationConsumer` を追加し FIB インストール応答待機モードに入る | sonic-swss/fpmsyncd/fpmsyncd.cpp:112-118 |
| ランタイム購読 | `fpmsyncd.cpp:82-83, 265-300` | `SubscriberStateTable` で `DEVICE_METADATA` を購読。`suppress-fib-pending` の動的変化を検出し `setSuppressionEnabled()` を呼び出す。`enabled → disabled` 遷移時は既存保留ルートを `offloaded` にマークする | sonic-swss/fpmsyncd/fpmsyncd.cpp:265-300 |

### bgpcfgd managers_bgp — apply_op での BGP_GLOBALS 間接読み出し

`BgpPeerMgr.apply_op()` は BGP neighbor コマンドを FRR に push するたびに
`bgp suppress-fib-pending` を FRR コマンドに **無条件で** 先頭に付加する。

| 参照種別 | コード箇所 | 用途 | evidence |
|---------|-----------|------|---------|
| FRR コマンド生成 | `managers_bgp.py:501-506` | `directory.get_slot("CONFIG_DB", CFG_DEVICE_METADATA_TABLE_NAME)["localhost"]["bgp_asn"]` で BGP ASN を取得し `router bgp <asn>\n bgp suppress-fib-pending` を常時生成。`DEVICE_METADATA.suppress-fib-pending` フィールドの値を直接参照せず**常に有効**として FRR に伝達する | sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:501-506 |

> **注意**: `managers_bgp.py:apply_op()` は `DEVICE_METADATA|localhost|suppress-fib-pending` フィールドを
> **読み取らない**。`bgp suppress-fib-pending` は FRR 設定コマンドとして無条件に付加される。
> 実際の有効/無効の制御は fpmsyncd 側 (`fpmsyncd.cpp:113-118`) で `suppress-fib-pending` フィールドを
> 読んで行う。

### bgpd.main.conf.j2 — sonic-cfggen 展開時のハードコード

| 参照種別 | コード箇所 | 用途 | evidence |
|---------|-----------|------|---------|
| Jinja2 テンプレート | `bgpd.main.conf.j2:107` | `bgp suppress-fib-pending` が `{% block bgp_init %}` 内に**無条件ハードコード**。`DEVICE_METADATA.suppress-fib-pending` の値にかかわらず FRR startup 設定に常時含まれる | sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/bgpd.main.conf.j2:105-108 |

> `bgpd.main.conf.j2` は sonic-cfggen が docker コンテナ起動時に展開する create-only テンプレート。
> 実行中の FRR への反映は `bgpcfgd BgpPeerMgr.apply_op()` 経由で行われる。

## BGP_GLOBALS との関係

`suppress-fib-pending` 機能は `BGP_GLOBALS` テーブルのフィールドとしては定義されていない。
YANG モデル (`sonic-device_metadata.yang`) で `DEVICE_METADATA|localhost` の leaf として定義され、
`must` 制約 (`suppress-fib-pending = 'enabled'` かつ `synchronous_mode != 'enable'` のとき reject) が付く。

bgpcfgd が `BGP_GLOBALS` を参照する経路で `suppress-fib-pending` が関与するのは次のケースのみ:

| 参照関係 | 説明 |
|---------|-----|
| `DEVICE_METADATA → bgpcfgd BgpPeerMgr → FRR "bgp suppress-fib-pending"` | BGP peer コマンド push 時に常時付加。BGP_GLOBALS には関与しない |
| `DEVICE_METADATA → fpmsyncd → FIB 応答待機モード` | fpmsyncd が suppress-fib-pending の enabled/disabled を読んで挙動を切り替える |

## 対応ドキュメントステータス

`docs/reference/config-db/suppress-pending-fib.md` は現時点で**未作成**。
当フィールドの cross-refs は `docs/reference/config-db/device-metadata.md` の
`<!-- cross-refs -->` ブロック (L993) に以下として記載済み:

```
| `fpmsyncd` | `suppress-fib-pending` | SubscriberStateTable で購読。`enabled` → FIB インストール応答待機モード。
  動的切り替え時に保留ルートを offloaded にマーク | sonic-swss/fpmsyncd/fpmsyncd.cpp:82-83,113-114,265-300 |
```

独立ページ化する場合は `device-metadata.md` の `<!-- cross-refs -->` から該当行を移動し、
`suppress-pending-fib.md` に `<!-- cross-refs -->` ブロックを新設する。

## 検証コマンド

```bash
# fpmsyncd: suppress-fib-pending の読み出し箇所を確認
grep -n "suppress.fib\|SubscriberStateTable\|setSuppressionEnabled" \
    .cache/sonic-sources/sonic-swss/fpmsyncd/fpmsyncd.cpp

# bgpcfgd: apply_op の suppress コマンド生成確認
grep -n "suppress.fib\|apply_op\|bgp_asn" \
    .cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py

# Jinja2 テンプレートのハードコード確認
grep -n "suppress" \
    .cache/sonic-sources/sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/bgpd.main.conf.j2

# YANG must 制約確認
grep -n "suppress.fib\|must\b" \
    .cache/sonic-sources/sonic-buildimage/src/sonic-yang-models/yang-models/sonic-device_metadata.yang
```
