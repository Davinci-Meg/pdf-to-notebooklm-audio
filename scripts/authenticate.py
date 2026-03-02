#!/usr/bin/env python3
"""NotebookLM 認証ヘルパー

使用方法:
  python3 authenticate.py          # 認証状態チェック、未認証なら認証実行
  python3 authenticate.py --force  # 強制再認証
  python3 authenticate.py --check  # 認証状態の確認のみ
"""
import argparse
import subprocess
import sys
import json
from pathlib import Path

STORAGE_PATH = Path.home() / ".notebooklm" / "storage_state.json"


def check_auth() -> bool:
    """認証状態を確認"""
    if not STORAGE_PATH.exists():
        return False
    try:
        data = json.loads(STORAGE_PATH.read_text(encoding="utf-8"))
        return bool(data.get("cookies"))
    except Exception:
        return False


def run_login():
    """ブラウザを開いて認証"""
    print("NotebookLM にログインします...")
    print("ブラウザが開くので Google アカウントでログインしてください。\n")
    try:
        result = subprocess.run(["notebooklm", "login"], capture_output=False)
        if result.returncode == 0 and check_auth():
            print("\n認証成功！")
        else:
            print("\n認証に失敗しました。再試行してください。")
            sys.exit(1)
    except FileNotFoundError:
        print("エラー: notebooklm コマンドが見つかりません。")
        print("先に setup.sh を実行してください:")
        print("  bash scripts/setup.sh")
        sys.exit(1)


def parse_args():
    p = argparse.ArgumentParser(description="NotebookLM 認証ヘルパー")
    p.add_argument("--force", action="store_true", help="強制再認証")
    p.add_argument("--check", action="store_true", help="認証状態の確認のみ")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.check:
        if check_auth():
            print("認証済みです。")
        else:
            print("未認証です。以下を実行してください:")
            print("  python3 scripts/authenticate.py")
            sys.exit(1)
        sys.exit(0)

    if check_auth() and not args.force:
        print("認証済みです（再認証するには --force を付けてください）")
        sys.exit(0)

    run_login()
