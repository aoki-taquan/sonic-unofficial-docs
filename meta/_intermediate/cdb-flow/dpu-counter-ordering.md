# dpu-counter — ordering analysis (Phase B)

Target: `FLEX_COUNTER_TABLE|ENI` / `FLEX_COUNTER_TABLE|DASH_METER`
Consumer: `FlexCounterOrch` + `DashOrch` (sonic-swss orchagent)

## Key ordering dependencies

1. **warm-start delay gate** — `FlexCounterOrch` sets a 60-second timer on warm-start;
   `doTask()` returns immediately until `m_delayTimerExpired` is true.
   (flexcounterorch.cpp:127-136, 156-158)

2. **`allPortsReady()` gate** — `doTask()` returns if `gPortsOrch && !gPortsOrch->allPortsReady()`.
   ENI/DASH_METER SET messages queue in `m_toSync` until all ports are ready.
   (flexcounterorch.cpp:164-166)

3. **`FLEX_COUNTER_STATUS=enable` → `handleFCStatusUpdate(true)`** — immediate on SET receipt.
   Calls `DashOrch::handleFCStatusUpdate` / `handleMeterFCStatusUpdate` inline.
   (flexcounterorch.cpp:299-305, dashorch.h:128-129)

4. **ENI entries must pre-exist in `eni_entries_`** — `refreshStats()` iterates over
   `eni_entries_`; empty map = no FLEX_COUNTER_DB writes. Individual ENI additions
   call `addToFC()` which respects current `fc_status`.
   (dashcounter.h:48-58, dashorch.cpp:751-752)

5. **enable_counters.py timing** — writes `enable` 60-180 s after boot; may arrive
   before `allPortsReady()`, which is fine as `m_toSync` buffers the event.
   (enable_counters.py:40-44)

## Evidence files
- sonic-swss/orchagent/flexcounterorch.cpp
- sonic-swss/orchagent/dash/dashorch.cpp
- sonic-swss/orchagent/dash/dashorch.h
- sonic-swss/orchagent/dash/dashcounter.h
- sonic-buildimage/dockers/docker-orchagent/enable_counters.py
