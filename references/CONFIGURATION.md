# 詳細設定リファレンス

`pdf-to-notebooklm-audio` の設定オプション、環境変数、カスタマイズ方法について説明します。

## 環境変数

| 環境変数 | デフォルト | 説明 |
|----------|-----------|------|
| `NOTEBOOKLM_STORAGE_PATH` | `~/.notebooklm/storage_state.json` | 認証情報の保存パス |

### 設定例

```bash
# 認証情報の保存先を変更する場合
export NOTEBOOKLM_STORAGE_PATH="/custom/path/storage_state.json"
```

## プロンプトのカスタマイズ

`--audio-prompt` と `--summary-prompt` でプロンプトを直接指定できます。

### 音声プロンプトのカスタマイズ

```bash
python3 scripts/process_pdfs.py ./papers \
  --audio-prompt "初心者向けに、各論文の概要をやさしい日本語で解説してください。専門用語は避け、具体例を多く使ってください。"
```

### 要約プロンプトのカスタマイズ

```bash
python3 scripts/process_pdfs.py ./papers \
  --summary-prompt "各論文について、1. 研究課題、2. 提案手法、3. 実験結果、4. 限界点の4項目で簡潔に要約してください。"
```

### デフォルトプロンプト

#### 日本語（--lang ja）

**音声用:**

```
日本語で解説してください。
ソースに含まれる論文を、研究者同士の対話形式で紹介してください。
各論文の面白いポイントや新規性に焦点を当て、
聴いている人が興味を持てるようなわかりやすい解説をお願いします。
```

**要約用:**

```
ソースに含まれる全ての論文について、各論文ごとに以下の形式で
日本語の要約を作成してください：

## [論文タイトル]
- **著者**: （著者名・所属）
- **概要**: （2〜3文で研究の目的と内容）
- **手法**: （使用した手法の説明）
- **結果・貢献**: （主な結果や学術的貢献）
- **キーワード**: （3〜5個）

全論文を漏れなく要約してください。
```

#### 英語（--lang en）

**音声用:**

```
Create an engaging discussion about the papers in the sources.
Use a conversational tone between two researchers.
Focus on interesting points and novelty of each paper.
```

**要約用:**

```
For every paper in the sources, create a structured summary
in the following format:

## [Paper Title]
- **Authors**: (names and affiliations)
- **Abstract**: (2-3 sentences on purpose and content)
- **Method**: (description of the approach)
- **Results/Contribution**: (key findings)
- **Keywords**: (3-5 keywords)

Summarize all papers without omission.
```

## バッチサイズの最適値ガイダンス

`--batch-size` は1つの NotebookLM ノートブックに登録する最大PDF数を指定します。

| バッチサイズ | 用途 | メリット・デメリット |
|-------------|------|---------------------|
| `5` | 少数の長い論文（50ページ以上） | ソース処理が安定しやすい。バッチ数が増えるため合計処理時間が長い |
| `10` | 一般的な論文（10〜30ページ） | バランスが良い。多くのケースで推奨 |
| `20`（デフォルト） | 短めの論文やレポート | 効率的だが、大量のソースで処理が不安定になる場合がある |
| `50` | NotebookLM の上限に近い | 処理失敗のリスクが高い。短いドキュメントにのみ推奨 |

NotebookLM のソース数上限は1ノートブックあたり50件です。大きなPDFが多い場合は `--batch-size 10` 程度に下げることを推奨します。

## 言語コード一覧

`--lang` オプションに指定可能な主要言語コード：

| コード | 言語 |
|--------|------|
| `ja` | 日本語（デフォルト） |
| `en` | 英語 |
| `zh` | 中国語 |
| `ko` | 韓国語 |
| `fr` | フランス語 |
| `de` | ドイツ語 |
| `es` | スペイン語 |
| `pt` | ポルトガル語 |
| `it` | イタリア語 |
| `ru` | ロシア語 |
| `ar` | アラビア語 |
| `hi` | ヒンディー語 |

上記以外の言語コードも NotebookLM が対応していれば使用可能です。`ja` と `en` 以外の言語では、デフォルトプロンプトは英語が使用されます。

## 出力ディレクトリの構造

`-o` / `--output` で指定したフォルダ（デフォルト: `./notebooklm_output`）に以下の構造で出力されます。

```
{output_dir}/
├── manifest.json            # 全体の処理結果メタデータ
├── batch_001/
│   ├── summary.md           # バッチ1の要約テキスト
│   ├── audio_overview.mp3   # バッチ1の音声解説
│   └── metadata.json        # バッチ1のメタデータ（ノートブックID等）
├── batch_002/
│   ├── summary.md
│   ├── audio_overview.mp3
│   └── metadata.json
├── ...
└── errors.log               # エラーが発生した場合のみ出力
```

### manifest.json

全体の処理結果をまとめた JSON ファイルです。

```json
{
  "tool": "pdf-to-notebooklm-audio",
  "version": "1.0.0",
  "created_at": "2026-03-02T15:30:00+09:00",
  "language": "ja",
  "input_dir": "/path/to/papers",
  "total_pdfs": 25,
  "batches": [
    {
      "batch_id": "batch_001",
      "notebook_id": "abc123...",
      "notebook_name": "papers (1/2)",
      "pdf_count": 20,
      "pdfs": ["paper1.pdf", "paper2.pdf"],
      "summary_generated": true,
      "audio_generated": true,
      "audio_duration_sec": 480,
      "processing_time_sec": 312,
      "errors": []
    }
  ],
  "total_errors": 0,
  "total_processing_time_sec": 625
}
```

### metadata.json

各バッチの詳細情報です。バッチフォルダ内に保存されます。

### errors.log

処理中にエラーが発生した場合のみ出力されます。各行にタイムスタンプ、エラー種別、対象ファイル、エラー内容が記録されます。
