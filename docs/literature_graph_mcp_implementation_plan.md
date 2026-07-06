# LiteratureGraph MCP 実装計画

## 1. 目的

LiteratureGraph MCP は、文献PDFフォルダを読み取り、論文内容を構造化して Knowledge Graph 化し、MCP 経由で AI アシスタントに渡すための OSS である。

目的は、単なる PDF RAG ではなく、文献同士の関係、手法、データセット、主張、限界、根拠を構造化し、関連研究整理や研究ギャップ抽出を支援することである。

---

## 2. 基本コンセプト

CodeGraphContext がコードを Graph 化するのに対し、本ツールでは文献を Graph 化する。

```text
CodeGraphContext:
  Code file
    → Function / Class / Module
    → CALLS / IMPORTS / INHERITS
    → Graph DB
    → MCP

LiteratureGraph MCP:
  Paper PDF
    → Paper / Method / Dataset / Claim / Limitation / Evidence
    → USES / CLAIMS / HAS_LIMITATION / SUPPORTED_BY / CITES
    → Graph DB
    → MCP
```

---

## 3. MVP の対象範囲

最初のバージョンでは、文献のみを対象にする。

### 入力

```text
papers/
  paper_001.pdf
  paper_002.pdf
  paper_003.pdf
```

### 対応ファイル

- `.pdf`
- `.bib`：任意
- `.md`：任意

### 対象外

- 自分の実験結果CSV
- コード
- 進捗報告
- スライド
- ノートブック

これらは将来的な拡張対象とする。

---

## 4. 全体アーキテクチャ

```text
PDF / BibTeX / Markdown
        ↓
File Scanner
        ↓
Hash Cache
        ↓
PDF Parser
        ↓
Section Splitter
        ↓
LLM Extractor
        ↓
Schema Validator
        ↓
Entity Normalizer
        ↓
Graph Builder
        ↓
Graph DB
        ↓
MCP Server
        ↓
Claude / Cursor / Codex / ChatGPT など
```

---

## 5. ディレクトリ構成案

```text
literature-graph/
  pyproject.toml
  README.md
  .env.example

  litgraph/
    __init__.py

    cli.py

    scanner/
      __init__.py
      file_scanner.py
      hash_cache.py

    parser/
      __init__.py
      pdf_parser.py
      section_splitter.py
      bib_parser.py

    extractor/
      __init__.py
      llm_extractor.py
      prompts.py
      schema.py

    graph/
      __init__.py
      graph_builder.py
      graph_store.py
      sqlite_store.py
      kuzu_store.py

    mcp/
      __init__.py
      server.py
      tools.py

    utils/
      __init__.py
      ids.py
      logging.py
      config.py

  examples/
    papers/
    outputs/

  tests/
    test_scanner.py
    test_parser.py
    test_extractor_schema.py
    test_graph_builder.py
```

---

## 6. 実装フェーズ

## Phase 0: プロジェクト初期化

### 目的

CLI と基本設定だけを用意する。

### 実装内容

- Python プロジェクト作成
- `pyproject.toml` 作成
- Typer による CLI 作成
- `.env` 読み込み
- ログ出力

### CLI 例

```bash
litgraph --help
litgraph init
```

### 完了条件

- `litgraph --help` が動く
- 設定ファイル `.litgraph/config.yaml` を作成できる

---

## Phase 1: File Scanner / Hash Cache

### 目的

文献フォルダを探索し、PDFの変更有無を管理する。

### 実装内容

- 指定フォルダ内の PDF を探索
- ファイルパス、サイズ、更新日時、SHA-256 hash を取得
- `.litgraph/cache/files.json` に保存
- 前回から変更がない PDF は再解析しない

### 出力例

```json
{
  "papers/paper_001.pdf": {
    "sha256": "abc123...",
    "size": 1234567,
    "modified_at": "2026-07-06T12:00:00"
  }
}
```

### CLI 例

```bash
litgraph scan ./papers
```

### 完了条件

- PDF一覧を取得できる
- hash を保存できる
- 変更ファイルだけを検出できる

---

## Phase 2: PDF Parser

### 目的

PDFから本文、ページ番号、セクション候補を抽出する。

### 実装内容

- PyMuPDF でPDF本文を抽出
- ページ単位でテキストを保存
- タイトル候補、Abstract、Introduction、Conclusion を抽出
- PDF抽出結果を JSON に保存

### 出力例

```json
{
  "paper_id": "paper_001",
  "path": "papers/paper_001.pdf",
  "pages": [
    {
      "page": 1,
      "text": "..."
    }
  ],
  "sections": [
    {
      "name": "Abstract",
      "page_start": 1,
      "page_end": 1,
      "text": "..."
    }
  ]
}
```

### CLI 例

```bash
litgraph parse
```

### 完了条件

- PDF本文をページ単位で抽出できる
- Abstract / Introduction / Conclusion をある程度抽出できる
- 抽出結果をキャッシュできる

---

## Phase 3: LLM Extractor

### 目的

論文内容から、文献レビューに必要な構造情報を抽出する。

### 抽出対象

- task
- method
- dataset
- metric
- contribution
- claim
- limitation
- evidence

### 実装内容

- OpenAI / Gemini / Anthropic / Ollama などの provider を抽象化
- JSON Schema で出力形式を固定
- Abstract, Introduction, Method, Experiment, Conclusion を中心に入力
- evidence_text, page, section を必ず保存
- Pydantic でバリデーション

### 抽出JSON例

```json
{
  "paper_id": "paper_001",
  "title": "Example Paper",
  "year": 2025,
  "tasks": ["mobility prediction"],
  "methods": ["Graph Neural Network", "GRU"],
  "datasets": ["GPS trajectory"],
  "metrics": ["MAE", "RMSE"],
  "claims": [
    {
      "text": "The proposed model improves spatial-temporal prediction accuracy.",
      "evidence_text": "...",
      "page": 1,
      "section": "Abstract"
    }
  ],
  "limitations": [
    {
      "text": "The method does not explicitly consider event information.",
      "evidence_text": "...",
      "page": 8,
      "section": "Conclusion"
    }
  ]
}
```

### CLI 例

```bash
litgraph extract
```

### 完了条件

- 論文1本から構造化JSONを生成できる
- evidence_text を保持できる
- JSON Schema違反を検出できる

---

## Phase 4: Entity Normalizer

### 目的

表記揺れを統一する。

### 例

```text
GNN
Graph Neural Network
graph neural networks
```

これらを同じ `Method: Graph Neural Network` として扱う。

### 実装内容

- 小文字化
- 記号除去
- alias辞書
- 類似度による候補提示
- 手動修正用ファイル `aliases.yaml`

### aliases.yaml 例

```yaml
methods:
  Graph Neural Network:
    - GNN
    - graph neural networks

datasets:
  GPS trajectory:
    - GPS trajectories
    - trajectory data
```

### 完了条件

- 同じ手法・データセットを同一ノードに統合できる
- alias を手動で追加できる

---

## Phase 5: Graph Builder

### 目的

抽出JSONをノードとエッジに変換する。

### 最小ノード

```text
Paper
Author
Venue
Task
Method
Dataset
Metric
Claim
Contribution
Limitation
Evidence
```

### 最小エッジ

```text
Paper -[:AUTHORED_BY]-> Author
Paper -[:PUBLISHED_IN]-> Venue
Paper -[:TARGETS]-> Task
Paper -[:USES]-> Method
Paper -[:EVALUATES_ON]-> Dataset
Paper -[:EVALUATES_WITH]-> Metric
Paper -[:CLAIMS]-> Claim
Paper -[:HAS_CONTRIBUTION]-> Contribution
Paper -[:HAS_LIMITATION]-> Limitation
Claim -[:SUPPORTED_BY]-> Evidence
Limitation -[:SUPPORTED_BY]-> Evidence
Paper -[:CITES]-> Paper
```

### graph.json 例

```json
{
  "nodes": [
    {
      "id": "paper_001",
      "type": "Paper",
      "title": "Example Paper"
    },
    {
      "id": "method_gnn",
      "type": "Method",
      "name": "Graph Neural Network"
    }
  ],
  "edges": [
    {
      "source": "paper_001",
      "target": "method_gnn",
      "type": "USES"
    }
  ]
}
```

### CLI 例

```bash
litgraph build
```

### 完了条件

- 抽出JSONから graph.json を生成できる
- ノード重複を避けられる
- evidence へのリンクを保持できる

---

## Phase 6: Graph DB 保存

### 目的

Graphを検索可能なDBへ保存する。

### 最初の選択肢

MVPでは SQLite または KuzuDB を推奨する。

| DB | 利点 | 欠点 |
|---|---|---|
| SQLite | 軽量・導入しやすい | Graphクエリは自前実装が必要 |
| KuzuDB | ローカルGraph DBとして使いやすい | 多少学習コストがある |
| Neo4j | Cypherが強い・可視化しやすい | 起動や配布が重め |

### 推奨

- MVP: SQLite + graph.json
- v0.2: KuzuDB
- v0.3以降: Neo4j optional

### 完了条件

- Paper / Method / Claim / Evidence をDBに保存できる
- paper_id から関連ノードを取得できる
- method名から関連論文を検索できる

---

## Phase 7: Query Layer

### 目的

Graphに対する検索APIを作る。

### 最小クエリ

```python
list_papers()
get_paper(paper_id)
find_papers_by_method(method)
find_papers_by_task(task)
find_limitations(topic)
get_evidence_for_claim(claim_id)
compare_papers(paper_ids)
```

### クエリ例

```text
find_papers_by_method("GNN")
  → GNNを使う論文一覧を返す

find_limitations("event")
  → eventに関係する限界を持つ論文を返す

get_evidence_for_claim("claim_001")
  → 根拠文・ページ番号・セクションを返す
```

### 完了条件

- Python APIとして検索できる
- CLIから検索できる

### CLI 例

```bash
litgraph query papers --method "GNN"
litgraph query limitations --topic "event"
```

---

## Phase 8: MCP Server

### 目的

AIアシスタントが文献Graphを使えるようにする。

### MCP tools

```text
list_papers()
summarize_paper(paper_id)
find_papers_by_method(method)
find_papers_by_task(task)
find_limitations(topic)
get_evidence_for_claim(claim_id)
compare_papers(paper_ids)
build_literature_matrix(topic)
generate_related_work_outline(topic)
```

### MCP tool の例

#### find_limitations

入力:

```json
{
  "topic": "event information"
}
```

出力:

```json
{
  "limitations": [
    {
      "paper_id": "paper_001",
      "title": "Example Paper",
      "limitation": "The method does not explicitly consider event information.",
      "evidence": {
        "page": 8,
        "section": "Conclusion",
        "text": "..."
      }
    }
  ]
}
```

### CLI 例

```bash
litgraph serve-mcp
```

### 完了条件

- MCPクライアントから文献Graphを検索できる
- evidence付きで結果を返せる
- 生PDFを毎回LLMに読ませず、構造化済みGraphを参照できる

---

## Phase 9: 文献比較機能

### 目的

複数論文を比較し、関連研究整理に使える表を生成する。

### 比較項目

- task
- method
- dataset
- metric
- contribution
- limitation
- difference

### 出力例

```markdown
| Paper | Task | Method | Dataset | Contribution | Limitation |
|---|---|---|---|---|---|
| Paper A | Mobility prediction | GNN | GPS | Spatial dependency modeling | Event information not considered |
| Paper B | Event forecasting | Transformer | Event logs | Event-aware prediction | Limited spatial modeling |
```

### MCP tool

```text
compare_papers(paper_ids)
build_literature_matrix(topic)
```

### 完了条件

- 複数論文の比較表を生成できる
- 根拠付きで各項目を返せる

---

## Phase 10: Research Gap 抽出

### 目的

文献群から未解決課題を抽出する。

### 方法

1. 各論文の limitation を収集
2. 類似 limitation をクラスタリング
3. 頻出する課題をまとめる
4. 手法・データセット・タスクとの関係を見る
5. evidence付きで返す

### 出力例

```json
{
  "gaps": [
    {
      "gap": "Event information is rarely integrated into mobility or consumption prediction models.",
      "supporting_papers": ["paper_001", "paper_003"],
      "evidence": [
        {
          "paper_id": "paper_001",
          "page": 8,
          "text": "..."
        }
      ]
    }
  ]
}
```

### MCP tool

```text
find_research_gaps(topic)
```

### 完了条件

- limitation から gap 候補を出せる
- evidence付きで返せる

---

## Phase 11: 関連研究セクション支援

### 目的

文献Graphを使って、関連研究セクションの構成案を出す。

### MCP tool

```text
generate_related_work_outline(topic)
```

### 出力例

```markdown
## Related Work Outline

1. Mobility prediction with deep learning
2. Graph-based spatial dependency modeling
3. Event-aware forecasting
4. Limitations of existing studies
5. Positioning of the current study
```

### 完了条件

- 文献群をトピック別に整理できる
- 関連研究の構成案を生成できる
- 各節に対応する論文を提示できる

---

## 7. 実装優先順位

最初の2週間で作るなら以下を優先する。

### Week 1

1. CLI作成
2. PDF探索
3. Hash Cache
4. PDFテキスト抽出
5. Section Splitter
6. LLM Extractor
7. Pydantic Schema

### Week 2

1. graph.json生成
2. SQLite保存
3. Query Layer
4. MCP Server
5. `find_limitations`
6. `compare_papers`
7. `get_evidence_for_claim`

---

## 8. MVP 完了条件

MVPでは以下ができれば十分である。

```bash
litgraph scan ./papers
litgraph parse
litgraph extract
litgraph build
litgraph serve-mcp
```

AIアシスタントから以下を呼べる。

```text
list_papers()
summarize_paper(paper_id)
find_papers_by_method(method)
find_limitations(topic)
compare_papers(paper_ids)
get_evidence_for_claim(claim_id)
```

さらに、すべての回答に以下が含まれる。

```text
paper_id
title
page
section
evidence_text
```

---

## 9. 注意点

## 9.1 LLM抽出の誤り

LLMは論文内容を誤って抽出する可能性がある。  
そのため、必ず evidence_text と page を保存する。

## 9.2 PDF抽出の不安定性

PDFによって本文抽出が崩れる。  
最初は完全なレイアウト復元を目指さず、Abstract / Introduction / Conclusion を中心に抽出する。

## 9.3 汎用Graphにしすぎない

最初から自由なKnowledge Graphにすると複雑になる。  
MVPでは文献レビューに必要な固定スキーマに絞る。

## 9.4 APIコスト

PDF全文を毎回LLMに投げるとコストが大きい。  
hash cache, section split, extraction cache を必ず入れる。

## 9.5 ライセンス

PDF本文を外部APIへ送る場合、論文PDFの利用条件に注意する。  
OSSとしてはローカルLLM対応や、送信前確認オプションを用意するとよい。

---

## 10. 将来拡張

### v0.2

- KuzuDB対応
- BibTeX対応
- Semantic Scholar API連携
- 引用関係 `CITES` の強化
- aliases.yaml による正規化

### v0.3

- Neo4j対応
- Graph可視化
- Zotero連携
- 論文間の CONTRASTS_WITH / EXTENDS 推定

### v0.4

- related work 自動ドラフト
- literature matrix 自動生成
- research gap clustering
- ローカルLLM対応

### v1.0

- MCP server 安定版
- GUI / Web UI
- チーム共有
- 文献レビュー支援OSSとして公開

---

## 11. 最小コマンド仕様

```bash
# 初期化
litgraph init

# 文献フォルダをスキャン
litgraph scan ./papers

# PDFをテキスト化
litgraph parse

# LLMで構造抽出
litgraph extract

# Graphを生成
litgraph build

# 検索
litgraph query papers --method "GNN"
litgraph query limitations --topic "event"

# MCPサーバー起動
litgraph serve-mcp
```

---

## 12. 最初に作るべきデモ

### デモ用入力

```text
papers/
  mobility_gnn_2024.pdf
  event_forecasting_2025.pdf
  spatial_temporal_transformer_2025.pdf
```

### デモ質問

```text
この文献群でイベント情報を扱っていない研究はどれか？
```

期待出力:

```text
Paper A はGNNによる人流予測を扱っているが、イベント情報を明示的に扱っていない。
根拠: p.8 Conclusion ...
```

### デモ質問2

```text
GNNを使う論文を比較して
```

期待出力:

```markdown
| Paper | Task | Method | Dataset | Limitation |
|---|---|---|---|---|
| Paper A | Mobility prediction | GNN | GPS | Event information not considered |
```

---

## 13. 開発時の判断基準

常に以下を優先する。

1. 根拠付きで返す
2. 文献レビューに使える
3. Graphに保存する
4. MCPでAIが使える
5. PDF全文を毎回読ませない
6. 最初は固定スキーマに絞る

---

## 14. 一言での説明

LiteratureGraph MCP は、研究論文フォルダを Paper・Method・Dataset・Claim・Limitation・Evidence の知識グラフに変換し、AIアシスタントが関連研究整理・文献比較・研究ギャップ抽出に使えるようにする OSS である。
