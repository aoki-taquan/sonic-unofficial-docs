# FEATURE — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/feature.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `hostcfgd` の `FeatureHandler` + `containercfgd` + `coppmgrd` + `dhcprelayd` |
| 2. CFG→APPL 翻訳 | なし (APPL_DB 中継なし) |
| 3. APPL→SAI | なし (SAI 非経由 — Docker コンテナの起動/停止制御) |
| 4. タイミング+副作用 | CONFIG_DB の `FEATURE` エントリ変化を `hostcfgd` が検知後、`systemctl start/stop <feature>` を... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`hostcfgd` の `FeatureHandler` + `containercfgd` + `coppmgrd` + `dhcprelayd` が CONFIG_DB の `FEATURE` テーブルを購読する。

`FEATURE` の key はフィーチャー名 (例: `bgp`, `swss`, `lldp`)。`always_enabled` フィーチャーは disable 不可。

### 段階 2 — CFG→APPL 翻訳

なし (APPL_DB 中継なし)

### 段階 3 — APPL→SAI

なし (SAI 非経由 — Docker コンテナの起動/停止制御)

### 段階 4 — タイミングと副作用

**適用タイミング**: CONFIG_DB の `FEATURE` エントリ変化を `hostcfgd` が検知後、`systemctl start/stop <feature>` を呼び出す。コンテナ起動/停止は非同期で時間がかかる。

**副作用**: `state: disabled` でコンテナ停止 → そのコンテナが管理するすべての機能が停止。`auto_restart: disabled` でクラッシュ時に自動復旧しない。`set_owner: kube` に変更で Kubernetes 管理に移行。
<!-- /runtime-trace -->
```
