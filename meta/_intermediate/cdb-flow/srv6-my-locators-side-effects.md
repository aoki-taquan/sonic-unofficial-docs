# SRV6_MY_LOCATORS — Phase F 副作用スキャンノート

対象テーブル: `SRV6_MY_LOCATORS`
Consumer: `bgpcfgd` (`SRv6Mgr`)、`frrcfgd` (`bgp_table_handler_common`)
スキャン範囲: `managers_srv6.py` 全行、`frrcfgd/frrcfgd.py:2732-2742`

---

## 検出した副作用

### 1. FRR zebra への locator コマンド送信 (bgpcfgd 経由)

`locators_set_handler()` (`managers_srv6.py:41-53`) は `SRV6_MY_LOCATORS` SET を受信すると
`cfg_mgr.push_list()` を呼び出して FRR に以下のコマンドを送信する:

```
segment-routing srv6 locators locator <name> prefix <p>/<len> block-len <b> node-len <n> func-bits <f> behavior usid
```

- `prefix` は `block_len + node_len` のビット数で自動拡張される (`managers_srv6.py:142`)
- `behavior usid` はハードコードされ、CONFIG_DB フィールドでは変更不可

DEL 時 (`locators_del_handler():108`) は `no locator <name>` を FRR に送信。

### 2. in-memory directory への登録 → pending SID の自動再試行トリガー

`locators_set_handler()` は FRR コマンド送信後、`self.directory.put()` でロケータオブジェクトを bgpcfgd プロセス内の共有ディレクトリに格納する (`managers_srv6.py:53`)。
このキャッシュが存在することで、後続の `sids_set_handler()` が `directory.path_exist()` チェックを通過できる。

**ロケータ SET の副作用として `SRV6_MY_SIDS` 処理が再トリガーされる**:
`sids_set_handler()` でロケータ不在により pending された SID エントリは、
ロケータ SET によって `on_deps_change` コールバックが発火し、SID の FRR 通知が自動再試行される (`managers_srv6.py:64-68`)。

DEL 時 (`locators_del_handler():111-115`) は directory からロケータを削除し、deps 購読も解除する。
**DEL の副作用として**: 以後 SID の SET を受けても `path_exist()` が false を返すようになり、全 SID 通知が保留状態に移行する。

### 3. FRR zebra への locator コマンド送信 (frrcfgd 経由)

`frrcfgd.py` の `bgp_table_handler_common()` もまた `SRV6_MY_LOCATORS` を購読し (`frrcfgd.py:2335, 121`)、
`SRV6_MY_LOCATORS: ['zebra']` という設定で zebra デーモンに同等のロケータコマンドを送信する (`frrcfgd.py:2732-2742`)。

```python
cmd = ['vtysh', '-c', 'configure terminal',
       '-c', 'segment-routing', '-c', 'srv6', '-c', 'locators',
       '-c', 'locator {}'.format(locator_name),
       '-c', 'prefix {} block-len {} node-len {} func-bits {}'.format(...)]
```

**bgpcfgd と frrcfgd の両方が独立して同じ FRR コマンドを発行する**。
二重適用になるが FRR の設定は冪等なため実害はない。DEL ハンドラは frrcfgd 側に実装なし（SET のみ）。

### 4. Srv6Orch の CONFIG_DB 直接参照への影響

`Srv6Orch` は `SRV6_MY_LOCATORS` を直接 DB GET するため、`SRV6_MY_LOCATORS` エントリの存在・内容が
APPL_DB の MySID 処理フローに間接的に影響する。
ロケータが DEL されると、次回 APPL_DB MySID SET 時に `getLocatorCfgFromDb()` が失敗し SAI 転送がスキップされる。

---

## 副作用サマリ

| # | トリガー | 副作用 | 対象 |
|---|---------|--------|------|
| 1 | `SRV6_MY_LOCATORS` SET | FRR に `locator <name>` コマンドを送信 | FRR zebra (bgpcfgd 経由) |
| 2a | `SRV6_MY_LOCATORS` SET | pending `SRV6_MY_SIDS` が自動再試行される | bgpcfgd `on_deps_change` |
| 2b | `SRV6_MY_LOCATORS` DEL | 以後の `SRV6_MY_SIDS` SET が全て保留に移行 | bgpcfgd directory |
| 3 | `SRV6_MY_LOCATORS` SET | FRR に同等コマンドを重複送信 | FRR zebra (frrcfgd 経由) |
| 4 | `SRV6_MY_LOCATORS` DEL | Srv6Orch の MySID 処理が SAI 転送失敗するようになる | Srv6Orch / SAI |
