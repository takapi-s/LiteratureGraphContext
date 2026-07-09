# LiteratureGraphContext Roadmap

> **Current version**: 0.7.0  
> **Last updated**: 2026-07

OSS (`literature-graph` on PyPI) の残タスクと既知の制約。v0.5 以前の実装履歴は [docs/literature_graph_mcp_implementation_plan.md](docs/literature_graph_mcp_implementation_plan.md) を参照。

## Design philosophy

LGC は **構造化エビデンス層**（解釈エンジンではない）。

| Layer | 役割 | 例 |
|---|---|---|
| **LGC（データ平面）** | 取り込み・構造化・接続・引用 | PDF → グラフ; `CITES` / `CONTRASTS_WITH`; MCP が `evidence_text` を返す |
| **接続エージェント** | 解釈・クラスタリング・執筆 | 研究ギャップ; Related Work 草稿; 横断的な統合 |

**コア:** 複数論文をグラフで正しくつなぎ、MCP がトピック絞り込み済みの根拠付きファクトを返し、エージェントがそれをもとに回答する。

**LGC に入れない:** ギャップの事前クラスタリング、Related Work 草稿生成、埋め込みベースのナラティブ合成。代わりに `find_limitations` / `compare_papers` / `build_literature_matrix` をエージェントのコンテキストとして使う。

**検索層（スコープ内）:** `search_papers`（キーワード + 埋め込みハイブリッド）、`explore_paper_graph`（多ホップ系譜）、不変 UUID `paper_id`。

**ビジョン:** *Literature* は学術論文に限らない。現状は PDF 中心の文献レビューだが、長期では Web・ドキュメント・技術ブログなど任意の構造化ソースを同じスキーマで扱う。

---

## Experimental ideas (Impact × Difficulty)

未コミット・不確実なアイデア。編集は `docs/assets/idea_matrix.drawio.svg`（draw.io / VS Code Draw.io 拡張）。意味論は [docs/LGC_KNOWLEDGE_BASE.md](docs/LGC_KNOWLEDGE_BASE.md) を参照。

![IDEA Matrix](docs/assets/idea_matrix.drawio.svg)

| ID | Idea | Target |
|---|---|---|
| I01 | Hybrid search entry (embeddings + keyword + graph) | v0.5 ✅ |
| I02 | New inputs: arXiv / URL / Zotero / CSV connectors | v0.9, v0.11 |
| I03 | Containment: section / subsection + `CONTAINS` edges | TBD |
| I04 | PDF structure: robust section detection + diagnostics | v0.8 |
| I05 | Citations: merge refs + bib better (`CITES` quality) | TBD |
| I06 | ID resolution & errors: actionable hints in MCP / CLI | v0.8+ |
| I07 | Auto-generate `paper_id_map` from `paper_registry` | TBD |
| I08 | Graph UI: paper-centric sidebar + preview cards | v0.8 |
| I09 | Workspace-scoped graph (`workspace_id` on nodes & queries) | v0.10 |
| I10 | Programmatic API (`LitgraphContext`, injectable store) | v0.9 |
| I11 | HTTP MCP transport (remote callers) | v0.12 |
| I12 | Folder watch / auto-ingest (`watch_papers_directory`) | v0.12 |
| I13 | MCP setup wizard (interactive onboarding) | v0.8+ |

---

## Known limitations

| Area | Status | Direction |
|---|---|---|
| Paper identity (slug ID が再抽出で変わる) | **Done (v0.6)** | UUID + `paper_registry.json` |
| Search entry (属性検索のみ) | **Done (v0.5)** | `search_papers` |
| Graph traversal (1-hop のみ) | **Done (v0.5)** | `explore_paper_graph` |
| MCP contract tests | **Done (v0.6)** | `litgraph test-mcp` |
| Entity resolution (重複 Method/Task) | **Done (v0.7)** | catalog fuzzy merge + optional LLM |
| MCP tool surface (14 → 6 ツール) | **Done (v0.7)** | 6 コアクエリツール; ingest は CLI のみ |
| PDF parsing | Active | セクションパターン拡張; 診断出力 (I04) |
| Graph UI | Active | 論文プレビューカード (I08) |
| MCP stability | Active | Kuzu 単一ライター方針の文書化 |
| Zotero | Partial | bib sync のみ; フル PDF パイプラインは v0.11 (I02) |
| md parser | Deferred | 単一論文ノートのみ |
| Neo4j migration | Deferred | Kuzu からの移行ツールなし |
| Claim-level embeddings | Deferred | 論文レベル埋め込みのみ |

**意図的にエージェントへ委譲:** ギャップクラスタリング、`generate_related_work_outline` による Related Work 草稿。

---

## Version roadmap

### v0.7 — MCP tool consolidation ✅

- [x] `explore_paper_graph` — `get_paper_neighbors` + `expand_paper_graph` を統合
- [x] 属性検索・マトリクス・Related Work 草稿・ジョブ管理を MCP から除去 → CLI
- [x] `get_evidence_for_claim` を `summarize_paper` に統合
- [x] MCP テスト & Cursor skill を 6 ツールに更新
- [x] Entity resolution（`entity_catalog.json` + build-time resolver）

### v0.8 — Local UX & graph quality

- [x] Project resolution fix — `~/.litgraph` excluded from walk-up; `litgraph init` required; `litgraph doctor` (I06)
- [ ] Documentation and tutorial — init → extract → MCP → viz
- [ ] PDF section detection — Related Work, Background, References パターン (I04)
- [ ] Graph UI paper sidebar — プレビューカード (I08)
- [ ] MCP setup wizard — 対話的オンボーディング (I13)
- [ ] ID / error hints — MCP / CLI の actionable メッセージ (I06)

### v0.9 — Programmatic API & ingest

- [ ] Injectable execution context — `GraphStore`、キャッシュパス、設定を cwd 非依存に (I10)
- [ ] Programmatic ingest API — `ingest_from_path` / `ingest_from_bytes`
- [ ] Ingest adapters — `source_ref` プラグイン（ローカルフォルダ、バイト、URL / arXiv）(I02)

### v0.10 — Workspace-scoped graph

- [ ] `workspace_id` on nodes — 全 build / query パスでフィルタ; `(workspace_id, paper_id)` 一意 (I09)
- [ ] Default workspace — 省略時は `default`（単一 `.litgraph` ワークフローは互換維持）
- [ ] CLI / MCP context — `--workspace` または `LitgraphContext(workspace_id=...)`

### v0.11 — Zotero full pipeline

**Shipped**

- [x] JSON export import — `litgraph import zotero <export.json>`
- [x] Web API bib sync — `litgraph import zotero-sync`

**Remaining**

- [ ] Zotero ingest adapter — `source_ref: zotero://{library}/{item_key}` (I02)
- [ ] `zotero_key` on Paper nodes — `(workspace_id, zotero_key) → paper_id`
- [ ] PDF attachment fetch — Web API 経由で PDF 取得 → parse → extract → build
- [ ] Full pipeline sync — bib sync 後に PDF 付き新規 / 変更アイテムを自動 ingest
- [ ] Collection filter — コレクション単位で workspace に同期
- [ ] Dedup — `zotero_key` / DOI / `content_hash` で既存論文と照合
- [ ] Docs & tutorial — Zotero → LGC ワークフロー

**Deferred (post-v1.0):** グループライブラリ、デスクトップ sqlite sync

### v0.12 — Remote MCP & watch (optional; v1.0 後でも可)

- [ ] HTTP MCP transport (I11)
- [ ] MCP `watch_papers_directory` — フォルダ変更の自動 ingest (I12)

### v1.0 — PyPI release

- [ ] PyPI 公開 — パッケージングと semver 安定の programmatic API（v0.8–v0.11 完了後）

---

## Future expansion (post-v1.0)

同一グラフスキーマと MCP 面; 新しい ingest adapter で拡張。

- [ ] Web pages and documentation
- [ ] Experiment result CSVs
- [ ] Code repos
- [ ] Slides and notebooks

---

## Out of scope

- フリーフォーム知識グラフ（文献レビュー固定スキーマのみ）
- PDF レイアウト完全復元
- LGC 内での Related Work 草稿生成・ギャップ事前クラスタリング
- Graphiti をランタイム依存にすること
- 認証・課金・マルチテナント SaaS

---

## Migrating to v0.6 (UUID `paper_id`)

再インデックスが必要（移行スクリプトなし）:

```bash
rm -rf .litgraph/cache/parsed .litgraph/cache/extracted .litgraph/cache/files.json \
  .litgraph/db .litgraph/paper_id_map.json
litgraph scan && litgraph parse --all && litgraph extract -y && litgraph build
litgraph test-mcp
```

`parse --all` はキャッシュクリア後にハッシュキャッシュが「変更なし」と報告しても再パースするために必要。
