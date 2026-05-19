# ipv6-link-local — Phase H platform 調査ノート

調査日: 2026-05-19
対象ソース: sonic-swss/cfgmgr/intfmgr.cpp, intfmgrd.cpp, neighsyncd/neighsync.cpp;
           sonic-utilities/config/main.py L9490-9570, show/main.py L1586-1629;
           sonic-utilities/tests/multi_asic_ipv6_link_local_test.py

## 結論サマリ

`ipv6_use_link_local_only` フィールドのスキーマ・処理ロジック自体は**全プラットフォームで共通**。
プラットフォーム差は (1) multi-ASIC 環境でのネームスペース分離、(2) VOQ inband interface の特殊パス、の 2 点に局所化される。

## multi-ASIC / ネームスペース差異

### CLI の namespace オプション

`config ipv6` グループは `multi_asic.is_multi_asic()` の結果で `-n/--namespace` オプションを必須化する
(config/main.py:9492)。single-ASIC では `namespace=None` → `DEFAULT_NAMESPACE` にフォールバック。

```python
# config/main.py:9491-9501
@config.group()
@click.option('-n', '--namespace', help='Namespace name',
              required=True if multi_asic.is_multi_asic() else False,
              type=click.Choice(multi_asic.get_namespace_list()))
@click.pass_context
def ipv6(ctx, namespace):
    if namespace is None:
        namespace = DEFAULT_NAMESPACE
    config_db = multi_asic.connect_config_db_for_ns(namespace)
```

`config interface ipv6` の個別インタフェースコマンドは `get_port_namespace(interface_name)` でポートが属する
ネームスペースを自動特定し、そのネームスペースの CONFIG_DB に書き込む (config/main.py:528-564)。

### `show ipv6 link-local-mode` のネームスペース対応

`@multi_asic_util.multi_asic_click_option_namespace` デコレータで `-n/--namespace` オプションを付与し、
`masic.get_ns_list_based_on_options()` で対象ネームスペースを列挙する (show/main.py:1595-1596)。

- `-n asic0` 指定 → asic0 の CONFIG_DB のみ参照 → asic0 所属ポートのみ表示
- 指定なし (single-ASIC) or 全ネームスペース → 全 asic の CONFIG_DB を順次参照して結合表示

multi_asic_ipv6_link_local_test.py の L39-45 でこの挙動が明示的にテストされている:
- `-n asic0` で Ethernet16 表示, Ethernet64 (asic1) は非表示
- `-n` なしで Ethernet16, Ethernet64 双方表示

### `config ipv6 enable/disable link-local` の全インタフェース一括操作

`enable_link_local()`/`disable_link_local()` は呼び出し時の `config_db`（ネームスペース指定済み）の
INTERFACE/PORTCHANNEL_INTERFACE/VLAN_INTERFACE のみを対象とする。multi-ASIC 環境では「全 ASIC
一括有効化」は CLI レイヤで複数回 namespace 指定して実行する必要がある; 単一 `config ipv6 enable link-local`
は指定ネームスペース内のポートのみを変更する (test L47-65 で `asic0` 変更が `asic1` に波及しないことを確認)。

## VOQ Inband Interface のバイパス

`intfmgr.cpp:1195-1203` において `CFG_VOQ_INBAND_INTERFACE_TABLE_NAME` (= `"VOQ_INBAND_INTERFACE"`) からの
SET イベントは `doIntfGeneralTask()` を経由せず、フィールド解析なしで直接 APP_DB に relay される:

```cpp
if((table_name == CFG_VOQ_INBAND_INTERFACE_TABLE_NAME) && (op == SET_COMMAND))
{
    //No further processing needed. Just relay to orchagent
    m_appIntfTableProducer.set(keys[0], data);
    m_stateIntfTable.hset(keys[0], "vrf", "");
    it = consumer.m_toSync.erase(it);
    continue;
}
```

`VOQ_INBAND_INTERFACE` は VOQ chassis (Cisco 8000 等) の inband 管理インタフェースに使用されるテーブル。
このテーブルに `ipv6_use_link_local_only` フィールドを書いても `m_ipv6LinkLocalModeList` への登録・
`delIpv6LinkLocalNeigh()` は実行されない。VOQ chassis 固有の制約。

## intfmgrd のインスタンス数

`intfmgrd.cpp` は単一の `IntfMgr` インスタンスを起動する。multi-ASIC SONiC では各ネームスペース (asic0, asic1, …)
で独立したコンテナ (swss) が走り、各コンテナが自 namespace の CONFIG_DB / APPL_DB / STATE_DB を接続する。
`intfmgrd.cpp` 自体に ASIC 番号分岐や `multi_asic` ライブラリへの依存は一切なく、
コンテナのネームスペース分離で multi-ASIC 対応を実現する。

## platform vendor 固有コードの有無

- `intfmgr.cpp`, `neighsync.cpp` において `platform`/`vendor`/`chassis`/`asic[0-9]`/`is_multi_npu` をキーワードに
  grep した結果 0 ヒット（`using namespace std;` / `using namespace swss;` を除く）
- `sonic-buildimage/device/` 配下の vendor/SKU ディレクトリに `ipv6_use_link_local_only` を含むファイルは存在しない
- YANG スキーマ (`sonic-interface.yang`, `sonic-portchannel.yang`, `sonic-vlan.yang`) の platform 条件分岐なし
