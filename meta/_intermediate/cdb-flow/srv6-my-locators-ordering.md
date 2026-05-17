# SRV6_MY_LOCATORS — Phase B 書込み順依存スキャンノート

対象テーブル: `SRV6_MY_LOCATORS`
Consumer: `bgpcfgd` (`SRv6Mgr`) (`sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_srv6.py`)
スキャン範囲: `locators_set_handler()`, `locators_del_handler()`, `sids_set_handler()`, `SRv6Mgr.__init__()` 全行精読

---

## 検出した順序依存・タイミング依存

### 1. SRV6_MY_LOCATORS → SRV6_MY_SIDS の先行必須

`sids_set_handler()` (managers_srv6.py:62-69) は `SRV6_MY_SIDS` エントリを処理する際、
`self.directory.path_exist(self.db_name, "SRV6_MY_LOCATORS", locator_name)` を確認する。
対応するロケータが `SRV6_MY_LOCATORS` にまだ存在しない場合:

- `log_warn()` を出力し `return False` でハンドラを終了する
- `self.deps.add((self.db_name, "SRV6_MY_LOCATORS", locator_name))` でロケータへの依存を登録
- `self.directory.subscribe([...], self.on_deps_change)` でロケータ登録イベントを購読し、ロケータが追加された時点で自動再試行される (`managers_srv6.py:64-68`)

**順序依存**: `SRV6_MY_LOCATORS` エントリを先に書いてから `SRV6_MY_SIDS` エントリを書くこと。逆順でも最終的には自動解決されるが、ロケータ到着まで SID は FRR へ通知されない。

evidence: `managers_srv6.py:62-69`

### 2. SRV6_MY_LOCATORS の prefix フィールドは必須

`Locator.__init__()` (managers_srv6.py:142) は `data['prefix'].lower()` に直接アクセスする。
`prefix` フィールドが欠落している場合、`KeyError` が発生し `locators_set_handler()` が例外で失敗する。
`SRV6_MY_SIDS` の処理はこの `Locator` オブジェクト生成 (`sids_set_handler():71`) に依存するため、
ロケータの `prefix` が正しく設定されていないと SID 処理全体が停止する。

**順序依存**: `SRV6_MY_LOCATORS` エントリには必ず `prefix` フィールドを含めて書き込む。

evidence: `managers_srv6.py:140-142`

### 3. ロケータの prefix 整合性チェックが SID より先に行われる

`sids_set_handler()` (managers_srv6.py:72-76) はロケータを取得した後、
`locator_prefix.supernet_of(sid_prefix)` で SID の IPv6 プレフィックスがロケータの配下に属するか確認する。
ロケータ `prefix` の値を後から変更した場合、既存の `SRV6_MY_SIDS` エントリの整合性が失われる可能性があるが、
`SRv6Mgr` は既存 SID の自動再検証を行わない（DEL/SET を受け取るまで再チェックされない）。

**順序依存 (変更時)**: ロケータ `prefix` を変更する場合は、先に関連する `SRV6_MY_SIDS` エントリを DEL してから
ロケータを更新し、その後 SID を再 SET する順序が推奨される。

evidence: `managers_srv6.py:72-76`

### 4. ロケータ DEL 時の SID クリーンアップはユーザー責任

`locators_del_handler()` (managers_srv6.py:106-115) はロケータを削除する際、
FRR に `no locator <name>` を送信するが、対応する `SRV6_MY_SIDS` エントリの DEL は行わない。
`self.deps` / `self.directory` からロケータのエントリを削除するのみ。
ロケータが消えた後に SID が残存している場合、`SRV6_MY_SIDS` への更新イベントが来た際に
`path_exist()` チェックで再び `return False` される。

**順序依存 (DEL 時)**: ロケータを DEL する前に、対応する `SRV6_MY_SIDS` エントリを先に DEL すること。

evidence: `managers_srv6.py:106-115`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `SRV6_MY_LOCATORS` → `SRV6_MY_SIDS` | **先行推奨**（逆順は自動再試行で最終解決） | `on_deps_change` コールバックで自動再試行 |
| 2 | `SRV6_MY_LOCATORS` に `prefix` 必須 | **必須**（欠落時 KeyError crash） | `prefix` を常に含めて書き込む |
| 3 | ロケータ `prefix` 変更時は SID を先に DEL | **推奨**（変更後 SID の整合性は自動検証されない） | SID DEL → ロケータ更新 → SID 再 SET |
| 4 | ロケータ DEL 前に SID を先に DEL | **推奨**（残存 SID は次回 SET まで zombie 状態） | SID DEL → ロケータ DEL の順序 |
