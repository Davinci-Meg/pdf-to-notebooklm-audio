#!/usr/bin/env python3
"""
process_pdfs.py / utils.py / authenticate.py のテストスイート

テストケース一覧 (仕様書セクション8-1):
  T-01: PDFなしフォルダで実行 → エラーメッセージ
  T-02: PDF1件で summary-only 実行 → Markdown 出力
  T-03: PDF1件で audio-only 実行 → MP3 出力
  T-04: PDF 25件で batch-size=10 → 3バッチに分割
  T-05: --lang en で英語プロンプトが使用される
  T-06: 認証切れ時に適切なエラーメッセージ
  T-07: --dry-run で実際の API 呼び出しなし
  T-08: 不正PDFをスキップして他を処理続行
  T-09: manifest.json のスキーマ検証
"""

import asyncio
import json
import sys
from pathlib import Path
from unittest import mock
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# scripts/ ディレクトリからインポートできるように sys.path を調整
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from utils import chunked, find_pdfs, safe_filename, format_duration
from authenticate import check_auth

# process_pdfs は notebooklm をインポートするので、モックモジュールを先に用意
_mock_notebooklm = MagicMock()
_mock_notebooklm.RateLimitError = type("RateLimitError", (Exception,), {})
sys.modules["notebooklm"] = _mock_notebooklm

from process_pdfs import (
    parse_args,
    get_summary_prompt,
    get_audio_prompt,
    print_dry_run,
    write_manifest,
    async_main,
    DEFAULT_SUMMARY_PROMPT_JA,
    DEFAULT_SUMMARY_PROMPT_EN,
    DEFAULT_AUDIO_PROMPT_JA,
    DEFAULT_AUDIO_PROMPT_EN,
)


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
SAMPLE_PDF = FIXTURES_DIR / "sample.pdf"

# 最小限のPDFバイナリ（テスト中にtmpディレクトリへ書き込む用）
MINIMAL_PDF = b"""%PDF-1.0
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer<</Size 4/Root 1 0 R>>
startxref
206
%%EOF"""


@pytest.fixture
def empty_dir(tmp_path):
    """PDFが含まれない空のフォルダ"""
    d = tmp_path / "empty"
    d.mkdir()
    return d


@pytest.fixture
def single_pdf_dir(tmp_path):
    """PDF1件が含まれるフォルダ"""
    d = tmp_path / "single"
    d.mkdir()
    (d / "paper1.pdf").write_bytes(MINIMAL_PDF)
    return d


@pytest.fixture
def multi_pdf_dir(tmp_path):
    """PDF25件が含まれるフォルダ"""
    d = tmp_path / "multi"
    d.mkdir()
    for i in range(25):
        (d / f"paper_{i:03d}.pdf").write_bytes(MINIMAL_PDF)
    return d


@pytest.fixture
def mixed_pdf_dir(tmp_path):
    """正常PDFと不正PDFが混在するフォルダ"""
    d = tmp_path / "mixed"
    d.mkdir()
    (d / "valid1.pdf").write_bytes(MINIMAL_PDF)
    (d / "valid2.pdf").write_bytes(MINIMAL_PDF)
    (d / "corrupt.pdf").write_bytes(b"NOT A PDF FILE")
    return d


@pytest.fixture
def output_dir(tmp_path):
    """出力先フォルダ"""
    d = tmp_path / "output"
    d.mkdir()
    return d


# ---------------------------------------------------------------------------
# utils.py のテスト
# ---------------------------------------------------------------------------
class TestChunked:
    def test_exact_division(self):
        result = list(chunked(range(10), 5))
        assert result == [[0, 1, 2, 3, 4], [5, 6, 7, 8, 9]]

    def test_remainder(self):
        result = list(chunked(range(7), 3))
        assert result == [[0, 1, 2], [3, 4, 5], [6]]

    def test_empty(self):
        result = list(chunked([], 5))
        assert result == []

    def test_single_chunk(self):
        result = list(chunked([1, 2, 3], 10))
        assert result == [[1, 2, 3]]


class TestFindPdfs:
    def test_empty_dir(self, empty_dir):
        assert find_pdfs(empty_dir) == []

    def test_single_pdf(self, single_pdf_dir):
        pdfs = find_pdfs(single_pdf_dir)
        assert len(pdfs) == 1
        assert pdfs[0].name == "paper1.pdf"

    def test_hidden_dir_excluded(self, tmp_path):
        hidden = tmp_path / ".hidden"
        hidden.mkdir()
        (hidden / "secret.pdf").write_bytes(MINIMAL_PDF)
        (tmp_path / "visible.pdf").write_bytes(MINIMAL_PDF)
        pdfs = find_pdfs(tmp_path)
        assert len(pdfs) == 1
        assert pdfs[0].name == "visible.pdf"

    def test_sorted_order(self, multi_pdf_dir):
        pdfs = find_pdfs(multi_pdf_dir)
        names = [p.name for p in pdfs]
        assert names == sorted(names)


class TestSafeFilename:
    def test_removes_special_chars(self):
        assert safe_filename('a<b>c:d"e/f\\g|h?i*j') == "a_b_c_d_e_f_g_h_i_j"

    def test_max_length(self):
        long_name = "a" * 200
        assert len(safe_filename(long_name)) == 100

    def test_normal_name(self):
        assert safe_filename("my_paper") == "my_paper"


class TestFormatDuration:
    def test_seconds_only(self):
        assert format_duration(30.5) == "30.5秒"

    def test_minutes_and_seconds(self):
        assert format_duration(125) == "2分5秒"

    def test_zero(self):
        assert format_duration(0) == "0.0秒"


# ---------------------------------------------------------------------------
# authenticate.py のテスト
# ---------------------------------------------------------------------------
class TestCheckAuth:
    def test_no_storage_file(self, tmp_path):
        fake_path = tmp_path / "nonexistent" / "storage_state.json"
        with patch("authenticate.STORAGE_PATH", fake_path):
            assert check_auth() is False

    def test_valid_storage(self, tmp_path):
        storage = tmp_path / "storage_state.json"
        storage.write_text(
            json.dumps({"cookies": [{"name": "sid", "value": "abc123"}]}),
            encoding="utf-8",
        )
        with patch("authenticate.STORAGE_PATH", storage):
            assert check_auth() is True

    def test_empty_cookies(self, tmp_path):
        storage = tmp_path / "storage_state.json"
        storage.write_text(json.dumps({"cookies": []}), encoding="utf-8")
        with patch("authenticate.STORAGE_PATH", storage):
            assert check_auth() is False

    def test_corrupt_json(self, tmp_path):
        storage = tmp_path / "storage_state.json"
        storage.write_text("NOT JSON", encoding="utf-8")
        with patch("authenticate.STORAGE_PATH", storage):
            assert check_auth() is False


# ---------------------------------------------------------------------------
# process_pdfs.py のテスト
# ---------------------------------------------------------------------------
class TestParseArgs:
    def test_defaults(self, tmp_path):
        args = parse_args([str(tmp_path)])
        assert args.input_dir == tmp_path
        assert args.lang == "ja"
        assert args.batch_size == 20
        assert args.dry_run is False
        assert args.audio_only is False
        assert args.summary_only is False

    def test_custom_args(self, tmp_path):
        args = parse_args([
            str(tmp_path),
            "--lang", "en",
            "--batch-size", "10",
            "--audio-only",
            "--dry-run",
            "-o", str(tmp_path / "out"),
        ])
        assert args.lang == "en"
        assert args.batch_size == 10
        assert args.audio_only is True
        assert args.dry_run is True
        assert args.output == tmp_path / "out"


class TestPromptSelection:
    def test_ja_summary_prompt(self, tmp_path):
        args = parse_args([str(tmp_path)])
        prompt = get_summary_prompt(args)
        assert prompt == DEFAULT_SUMMARY_PROMPT_JA

    def test_en_summary_prompt(self, tmp_path):
        args = parse_args([str(tmp_path), "--lang", "en"])
        prompt = get_summary_prompt(args)
        assert prompt == DEFAULT_SUMMARY_PROMPT_EN

    def test_custom_summary_prompt(self, tmp_path):
        args = parse_args([
            str(tmp_path), "--summary-prompt", "Custom prompt"
        ])
        prompt = get_summary_prompt(args)
        assert prompt == "Custom prompt"

    def test_ja_audio_prompt(self, tmp_path):
        args = parse_args([str(tmp_path)])
        prompt = get_audio_prompt(args)
        assert prompt == DEFAULT_AUDIO_PROMPT_JA

    def test_en_audio_prompt(self, tmp_path):
        args = parse_args([str(tmp_path), "--lang", "en"])
        prompt = get_audio_prompt(args)
        assert prompt == DEFAULT_AUDIO_PROMPT_EN

    def test_custom_audio_prompt(self, tmp_path):
        args = parse_args([
            str(tmp_path), "--audio-prompt", "Talk about this"
        ])
        prompt = get_audio_prompt(args)
        assert prompt == "Talk about this"


# ---------------------------------------------------------------------------
# T-01: PDFなしフォルダで実行 → エラーメッセージ
# ---------------------------------------------------------------------------
class TestT01NoPdfFolder:
    def test_no_pdfs_exits_with_error(self, empty_dir, output_dir):
        args = parse_args([str(empty_dir), "-o", str(output_dir)])
        with pytest.raises(SystemExit) as exc_info:
            asyncio.run(async_main(args))
        assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# T-02: PDF1件で summary-only 実行 → Markdown 出力
# ---------------------------------------------------------------------------
class TestT02SummaryOnly:
    def test_summary_only_generates_markdown(self, single_pdf_dir, output_dir):
        args = parse_args([
            str(single_pdf_dir), "-o", str(output_dir), "--summary-only",
        ])

        # NotebookLMClient のモック構築
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.notebooks.create = AsyncMock(
            return_value=MagicMock(id="nb-001")
        )
        mock_client.sources.add_file = AsyncMock()
        mock_client.chat.ask = AsyncMock(
            return_value=MagicMock(answer="## Test Paper\n- summary here")
        )

        with patch("process_pdfs.check_auth", return_value=True), \
             patch("process_pdfs.NotebookLMClient") as MockClient:
            MockClient.from_storage = AsyncMock(return_value=mock_client)
            asyncio.run(async_main(args))

        # summary.md が生成されたか確認
        summary_files = list(output_dir.rglob("summary.md"))
        assert len(summary_files) == 1
        content = summary_files[0].read_text(encoding="utf-8")
        assert "論文要約" in content
        assert "Test Paper" in content

        # 音声ファイルは生成されていないこと
        audio_files = list(output_dir.rglob("*.mp3"))
        assert len(audio_files) == 0


# ---------------------------------------------------------------------------
# T-03: PDF1件で audio-only 実行 → MP3 出力
# ---------------------------------------------------------------------------
class TestT03AudioOnly:
    def test_audio_only_generates_mp3(self, single_pdf_dir, output_dir):
        args = parse_args([
            str(single_pdf_dir), "-o", str(output_dir), "--audio-only",
        ])

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.notebooks.create = AsyncMock(
            return_value=MagicMock(id="nb-002")
        )
        mock_client.sources.add_file = AsyncMock()
        mock_client.artifacts.generate_audio = AsyncMock(
            return_value=MagicMock(task_id="task-001")
        )
        mock_client.artifacts.wait_for_completion = AsyncMock()

        # download_audio が呼ばれたらダミーMP3ファイルを作成
        async def fake_download(notebook_id, path):
            Path(path).write_bytes(b"\xff\xfb\x90\x00" + b"\x00" * 100)

        mock_client.artifacts.download_audio = AsyncMock(
            side_effect=fake_download
        )

        with patch("process_pdfs.check_auth", return_value=True), \
             patch("process_pdfs.NotebookLMClient") as MockClient:
            MockClient.from_storage = AsyncMock(return_value=mock_client)
            asyncio.run(async_main(args))

        # MP3 が生成されたか確認
        audio_files = list(output_dir.rglob("audio_overview.mp3"))
        assert len(audio_files) == 1
        assert audio_files[0].stat().st_size > 0

        # summary は生成されていないこと
        summary_files = list(output_dir.rglob("summary.md"))
        assert len(summary_files) == 0


# ---------------------------------------------------------------------------
# T-04: PDF 25件で batch-size=10 → 3バッチに分割
# ---------------------------------------------------------------------------
class TestT04BatchSplit:
    def test_25_pdfs_with_batch_10_creates_3_batches(self, multi_pdf_dir):
        pdfs = find_pdfs(multi_pdf_dir)
        assert len(pdfs) == 25

        batches = list(chunked(pdfs, 10))
        assert len(batches) == 3
        assert len(batches[0]) == 10
        assert len(batches[1]) == 10
        assert len(batches[2]) == 5

    def test_dry_run_shows_3_batches(self, multi_pdf_dir, output_dir, capsys):
        args = parse_args([
            str(multi_pdf_dir), "-o", str(output_dir),
            "--batch-size", "10", "--dry-run",
        ])
        asyncio.run(async_main(args))
        captured = capsys.readouterr()
        assert "バッチ数:         3" in captured.out
        assert "バッチ 1/3" in captured.out
        assert "バッチ 2/3" in captured.out
        assert "バッチ 3/3" in captured.out


# ---------------------------------------------------------------------------
# T-05: --lang en で英語プロンプトが使用される
# ---------------------------------------------------------------------------
class TestT05LanguageSelection:
    def test_en_uses_english_prompts(self, tmp_path):
        args = parse_args([str(tmp_path), "--lang", "en"])
        summary_prompt = get_summary_prompt(args)
        audio_prompt = get_audio_prompt(args)
        assert "For every paper" in summary_prompt
        assert "Create an engaging discussion" in audio_prompt
        # 日本語が含まれていないこと
        assert "ソース" not in summary_prompt
        assert "日本語" not in audio_prompt

    def test_ja_uses_japanese_prompts(self, tmp_path):
        args = parse_args([str(tmp_path), "--lang", "ja"])
        summary_prompt = get_summary_prompt(args)
        audio_prompt = get_audio_prompt(args)
        assert "ソースに含まれる" in summary_prompt
        assert "日本語で解説" in audio_prompt


# ---------------------------------------------------------------------------
# T-06: 認証切れ時に適切なエラーメッセージ
# ---------------------------------------------------------------------------
class TestT06AuthExpired:
    def test_auth_failure_exits_with_error(self, single_pdf_dir, output_dir):
        args = parse_args([str(single_pdf_dir), "-o", str(output_dir)])
        with patch("process_pdfs.check_auth", return_value=False):
            with pytest.raises(SystemExit) as exc_info:
                asyncio.run(async_main(args))
            assert exc_info.value.code == 1

    def test_expired_storage_detected(self, tmp_path):
        """cookies が空の場合は認証切れと判定される"""
        storage = tmp_path / "storage_state.json"
        storage.write_text(json.dumps({"cookies": []}), encoding="utf-8")
        with patch("authenticate.STORAGE_PATH", storage):
            assert check_auth() is False


# ---------------------------------------------------------------------------
# T-07: --dry-run で実際の API 呼び出しなし
# ---------------------------------------------------------------------------
class TestT07DryRun:
    def test_dry_run_no_api_calls(self, single_pdf_dir, output_dir, capsys):
        args = parse_args([
            str(single_pdf_dir), "-o", str(output_dir), "--dry-run",
        ])

        with patch("process_pdfs.check_auth") as mock_auth, \
             patch("process_pdfs.NotebookLMClient") as MockClient:
            asyncio.run(async_main(args))

            # check_auth は呼ばれない（dry-runでは認証チェック不要）
            mock_auth.assert_not_called()
            # NotebookLMClient は使用されない
            MockClient.from_storage.assert_not_called()

        captured = capsys.readouterr()
        assert "ドライラン" in captured.out
        assert "PDF総数:          1" in captured.out

    def test_dry_run_shows_plan(self, multi_pdf_dir, output_dir, capsys):
        args = parse_args([
            str(multi_pdf_dir), "-o", str(output_dir),
            "--batch-size", "5", "--dry-run",
        ])
        asyncio.run(async_main(args))
        captured = capsys.readouterr()
        assert "PDF総数:          25" in captured.out
        assert "バッチサイズ:     5" in captured.out
        assert "バッチ数:         5" in captured.out


# ---------------------------------------------------------------------------
# T-08: 不正PDFをスキップして他を処理続行
# ---------------------------------------------------------------------------
class TestT08CorruptPdfSkip:
    def test_corrupt_pdf_skipped_others_continue(
        self, mixed_pdf_dir, output_dir
    ):
        args = parse_args([
            str(mixed_pdf_dir), "-o", str(output_dir), "--summary-only",
        ])

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.notebooks.create = AsyncMock(
            return_value=MagicMock(id="nb-003")
        )

        # corrupt.pdf の登録時のみ例外を発生させる
        async def fake_add_file(notebook_id, path, wait=True):
            if "corrupt" in path.name:
                raise Exception("Invalid PDF format")
            return MagicMock()

        mock_client.sources.add_file = AsyncMock(side_effect=fake_add_file)
        mock_client.chat.ask = AsyncMock(
            return_value=MagicMock(answer="## Valid Paper\n- summary")
        )

        with patch("process_pdfs.check_auth", return_value=True), \
             patch("process_pdfs.NotebookLMClient") as MockClient:
            MockClient.from_storage = AsyncMock(return_value=mock_client)
            asyncio.run(async_main(args))

        # manifest.json を確認
        manifest_path = output_dir / "manifest.json"
        assert manifest_path.exists()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        # 処理は完了しているはず
        assert manifest["total_pdfs"] == 3
        batches = manifest["batches"]
        assert len(batches) == 1

        # エラーが記録されている
        batch_errors = batches[0]["errors"]
        assert any("corrupt" in e.lower() for e in batch_errors)

        # 要約は生成されている（正常なPDFがあるため）
        assert batches[0]["summary_generated"] is True


# ---------------------------------------------------------------------------
# T-09: manifest.json のスキーマ検証
# ---------------------------------------------------------------------------
class TestT09ManifestSchema:
    def test_manifest_has_required_fields(self, single_pdf_dir, output_dir):
        args = parse_args([
            str(single_pdf_dir), "-o", str(output_dir), "--summary-only",
        ])

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.notebooks.create = AsyncMock(
            return_value=MagicMock(id="nb-004")
        )
        mock_client.sources.add_file = AsyncMock()
        mock_client.chat.ask = AsyncMock(
            return_value=MagicMock(answer="## Paper\n- summary")
        )

        with patch("process_pdfs.check_auth", return_value=True), \
             patch("process_pdfs.NotebookLMClient") as MockClient:
            MockClient.from_storage = AsyncMock(return_value=mock_client)
            asyncio.run(async_main(args))

        manifest_path = output_dir / "manifest.json"
        assert manifest_path.exists()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        # トップレベルの必須フィールド
        required_top = [
            "tool", "version", "created_at", "language",
            "input_dir", "total_pdfs", "batches",
            "total_errors", "total_processing_time_sec",
        ]
        for field in required_top:
            assert field in manifest, f"Missing top-level field: {field}"

        assert manifest["tool"] == "pdf-to-notebooklm-audio"
        assert manifest["version"] == "1.0.0"
        assert manifest["language"] == "ja"
        assert isinstance(manifest["batches"], list)
        assert len(manifest["batches"]) >= 1

        # バッチの必須フィールド
        batch = manifest["batches"][0]
        required_batch = [
            "batch_id", "notebook_id", "notebook_name",
            "pdf_count", "pdfs", "summary_generated",
            "audio_generated", "processing_time_sec", "errors",
        ]
        for field in required_batch:
            assert field in batch, f"Missing batch field: {field}"

        assert isinstance(batch["pdfs"], list)
        assert isinstance(batch["errors"], list)
        assert isinstance(batch["pdf_count"], int)
        assert isinstance(batch["processing_time_sec"], (int, float))

    def test_manifest_write_function(self, output_dir, tmp_path):
        """write_manifest 関数が正しい形式で出力するか"""
        args = parse_args([str(tmp_path), "--lang", "en"])
        results = [
            {
                "batch_id": "batch_001",
                "notebook_id": "nb-test",
                "notebook_name": "test_nb",
                "pdf_count": 2,
                "pdfs": ["a.pdf", "b.pdf"],
                "summary_generated": True,
                "audio_generated": False,
                "audio_duration_sec": None,
                "processing_time_sec": 45.2,
                "errors": [],
            }
        ]
        write_manifest(results, args, 45.2, output_dir)

        manifest_path = output_dir / "manifest.json"
        assert manifest_path.exists()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["language"] == "en"
        assert manifest["total_pdfs"] == 2
        assert manifest["total_errors"] == 0
        assert manifest["total_processing_time_sec"] == 45.2


# ---------------------------------------------------------------------------
# サンプルPDFフィクスチャの存在チェック
# ---------------------------------------------------------------------------
class TestFixtures:
    def test_sample_pdf_exists(self):
        assert SAMPLE_PDF.exists(), f"sample.pdf not found at {SAMPLE_PDF}"
        content = SAMPLE_PDF.read_bytes()
        assert content.startswith(b"%PDF"), "sample.pdf is not a valid PDF"
