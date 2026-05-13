# policer 例外条件エビデンス

## 調査ソース

- `sonic-swss/orchagent/policerorch.cpp`
- `sonic-buildimage/src/sonic-yang-models/yang-models/` (sonic-policer.yang)

## 例外条件まとめ

### consumer (policerorch) 例外動作
- 重複 SET: `policerExists()` チェックで既存なら update パスへ分岐 (policerorch.cpp:72,150)
- DEL で存在しない policer: `Policer %s does not exist` → SWSS_LOG_WARN + `return false` (policerorch.cpp:88,105)
- 不明な attribute: `Unknown policer attribute %s specified` → SWSS_LOG_ERROR (policerorch.cpp:480)
- SAI policer create 失敗: `Failed to create policer %s, rv:%d` → SWSS_LOG_ERROR (policerorch.cpp:493,502)
- SAI attribute update 失敗: `Failed to update policer %s attribute, rv:%d` → SWSS_LOG_ERROR (policerorch.cpp:539)
- DEL 時 SAI remove 失敗: `Failed to remove policer %s, rv:%d` → SWSS_LOG_ERROR (policerorch.cpp:574)
- 参照カウントが残る policer の DEL: `Policer %s does not exists` (remove 試行時) → SWSS_LOG_ERROR (policerorch.cpp:558)

### STORM_CONTROL 経由
- 不明な storm_type: `Unknown storm_type %s` → SWSS_LOG_ERROR (policerorch.cpp:218,338)
- 不正インターフェース: `Unsupported / Invalid interface %s` → SWSS_LOG_ERROR (policerorch.cpp:134)
- ポート未発見: `Failed to apply storm-control %s to port %s. Port not found` → SWSS_LOG_ERROR (policerorch.cpp:140)
