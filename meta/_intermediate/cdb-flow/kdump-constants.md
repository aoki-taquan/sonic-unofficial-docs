# KDUMP ハードコード定数 (Phase E)

ソース: `sonic-utilities/scripts/sonic-kdump-config`、`sonic-utilities/config/kdump.py`

## 抽出定数一覧

| 定数名 | 値 | 場所 | 説明 |
|--------|----|------|------|
| `DEFAULT_MEMORY` | `"0M-2G:256M,2G-4G:320M,4G-8G:384M,8G-:448M"` | `sonic-kdump-config` `get_kdump_memory()` L398 | crashkernel メモリのフォールバック値。DB 未設定時に使用される |
| `DEFAULT_NUM_DUMPS` | `3` | `sonic-kdump-config` `get_kdump_num_dumps()` L416 | 保持 coredump 数のフォールバック値。DB 未設定時に使用される |
| `DEFAULT_ENABLED` | `False` | `sonic-kdump-config` `get_kdump_administrative_mode()` L365 | enabled フィールドのデフォルト。kdump は初期状態で無効 |
| `DEFAULT_REMOTE` | `False` | `sonic-kdump-config` `get_kdump_remote()` L275 | remote SSH ダンプのデフォルト。初期状態で無効 |
| `KDUMP_CFG_PATH` | `"/etc/default/kdump-tools"` | `sonic-kdump-config` L37 | hostcfgd が書き換える設定ファイルパス |
| `KDUMP_MEM_FILE` | `"/sys/kernel/kexec_crash_size"` | `sonic-kdump-config` L38 | 現在 allocate 済み crash kernel メモリサイズの読み取りパス |
| `SSH_STRING_RE` | `r'^[a-zA-Z0-9][a-zA-Z0-9._%+-]*@([a-zA-Z0-9.-]+\|[0-9]{1,3}(\.[0-9]{1,3}){3})\Z'` | `sonic-kdump-config` L567 | ssh_string の入力バリデーション正規表現 |
| `SSH_PATH_RE` | `r'^(/[a-zA-Z0-9._-]+)+\Z'` | `sonic-kdump-config` L568 | ssh_path の入力バリデーション正規表現 |
| `NUM_DUMPS_RANGE` | `1..9` | `sonic-kdump.yang` L51 | YANG 定義の num_dumps 有効範囲 (uint8) |

## memory フォールバック書式

```
0M-2G:256M,2G-4G:320M,4G-8G:384M,8G-:448M
```

解釈:
- RAM 0〜2 GB: 256 MB を crash kernel に確保
- RAM 2〜4 GB: 320 MB を crash kernel に確保
- RAM 4〜8 GB: 384 MB を crash kernel に確保
- RAM 8 GB 超: 448 MB を crash kernel に確保

## enabled / remote の enum 値

| フィールド | 有効値 | DB 格納形式 |
|-----------|--------|------------|
| `enabled` | `true` / `false` | 文字列 `"true"` / `"false"` |
| `remote`  | `true` / `false` | 文字列 `"true"` / `"false"` |

判定: `config_data.get('enabled').lower() == 'true'`（大文字小文字を無視）

## 注記

- `get_kdump_memory()` と `get_kdump_num_dumps()` はフォールバック値をコードにハードコードしており、DB や設定ファイルに書かれていない場合に使われる
- YANG の `num_dumps` range `1..9` は CLI / NETCONF 経由時のみ適用。redis 直書きではバリデーションなし
- `ssh_string` / `ssh_path` の正規表現バリデーションは `sonic-kdump-config` スクリプト側で実施。CLI (`config/kdump.py`) は独自バリデーションロジックを持つ（`is_valid_ssh_key()`）
