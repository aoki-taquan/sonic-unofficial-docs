# BGP_DEVICE_GLOBAL テーブル 暗黙参照スキャン (Phase C / Task F)

`docs/reference/config-db/bgp-device-global.md` の暗黙参照 (`<!-- cross-refs -->`) ブロック裏付け資料。

ソースは:

- `sonic-net/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_device_global.py`
- `sonic-net/sonic-swss/orchagent/bfdorch.{cpp,h}` (`BgpGlobalStateOrch` 実装。専用 `.cpp` は `bfdorch.cpp` に同居)
- `sonic-net/sonic-swss/orchagent/orchdaemon.cpp` (`BgpGlobalStateOrch` 構築箇所)

`BGP_DEVICE_GLOBAL` テーブル本体のフィールド (`tsa_enabled` / `wcmp_enabled` / `idf_isolation_state` / `asn` / `peers`) には現れないが、`bgpcfgd` `DeviceGlobalCfgMgr` および orchagent `BgpGlobalStateOrch` / `BfdOrch` が間接的に読み出す関連 CONFIG_DB エンティティと、CHASSIS_APP_DB / constants.yml 由来の外部依存を列挙する。

## スキャン手順

```
grep -nE "DEVICE_METADATA|CHASSIS_APP_DB|chassis|switch_role|switch_type|FEATURE|bgp_asn" \
    .cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_device_global.py

grep -nE "BgpGlobalStateOrch|handleTsaStateChange|getTsaState|getSoftwareBfd|CFG_BGP_DEVICE_GLOBAL" \
    .cache/sonic-sources/sonic-swss/orchagent/bfdorch.{cpp,h} \
    .cache/sonic-sources/sonic-swss/orchagent/orchdaemon.cpp

grep -nE "FEATURE|frr_mgmt_framework" \
    .cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/*.py
```

## 検出された暗黙参照

### 1. `DEVICE_METADATA` (CONFIG_DB)

`DeviceGlobalCfgMgr.__init__` は明示的に `DEVICE_METADATA` を `directory.subscribe` し、`localhost/type` 変化時に `handle_type_update()` を駆動する:

| フィールド | 役割 | 参照箇所 |
|---|---|---|
| `localhost.type` (switch_role) | `downstream_isolate_unisolate()` が `SpineRouter` / `LowerSpineRouter` / `UpperSpineRouter` 以外で IDF 適用を **スキップ** (`return True` 早期 return) | `managers_device_global.py:23,33,53-55,260-262` |

> `DEVICE_METADATA.localhost.bgp_asn` / `subtype` / `switch_type` は `managers_device_global.py` で **0 ヒット**。`switch_role` のみが IDF 分岐に使われる。
>
> 初期値は `self.switch_role = ""` (空文字)。`switch_role and switch_role not in [...]` 条件のため、**`DEVICE_METADATA` 未設定時は条件 falsy → IDF 適用が進む**（スキップされない）。

| エンティティ | 種別 | 関係 | evidence |
|---|---|---|---|
| `DEVICE_METADATA.localhost.type` | CONFIG_DB フィールド | IDF route-map push の条件分岐 | `managers_device_global.py:33,53-55,260-262` |
| `DEVICE_METADATA.localhost.bgp_asn` | CONFIG_DB フィールド | **無関係** (`managers_device_global.py` で 0 ヒット。`BGP_GLOBALS` 側で参照される) | (grep 0 ヒット) |

### 2. `CHASSIS_APP_DB.BGP_DEVICE_GLOBAL` (CHASSIS_APP_DB)

`get_chassis_tsa_status()` は **別 DB (`CHASSIS_APP_DB`)** の `BGP_DEVICE_GLOBAL|STATE.tsa_enabled` を直接読み、シャーシ全体 TSA を表現する:

| 参照キー | 役割 | evidence |
|---|---|---|
| `CHASSIS_APP_DB.BGP_DEVICE_GLOBAL|STATE.tsa_enabled` | シャーシ全体 TSA。`chassis_tsa == "true"` の間は個別 LC の `BGP_DEVICE_GLOBAL|STATE.tsa_enabled` 書き込みでは `isolate_unisolate_device()` を呼ばない (chassis TSA 優先) | `managers_device_global.py:100,106,238-251` |

> `device_info.is_chassis()` が `false` の通常スイッチでは `chassis_tsa_status = "false"` を返し、CHASSIS_APP_DB へのアクセスは行わない (`managers_device_global.py:241-242`)。
>
> シャーシ環境では `bgpcfgd` 内 `ChassisAppDbMgr` (`main.py:113`) が CHASSIS_APP_DB を別途購読する。同一テーブル名 `BGP_DEVICE_GLOBAL` を CONFIG_DB / CHASSIS_APP_DB の二系統で使う設計。

### 3. `BgpGlobalStateOrch` → `BfdOrch` (orchagent 内 directory)

orchagent 側では `BgpGlobalStateOrch` (`bfdorch.h:58-72`) が `BGP_DEVICE_GLOBAL` の CONFIG_DB consumer となり、`BfdOrch::doTask` から `gDirectory.get<BgpGlobalStateOrch*>()` 経由で読み出される:

| API | 役割 | evidence |
|---|---|---|
| `BgpGlobalStateOrch::getTsaState()` | `BfdOrch::doTask` 内で BFD セッション生成可否を判定 (`tsa_enabled` 時に `shutdown_bfd_during_tsa == "true"` の BFD セッションを非作成) | `bfdorch.cpp:114-160`, `bfdorch.h:64` |
| `BgpGlobalStateOrch::getSoftwareBfd()` | `m_stateSoftBfdSessionTable` 経路で software BFD に切替えるか判定 | `bfdorch.cpp:114-188`, `bfdorch.h:65` |

`orchdaemon.cpp:239-241` で `BgpGlobalStateOrch` を `BfdOrch` 構築の **前** に new + `gDirectory.set()` する順序が明示。`m_orchList` (`orchdaemon.cpp:500`) でも `bgp_global_state_orch` が `gBfdOrch` より先に並ぶ。

> このパスは CONFIG_DB ではなく **orchagent プロセス内 directory** を経由する暗黙参照。docs 側では「BFD orch との連携」として記述する。

### 4. `BFD_SESSION` (CONFIG_DB) — `BGP_DEVICE_GLOBAL` 変化が間接波及するテーブル

`BFD_SESSION` テーブル自体は `BGP_DEVICE_GLOBAL` を読まないが、逆方向に `BGP_DEVICE_GLOBAL.tsa_enabled` 変化が `BfdOrch::doTask` の判定経由で BFD セッション作成可否 (`shutdown_bfd_during_tsa`) に影響する。`bfdorch.cpp:141-160` を参照:

```cpp
if (fvField(i) == "shutdown_bfd_during_tsa" && value == "true" )
    tsa_shutdown_enabled = true;
...
if (tsa_shutdown_enabled) {
    if (!tsa_enabled) { /* create */ }
}
```

| エンティティ | 種別 | 関係 | evidence |
|---|---|---|---|
| `BFD_SESSION` (CONFIG_DB) | CONFIG_DB テーブル | `BGP_DEVICE_GLOBAL.tsa_enabled` 変化時に `BfdOrch::doTask` 経由で `shutdown_bfd_during_tsa=true` セッションの作成/維持判定を再評価 | `bfdorch.cpp:114-160` |

### 5. `FEATURE` (CONFIG_DB) — 明示参照なし

`managers_device_global.py` および `bfdorch.{cpp,h}` を `FEATURE` で grep して **0 ヒット**。`BGP_DEVICE_GLOBAL` フローは `FEATURE` テーブルを直接読まない。

> BGP コンテナ起動可否 (`FEATURE|bgp.state`) は `hostcfgd` 系のサービス起動制御で扱われ、`bgpcfgd` プロセス内 (`DeviceGlobalCfgMgr`) には FEATURE 参照が存在しない。`software_bfd` 機能ゲートは `constants.yml` (build-time) で制御され、CONFIG_DB の `FEATURE` ではない (`main.py:118-119`)。
>
> 隣接リファレンスとしては `FEATURE|bgp` が BGP コンテナ起動を司るため、`BGP_DEVICE_GLOBAL` の処理は `FEATURE|bgp.state == "enabled"` が前提という運用上の含意がある (明示的なコード参照はなし)。

### 6. `constants.yml` (CONFIG_DB 外部依存)

`DeviceGlobalCfgMgr` は `common_objs['constants']` を保持し、Jinja2 テンプレレンダリングに渡す:

| 経路 | 用途 | evidence |
|---|---|---|
| `tsa_template.render(... constants=self.constants)` | TSA route-map テンプレ展開 | `managers_device_global.py:225` |
| `idf_isolate_template.render(... constants=self.constants)` | IDF isolate route-map テンプレ展開 | `managers_device_global.py:269,285` |
| `idf_unisolate_template.render(constants=self.constants)` | IDF unisolate route-map テンプレ展開 | `managers_device_global.py:266` |
| `wcmp_template.render(wcmp_enabled=status)` | W-ECMP テンプレ展開 (constants 不使用) | `managers_device_global.py:158` |

`constants.yml` 内の関連キー (`bgp.*` 配下) はテンプレ側で参照され、CONFIG_DB ではないが BGP_DEVICE_GLOBAL の挙動 (community 値・tag 等) を決定する外部依存。

### 7. `BGP_GLOBALS` (CONFIG_DB) — 隣接テーブルだが直接参照なし

`managers_device_global.py` を `BGP_GLOBALS` で grep して **0 ヒット**。`BGP_DEVICE_GLOBAL` は VRF 横断・装置全体スコープ、`BGP_GLOBALS` は VRF 単位という設計分離。両者は同じ `bgpcfgd` プロセス内で別マネージャ (`BGPCfgMgr` 系) が処理する。

> ただし TSA route-map は `cfg_mgr.get_text()` (FRR running-config) から `neighbor <X> route-map <name> out` を逆引きするため、`BGP_GLOBALS` 由来の neighbor 設定が FRR へ反映済みである必要がある (実行時依存)。CONFIG_DB レベルの読み合いではない。

## まとめ — `bgp-device-global.md` Phase C 記載対象

| カテゴリ | エンティティ | 種別 |
|---|---|---|
| switch_role 分岐 | `DEVICE_METADATA.localhost.type` | CONFIG_DB フィールド |
| 別 DB の同名テーブル (chassis TSA) | `CHASSIS_APP_DB.BGP_DEVICE_GLOBAL|STATE.tsa_enabled` | CHASSIS_APP_DB |
| orchagent 内 directory 経由 | `BgpGlobalStateOrch` → `BfdOrch` (`getTsaState` / `getSoftwareBfd`) | orchagent プロセス内 |
| BFD セッション波及 | `BFD_SESSION` (`shutdown_bfd_during_tsa`) | CONFIG_DB テーブル |
| 外部依存 | `constants.yml` (`bgp.*` テンプレ変数) | CONFIG_DB 外 |

## 明示的に **無関係** と確認した参照候補

| 候補 | 確認内容 |
|---|---|
| `FEATURE` (CONFIG_DB) | `managers_device_global.py` / `bfdorch.{cpp,h}` で grep 0 ヒット。BGP コンテナ起動制御は `hostcfgd` 側に分離 |
| `BGP_GLOBALS` (CONFIG_DB) | `managers_device_global.py` で grep 0 ヒット。VRF 単位 BGP 設定は別マネージャ |
| `DEVICE_METADATA.localhost.bgp_asn` | `managers_device_global.py` で grep 0 ヒット。TSA/W-ECMP/IDF は AS 番号非依存 |
| `BGP_NEIGHBOR` / `BGP_PEER_GROUP` | CONFIG_DB レベルでは直接参照なし。TSA は FRR running-config テキストから `neighbor route-map out` を逆引きする (`managers_device_global.py:229-236`) |

このスキャン結果から `docs/reference/config-db/bgp-device-global.md` の `<!-- cross-refs -->` ブロックを生成する。
