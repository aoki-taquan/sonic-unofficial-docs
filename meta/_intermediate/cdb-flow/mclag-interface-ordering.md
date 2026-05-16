# MCLAG_INTERFACE — Phase B 書込み順序依存スキャンノート

対象テーブル: `MCLAG_INTERFACE`
Consumer: `MlagOrch::doMlagInterfaceTask()` (`sonic-swss/orchagent/mlagorch.cpp` L117-153)
スキャン範囲: `mlagorch.cpp` 全行精読、`sonic-mclag.yang` 全行精読、`config/mclag.py` 全行精読

---

## 検出した順序依存・タイミング依存

### 1. allPortsReady() ガード（ポート初期化先行必須）

`MlagOrch::doTask()` L49-52: `gPortsOrch->allPortsReady()` が false の間は `doMlagInterfaceTask()` を含む全テーブル処理が即 return でブロックされる。  
PortsOrch 起動完了前に書き込まれた MCLAG_INTERFACE エントリはキューに保留され、ポート初期化完了後に一括処理される。  
evidence: `mlagorch.cpp:49-52`

### 2. MCLAG_DOMAIN が先行必須（leafref + YANG must）

`MCLAG_INTERFACE.domain_id` は `MCLAG_DOMAIN.domain_id` への leafref (`sonic-mclag.yang` L108-109)。MCLAG_DOMAIN が CONFIG_DB に存在しない状態で MCLAG_INTERFACE を書くと YANG バリデーション段階で拒否される。  
CLI `config mclag member add` は `ADHOC_VALIDATION` ブロックで事前に `MCLAG_DOMAIN` エントリ存在を確認し、0 件の場合は `ctx.fail("MCLAG Domain ... not configured")` で中断する (`config/mclag.py` L283-286)。  
evidence: `sonic-mclag.yang:108-109`, `config/mclag.py:283-286`

### 3. PORTCHANNEL が先行必須（leafref）

`MCLAG_INTERFACE.if_name` は `PORTCHANNEL.name` への leafref (`sonic-mclag.yang` L115-116)。対象 PortChannel が CONFIG_DB に存在しない場合は YANG バリデーションで拒否される。  
`addMlagInterface()` (L193-213) は `gPortsOrch->getPort()` を呼ばないため orchagent 側では PORTCHANNEL 存在確認を行わない。YANG バリデーション段階での拒否が唯一の強制手段。  
evidence: `sonic-mclag.yang:115-116`, `mlagorch.cpp:193-213`

### 4. mclagsyncd の購読開始タイミング（MCLAG_DOMAIN 初回 SET 後）

`MclagLink::addDomainCfgDependentSelectables()` (`mclaglink.cpp` L910-929) は MCLAG_DOMAIN の**初回 SET 成功後**に初めて MCLAG_INTERFACE テーブルの SubscriberStateTable を生成・Select に追加する。  
MCLAG_DOMAIN SET が完了する前に MCLAG_INTERFACE を書いても mclagsyncd は購読しておらず、iccpd への通知が届かない。  
evidence: `mclaglink.cpp:814-818`, `mclaglink.cpp:910-921`

### 5. 削除順序（MCLAG_INTERFACE → MCLAG_DOMAIN）

MCLAG_DOMAIN DEL の前に MCLAG_INTERFACE を DEL することで `domain_id` leafref の dangling を防ぐ。  
CLI `config mclag del <domain_id>` (mclag.py L186-199) は対象 domain_id の全 MCLAG_INTERFACE を自動 DEL してから MCLAG_DOMAIN を削除する。手動 DB 操作では上記順序を遵守すること。  
evidence: `config/mclag.py:186-199`

---

## 順序依存サマリ

| # | 依存関係 | 強制度 | 緩和策 |
|---|----------|--------|--------|
| 1 | allPortsReady() 完了 → MCLAG_INTERFACE 処理 | 強制（PortsOrch 先行） | 自動待機（キュー保留） |
| 2 | MCLAG_DOMAIN 存在 → MCLAG_INTERFACE SET | YANG leafref + CLI チェック必須 | MCLAG_DOMAIN を先に書く |
| 3 | PORTCHANNEL 存在 → MCLAG_INTERFACE.if_name | YANG leafref 必須 | PortChannel を先に設定 |
| 4 | MCLAG_DOMAIN 初回 ADD → mclagsyncd が MCLAG_INTERFACE 購読開始 | mclagsyncd 内部タイミング | MCLAG_DOMAIN SET 完了後に MCLAG_INTERFACE を書く |
| 5 | MCLAG_INTERFACE DEL → MCLAG_DOMAIN DEL | 推奨（leafref dangling 防止） | CLI del が自動実行 |
