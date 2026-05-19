# kubernetes-master: Phase H プラットフォーム差 調査ノート

調査日: 2026-05-19
対象: `sonic-buildimage/src/sonic-ctrmgrd/ctrmgr/ctrmgrd.py`

## 結論サマリ

`KUBERNETES_MASTER` テーブルの処理コア（`ctrmgrd`）は **全プラットフォームで動作ロジックが同一**。
ただし以下の 2 点でプラットフォーム依存性が存在する:

1. **ビルド時フラグ `INCLUDE_KUBERNETES_MASTER`**: デフォルト `n`。`y` にセットした場合のみ kubelet / kubeadm パッケージがイメージに組み込まれる。
2. **`worker.sonic/platform` ラベル**: join 成功後に `device_info.get_platform()` を呼び、取得値を `KUBE_LABELS|SET.worker.sonic/platform` に書く。値はプラットフォームごとに異なる文字列になるが、処理フロー自体は変わらない。

## ビルド時フラグ

`rules/config:260`:
```
INCLUDE_KUBERNETES_MASTER ?= n
```

`build_debian.sh:271` および `sonic_debian_extension.j2:974`:
```bash
{% if include_kubernetes_master == "y" %}
...kubernetes パッケージインストール・サービス有効化...
{% endif %}
```

`n`（デフォルト）のビルドイメージでは kubelet / kubeadm がインストールされず、`ctrmgrd` が `kube_join_master()` を実行しても失敗する。CI ビルド (`azure-pipelines-build.yml:148`) では VS イメージのみ `INCLUDE_KUBERNETES_MASTER=y` でビルドしている。

## multi-asic / namespace 非依存

`ctrmgrd.py` の全行を `namespace|asic|multi_asic|is_multi_npu|chassis|per_asic|NUM_ASIC` で grep → **ヒット 0 件**。

ctrmgrd は:
- host namespace 固定の単一インスタンスで動作
- `CONFIG_DB`（DB index 4）/ `STATE_DB`（DB index 6）を直接参照
- multi-asic 環境でも asic0..N の各 Redis への書き込み経路なし
- VOQ chassis / disaggregated chassis 環境でも動作ロジック変化なし

## platform 文字列参照 (ctrmgrd.py:304-305)

```python
platform = device_info.get_platform()
labels["worker.sonic/platform"] = platform if platform is not None else ""
```

取得値はラベルとして Kubernetes API Server に送信されるだけで、ローカルの動作フロー（join / reset / retry）に影響しない。`get_platform()` が `None` を返した場合（VS 環境等）は空文字列 `""` に置換される。

## hwsku 参照 (ctrmgrd.py:302)

```python
labels["hwsku"] = device_info.get_hwsku() if not UNIT_TESTING else "mock"
```

こちらも K8s ラベルとして送信されるだけで処理ロジックへの影響なし。UNIT_TESTING モード時は `"mock"` に固定される。

## evidence

- `sonic-buildimage/src/sonic-ctrmgrd/ctrmgr/ctrmgrd.py:290-307` (set_node_labels)
- `sonic-buildimage/rules/config:258-260` (INCLUDE_KUBERNETES_MASTER)
- `sonic-buildimage/files/build_templates/sonic_debian_extension.j2:974-1011`
- `sonic-buildimage/.azure-pipelines/azure-pipelines-build.yml:148`
- `sonic-buildimage/src/sonic-ctrmgrd/ctrmgr/ctrmgrd.service` (host namespace, single instance)
