# pdf-to-notebooklm-audio

> フォルダのPDFをNotebookLMの音声解説＆要約に自動変換する Claude Code Skill

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)

[English README](README_en.md)

## できること

- 指定フォルダ内のPDFを自動検出・バッチ処理
- NotebookLM Audio Overview（ポッドキャスト形式）を自動生成
- 全論文の構造化要約を Markdown で出力
- 日本語・英語ほか多言語に対応
- Claude Code から `/pdf-to-notebooklm-audio` で即実行

## クイックスタート

### 1. インストール

```bash
cd ~/.claude/skills
git clone https://github.com/{user}/pdf-to-notebooklm-audio.git
cd pdf-to-notebooklm-audio && bash scripts/setup.sh
```

### 2. 認証（初回のみ）

```bash
notebooklm login
```

ブラウザが開くので Google アカウントでログインしてください。

### 3. 実行

Claude Code 内で：

```
/pdf-to-notebooklm-audio
```

または直接実行：

```bash
python3 ~/.claude/skills/pdf-to-notebooklm-audio/scripts/process_pdfs.py ./papers
```

## 使い方

### 基本（日本語で音声＋要約を生成）

```bash
python3 scripts/process_pdfs.py /path/to/pdfs
```

### 英語で生成

```bash
python3 scripts/process_pdfs.py /path/to/pdfs --lang en
```

### 音声だけ欲しい

```bash
python3 scripts/process_pdfs.py /path/to/pdfs --audio-only
```

### 要約だけ欲しい

```bash
python3 scripts/process_pdfs.py /path/to/pdfs --summary-only
```

### 出力先を変更

```bash
python3 scripts/process_pdfs.py /path/to/pdfs -o ~/Desktop/output
```

## オプション一覧

| 引数 | 必須 | デフォルト | 説明 |
|------|------|-----------|------|
| `input_dir` | Yes | - | PDFファイルが入ったフォルダのパス |
| `-o`, `--output` | - | `./notebooklm_output` | 出力先フォルダ |
| `--lang` | - | `ja` | 生成言語コード（`ja`, `en`, `zh`, `ko` 等） |
| `--audio-only` | - | `false` | 音声のみ生成（要約をスキップ） |
| `--summary-only` | - | `false` | 要約のみ生成（音声をスキップ） |
| `--notebook-name` | - | 自動生成 | NotebookLM ノートブック名 |
| `--batch-size` | - | `20` | 1ノートブックに登録する最大PDF数 |
| `--audio-prompt` | - | 組み込み | Audio Overview 生成時のカスタムプロンプト |
| `--summary-prompt` | - | 組み込み | 要約生成時のカスタムプロンプト |
| `--timeout` | - | `600` | 音声生成の最大待機秒数 |
| `--dry-run` | - | `false` | 実際の処理を行わず計画のみ表示 |

## 出力例

### フォルダ構造

```
notebooklm_output/
├── manifest.json            # 処理結果メタデータ
├── batch_001/
│   ├── summary.md           # 要約テキスト（Markdown）
│   ├── audio_overview.mp3   # 音声解説
│   └── metadata.json        # ノートブックID、処理時間など
├── batch_002/
│   ├── summary.md
│   ├── audio_overview.mp3
│   └── metadata.json
└── errors.log               # エラーログ（あれば）
```

### summary.md サンプル

```markdown
# 論文要約 -- papers (1/2)

生成日時: 2026-03-03 08:00 JST
言語: 日本語
ソースPDF数: 20

---

## [論文タイトル1]
- **著者**: 山田太郎（東京大学）, 鈴木花子（京都大学）
- **概要**: 本研究ではXXを提案した。YYの課題に対しZZの手法で解決を試みた。
- **手法**: 深層学習を用いたマルチモーダルアプローチ
- **結果・貢献**: 従来手法と比較して精度15%向上を達成
- **キーワード**: HCI, VR, 触覚フィードバック

## [論文タイトル2]
...
```

## 注意事項

- **非公式ライブラリ**: notebooklm-py は Google 非公式のライブラリです。自己責任でご使用ください。
- **API変更リスク**: Google の仕様変更により突然動作しなくなる可能性があります。
- **著作権**: 論文PDFの著作権に留意し、個人の研究・学習目的でご使用ください。
- **Cookie期限**: 認証 Cookie は数週間で期限切れになります。期限切れ時は `notebooklm login` で再認証してください。

## Contributing

Issue・PR 歓迎です。バグ報告や機能提案は GitHub Issues からお願いします。

## License

[MIT License](LICENSE)
