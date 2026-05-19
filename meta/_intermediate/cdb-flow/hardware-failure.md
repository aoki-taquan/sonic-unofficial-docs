# HARDWARE — Phase D 失敗挙動スキャンノート

対象テーブル: `CONFIG_DB HARDWARE|ACCESS_LIST`
Consumer: **なし（community sonic-swss/orchagent は未購読）**
スキャン範囲: sonic-swss orchagent 全ソース（grep -rn 'COUNTER_MODE|LOOKUP_MODE|TCAM_SHARING|HARDWARE' → 0 件）

---

## 結論: community コードパスでの失敗連鎖なし（dead consumer）

`HARDWARE` テーブルは community sonic-swss/orchagent が**一切購読しない**ため、
書込みの成否が ACL 設定失敗に連鎖することはない。

---

## 失敗パス調査

### orchagent 側の受信処理

```
grep -rn 'HARDWARE\|ACCESS_LIST\|COUNTER_MODE\|LOOKUP_MODE\|TCAM_SHARING' sonic-swss/orchagent/
→ 0 件（HARDWARE テーブルを購読する Orch クラスは存在しない）
```

orchagent に subscribe 処理がないため:
- SET 成功後の SAI 設定失敗: 発生しない
- SAI rollback: 発生しない
- retry ループ: 発生しない
- STATE_DB への失敗ステータス書込み: 発生しない

### Redis 書込みエラー

Redis への `HSET` 自体が失敗する（メモリ不足、接続断等）シナリオはあるが、
これは `HARDWARE` テーブル固有の問題ではなく Redis 共通の問題。
consumer がいないため ASIC への二次影響は生じない。

### YANG CVL 検証

`sonic-yang-models` に `HARDWARE` テーブルの YANG モジュールが存在しないため、
CVL (Config Validation Layer) による不正値の書込みブロックは機能しない。

```
ls sonic-buildimage/src/sonic-yang-models/yang-models/ | grep -i hardware
→ 0 件
```

不正値はそのまま CONFIG_DB に書き込まれる。consumer がいないため実害なし。

### leaf-list エンコーディング

`TCAM_SHARING` フィールドは Redis leaf-list 規約（`@` サフィックス）でエンコードされるが、
不正エンコーディングで書き込んでも community コードパスでは無影響。

---

## ベンダー実装（対象外）

Dell 等のベンダー向け `sonic-mgmt-common` translib/transformer では
`HARDWARE|ACCESS_LIST` を READ/WRITE する可能性があり、
そちらのスタックでは独自の失敗パスが存在しうる。
当該コードは community リポジトリ外のため本調査の対象外。
