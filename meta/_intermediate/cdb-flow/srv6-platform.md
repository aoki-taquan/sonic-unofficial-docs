# Phase H: Platform / プラットフォーム差分 — SRv6 Orch (srv6-orch.md)

## 調査対象ファイル

- `sonic-swss/orchagent/srv6orch.cpp` (rev 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/srv6orch.h`
- `sonic-sairedis/syncd/VendorSai.cpp`
- `sonic-sairedis/vslib/vpp/SwitchVppSRv6.cpp`
- `SONiC/doc/srv6/srv6_hld.md`
- `SONiC/doc/srv6/SRv6_uSID.md`
- `SONiC/doc/srv6/srv6_sid_l3adj.md`
- `SONiC/doc/flow_counters/routes_flow_counters.md`

## VOQ Chassis

srv6orch.cpp に VOQ Chassis 固有の分岐コードは存在しない。
SRV6_MY_SID_TABLE / SRV6_SID_LIST_TABLE / PIC_CONTEXT_TABLE の処理ロジックは
スタンドアロン・VOQ Chassis で共通。

ただし VOQ Chassis では system port / inband channel の存在により、
NeighOrch が返す nexthop オブジェクトの実体が NPU 間の system port 経由になる。
`end.x` / `ua` / `uA` 等の adj フィールドが指す neighbor の解決経路が
通常シャーシと異なるため、NeighOrch への pending がより長くなる可能性がある。
srv6orch 自体はこの差を意識せず NeighOrch の通知に委任する。

## SmartSwitch DPU

srv6orch.cpp に `switch_type == "dpu"` 等の DPU 固有分岐は存在しない。
SmartSwitch の DPU は独立した SONiC インスタンスとして動作し、
SRv6 サポートは DPU 側の SAI/ASIC 実装に依存する。
DPU 向け SAI が `SAI_OBJECT_TYPE_MY_SID_ENTRY` / `SAI_OBJECT_TYPE_SRV6_SIDLIST` を
実装していない場合、MySID / SID リスト操作は SAI エラーで失敗する。

## SAI 実装依存 (Vendor 差)

### MySID カウンタ非対応 ASIC

`queryMySidCountersCapability()` (`srv6orch.cpp:144-155`) により起動時に
`sai_query_attribute_capability(SAI_OBJECT_TYPE_MY_SID_ENTRY, SAI_MY_SID_ENTRY_ATTR_COUNTER_ID)`
を実行する。`set_implemented && create_implemented` が false の場合、
`m_mysid_counters_supported = false` となり FlexCounter 初期化はスキップされる。

該当 ASIC では:
- `show srv6 mysid counters` で常にゼロ表示
- `counterpoll srv6 enable` を実行しても WARN ログのみ出力・効果なし
- ログ: `"SRv6 counters are not supported on this platform"` (srv6orch.cpp:125)
- ログ: `"Ignoring SRv6 counters state change as they are not supported on this platform"` (srv6orch.cpp:257)

現時点のコードでは Mellanox Spectrum / Broadcom 等の具体的 ASIC 名を判別するロジックはなく、
すべて SAI capability query の結果で動的に判断する。

### SRv6 SID List (Encap/Insert 系) の ASIC 非対応

`sidlist_type_map`（srv6orch.cpp:73-79）で `insert` / `insert.red` / `encaps` / `encaps.red`
の 4 種を SAI SRV6_SIDLIST_TYPE にマップする。
ASIC が特定タイプ（例: `insert` / `insert.red`）を未実装の場合は SAI からエラーが返り、
`Failed to create srv6 sidlist object` ログが出力される。
SONiC orch レイヤには type 別の capability チェックは存在しない（SAI エラーが実質的な検出手段）。

### VPP ソフトウェアスイッチ

`sonic-sairedis/vslib/vpp/SwitchVppSRv6.cpp` で VPP 向け MySID / SID リスト変換が実装されている。
VPP は最大 SID リストサイズ 16 の制約を持つ (`SwitchVppSRv6.cpp:235`: `VPP max sid list size is 16`)。
SAI ハードウェアでこの制約はないが VPP ターゲットでは 17 個以上の SID を含む SID リストは
SAI エラーとなる。

## Micro-SID (uSID / uN / uA / uDT / uDX) の SAI 対応状況

uSID behaviors (`un` / `ua` / `udt4` / `udt6` / `udt46` / `udx4` / `udx6`) は
SRv6_uSID.md (2022-07 追加) で定義され、SAI API 側は当時から定義済み。
`SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_UN` / `_UA` 等は SAI 仕様上は共通だが、
実 ASIC での実装は各ベンダーの SAI SDK バージョンに依存する。
SAI capability query は `SAI_MY_SID_ENTRY_ATTR_COUNTER_ID` のみを確認し、
各 endpoint behavior 個別の対応チェックは行わない。

## ECMP adj の未対応

`srv6orch.cpp:1516-1519` にて、`adj` フィールドがカンマ区切り複数アドレスの場合
`"ECMP adjacency not yet supported"` エラーで処理を拒否する。
ハードウェア能力に関わらず、orchagent の実装制限として単一 adj しか受け付けない。

## まとめ: プラットフォーム差一覧

| 機能 | スタンドアロン (標準 ASIC) | VOQ Chassis | SmartSwitch DPU | VPP ソフトスイッチ |
|------|--------------------------|-------------|-----------------|------------------|
| MySID Counter | SAI 依存（capability query） | 共通 | SAI 実装依存 | 非対応 |
| SID List (encaps/insert) | ASIC SAI 依存 | 共通 | SAI 実装依存 | 最大 16 SID |
| uSID (uN/uA/uDT/uDX) | SAI SDK 依存 | 共通 | SAI 実装依存 | VPP 実装依存 |
| ECMP adj | 未対応（orchagent 制限） | 未対応 | 未対応 | 未対応 |
| VOQ nexthop 解決 | N/A | NeighOrch 委任（遅延増大の可能性） | N/A | N/A |
