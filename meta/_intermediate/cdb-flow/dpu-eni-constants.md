# dpu-eni constants (Phase E)

source: sonic-swss/orchagent/dash/dashenifwdorch.h, dashenifwdinfo.cpp

## Summary

DashEniFwdOrch / DpuRegistry / EniAclRule manage all CONFIG_DB field names,
ACL table names, priorities, and MAC format as code-level constants.
No YANG schema exists; these constants are the canonical schema reference.

## Table name constants (dashenifwdorch.h:63-66)

| constant | value |
|----------|-------|
| DashEniFwd::DPU_TABLE | "DPU" |
| DashEniFwd::REMOTE_DPU_TABLE | "REMOTE_DPU" |
| DashEniFwd::VDPU_TABLE | "VDPU" |
| DashEniFwd::VIP_TABLE | "VIP_TABLE" |

## ACL table/type name constants (dashenifwdorch.h:69-70)

| constant | value |
|----------|-------|
| DashEniFwd::TABLE_TYPE | "ENI_REDIRECT" |
| DashEniFwd::TABLE | "ENI" |

## Field name constants (dashenifwdorch.h:71-80)

| constant | value | table |
|----------|-------|-------|
| DashEniFwd::VDPU_IDS | "vdpu_ids" | DASH_ENI_FORWARD_TABLE |
| DashEniFwd::PRIMARY | "primary_vdpu" | DASH_ENI_FORWARD_TABLE |
| DashEniFwd::STATE | "state" | DPU |
| DashEniFwd::PA_V4 | "pa_ipv4" | DPU / REMOTE_DPU |
| DashEniFwd::PA_V6 | "pa_ipv6" | DPU / REMOTE_DPU |
| DashEniFwd::NPU_V4 | "npu_ipv4" | REMOTE_DPU |
| DashEniFwd::NPU_V6 | "npu_ipv6" | REMOTE_DPU |
| DashEniFwd::DPU_IDS | "main_dpu_ids" | VDPU |

## ACL rule priority constants (dashenifwdinfo.cpp:6)

EniAclRule::BASE_PRIORITY = 9996
rule_type_t::NO_TUNNEL_TERM = 0 → priority 9996
rule_type_t::TUNNEL_TERM = 1 → priority 9997

## ACL table type / table hardcoded values (dashenifwdorch.cpp:605-643)

ACL_TABLE_TYPE_TABLE ENI_REDIRECT:
- matches: "DST_IP,INNER_DST_MAC,TUNNEL_TERM"
- actions: "REDIRECT_ACTION"
- bind_point_types: "PORT,PORTCHANNEL"

ACL_TABLE_TABLE ENI:
- policy_desc: "Contains Rule for DASH ENI Based Forwarding"
- type: "ENI_REDIRECT"
- stage: "INGRESS" (STAGE_INGRESS constant, not configurable)
- ports: dynamically listed PHY/LAG ports excluding PORT_ROLE_DPC ("Dpc")

## MAC key format (dashenifwdinfo.cpp:381-391)

EniInfo::formatMac() removes colons and uppercases: "f4:93:9f:ef:c4:7e" → "F4939FEFC47E"
Used in ACL rule key: "ENI:<vnet>_<MAC>"

## PORT_ROLE_DPC exclusion

findInternalPorts() (dashenifwdorch.cpp:414-431) excludes ports with role == "Dpc"
from ACL bind points. SmartSwitch NPU-DPU internal links use this role.
