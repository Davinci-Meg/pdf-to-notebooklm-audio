---
name: pdf-to-notebooklm-audio
description: >-
  フォルダ内のPDFファイルをGoogle NotebookLMに登録し、音声解説（Audio Overview）
  と要約テキストを自動生成するSkill。論文PDF、レポート、技術文書などを指定フォルダ
  に入れてこのSkillを実行するだけで、ポッドキャスト形式の音声解説と構造化された
  Markdown要約が出力される。「PDFから音声」「論文を音声化」「PDFをNotebookLMで
  処理」「論文の要約と音声を作って」「フォルダのPDFをまとめて音声解説にして」
  といったリクエストで使用する。
---

# PDF to NotebookLM Audio

フォルダ内のPDFをNotebookLMに登録し、音声解説と要約を自動生成する。

## 前提条件
- notebooklm-py がインストール済みであること
- NotebookLM への認証が完了していること
- 未セットアップの場合は scripts/setup.sh を実行

## 基本的な使い方

### 全PDFを処理（デフォルト：日本語）
python3 {SKILL_DIR}/scripts/process_pdfs.py /path/to/pdf/folder

### 英語で生成
python3 {SKILL_DIR}/scripts/process_pdfs.py /path/to/pdf/folder --lang en

### 音声のみ生成（要約なし）
python3 {SKILL_DIR}/scripts/process_pdfs.py /path/to/pdf/folder --audio-only

### 要約のみ生成（音声なし）
python3 {SKILL_DIR}/scripts/process_pdfs.py /path/to/pdf/folder --summary-only

### 出力先を指定
python3 {SKILL_DIR}/scripts/process_pdfs.py /path/to/pdf/folder -o /path/to/output

## 引数一覧
| 引数 | 必須 | デフォルト | 説明 |
|------|------|-----------|------|
| input_dir | ○ | - | PDF が入ったフォルダパス |
| -o, --output | - | ./notebooklm_output | 出力先フォルダ |
| --lang | - | ja | 生成言語（ja, en, zh, ko, ...） |
| --audio-only | - | false | 音声のみ生成 |
| --summary-only | - | false | 要約のみ生成 |
| --notebook-name | - | 自動生成 | NotebookLM ノートブック名 |
| --batch-size | - | 20 | 1ノートブックに登録する最大PDF数 |
| --audio-prompt | - | 組み込み | Audio Overview 生成時の指示文 |
| --summary-prompt | - | 組み込み | 要約生成時の指示文 |
| --timeout | - | 600 | 音声生成の最大待機秒数 |

## 認証が未完了の場合
python3 {SKILL_DIR}/scripts/authenticate.py
を実行すると、ブラウザが開いて Google ログインを行える。

## 詳細設定
references/CONFIGURATION.md を参照。

## トラブルシューティング
references/TROUBLESHOOTING.md を参照。
