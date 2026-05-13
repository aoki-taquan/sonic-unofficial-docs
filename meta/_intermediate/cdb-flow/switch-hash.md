# SWITCH_HASH 例外条件調査メモ

ソース: `sonic-swss/orchagent/switchorch.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## 抽出した例外条件

1. **ASIC capability 未サポート** — `validateSwitchEcmpHashCap` / `validateSwitchLagHashCap` / `validateSwitchEcmpHashAlgorithmCap` / `validateSwitchLagHashAlgorithmCap` がいずれも false を返すと、
   `"Failed to validate switch ECMP/LAG hash: capability is not supported"` を LOG_ERROR し `return false`。
   SET コマンドを受け付けず CONFIG_DB のエントリが無効化される。

2. **SAI set 失敗** — SAI API 呼び出し失敗時は `"Failed to set switch ECMP/LAG hash in SAI"` / `"Failed to set switch ECMP/LAG hash algorithm in SAI"` を LOG_ERROR して `return false`。

3. **DEL 操作不可** — hash/hash_algorithm 設定を DEL で削除しようとすると
   `"Failed to remove switch ECMP/LAG hash configuration: operation is not supported"` を LOG_ERROR して `return false`。
   ハッシュ設定は一度入れたら実行時に削除できない。

4. **ASIC/CONFIG_DB 乖離** — SET 時に ASIC 側と CONFIG_DB 側で値が食い違っていると
   `"Failed to set switch hash: ASIC and CONFIG DB are diverged"` を LOG_ERROR。
   DEL 時も同様 `"Failed to remove switch hash: operation is not supported: ASIC and CONFIG DB are diverged"`。

5. **空キー** — key が空文字列だと `"Failed to parse switch hash key: empty string"` を LOG_ERROR してスキップ。
