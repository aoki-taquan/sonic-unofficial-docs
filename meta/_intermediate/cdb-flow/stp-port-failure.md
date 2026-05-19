# STP_PORT — Phase D failure-behavior evidence

Source: `sonic-net/sonic-swss` cfgmgr/stpmgr.cpp @ 4305596156d70e9797e8a881b3d19b46de0bce0d

## calloc failure (processStpPortAttr)

stpmgr.cpp:537:
```cpp
msg = static_cast<STP_PORT_CONFIG_MSG *>(calloc(1, len));
if (!msg)
{
    SWSS_LOG_ERROR("calloc failed for interface %s", intfName.c_str());
    return;
}
```
If calloc fails, the function returns immediately. The IPC message is never sent to stpd.
The consumer entry is erased regardless (doStpPortTask erases after processStpPortAttr returns).
=> silent drop with SWSS_LOG_ERROR, no retry.

## stoi exception risk (path_cost / priority)

stpmgr.cpp:590-597:
```cpp
else if (field == "path_cost")
    msg->path_cost = stoi(value);
else if (field == "priority")
    msg->priority = stoi(value);
```
`stoi()` throws `std::invalid_argument` or `std::out_of_range` if value is non-numeric.
No try/catch in processStpPortAttr → uncaught C++ exception → stpmgrd process crash.

## stoi(field) bug for link_type (MST)

stpmgr.cpp:611-613:
```cpp
else if (field == "link_type" && l2ProtoEnabled == L2_MSTP)
    msg->link_type = static_cast<LinkType>(stoi(field.c_str()));
```
`stoi(field.c_str())` parses the literal string "link_type", not the value.
`stoi("link_type")` throws `std::invalid_argument` → stpmgrd process crash in MST mode
whenever a STP_PORT entry with link_type is written.

## sendMsgStpd failures

stpmgr.cpp:1231-1246:
- calloc of tx_msg fails → SWSS_LOG_ERROR + return -1 (message dropped, no retry)
- sendto fails (rc == -1) → SWSS_LOG_ERROR only, return rc; caller ignores return value

=> IPC send failures are logged but the consumer entry is erased; the SET is permanently lost.

## isLagEmpty silent drop

stpmgr.cpp:648-653 (doStpPortTask):
```cpp
if (isLagEmpty(key))
{
    it = consumer.m_toSync.erase(it);
    continue;
}
```
If PortChannel has no members, the entire entry is silently erased.
No error log; re-added when LAG member arrives via doLagMemUpdateTask.

## DEL with L2_NONE — silent discard

stpmgr.cpp:663-669:
```cpp
else  // DEL
{
    if (l2ProtoEnabled == L2_NONE)
    {
        it = consumer.m_toSync.erase(it);
        continue;
    }
}
```
DEL events received before STP mode is set are silently discarded (not deferred).
Unlike SET which iterates past, DEL is erased immediately.
