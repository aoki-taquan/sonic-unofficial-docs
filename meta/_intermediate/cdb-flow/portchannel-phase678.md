# PORTCHANNEL — Phase 6/7/8 derivation & handler-branching

対象ページ: `docs/reference/config-db/portchannel.md`
バッチ: cdb_batch_9

---

## Phase 6: 自動派生 (minigraph.py 代入)

<!-- derivation -->

### 1. `min_links` — PortChannel メンバ数から自動計算

**ソース**: `sonic-buildimage/src/sonic-config-engine/minigraph.py:969-971`

```python
pcs[pcintfname] = {
    'fallback': pcintf.find(str(QName(ns, "Fallback"))).text,
    'min_links': str(int(math.ceil(len(pcmbr_list) * 0.75))),
    'lacp_key': 'auto'
}
```

- `min_links` はメンバポート数の 75% を切り上げた値が自動代入される。ユーザーが XML に `<MinLinks>` タグを書かない限り手動指定は不要。
- メンバ数 4 → `min_links = 3`、メンバ数 2 → `min_links = 2` となる。

### 2. `fallback` — XML Fallback タグから代入

**ソース**: `sonic-buildimage/src/sonic-config-engine/minigraph.py:969`

```python
'fallback': pcintf.find(str(QName(ns, "Fallback"))).text
```

- `<Fallback>true</Fallback>` が存在する場合 `"true"` を代入。存在しない場合は fallback なしのコードパスへ（minigraph.py:971 の代替ブランチでは fallback キー自体が省略）。

### 3. `lacp_key` — 常時 `auto` を代入

**ソース**: `sonic-buildimage/src/sonic-config-engine/minigraph.py:969,971`

```python
'lacp_key': 'auto'
```

- 全 PortChannel に対して `lacp_key = auto` が固定代入される。minigraph 経由での手動 LACP key 設定は未サポート。

### 4. 不要エントリの除去 — 条件付き削除

**ソース**: `sonic-buildimage/src/sonic-config-engine/minigraph.py:2535`

```python
del pcs[pc_name]
```

- インターフェースが backend port に属する場合、対応する PortChannel エントリは削除される（BackEnd ASIC トポロジ対応）。

<!-- /derivation -->

---

## Phase 7: 条件付き登録 (add_manager)

<!-- derivation -->

該当なし。

`teammgrd` は `orchdaemon` の初期化時に `include_teamd == "y"` の場合のみ起動するが、これはビルド時定数であり、実行時の登録条件チェックは行われない。`teamd` Feature が `always_disabled` の場合 systemd ユニットが起動せず PORTCHANNEL ハンドラも動作しない点に注意。

<!-- /derivation -->

---

## Phase 8: manager メソッド内 early return / dispatch

<!-- handler-branching -->

### teammgrd の doTask() 分岐

**ソース**: `sonic-swss/cfgmgr/teammgrd.cpp`

1. **op == "SET"**: `fallback` が `"true"` の場合のみ `teamd` の `fallback_mode` を有効化。`min_links` は `teamd` JSON config に渡される。`admin_status` が未設定の場合は early return せずデフォルト動作継続。
2. **op == "DEL"**: `teamd` プロセスに stop シグナルを送り、对応するカーネル bond インターフェースを削除。
3. `lacp_key == "auto"` 以外の場合（将来拡張）: 現時点では分岐なし。

<!-- /handler-branching -->
