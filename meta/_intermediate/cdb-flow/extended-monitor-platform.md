# extended-monitor — Phase H: プラットフォーム差調査

調査日: 2026-05-19  
対象: `eventd` デーモン・`/etc/eventd.json`・`/etc/evprofile/default.json` のプラットフォーム差

## 調査対象ソース

- `SONiC/doc/event-alarm-framework/event-alarm-framework.md` — HLD section 3.1.4.1 (System LED)
- `sonic-buildimage/src/sonic-eventd/src/eventd.cpp` — `run_eventd_service()` 全体
- `sonic-buildimage/src/sonic-eventd/src/eventd.h` — 定数定義
- `sonic-buildimage/dockers/docker-eventd/Dockerfile.j2` — コンテナビルド定義
- `sonic-buildimage/dockers/docker-eventd/supervisord.conf` — 起動設定

---

## 結論

**eventd 本体・設定ファイルスキーマはプラットフォーム差なし**。唯一の例外は `pmon` の LED 制御で、HLD が明示的にプラットフォーム依存性を記述している。

---

## 詳細

### 1. eventd.cpp — プラットフォーム分岐なし

`eventd.cpp` 全体 (840 行) を `platform`, `asic`, `multi`, `broadcom`, `mellanox`, `marvell`, `nvidia`, `chassis`, `namespace`, `vendor` で grep → **0 ヒット**。

ZMQ エンドポイント (`xsub_path`, `xpub_path`, `capture_path`) のデフォルト値も `tcp://127.0.0.1:5570〜5573` の固定値であり、ASIC 種別・multi-asic namespace ごとの分岐は存在しない。

### 2. docker-eventd コンテナビルド — プラットフォーム分岐なし

`dockers/docker-eventd/Dockerfile.j2` を `platform|asic|chassis|namespace|vendor` で grep → **0 ヒット**。ベースイメージは `docker-config-engine-trixie` で固定。プラットフォーム固有ファイルのコピーや条件インストールはなし。

`docker-eventd/supervisord.conf` も `platform|asic` で grep → **0 ヒット**。起動スクリプト `start.sh` は `RUNTIME_OWNER` の分岐のみ (kube vs local) で、プラットフォーム依存なし。

### 3. evprofile / eventd.json — プラットフォーム差なし

`/etc/evprofile/default.json` および `/etc/eventd.json` はプラットフォーム共通フォーマット。  
`sonic-buildimage/files/` および各 `platform/` ディレクトリにプラットフォーム固有 `evprofile` ファイルは存在しない。  
`sonic-buildimage/dockers/docker-eventd/*.json` はイベントカテゴリ別の rsyslog プラグイン設定であり、evprofile とは別物。プラットフォーム分岐なし。

### 4. pmon の LED 制御 — プラットフォーム依存あり (HLD 明記)

HLD section 3.1.4.1 が明示:

> "on most of the platforms the system/power/fan LEDs are managed by the BMC."  
> "There is an API that can be invoked to control LED, but not all platforms will support that API if they are fully controlled by the BMC."  
> "So, on certain platforms, system LED could not represent events on the system."

`pmon` が `ALARM_STATS` を購読してシステム LED を制御する仕組みは framework 設計上の "提案" であり、**BMC 管理型プラットフォームでは LED API が利用不可のため LED 制御が無効化される**。ただしこれは `eventd` 本体・設定ファイルスキーマの差ではなく、`pmon` の LED ドライバ層の差である。`eventd` は ALARM_STATS を書くだけで、LEDへの反映可否には関与しない。

### 5. multi-asic / VOQ chassis

`eventd` は host コンテナ (`docker-eventd`) 内で 1 インスタンスのみ起動し、`asicN` namespace へのアクセスや namespace 間 ZMQ ソケットの複数化は行わない。multi-asic 環境でも EVENT_DB は 1 つのホスト Redis であり、ASIC ごとの分離は存在しない。

VOQ chassis (supervisor + line cards) の各 host で独立した `docker-eventd` が起動するが、設定スキーマ・ファイルパスは同一。chassis 全体集中化機構なし。

---

## まとめ

| 観点 | 結果 | 根拠 |
|------|------|------|
| ASIC 種別 (Broadcom / Mellanox / Marvell 等) | 影響なし | `eventd.cpp` に ASIC 分岐なし |
| multi-asic (`is_multi_npu() == True`) | 影響なし | eventd は host Redis に 1 インスタンス。namespace 分離なし |
| VOQ chassis (supervisor + line cards) | 各 host で独立起動 | 設定スキーマ同一。集中管理機構なし |
| evprofile / eventd.json フォーマット | 差なし | プラットフォーム固有ファイルなし |
| docker-eventd コンテナビルド | 差なし | Dockerfile.j2 にプラットフォーム分岐なし |
| pmon の LED 制御 | **プラットフォーム依存** | BMC 管理型では LED API 不可 (HLD section 3.1.4.1) |
