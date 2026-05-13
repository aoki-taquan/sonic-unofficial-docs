# port-storm-control 例外条件エビデンス

## 調査ソース

- `sonic-swss/orchagent/policerorch.cpp`

## 例外条件まとめ

### consumer (policerorch) 例外動作
- 不正/非サポートインターフェース: `Unsupported / Invalid interface %s` → SWSS_LOG_ERROR (policerorch.cpp:134)
- ポート未発見: `Failed to apply storm-control %s to port %s. Port not found` → SWSS_LOG_ERROR (policerorch.cpp:140)
- 不明な storm_type (bcUnknown 等): `Unknown storm_type %s` → SWSS_LOG_ERROR (policerorch.cpp:218,338)
- 不明な storm control attribute: `Unknown storm control attribute %s specified` → SWSS_LOG_ERROR (policerorch.cpp:189)
- SAI policer create 失敗: `Failed to create storm control policer %s` → SWSS_LOG_ERROR (policerorch.cpp:197)
- SAI policer create 失敗 (rv): `Failed to create policer %s, rv:%d` → SWSS_LOG_ERROR (policerorch.cpp:230)
- SAI attribute update 失敗: `Failed to update policer %s attribute, rv:%d` → SWSS_LOG_ERROR (policerorch.cpp:261)
- SAI remove storm-control 失敗: `Failed to remove storm-control %s from port %s, rv:%d` → SWSS_LOG_ERROR (policerorch.cpp:281,347)
- SAI apply storm-control 失敗: `Failed to apply storm-control %s to port %s, rv:%d` → SWSS_LOG_ERROR (policerorch.cpp:294)
- SAI policer remove 失敗: `Failed to remove policer %s, rv:%d` → SWSS_LOG_ERROR (policerorch.cpp:302,359)
- 未設定 storm policer の参照: `Policer %s not configured` → SWSS_LOG_ERROR (policerorch.cpp:319)
