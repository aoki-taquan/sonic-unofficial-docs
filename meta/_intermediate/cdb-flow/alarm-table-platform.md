# ALARM テーブル — プラットフォーム差調査

Task F Phase H: `ALARM` テーブル (EVENT_DB) 適用時のプラットフォーム/構成差を `sonic-buildimage/src/sonic-eventd/` と `src/system-health/` および周辺ビルドアセットから精読した結果。

## 結論

**ALARM テーブル本体の書込側 (eventd) にはプラットフォーム差なし**。`type-id="liquid-cooling-leak"` のような **publisher 側の RAISE 条件には機種依存** があるが、テーブルスキーマ・配置 (EVENT_DB / Redis index 6)・書込フォーマット・retention は全プラットフォームで同一。multi-asic / VOQ chassis においても eventd は **per-asic ではなく host 単位の単一インスタンス**で動作する。

## 根拠

### 1. eventd 自身にプラットフォーム分岐コードなし

`sonic-buildimage/src/sonic-eventd/src/` 配下を `multi_asic|is_multi_npu|chassis|asic[0-9]|namespace|platform|vendor` で grep するとヒット 0 件 (`using namespace std;` 等の C++ namespace 文を除く)。

- `eventd.cpp` / `eventd.h` は ZMQ XPUB/XSUB proxy・heartbeat publisher (2 秒周期)・stats_collector のみで構成されており、`DEVICE_METADATA.platform` / `asic_type` / `subtype` を一切参照しない
- 同様に `rsyslog_plugin/` 側 (syslog → event 変換) も platform 情報を読まない

### 2. eventd feature は per-asic scope ではない (single instance)

`sonic-buildimage/files/build_templates/init_cfg.json.j2:95-97`:

```
{%- if include_system_eventd == "y" and BUILD_REDUCE_IMAGE_SIZE == "y" %}
    {% do features.append(("eventd","disabled", false, "enabled")) %}
{%- elif include_system_eventd == "y" %}
    {% do features.append(("eventd", "enabled", false, "enabled")) %}
{%- endif %}
```

タプル形式は `(name, state, has_per_asic_scope, auto_restart)`。**第 3 要素 `false` が固定** されている。これは `service_checker.py:134` の `has_per_asic_scope == "True"` 分岐 (multi-asic でコンテナを `name0..N` 並列起動) を **eventd は通らない** ことを意味し、VOQ chassis / multi-asic platform でも eventd コンテナは host 1 個・EVENT_DB 1 個 (host namespace) で運用される。

### 3. `eventd.service.j2` にプラットフォーム分岐なし

`files/build_templates/eventd.service.j2` は `{{docker_container_name}}` 1 変数のみで、`platform|asic|chassis|namespace|vendor|supervisor|line.?card` 系の条件分岐ゼロ。systemd unit としてのインスタンス分割もない (`@%i` テンプレート未使用)。

### 4. ALARM テーブルの key/value スキーマは固定

`sonic-swss-common/common/schema.h:551-554` の `#define EVENT_CURRENT_ALARM_TABLE_NAME "ALARM"` は build time 定数。platform 差し替え機構なし。HLD §3.1.7 のフィールド一覧 (`id` / `revision` / `type-id` / `text` / `time-created` / `severity` / `action` / `resource` / `acknowledged` / `acknowledge-time`) は機種非依存。retention (上限なし・非永続) も同じ。

### 5. healthd publisher 側にプラットフォーム差はあるが ALARM テーブルスキーマには波及しない

`src/system-health/health_checker/` には platform 由来の **publish 発火条件** が存在する。これは「ALARM 行が生成されるか否か」に影響するが、生成された ALARM 行の書込先・形式は不変。

| publisher | tag | プラットフォーム条件 | evidence |
|---|---|---|---|
| `hardware_checker._check_asic_status` | (publish なし; ALARM 直接 raise ではなく `set_object_not_ok`) | STATE_DB に `TEMPERATURE_INFO\|ASIC*` キーが存在するプラットフォームでのみ ASIC 温度判定が走る | `hardware_checker.py:15,46-71` |
| `hardware_checker` `liquid-cooling-leak` | `sonic-events-host` | liquid cooling 搭載機 (該当 STATE_DB エントリ無ければ 0 件のまま) | `hardware_checker.py:7-8,298-302` |
| `service_checker` `process-not-running` | `sonic-events-host` | `CONFIG_DB:FEATURE` の `has_per_asic_scope` を見て multi-asic 機では `<container>0..N` を期待コンテナとして展開 | `service_checker.py:130-138` |
| `service_checker` chassis supervisor 分岐 | `database-chassis` をチェック対象に追加 | `device_info.is_supervisor() or is_disaggregated_chassis()` で増減 | `service_checker.py:144-146` |

つまり「**何件 / どの type-id で ALARM が立つかは機種で変わる**」が、立った瞬間に書込まれる先 (EVENT_DB:ALARM) / フィールド名 / severity 列挙 / id 採番フォーマットは全プラットフォーム共通。

### 6. multi-asic / VOQ chassis 時の EVENT_DB 配置

- eventd は host namespace の Redis (EVENT_DB index 6) にのみ書く。`asic0..N` の Redis インスタンスには ALARM テーブルは存在しない
- VOQ chassis (line card + supervisor) では各 host が独立して自分の eventd / EVENT_DB / ALARM テーブルを持つ。chassis 全体の集中 ALARM ストアは存在しない (HLD §3.1.7 にも記載なし)
- `service_checker.py:144-146` で supervisor / disaggregated chassis では `database-chassis` コンテナの稼働を期待コンテナに加える、という監視側差分はあるが、ALARM テーブル自身は依然 host EVENT_DB のみ

### 7. System LED 連動側のプラットフォーム差

`src/system-health/health_checker/manager.py:75-79`:

```python
def _set_system_led(self, chassis):
    try:
        chassis.set_status_led(self._get_led_target_color())
    except NotImplementedError:
        print('chassis.set_status_led is not implemented')
```

`chassis.set_status_led()` は `sonic-platform-common/sonic_platform_base/chassis_base.py` の抽象 API で、各ベンダー platform ドライバ (`device/<vendor>/<sku>/plugins/`) で実装される。ALARM_STATS の severity 別カウンタから LED 色を計算するロジック自体は機種共通 (manager.py 内) で、**LED ハードウェアへの最終書込のみがプラットフォーム実装依存**。`NotImplementedError` を握り潰す設計のため、対応ドライバが無い VS / 一部低位機種では LED 色付けが no-op となる。

### 8. image_config / build_templates に ALARM / eventd 固有のプラットフォーム上書きなし

- `files/image_config/` に `eventd` / `alarm` / `event` ディレクトリは存在しない (HLD §3.1.2.4 の `default.json` event profile は eventd Docker image に固定で焼き込み、機種別差し替え機構なし)
- `dockers/docker-eventd/` も `Dockerfile.j2` レベルで platform 分岐なし

### 9. ベンダー固有 ALARM publisher の hook ポイントなし

community master 内に「ベンダー固有 alarm publisher SDK」「platform plugin が ALARM テーブルへ直接書く」経路は存在しない。すべての RAISE_ALARM は `swsscommon.event_publish()` API → ZMQ → eventd 経由で集中処理される。ベンダー版 SONiC (NVIDIA / Edgecore / Cisco / AsterNOS 等) は本リポジトリのスコープ外。

## まとめ

ALARM テーブル (EVENT_DB) は **書込スキーマ・格納先・retention・通信モデルのすべてが機種非依存**。プラットフォーム差は (a) どの publisher が発火するか (例: liquid-cooling 搭載機種のみ `liquid-cooling-leak` が立つ)、(b) multi-asic 環境で `process-not-running` の期待コンテナ集合が `*0..N` に展開される、(c) 最終的な System LED 書込ドライバが platform 実装依存、の 3 点に限られる。eventd 本体・ALARM テーブルキー設計・severity 列挙はすべて固定。
