# RADIUS — 書込み順依存調査 (Phase B)

## 調査対象

- `sonic-host-services/scripts/hostcfgd` (AaaCfg クラス)

## 検出された順序依存

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `RADIUS_SERVER` 先行 → `RADIUS|global` 書き込み | 推奨（中間状態最小化） | runtime は subscribe 後追い自動更新 |
| 2 | `RADIUS_SERVER.src_intf` 参照インタフェース IP 存在 → 先行推奨 | 推奨先行 | `handle_radius_source_intf_ip_chg()` で後追い自動更新 |
| 3 | `eth0` IP 解決 → `nas_ip` 自動補完 | load 時 1 回解決 | `nas_ip` 明示指定で回避 |
| 4 | `DEVICE_METADATA.hostname` → `nas_id` 自動補完 | load 時 1 回解決 | runtime 追加時は hostname 設定済みであること |
| 5 | `RADIUS_SERVER` 完了 → `AAA.authentication.login = radius` 書き込み | 後書き推奨 | 先書き時は一時 local 相当動作 |
| 6 | `RADIUS|global` の key は `global` 固定 | — | 他 key はサイレントスキップ |

## Evidence

- `hostcfgd:399-417` — `load()` の全テーブル読み順序と末尾 `modify_conf_file()` 単一呼び出し
- `hostcfgd:535-545` — `radius_server_update()`: data={}削除、modify_conf=True 時即時 `modify_conf_file()`
- `hostcfgd:495-510` — `handle_radius_source_intf_ip_chg()`: src_intf IP 変化時自動再生成
- `hostcfgd:667-678` — `modify_conf_file()` 内の `nas_ip` / `nas_id` 自動補完
- `hostcfgd:752-780` — `modify_conf_file()` 内の NSS/PAM radius 有効化条件

## 結論

`RADIUS|global` は単純なシングルトン設定で、AAA 系テーブルの中では依存が最も少ない。
主要な注意点は (1) RADIUS_SERVER を先に揃えてから AAA に radius を追加すること、
(2) src_intf 指定時はインタフェース IP の後追い自動更新に依存できること。
