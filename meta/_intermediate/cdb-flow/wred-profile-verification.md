# wred-profile Phase 8 scan (no existing derivation block to re-verify)

## Phase 8: Handler method scan

### Scanned files
- `sonic-swss/orchagent/qosorch.cpp` — key: `WredMapHandler::convertFieldValuesToAttributes()` (L585), `addQosItem()` (L784), `modifyQosItem()` (L768)

### Hits

1. **`WredMapHandler::convertFieldValuesToAttributes()` L634-751**: Giant if-elif chain dispatching on field name value:
   - `fvField == yellow_max_threshold_field_name` → `appendThresholdToAttributeList(SAI_WRED_ATTR_YELLOW_MAX_THRESHOLD, ...)` — 2-phase deferred logic
   - `fvField == green_max_threshold_field_name` → `SAI_WRED_ATTR_GREEN_MAX_THRESHOLD`
   - `fvField == red_max_threshold_field_name` → `SAI_WRED_ATTR_RED_MAX_THRESHOLD`
   - `fvField == green_drop_probability_field_name` → `SAI_WRED_ATTR_GREEN_DROP_PROBABILITY`
   - `fvField == yellow_drop_probability_field_name` → `SAI_WRED_ATTR_YELLOW_DROP_PROBABILITY`
   - `fvField == red_drop_probability_field_name` → `SAI_WRED_ATTR_RED_DROP_PROBABILITY`
   - `fvField == wred_green_enable_field_name` → `SAI_WRED_ATTR_GREEN_ENABLE`; `convertBool()` fail → `return false`
   - `fvField == wred_yellow_enable_field_name` → `SAI_WRED_ATTR_YELLOW_ENABLE`; fail → `return false`
   - `fvField == wred_red_enable_field_name` → `SAI_WRED_ATTR_RED_ENABLE`; fail → `return false`
   - `fvField == ecn_field_name` → `ecn_map.at(fvValue(*i))` → `SAI_WRED_ATTR_ECN_MARK_MODE` — unknown ecn value throws `std::out_of_range`

2. **`WredMapHandler::appendThresholdToAttributeList()` L561-583**:
   Deferred logic: `if (storedProfile.yellow_min_threshold > threshold)` (or max<threshold) → deferred list, preventing SAI min>max ordering violation

3. **`WredMapHandler::addQosItem()` L792-855**:
   - `if (attr.id == SAI_WRED_ATTR_GREEN_ENABLE && attr.value.booldata)` → `wred_enable_set |= GREEN_WRED_ENABLED`
   - Similarly for YELLOW and RED
   - If `wred_enable_set & GREEN_WRED_ENABLED` but `drop_prob_set` doesn't have green → auto-add `SAI_WRED_ATTR_GREEN_DROP_PROBABILITY = 100`

### Verdict: 3 major handler patterns. The `ecn` dispatch and `wred_*_enable` boolean dispatch are the key branching points. No existing derivation block to re-verify.
