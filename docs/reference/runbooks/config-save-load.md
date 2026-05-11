---
title: CONFIG_DB save / load が反映されない
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-utilities
    path: config/main.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
  - repo: sonic-net/sonic-utilities
    path: scripts/db_migrator.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db: []
  cli: [config save, config reload, config load_minigraph, sonic-cfggen]
  yang: []
---

# Runbook: CONFIG_DB save / load が反映されない

## 症状

- `config save -y` 後の再起動で設定が古いまま戻る
- `config reload -y` を打っても CLI が処理しない / 完了しても CONFIG_DB に乗らない
- `config load_minigraph` で minigraph.xml から再構成しても期待設定にならない

## 想定原因

1. **`/etc/sonic/config_db.json` の権限 / オーナーが root 以外で書き込み失敗**
2. **multi-asic 環境で host 側だけ save し、`config_db<N>.json` が更新されていない**
3. **YANG / sonic-cfggen 検証で reject されたが ユーザが気付いていない**
4. **db_migrator のバージョン不整合**: ファイル format version と SONiC ビルドの期待バージョン不一致
5. **minigraph.xml を編集したのに `load_minigraph` を打たず `reload` だけしている**

## 切り分け手順

### 1. ファイル時刻 / 権限

```bash
ls -la /etc/sonic/
sudo cat /etc/sonic/config_db.json | jq 'keys | length'
```

- 期待: `config save` 直後に mtime が更新、所有 root:root, 644
- 異常: 古いまま → save が disk まで届いていない

### 2. multi-asic 用 namespace 別ファイル

```bash
ls -la /etc/sonic/config_db*.json
sudo cat /etc/sonic/config_db0.json | jq 'keys | length' 2>/dev/null
```

- 期待: 全 asic 分のファイルが揃っている

### 3. save / reload エラー出力

```bash
sudo config save -y 2>&1 | tee /tmp/save.log
sudo config reload -y 2>&1 | tee /tmp/reload.log
```

- 期待: `Running command:` が無事 0 で終わる
- 異常: YANG validation エラー → 出力中の table / field を CONFIG_DB から修正

### 4. db_migrator のバージョン

```bash
sonic-db-cli CONFIG_DB hgetall "VERSIONS|DATABASE"
sudo cat /etc/sonic/config_db.json | jq '.VERSIONS'
```

- 期待: 両者一致、または migrator が起動時にアップグレード
- 異常: image とファイルで大きな差 → `sudo db_migrator.py -o migrate` で修復

### 5. minigraph と CONFIG_DB の整合

```bash
sudo sonic-cfggen -m /etc/sonic/minigraph.xml --print-data | jq 'keys | length'
diff <(sudo sonic-cfggen -m /etc/sonic/minigraph.xml --print-data | jq -S .) \
     <(sudo cat /etc/sonic/config_db.json | jq -S .)
```

## 対処方法

- ファイル権限修復: `sudo chown root:root /etc/sonic/config_db*.json && sudo chmod 644 /etc/sonic/config_db*.json`
- multi-asic で per-asic save:

```bash
sudo config save -y    # host
for ns in $(ip netns list | awk '{print $1}'); do
  sudo ip netns exec $ns config save -y
done
```

- minigraph 起点に戻す: `sudo config load_minigraph -y` （注意: 全 dynamic config 上書き）
- db_migrator 不整合: `sudo db_migrator.py -o migrate` 後 `sudo systemctl restart database`

## 関連ページ

- [../cli/show-running-config.md](../cli/show-running-config.md)
- [../cli/sonic-cfggen.md](../cli/sonic-cfggen.md)

## 引用元

[^1]: sonic-net/sonic-utilities @ 39732bceb — `config/main.py`, `scripts/db_migrator.py`
