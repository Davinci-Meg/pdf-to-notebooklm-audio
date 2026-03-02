# トラブルシューティング

`pdf-to-notebooklm-audio` で発生しうるエラーと対処法をまとめています。

---

## 認証エラー

### 症状

```
エラー: 認証が必要です。以下を実行してください:
  python3 scripts/authenticate.py
```

または処理中に認証切れで API 呼び出しが失敗する。

### 原因

- NotebookLM への認証が未実施
- 認証 Cookie の期限切れ（通常数週間で期限切れ）
- `~/.notebooklm/storage_state.json` が破損または削除された

### 対処法

1. 認証を実行する：
   ```bash
   notebooklm login
   ```
2. ブラウザが開くので Google アカウントでログインする
3. 認証状態を確認する：
   ```bash
   python3 scripts/authenticate.py --check
   ```

認証ファイルが破損している場合は、強制再認証を実行：

```bash
python3 scripts/authenticate.py --force
```

---

## PDF 読み込みエラー

### 症状

```
エラー: PDFファイルが見つかりません: /path/to/folder
```

またはソース登録時に特定の PDF がスキップされる。

### 原因

- 指定したフォルダに PDF ファイルが存在しない
- ファイル拡張子が `.pdf` ではない（`.PDF` 等の大文字は検索対象外）
- PDF ファイルが破損している
- ファイル名に特殊文字が含まれている
- `.` で始まるフォルダ内の PDF は自動除外される

### 対処法

1. フォルダパスが正しいか確認する：
   ```bash
   ls /path/to/folder/*.pdf
   ```
2. PDF ファイルの拡張子が小文字の `.pdf` であることを確認する
3. `--dry-run` で処理対象の PDF を事前確認する：
   ```bash
   python3 scripts/process_pdfs.py /path/to/folder --dry-run
   ```
4. 破損した PDF は別のフォルダに移動してから再実行する

---

## 音声生成タイムアウト

### 症状

```
エラー: 音声生成がタイムアウトしました（600秒）
--timeout オプションで待機時間を延長できます
```

### 原因

- PDF のページ数が多く、Audio Overview の生成に時間がかかっている
- NotebookLM サーバー側の処理遅延
- ネットワーク接続が不安定

### 対処法

1. `--timeout` でタイムアウト値を延長する：
   ```bash
   python3 scripts/process_pdfs.py ./papers --timeout 1200
   ```
2. `--batch-size` を小さくしてバッチあたりの PDF 数を減らす：
   ```bash
   python3 scripts/process_pdfs.py ./papers --batch-size 10
   ```
3. ネットワーク接続を確認する
4. 時間をおいて再実行する

---

## レート制限

### 症状

処理中にレート制限エラーが発生し、一部の PDF がスキップされる。errors.log に以下のような記録が残る：

```
[2026-03-02 15:30:00] RATE_LIMIT: リトライ上限に達しました
```

### 原因

- 短時間に大量の NotebookLM API 呼び出しを行った
- NotebookLM 側のリクエスト制限に到達した

### 対処法

1. スクリプトはレート制限時に 30 秒待機して自動リトライ（最大3回）を行います。通常は自動回復します
2. 繰り返し発生する場合は、`--batch-size` を小さく設定してバッチ間の負荷を分散する：
   ```bash
   python3 scripts/process_pdfs.py ./papers --batch-size 5
   ```
3. 時間をおいてから再実行する

---

## ネットワークエラー

### 症状

処理中にネットワーク接続エラーが発生して中断する。

### 原因

- インターネット接続が不安定または切断された
- プロキシやファイアウォールが NotebookLM へのアクセスをブロックしている
- NotebookLM サービスが一時的にダウンしている

### 対処法

1. インターネット接続を確認する：
   ```bash
   curl -I https://notebooklm.google.com
   ```
2. プロキシ環境の場合は、適切なプロキシ設定がされているか確認する
3. スクリプトは自動リトライを行いますが、完全に接続不可の場合は中断されます。接続回復後に再実行してください
4. 部分的に処理が完了している場合、出力フォルダ内の `manifest.json` で処理済みバッチを確認できます

---

## `notebooklm` コマンドが見つからない

### 症状

```
エラー: notebooklm コマンドが見つかりません。
先に setup.sh を実行してください:
  bash scripts/setup.sh
```

### 原因

- `notebooklm-py` パッケージがインストールされていない
- Python のパスが通っていない
- 仮想環境内でインストールしたが、現在の環境からは見えない

### 対処法

1. セットアップスクリプトを実行する：
   ```bash
   bash scripts/setup.sh
   ```
2. 手動でインストールする場合：
   ```bash
   pip install notebooklm-py
   pip install "notebooklm-py[browser]"
   playwright install chromium
   ```
3. パスを確認する：
   ```bash
   which notebooklm
   # または
   python3 -m pip show notebooklm-py
   ```
4. 仮想環境を使用している場合は、正しい環境がアクティブか確認する

---

## Python バージョンエラー

### 症状

```
Python 3.10+ が必要です
```

または `SyntaxError` がスクリプト実行時に発生する。

### 原因

- Python 3.10 未満のバージョンが使用されている
- `python3` コマンドが古いバージョンを指している

### 対処法

1. Python バージョンを確認する：
   ```bash
   python3 --version
   ```
2. Python 3.10 以上がインストールされていない場合はインストールする：
   - **macOS**: `brew install python@3.12`
   - **Ubuntu/Debian**: `sudo apt install python3.12`
   - **Windows**: [python.org](https://www.python.org/downloads/) からダウンロード
3. 複数バージョンがインストールされている場合は、明示的にバージョンを指定する：
   ```bash
   python3.12 scripts/process_pdfs.py ./papers
   ```

---

## その他のエラー

上記に該当しないエラーが発生した場合：

1. `errors.log` の内容を確認する
2. `--dry-run` で処理計画を確認する
3. `--batch-size 1` で1件ずつ処理して問題の PDF を特定する
4. [GitHub Issues](https://github.com/{user}/pdf-to-notebooklm-audio/issues) で報告する
