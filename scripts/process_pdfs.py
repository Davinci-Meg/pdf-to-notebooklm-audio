#!/usr/bin/env python3
"""
フォルダ内のPDFをNotebookLMに登録し、音声解説と要約を自動生成する。

使用例:
  python3 process_pdfs.py ./papers
  python3 process_pdfs.py ./papers --lang en --audio-only
  python3 process_pdfs.py ./papers -o ./output --batch-size 10
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from textwrap import dedent

# 同じ scripts/ ディレクトリ内のモジュールをインポートできるよう調整
sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import chunked, find_pdfs, safe_filename, format_duration
from authenticate import check_auth

from notebooklm import NotebookLMClient, RateLimitError

# ---------------------------------------------------------------------------
# ロギング設定
# ---------------------------------------------------------------------------
logger = logging.getLogger("process_pdfs")

# ---------------------------------------------------------------------------
# デフォルトプロンプト
# ---------------------------------------------------------------------------
DEFAULT_SUMMARY_PROMPT_JA = dedent("""\
    ソースに含まれる全ての論文について、各論文ごとに以下の形式で
    日本語の要約を作成してください：

    ## [論文タイトル]
    - **著者**: （著者名・所属）
    - **概要**: （2〜3文で研究の目的と内容）
    - **手法**: （使用した手法の説明）
    - **結果・貢献**: （主な結果や学術的貢献）
    - **キーワード**: （3〜5個）

    全論文を漏れなく要約してください。
""")

DEFAULT_SUMMARY_PROMPT_EN = dedent("""\
    For every paper in the sources, create a structured summary
    in the following format:

    ## [Paper Title]
    - **Authors**: (names and affiliations)
    - **Abstract**: (2-3 sentences on purpose and content)
    - **Method**: (description of the approach)
    - **Results/Contribution**: (key findings)
    - **Keywords**: (3-5 keywords)

    Summarize all papers without omission.
""")

DEFAULT_AUDIO_PROMPT_JA = dedent("""\
    日本語で解説してください。
    ソースに含まれる論文を、研究者同士の対話形式で紹介してください。
    各論文の面白いポイントや新規性に焦点を当て、
    聴いている人が興味を持てるようなわかりやすい解説をお願いします。
""")

DEFAULT_AUDIO_PROMPT_EN = dedent("""\
    Create an engaging discussion about the papers in the sources.
    Use a conversational tone between two researchers.
    Focus on interesting points and novelty of each paper.
""")

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------
VERSION = "1.0.0"
MAX_RETRIES = 3
RATE_LIMIT_WAIT_SEC = 30


# ---------------------------------------------------------------------------
# 引数パース
# ---------------------------------------------------------------------------
def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="PDFフォルダ → NotebookLM 音声解説 & 要約 自動生成"
    )
    p.add_argument(
        "input_dir", type=Path,
        help="PDFファイルが入ったフォルダのパス",
    )
    p.add_argument(
        "-o", "--output", type=Path,
        default=Path("./notebooklm_output"),
        help="出力先フォルダ (default: ./notebooklm_output)",
    )
    p.add_argument(
        "--lang", default="ja",
        help="生成言語コード (default: ja)",
    )
    p.add_argument(
        "--audio-only", action="store_true",
        help="音声のみ生成（要約をスキップ）",
    )
    p.add_argument(
        "--summary-only", action="store_true",
        help="要約のみ生成（音声をスキップ）",
    )
    p.add_argument(
        "--notebook-name", default=None,
        help="ノートブック名 (default: フォルダ名_YYYYMMDD_HHMMSS)",
    )
    p.add_argument(
        "--batch-size", type=int, default=20,
        help="1ノートブックあたりの最大PDF数 (default: 20)",
    )
    p.add_argument(
        "--audio-prompt", default=None,
        help="Audio Overview 生成用カスタムプロンプト",
    )
    p.add_argument(
        "--summary-prompt", default=None,
        help="要約生成用カスタムプロンプト",
    )
    p.add_argument(
        "--timeout", type=int, default=600,
        help="音声生成タイムアウト秒数 (default: 600)",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="実際の処理を行わず計画のみ表示",
    )
    return p.parse_args(argv)


# ---------------------------------------------------------------------------
# プロンプト選択
# ---------------------------------------------------------------------------
def get_summary_prompt(args) -> str:
    if args.summary_prompt:
        return args.summary_prompt
    if args.lang == "ja":
        return DEFAULT_SUMMARY_PROMPT_JA
    return DEFAULT_SUMMARY_PROMPT_EN


def get_audio_prompt(args) -> str:
    if args.audio_prompt:
        return args.audio_prompt
    if args.lang == "ja":
        return DEFAULT_AUDIO_PROMPT_JA
    return DEFAULT_AUDIO_PROMPT_EN


# ---------------------------------------------------------------------------
# リトライ付きAPIコール
# ---------------------------------------------------------------------------
async def retry_with_backoff(coro_func, description: str, max_retries=MAX_RETRIES):
    """コルーチンファクトリを最大max_retries回リトライする。

    RateLimitError の場合は30秒待機してリトライする。
    その他のエラーは指数バックオフでリトライする。
    """
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            return await coro_func()
        except RateLimitError as e:
            last_error = e
            if attempt < max_retries:
                logger.warning(
                    "%s: レート制限検出。%d秒待機してリトライします (試行 %d/%d)",
                    description, RATE_LIMIT_WAIT_SEC, attempt, max_retries,
                )
                await asyncio.sleep(RATE_LIMIT_WAIT_SEC)
            else:
                logger.error(
                    "%s: レート制限により全 %d 回の試行が失敗しました",
                    description, max_retries,
                )
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                wait = 2 ** attempt
                logger.warning(
                    "%s: 失敗 (%s)。%d秒後にリトライします (試行 %d/%d)",
                    description, e, wait, attempt, max_retries,
                )
                await asyncio.sleep(wait)
            else:
                logger.error(
                    "%s: 全 %d 回の試行が失敗しました。最後のエラー: %s",
                    description, max_retries, e,
                )
    raise last_error


# ---------------------------------------------------------------------------
# バッチ処理
# ---------------------------------------------------------------------------
async def process_batch(
    client: NotebookLMClient,
    batch_pdfs: list[Path],
    batch_index: int,
    total_batches: int,
    notebook_name: str,
    args,
    output_dir: Path,
    error_log_path: Path,
) -> dict:
    """1バッチ分のPDFを処理し、結果辞書を返す。"""
    batch_id = f"batch_{batch_index + 1:03d}"
    batch_dir = output_dir / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)

    batch_start = time.monotonic()
    result = {
        "batch_id": batch_id,
        "notebook_id": None,
        "notebook_name": notebook_name,
        "pdf_count": len(batch_pdfs),
        "pdfs": [p.name for p in batch_pdfs],
        "summary_generated": False,
        "audio_generated": False,
        "audio_duration_sec": None,
        "processing_time_sec": 0,
        "errors": [],
    }

    # [4a] ノートブック作成
    logger.info(
        "[バッチ %d/%d] ノートブック作成: %s",
        batch_index + 1, total_batches, notebook_name,
    )
    try:
        notebook = await retry_with_backoff(
            lambda: client.notebooks.create(title=notebook_name),
            f"ノートブック作成 ({notebook_name})",
        )
        notebook_id = notebook.id
        result["notebook_id"] = notebook_id
    except Exception as e:
        msg = f"ノートブック作成失敗: {e}"
        logger.error(msg)
        result["errors"].append(msg)
        _append_error_log(error_log_path, batch_id, msg)
        result["processing_time_sec"] = time.monotonic() - batch_start
        return result

    # [4b] PDFソース登録（逐次 + リトライ）
    registered_count = 0
    for pdf_path in batch_pdfs:
        try:
            await retry_with_backoff(
                lambda p=pdf_path: client.sources.add_file(
                    notebook_id, p, wait=True,
                ),
                f"ソース登録 ({pdf_path.name})",
            )
            registered_count += 1
            logger.info(
                "  ソース登録完了: %s (%d/%d)",
                pdf_path.name, registered_count, len(batch_pdfs),
            )
        except Exception as e:
            msg = f"ソース登録スキップ ({pdf_path.name}): {e}"
            logger.warning(msg)
            result["errors"].append(msg)
            _append_error_log(error_log_path, batch_id, msg)

    if registered_count == 0:
        msg = "登録成功したPDFがないためバッチをスキップします"
        logger.warning(msg)
        result["errors"].append(msg)
        result["processing_time_sec"] = time.monotonic() - batch_start
        return result

    # [4c] 要約テキスト生成（--audio-only 時はスキップ）
    if not args.audio_only:
        summary_prompt = get_summary_prompt(args)
        logger.info(
            "[バッチ %d/%d] 要約テキスト生成中...",
            batch_index + 1, total_batches,
        )
        try:
            ask_result = await retry_with_backoff(
                lambda: client.chat.ask(notebook_id, summary_prompt),
                "要約テキスト生成",
            )
            summary_text = ask_result.answer

            # summary.md ヘッダー生成
            lang_label = "日本語" if args.lang == "ja" else args.lang
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            summary_header = (
                f"# 論文要約 — {notebook_name}\n\n"
                f"生成日時: {now_str}\n"
                f"言語: {lang_label}\n"
                f"ソースPDF数: {registered_count}\n\n---\n\n"
            )

            summary_path = batch_dir / "summary.md"
            summary_path.write_text(
                summary_header + summary_text, encoding="utf-8",
            )
            result["summary_generated"] = True
            logger.info("  要約保存: %s", summary_path)
        except Exception as e:
            msg = f"要約生成失敗: {e}"
            logger.error(msg)
            result["errors"].append(msg)
            _append_error_log(error_log_path, batch_id, msg)

    # [4d] 音声解説生成（--summary-only 時はスキップ）
    if not args.summary_only:
        audio_prompt = get_audio_prompt(args)
        logger.info(
            "[バッチ %d/%d] 音声解説生成中 (タイムアウト: %d秒)...",
            batch_index + 1, total_batches, args.timeout,
        )
        try:
            # 音声生成を開始
            gen_status = await retry_with_backoff(
                lambda: client.artifacts.generate_audio(
                    notebook_id,
                    language=args.lang,
                    instructions=audio_prompt,
                ),
                "音声解説生成リクエスト",
            )

            # 生成完了を待機
            await client.artifacts.wait_for_completion(
                notebook_id,
                gen_status.task_id,
                timeout=float(args.timeout),
            )

            # 音声ファイルをダウンロード
            audio_path = batch_dir / "audio_overview.mp3"
            await client.artifacts.download_audio(
                notebook_id, str(audio_path),
            )

            result["audio_generated"] = True
            logger.info("  音声保存: %s", audio_path)
        except asyncio.TimeoutError:
            msg = (
                f"音声生成がタイムアウトしました ({args.timeout}秒)。"
                f"--timeout オプションでタイムアウト値を増やしてください。"
            )
            logger.error(msg)
            result["errors"].append(msg)
            _append_error_log(error_log_path, batch_id, msg)
        except Exception as e:
            msg = f"音声生成失敗: {e}"
            logger.error(msg)
            result["errors"].append(msg)
            _append_error_log(error_log_path, batch_id, msg)

    # バッチ metadata.json 保存
    result["processing_time_sec"] = round(time.monotonic() - batch_start, 1)
    metadata_path = batch_dir / "metadata.json"
    metadata_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # [4e] 進捗ログ
    logger.info(
        "[バッチ %d/%d] 完了 (所要時間: %s, エラー: %d件)",
        batch_index + 1,
        total_batches,
        format_duration(result["processing_time_sec"]),
        len(result["errors"]),
    )
    return result


# ---------------------------------------------------------------------------
# ドライラン表示
# ---------------------------------------------------------------------------
def print_dry_run(pdfs: list[Path], batches: list[list[Path]], args):
    """--dry-run 時に処理計画を表示する。"""
    print("\n=== ドライラン (実際の処理は行いません) ===\n")
    print(f"入力フォルダ:     {args.input_dir.resolve()}")
    print(f"出力フォルダ:     {args.output.resolve()}")
    print(f"PDF総数:          {len(pdfs)}")
    print(f"バッチサイズ:     {args.batch_size}")
    print(f"バッチ数:         {len(batches)}")
    print(f"言語:             {args.lang}")
    print(f"要約生成:         {'スキップ' if args.audio_only else 'あり'}")
    print(f"音声生成:         {'スキップ' if args.summary_only else 'あり'}")
    print(f"音声タイムアウト: {args.timeout}秒")
    print()

    for i, batch in enumerate(batches):
        nb_name = _make_notebook_name(args, i, len(batches))
        print(f"--- バッチ {i + 1}/{len(batches)}: {nb_name} ---")
        for pdf_path in batch:
            print(f"  - {pdf_path.name}")
    print()


# ---------------------------------------------------------------------------
# 結果レポート
# ---------------------------------------------------------------------------
def print_report(results: list[dict], total_time: float, output_dir: Path):
    """処理完了後の結果レポートを表示する。"""
    total_pdfs = sum(r["pdf_count"] for r in results)
    total_errors = sum(len(r["errors"]) for r in results)
    summaries = sum(1 for r in results if r["summary_generated"])
    audios = sum(1 for r in results if r["audio_generated"])

    print("\n" + "=" * 60)
    print("処理結果レポート")
    print("=" * 60)
    print(f"処理バッチ数:     {len(results)}")
    print(f"PDF総数:          {total_pdfs}")
    print(f"要約生成:         {summaries}/{len(results)} バッチ")
    print(f"音声生成:         {audios}/{len(results)} バッチ")
    print(f"合計エラー:       {total_errors}件")
    print(f"合計処理時間:     {format_duration(total_time)}")
    print(f"出力先:           {output_dir.resolve()}")

    if total_errors > 0:
        print(f"\nエラーログ:       {output_dir.resolve() / 'errors.log'}")
        print("\nエラー詳細:")
        for r in results:
            for err in r["errors"]:
                print(f"  [{r['batch_id']}] {err}")

    print("=" * 60 + "\n")


# ---------------------------------------------------------------------------
# manifest.json 生成
# ---------------------------------------------------------------------------
def write_manifest(results: list[dict], args, total_time: float, output_dir: Path):
    """manifest.json を出力フォルダに書き出す。"""
    jst = timezone(timedelta(hours=9))
    manifest = {
        "tool": "pdf-to-notebooklm-audio",
        "version": VERSION,
        "created_at": datetime.now(jst).isoformat(),
        "language": args.lang,
        "input_dir": str(args.input_dir.resolve()),
        "total_pdfs": sum(r["pdf_count"] for r in results),
        "batches": results,
        "total_errors": sum(len(r["errors"]) for r in results),
        "total_processing_time_sec": round(total_time, 1),
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("manifest.json 保存: %s", manifest_path)


# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------
def _make_notebook_name(args, batch_index: int, total_batches: int) -> str:
    """ノートブック名を生成する。"""
    if args.notebook_name:
        base = args.notebook_name
    else:
        folder_name = safe_filename(args.input_dir.resolve().name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = f"{folder_name}_{timestamp}"

    if total_batches > 1:
        return f"{base} ({batch_index + 1}/{total_batches})"
    return base


def _append_error_log(error_log_path: Path, batch_id: str, message: str):
    """errors.log にエラーメッセージを追記する。"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(error_log_path, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] [{batch_id}] {message}\n")


def _setup_logging():
    """ロギングを設定する。"""
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    ))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------
async def async_main(args):
    total_start = time.monotonic()

    # [1] 引数バリデーション
    if not args.input_dir.exists():
        logger.error("エラー: 指定されたフォルダが存在しません: %s", args.input_dir)
        sys.exit(1)

    if not args.input_dir.is_dir():
        logger.error("エラー: 指定されたパスはフォルダではありません: %s", args.input_dir)
        sys.exit(1)

    pdfs = find_pdfs(args.input_dir)
    if not pdfs:
        logger.error("エラー: PDFファイルが見つかりません: %s", args.input_dir)
        sys.exit(1)

    logger.info("PDF %d 件を検出: %s", len(pdfs), args.input_dir.resolve())

    # [3] バッチ分割
    batches = list(chunked(pdfs, args.batch_size))
    logger.info(
        "バッチ分割: %d バッチ (バッチサイズ: %d)",
        len(batches), args.batch_size,
    )

    # --dry-run の場合は認証不要で計画のみ表示して終了
    if args.dry_run:
        print_dry_run(pdfs, batches, args)
        return

    # [2] 認証チェック
    if not check_auth():
        logger.error(
            "認証が必要です。以下を実行してください:\n"
            "  python3 scripts/authenticate.py"
        )
        sys.exit(1)

    # 出力ディレクトリ作成
    output_dir = args.output
    output_dir.mkdir(parents=True, exist_ok=True)
    error_log_path = output_dir / "errors.log"

    # [4] メインループ
    results = []
    # NotebookLM の chat API は応答に時間がかかるためタイムアウトを長めに設定
    async with await NotebookLMClient.from_storage(timeout=120.0) as client:
        for i, batch in enumerate(batches):
            notebook_name = _make_notebook_name(args, i, len(batches))
            result = await process_batch(
                client=client,
                batch_pdfs=batch,
                batch_index=i,
                total_batches=len(batches),
                notebook_name=notebook_name,
                args=args,
                output_dir=output_dir,
                error_log_path=error_log_path,
            )
            results.append(result)

    # [5] 結果レポート
    total_time = round(time.monotonic() - total_start, 1)
    write_manifest(results, args, total_time, output_dir)
    print_report(results, total_time, output_dir)


def main():
    _setup_logging()
    args = parse_args()
    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
