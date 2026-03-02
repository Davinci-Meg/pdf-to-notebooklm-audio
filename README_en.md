# pdf-to-notebooklm-audio

> A Claude Code Skill that automatically converts PDFs in a folder into NotebookLM audio overviews & structured summaries

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)

[日本語 README](README.md)

## Features

- Auto-detect and batch-process PDFs in a specified folder
- Generate NotebookLM Audio Overviews (podcast-style) automatically
- Output structured summaries for all papers in Markdown
- Multi-language support (Japanese, English, and 80+ languages)
- Run instantly from Claude Code with `/pdf-to-notebooklm-audio`

## Quick Start

### 1. Install

```bash
cd ~/.claude/skills
git clone https://github.com/Davinci-Meg/pdf-to-notebooklm-audio.git
cd pdf-to-notebooklm-audio && bash scripts/setup.sh
```

### 2. Authenticate (first time only)

```bash
notebooklm login
```

A browser window will open — sign in with your Google account.

### 3. Run

Inside Claude Code:

```
/pdf-to-notebooklm-audio
```

Or run directly:

```bash
python3 ~/.claude/skills/pdf-to-notebooklm-audio/scripts/process_pdfs.py ./papers
```

## Usage

### Basic (generate audio + summary in Japanese)

```bash
python3 scripts/process_pdfs.py /path/to/pdfs
```

### Generate in English

```bash
python3 scripts/process_pdfs.py /path/to/pdfs --lang en
```

### Audio only (skip summary)

```bash
python3 scripts/process_pdfs.py /path/to/pdfs --audio-only
```

### Summary only (skip audio)

```bash
python3 scripts/process_pdfs.py /path/to/pdfs --summary-only
```

### Custom output directory

```bash
python3 scripts/process_pdfs.py /path/to/pdfs -o ~/Desktop/output
```

## Options

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `input_dir` | Yes | - | Path to folder containing PDF files |
| `-o`, `--output` | - | `./notebooklm_output` | Output directory |
| `--lang` | - | `ja` | Language code (`ja`, `en`, `zh`, `ko`, etc.) |
| `--audio-only` | - | `false` | Generate audio only (skip summary) |
| `--summary-only` | - | `false` | Generate summary only (skip audio) |
| `--notebook-name` | - | Auto-generated | NotebookLM notebook name |
| `--batch-size` | - | `20` | Max PDFs per notebook |
| `--audio-prompt` | - | Built-in | Custom prompt for Audio Overview generation |
| `--summary-prompt` | - | Built-in | Custom prompt for summary generation |
| `--timeout` | - | `600` | Max wait time for audio generation (seconds) |
| `--dry-run` | - | `false` | Show plan only without actual processing |

## Output Example

### Folder Structure

```
notebooklm_output/
├── manifest.json            # Processing result metadata
├── batch_001/
│   ├── summary.md           # Summary text (Markdown)
│   ├── audio_overview.mp3   # Audio overview
│   └── metadata.json        # Notebook ID, processing time, etc.
├── batch_002/
│   ├── summary.md
│   ├── audio_overview.mp3
│   └── metadata.json
└── errors.log               # Error log (if any)
```

### summary.md Sample

```markdown
# Paper Summaries — papers (1/2)

Generated: 2026-03-03 08:00 JST
Language: English
Source PDFs: 20

---

## Attention Is All You Need
- **Authors**: Ashish Vaswani et al. (Google Brain)
- **Abstract**: This paper proposes the Transformer architecture, relying entirely on self-attention mechanisms without recurrence or convolution, achieving new SOTA on machine translation.
- **Method**: Multi-Head Self-Attention with Positional Encoding in an Encoder-Decoder model
- **Results/Contribution**: Achieved BLEU 28.4 on WMT 2014 EN-DE, significantly reducing training time.
- **Keywords**: Transformer, Self-Attention, Machine Translation, Encoder-Decoder
```

## Important Notes

- **Unofficial library**: notebooklm-py is an unofficial Google library. Use at your own risk.
- **API changes**: May stop working without notice due to Google API changes.
- **Copyright**: Be mindful of paper copyrights. Use for personal research and learning purposes.
- **Cookie expiration**: Authentication cookies expire after a few weeks. Re-authenticate with `notebooklm login` when expired.

## Contributing

Issues and PRs are welcome. Please report bugs or suggest features via GitHub Issues.

## License

[MIT License](LICENSE)
