#!/bin/bash
set -euo pipefail

echo "=== pdf-to-notebooklm-audio セットアップ ==="

# Python バージョンチェック
python3 -c "import sys; assert sys.version_info >= (3,10), 'Python 3.10+ が必要です'" \
  || { echo "❌ Python 3.10以上をインストールしてください"; exit 1; }

# 依存パッケージインストール
pip install --upgrade notebooklm-py 2>/dev/null \
  || pip install --upgrade --break-system-packages notebooklm-py

# ブラウザ対応版（初回認証用）
pip install "notebooklm-py[browser]" 2>/dev/null \
  || pip install --break-system-packages "notebooklm-py[browser]"
playwright install chromium

echo ""
echo "✅ セットアップ完了！"
echo ""
echo "次のステップ："
echo "  1. 認証:  notebooklm login"
echo "  2. 実行:  /pdf-to-notebooklm-audio"
