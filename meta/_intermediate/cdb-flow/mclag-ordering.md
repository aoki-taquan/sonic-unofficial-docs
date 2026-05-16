# MCLAG_DOMAIN / MCLAG_INTERFACE / MCLAG_UNIQUE_IP — Phase B 書込み順依存スキャンノート

対象テーブル: `MCLAG_DOMAIN`, `MCLAG_INTERFACE`, `MCLAG_UNIQUE_IP`
Consumer: `MlagOrch::doTask()` (`sonic-swss/orchagent/mlagorch.cpp`)、`MclagLink::processMclagDomainCfg()` (`sonic-swss/mclagsyncd/mclaglink.cpp`)
スキャン範囲: `mlagorch.cpp` L45-250 全行精読、`mclaglink.cpp` L626-930 全行精読、`sonic-mclag.yang` 全行精読、`config/mclag.py` 全行精読

---

## 検出した順序依存・タイミング依存

### 1. allPortsReady() ガード（ポート初期化先行必須）

- `MlagOrch::doTask()` L49-52: `gPortsOrch->allPortsReady()` が false の間は即 return。
- **MCLAG_DOMAIN および MCLAG_INTERFACE の両テーブル処理がブロックされる**。
- PortsOrch の起動完了前に書き込んだ CONFIG_DB エントリは、ポート初期化完了後に一括処理される（キューに保留）。
- 順序依存: `PORT` テーブルの初期化完了（PortsOrch）が MCLAG_DOMAIN / MCLAG_INTERFACE より**先に**完了していること。
- evidence: `mlagorch.cpp:49-52`

### 2. PORTCHANNEL が先行必須（MCLAG_DOMAIN.peer_link）

- `MlagOrch::doMlagDomainTask()` L91: `peer_link` が空文字列の場合は erase してスキップ（エラーなし）。
- `peer_link` が非空の場合は `addIslInterface(peer_link)` を呼ぶ（L93）。`addIslInterface()` は L156-172 で常に `true` を返すため待機ループは起きないが、`peer_link` の leafref は YANG で `PORT.name` または `PORTCHANNEL.name` への参照であり、**YANG バリデーション段階で存在確認される**。
- `sonic-mclag.yang` L62-71: `peer_link` の型は `union { leafref → PORT; leafref → PORTCHANNEL }` であり、CONFIG_DB にそのポートが存在しないとバリデーション拒否となる。
- 順序依存: `PORTCHANNEL|<name>` または `PORT|<name>` が CONFIG_DB に**先に**存在すること。
- evidence: `mlagorch.cpp:85-96`, `sonic-mclag.yang:62-71`

### 3. PORTCHANNEL が先行必須（MCLAG_INTERFACE.if_name）

- `MCLAG_INTERFACE.if_name` の YANG leafref は `PORTCHANNEL.name` への参照 (`sonic-mclag.yang` L115-116)。
- `domain_id` の leafref は `MCLAG_DOMAIN.domain_id` への参照 (`sonic-mclag.yang` L108-109)。
- **MCLAG_INTERFACE の SET は PORTCHANNEL が先に CONFIG_DB に存在し、かつ MCLAG_DOMAIN が先に存在することが YANG 制約として必須**。
- `addMlagInterface()` (L193-213) は即 return true（待機なし）のため orchagent 側では再試行ループなし。YANG バリデーション失敗の場合はエントリ自体が書き込まれない。
- evidence: `mlagorch.cpp:136-138`, `sonic-mclag.yang:108-116`

### 4. MCLAG_DOMAIN が先行必須（MCLAG_INTERFACE・MCLAG_UNIQUE_IP 共通）

- MCLAG_INTERFACE の `domain_id` は `MCLAG_DOMAIN.domain_id` への leafref（YANG バリデーション）。
- MCLAG_UNIQUE_IP には `must "count(../../MCLAG_DOMAIN/MCLAG_DOMAIN_LIST/domain_id) != 0"` の YANG 制約がある (`sonic-mclag.yang` L132-134)。**MCLAG_DOMAIN が 1 件も存在しない状態で MCLAG_UNIQUE_IP を書くとバリデーション拒否**。
- CLI `config mclag unique-ip add` (mclag.py L328-329) も同様に `MCLAG_DOMAIN` のキー存在を事前チェックして失敗する。
- 順序依存: `MCLAG_DOMAIN` が先に存在 → `MCLAG_INTERFACE` および `MCLAG_UNIQUE_IP` を追加可能。
- evidence: `sonic-mclag.yang:132-134`, `config/mclag.py:328-329`

### 5. mclagsyncd の依存テーブル（MCLAG_INTERFACE・MCLAG_UNIQUE_IP の購読開始タイミング）

- `MclagLink::addDomainCfgDependentSelectables()` (mclaglink.cpp L910-929): **MCLAG_DOMAIN の初回 SET が成功した後**に初めて `MCLAG_INTERFACE` テーブルと `MCLAG_UNIQUE_IP` テーブルの SubscriberStateTable を生成し、Select に追加する。
- それ以前に MCLAG_INTERFACE / MCLAG_UNIQUE_IP を書いても mclagsyncd はこれらを購読しておらず、iccpd への通知が行われない。
- `add_cfg_dependent_selectables = 1` は MCLAG_DOMAIN の `entryExists == 0`（初回 ADD）時のみセットされる（L814-818）。
- 順序依存: **MCLAG_DOMAIN の初回書込みが完了してから** MCLAG_INTERFACE および MCLAG_UNIQUE_IP を書くことで、mclagsyncd への通知が保証される。
- evidence: `mclaglink.cpp:814-818`, `mclaglink.cpp:903-907`, `mclaglink.cpp:910-929`

### 6. VLAN_INTERFACE の IP/VRF を先に削除（MCLAG_UNIQUE_IP 追加前提条件）

- CLI `config mclag unique-ip add` (mclag.py L338-347) は、対象 VLAN インターフェースに VRF バインドまたは IP アドレスが設定されている場合に失敗する。
- **推奨手順**: VLAN_INTERFACE の IP アドレス / VRF を DEL → MCLAG_UNIQUE_IP を SET → IP アドレス / VRF を再設定。
- CONFIG_DB への直接書き込み（sonic-db-cli）では CLI チェックをバイパスできるが、YANG `must` 制約 (`sonic-mclag.yang` L138-142 のコメントアウト参照) はバックリンク問題で現在無効化されている。
- evidence: `config/mclag.py:338-347`, `sonic-mclag.yang:137-142`

### 7. MCLAG_DOMAIN DEL 時の MCLAG_INTERFACE 先行削除

- CLI `config mclag del` (mclag.py L186-199): ドメイン削除時に、まず同 domain_id に属する全 MCLAG_INTERFACE エントリを削除（L188-194）してから MCLAG_DOMAIN を削除する（L197-200）。
- mclagsyncd 側は MCLAG_DOMAIN DEL 時に `delDomainCfgDependentSelectables()` を呼び、MCLAG_INTERFACE / MCLAG_UNIQUE_IP テーブルの購読を停止する（L846）。
- **推奨順序（削除）**: MCLAG_INTERFACE DEL → MCLAG_UNIQUE_IP DEL → MCLAG_DOMAIN DEL。
- MCLAG_DOMAIN を先に DEL すると MCLAG_INTERFACE の leafref (`domain_id`) が dangling となり、YANG バリデーション（leafref 整合性）が次回の SET/GET 時に問題を起こす可能性がある。
- evidence: `config/mclag.py:186-199`, `mclaglink.cpp:845-848`

### 8. max-elements 1 の排他制約

- `MCLAG_DOMAIN` は `max-elements 1`（`sonic-mclag.yang` L43）。
- YANG バリデーション有効時は 2 件目の MCLAG_DOMAIN 書込みが拒否される。
- CLI も `len(mclag_domain_keys) > 0` かつ `domain_id` が既存と異なる場合に失敗する（mclag.py L161-162）。
- 実質的に MCLAG_DOMAIN は 1 スイッチに 1 件しか持てないため、複数ドメインを前提とした順序設計は不要。
- evidence: `sonic-mclag.yang:43`, `config/mclag.py:148-162`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | allPortsReady() 完了 → MCLAG_DOMAIN / MCLAG_INTERFACE 処理 | 強制先行 | なし（PortsOrch 起動待ち） |
| 2 | PORT または PORTCHANNEL 存在 → MCLAG_DOMAIN.peer_link | YANG バリデーション必須 | peer_link はポートが存在してから設定 |
| 3 | PORTCHANNEL 存在 かつ MCLAG_DOMAIN 存在 → MCLAG_INTERFACE | YANG バリデーション必須 | 同上 + MCLAG_DOMAIN 先行 |
| 4 | MCLAG_DOMAIN 存在 → MCLAG_INTERFACE / MCLAG_UNIQUE_IP | YANG must 制約必須 | MCLAG_DOMAIN を最初に書く |
| 5 | MCLAG_DOMAIN 初回 ADD 完了 → mclagsyncd が MCLAG_INTERFACE / MCLAG_UNIQUE_IP を購読開始 | mclagsyncd 内部タイミング | MCLAG_DOMAIN SET 完了後に MCLAG_INTERFACE/UNIQUE_IP を書く |
| 6 | VLAN_INTERFACE の IP/VRF 削除 → MCLAG_UNIQUE_IP 設定 | CLI チェック必須（YANG は未enforced） | CLI 経由では IP/VRF を先に外す必要あり |
| 7 | MCLAG_INTERFACE DEL → MCLAG_UNIQUE_IP DEL → MCLAG_DOMAIN DEL | 推奨削除順序 | CLI の del コマンドが自動実行。手動 DB 操作では要注意 |
| 8 | MCLAG_DOMAIN は max-elements 1 | YANG 排他 | 2 件目は書けない。変更は既存エントリへの mod_entry |
