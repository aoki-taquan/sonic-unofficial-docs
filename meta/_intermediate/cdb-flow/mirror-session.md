# CONFIG_DB 例外条件分析: MIRROR_SESSION

## Consumer

- `orchagent` / `MirrorOrch` (`sonic-swss/orchagent/mirrororch.cpp`): `MIRROR_SESSION` テーブルを購読し SAI MIRROR_SESSION オブジェクトを管理。

## 例外条件

### 1. セッション名が不正形式 → YANG が拒否
- ソース: `sonic-mirror-session.yang` — `pattern '[a-zA-Z0-9]{1}([-a-zA-Z0-9_]{0,31})'` / 長さ 1-32。違反は YANG バリデーションで拒否。

### 2. src_ip と dst_ip のアドレスファミリ不一致 → YANG must + orchagent が task_invalid_entry
- ソース: `sonic-mirror-session.yang` — `must` 制約でファミリ一致を強制。`mirrororch.cpp` L495-499 でも address family チェックを行い `task_invalid_entry`。

### 3. dscp が 0-63 の範囲外 → YANG が拒否 / orchagent が例外キャッチ
- ソース: `sonic-mirror-session.yang` — `range "0..63"`. `mirrororch.cpp` L484-490 — `to_uint` 変換例外を catch して `task_invalid_entry`。

### 4. queue が ハードウェア最大 TC 数以上 → task_invalid_entry
- ソース: `mirrororch.cpp` L427-430 — `entry.queue >= m_maxNumTC` の場合 `"Failed to get valid queue"` をログし `task_invalid_entry`。

### 5. 参照する policer が存在しない → task_need_retry
- ソース: `mirrororch.cpp` L437-444 — `m_policerOrch->policerExists()` が false の場合 `task_need_retry`。policer が後から追加されると再処理される。

### 6. dst_port が不正 (非物理ポートまたは CPU 以外) → task_invalid_entry
- ソース: `mirrororch.cpp` L279 — `"Not supported port %s type %d"` をログ。SPAN セッションで dest_port が PORT_TYPE_PHYSICAL 以外の場合。

### 7. HW リソース不足 → task_failed
- ソース: `mirrororch.cpp` L501-505 — `isHwResourcesAvailable()` が false の場合 `"HW resources are not available"` をログし `task_failed`。

### 8. 削除時に他から参照中 → task_failed (参照カウンタ正)
- ソース: `mirrororch.cpp` L266 — `session.refCount > 0` の場合 `runtime_error` をスロー。ACL 等で参照されているセッションは削除できない。

### 9. type のデフォルト = "ERSPAN"
- ソース: `sonic-mirror-session.yang` — `default "ERSPAN"`。type を省略すると ERSPAN として処理される。SPAN セッションは明示的に `type = SPAN` を設定し `dst_port` を指定する必要がある。

### 10. gre_type のデフォルト = 0x88be
- ソース: `sonic-mirror-session.yang` — `default 0x88be`。ERSPAN over GRE では EtherType 0x88BE (ERSPAN) がデフォルトとして使用される。
