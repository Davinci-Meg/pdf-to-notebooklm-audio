#!/usr/bin/env python3
"""共通ユーティリティ"""
from itertools import islice
from pathlib import Path
import re
import logging

logger = logging.getLogger(__name__)


def chunked(iterable, size):
    """イテラブルを指定サイズのチャンクに分割"""
    it = iter(iterable)
    while True:
        chunk = list(islice(it, size))
        if not chunk:
            break
        yield chunk


def find_pdfs(directory: Path) -> list[Path]:
    """フォルダ内のPDFを再帰的に検索（.で始まるフォルダは除外）"""
    pdfs = []
    for p in sorted(directory.rglob("*.pdf")):
        if any(part.startswith(".") for part in p.parts):
            continue
        pdfs.append(p)
    return pdfs


def safe_filename(name: str, max_len: int = 100) -> str:
    """ファイル名に使えない文字を除去"""
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    return name[:max_len]


def format_duration(seconds: float) -> str:
    """秒数を人間が読みやすい形式に変換"""
    if seconds < 60:
        return f"{seconds:.1f}秒"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}分{secs}秒"
