#!/usr/bin/env python3
"""arXiv API 直接アクセスのフォールバックスクリプト（alphaXiv MCP が使えない場合用）。

依存: arxiv, requests, pypdf (いずれも pip)
参照実装: https://github.com/lukasschwab/arxiv.py

サブコマンド:
  search  キーワード/カテゴリ/日付範囲/IDリストで検索し、結果をJSON配列で標準出力に出す
  pdf     指定したarXiv IDのPDFをダウンロードする
  text    指定したarXiv IDまたはローカルPDFから本文テキストを抽出して標準出力に出す

使い方:
  python arxiv_fallback.py search "diffusion model" --max-results 30 \
      --category cs.LG --category cs.CV --sort-by submittedDate --date-from 2024-01-01
  python arxiv_fallback.py search --id-list 2005.14165,1706.03762
  python arxiv_fallback.py pdf 2005.14165 --outdir ./papers
  python arxiv_fallback.py text 2005.14165 --outdir ./papers --first 1 --last 3

注意:
- arXiv APIの利用規約によりリクエスト間隔は3秒以上必要（--delay の既定値3.0を減らさない）。
- search の結果には被引用数が含まれない（alphaXiv/arXivいずれも同じ制約）。
- summary（要旨）で足りる場合は pdf/text まで踏み込まない。本文確認が必要な論文だけ使う。
- 標準出力に出るのは search の JSON と text の抽出テキストのみ。進捗・警告は標準エラー出力。
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import arxiv

# Windows(PowerShell)のコンソールがcp932等の場合に日本語出力が文字化けするのを防ぐ
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

SORT_BY = {
    "relevance": arxiv.SortCriterion.Relevance,
    "lastUpdatedDate": arxiv.SortCriterion.LastUpdatedDate,
    "submittedDate": arxiv.SortCriterion.SubmittedDate,
}
SORT_ORDER = {
    "descending": arxiv.SortOrder.Descending,
    "ascending": arxiv.SortOrder.Ascending,
}

ID_RE = re.compile(r"(\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})(v\d+)?", re.IGNORECASE)


def build_query(args) -> str:
    parts = []
    if args.query:
        parts.append(f'all:"{args.query}"' if " " in args.query else f"all:{args.query}")
    if args.category:
        cat = " OR ".join(f"cat:{c}" for c in args.category)
        parts.append(f"({cat})" if len(args.category) > 1 else cat)
    if args.date_from or args.date_to:
        d_from = (args.date_from or "1991-01-01").replace("-", "") + "000000"
        d_to = (args.date_to or datetime.now(timezone.utc).strftime("%Y-%m-%d")).replace("-", "") + "235959"
        parts.append(f"submittedDate:[{d_from} TO {d_to}]")
    return " AND ".join(parts)


def result_to_dict(r: "arxiv.Result") -> dict:
    short_id = r.get_short_id()
    base_id = re.sub(r"v\d+$", "", short_id)
    return {
        "arxiv_id": short_id,
        "arxiv_id_base": base_id,
        "title": " ".join(r.title.split()),
        "authors": [a.name for a in r.authors],
        "published": r.published.date().isoformat() if r.published else None,
        "updated": r.updated.date().isoformat() if r.updated else None,
        "primary_category": r.primary_category,
        "categories": r.categories,
        "summary": " ".join(r.summary.split()),
        "comment": r.comment,
        "journal_ref": r.journal_ref,
        "doi": r.doi,
        "abs_url": r.entry_id,
        "pdf_url": r.pdf_url,
    }


def cmd_search(args):
    id_list = [s.strip() for s in args.id_list.split(",") if s.strip()] if args.id_list else None
    query = build_query(args)
    if not query and not id_list:
        sys.exit("ERROR: query か --id-list のどちらかを指定してください")

    search = arxiv.Search(
        query=query,
        id_list=id_list or [],
        max_results=args.max_results,
        sort_by=SORT_BY[args.sort_by],
        sort_order=SORT_ORDER[args.sort_order],
    )
    if args.delay < 3.0:
        print("警告: arXiv APIの利用規約によりdelayは3秒以上を推奨します", file=sys.stderr)
    client = arxiv.Client(page_size=min(100, args.max_results or 100), delay_seconds=args.delay)

    results = []
    try:
        for r in client.results(search):
            results.append(result_to_dict(r))
    except arxiv.UnexpectedEmptyPageError:
        print(f"警告: arXiv APIが途中で空ページを返したため打ち切り（{len(results)}件取得）", file=sys.stderr)
    except arxiv.HTTPError as e:
        if len(results) == 0:
            sys.exit(
                f"ERROR: arXiv APIへのリクエストが失敗しました（{e}）。\n"
                "一時的なレート制限（429/503）の可能性があります。数十秒〜数分待って"
                "再試行するか、--max-results を減らす／クエリ数を減らしてください。"
            )
        print(f"警告: 途中でarXiv APIエラーのため打ち切り（{len(results)}件取得, {e}）", file=sys.stderr)

    print(f"クエリ: {query or '(id_list指定)'}", file=sys.stderr)
    print(f"取得件数: {len(results)}", file=sys.stderr)
    print(json.dumps(results, ensure_ascii=False, indent=2))


def _resolve_id_and_pdf_url(id_or_url: str):
    m = ID_RE.search(id_or_url)
    if not m:
        sys.exit(f"ERROR: arXiv IDを認識できません: {id_or_url}")
    short_id = m.group(0)
    return short_id, f"https://arxiv.org/pdf/{short_id}"


def _download(pdf_url: str, out_path: Path):
    import requests

    try:
        resp = requests.get(pdf_url, timeout=60, headers={"User-Agent": "arxiv-deep-research-fallback/1.0"})
        resp.raise_for_status()
    except requests.RequestException as e:
        sys.exit(f"ERROR: PDFの取得に失敗しました（{pdf_url}）: {e}")
    out_path.write_bytes(resp.content)
    return len(resp.content)


def cmd_pdf(args):
    short_id, pdf_url = _resolve_id_and_pdf_url(args.id_or_url)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    out_path = outdir / f"{short_id.replace('/', '_')}.pdf"

    size = _download(pdf_url, out_path)
    print(f"保存先: {out_path} ({size:,} bytes)")


def cmd_text(args):
    from pypdf import PdfReader

    short_id, pdf_url = _resolve_id_and_pdf_url(args.id_or_url)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    pdf_path = outdir / f"{short_id.replace('/', '_')}.pdf"

    if not pdf_path.exists():
        _download(pdf_url, pdf_path)

    reader = PdfReader(str(pdf_path))
    total = len(reader.pages)
    first = max(1, args.first)
    last = total if args.last <= 0 else min(args.last, total)

    print(f"総ページ数: {total} / 抽出範囲: {first}-{last}", file=sys.stderr)
    print("注意: レイアウト崩れ・数式/表の抜けが起こり得る機械抽出です。重要箇所は元PDFで確認してください。", file=sys.stderr)
    for n in range(first, last + 1):
        text = (reader.pages[n - 1].extract_text() or "").strip()
        print(f"\n--- p.{n} ---")
        print(text)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("search", help="キーワード/カテゴリ/日付/IDリストで検索しJSONを標準出力に出す")
    p.add_argument("query", nargs="?", default="", help='検索語（例: "diffusion model"）。省略時は --id-list が必須')
    p.add_argument("--id-list", default=None, help="カンマ区切りのarXiv ID（例: 2005.14165,1706.03762）")
    p.add_argument("--category", action="append", default=[],
                   help="cat: フィルタ。複数指定でOR結合（例: --category cs.LG --category cs.CV）")
    p.add_argument("--date-from", default=None, help="YYYY-MM-DD（submittedDateの下限）")
    p.add_argument("--date-to", default=None, help="YYYY-MM-DD（submittedDateの上限）")
    p.add_argument("--max-results", type=int, default=50)
    p.add_argument("--sort-by", choices=list(SORT_BY), default="relevance")
    p.add_argument("--sort-order", choices=list(SORT_ORDER), default="descending")
    p.add_argument("--delay", type=float, default=3.0, help="リクエスト間隔秒（3秒未満は非推奨）")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("pdf", help="PDFをダウンロード")
    p.add_argument("id_or_url", help="arXiv ID（例: 2005.14165）またはabs/pdf URL")
    p.add_argument("--outdir", default=".")
    p.set_defaults(func=cmd_pdf)

    p = sub.add_parser("text", help="PDFから本文テキストを抽出して標準出力に出す（必要な論文のみ精読用）")
    p.add_argument("id_or_url", help="arXiv ID（例: 2005.14165）またはabs/pdf URL")
    p.add_argument("--outdir", default=".", help="PDFのダウンロード/キャッシュ先")
    p.add_argument("--first", type=int, default=1)
    p.add_argument("--last", type=int, default=0, help="0以下なら最終ページまで")
    p.set_defaults(func=cmd_text)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
