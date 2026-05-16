# BANNER_MESSAGE — プラットフォーム差 (Phase H)

調査日: 2026-05-15
対象テーブル: `BANNER_MESSAGE|global`

## 結論

**プラットフォーム差なし**（multi-asic / chassis / ベンダー固有分岐すべて該当なし）。

`BANNER_MESSAGE` はホスト名前空間限定のシングルトンテーブルで、対象は Linux ホストの `/etc/issue` `/etc/issue.net` `/etc/motd` `/etc/logout_message` というファイルのみ。SAI / asic / chassis ハードウェアには一切タッチしない。

## 根拠

### 1. multi-asic 分岐なし

`hostcfgd` の `BannerCfg` クラス内に `namespace` / `asic_id` / `multi_asic` / `host_namespace` の参照なし。グローバル CONFIG_DB (host namespace) を直接読み、`systemctl restart banner-config` をホスト側で 1 回発行するだけ。

- `sonic-host-services/scripts/hostcfgd:2044-2114` — `BannerCfg` 全体に multi-asic 関連 import / 分岐なし
- `sonic-host-services/scripts/hostcfgd:2074-2082` — `banner_messages_config.get("state"|"login"|"motd"|"logout", {})` 4 つだけ。namespace ループなし

### 2. chassis (VoQ / packet-chassis) 分岐なし

`banner-config.sh` (12 行) は `sonic-db-cli CONFIG_DB HGET 'BANNER_MESSAGE|global' ...` を 4 回呼ぶだけ。linecard / supervisor / midplane 等の chassis 文脈や `database-chassis` への分岐なし。

- `sonic-buildimage/files/image_config/bannerconfig/banner-config.sh:1-18` 全体に `chassis` / `linecard` / `supervisor` 文字列なし

### 3. ベンダー固有 banner なし

`platform/*/` 配下に banner-* スクリプトや上書きファイルなし。`bannerconfig/banner-config.service` は全プラットフォーム共通で `sonic_debian_extension.j2:652-654` から `FILESYSTEM_ROOT_USR_LIB_SYSTEMD_SYSTEM` に常時コピーされる (platform 別 if 文の外)。

- `sonic-buildimage/files/build_templates/sonic_debian_extension.j2:652-654` — platform 条件なしで全イメージに含まれる
- `.cache/sonic-sources/sonic-buildimage/platform/` 配下に `banner` 関連ファイルなし (grep 確認)

### 4. ASIC タイプ依存なし

書き換え対象は Linux ファイルシステム上のテキストファイル 4 つのみ。Broadcom / Mellanox / Marvell / Innovium 等の SAI ライブラリ呼び出しなし。

### 5. systemd unit は単一インスタンス

`banner-config.service` は `[Install] WantedBy=sonic.target`、テンプレ化 (`@.service`) なし。multi-asic chassis でも 1 インスタンスのみ起動。

- `sonic-buildimage/files/image_config/bannerconfig/banner-config.service:1-14`

### 6. HLD 確認

`SONiC/doc/banner/banner_hld.md` 全文 (203 行) に "asic" / "chassis" / "namespace" / "platform" / "vendor" の言及なし — 機能設計上もプラットフォーム非依存。

## サマリ表

| 観点 | 差の有無 | 根拠 |
|------|---------|------|
| multi-asic (namespace) | なし | hostcfgd `BannerCfg` に namespace 分岐なし |
| chassis (VoQ / packet) | なし | `banner-config.sh` は host CONFIG_DB のみ参照 |
| ASIC ベンダー (Broadcom/Mellanox/…) | なし | SAI 非経由 / Linux ファイル書き換えのみ |
| プラットフォーム別オーバーライド | なし | `platform/*/` に banner 関連ファイルなし |
| systemd template instance | なし | 単一 unit `banner-config.service` |

## 結論再掲

`BANNER_MESSAGE` テーブルおよびその唯一の購読者 (`hostcfgd` `BannerCfg` + `banner-config.sh`) はすべてのプラットフォーム / ASIC / chassis 構成で同一に動作する。プラットフォーム差はない。
