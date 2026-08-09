#!/usr/bin/env python3
"""PDFプレゼンの各ページをPNG画像に変換し、ページごとのテキストを抽出する。

poppler-utils (pdftoppm / pdftotext / pdfinfo) を使用。追加のpip依存なし。

使い方:
    python3 convert_pages.py input.pdf output_dir [--dpi 150] [--first N] [--last N]

出力:
    output_dir/images/page_001.png, page_002.png, ...   (成果物)
    <一時ディレクトリ>/<PDF名>_text/page_001.txt, ...    (テキスト層の抽出結果。
        中間生成物なので成果物フォルダには置かない。実際のパスは標準出力に表示)
    標準出力に総ページ数・処理範囲・テキスト層の品質ヒントを表示
"""
import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def page_count(pdf: str) -> int:
    out = run(["pdfinfo", pdf]).stdout
    m = re.search(r"^Pages:\s+(\d+)", out, re.M)
    if not m:
        sys.exit(f"ERROR: pdfinfo でページ数を取得できません: {pdf}")
    return int(m.group(1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("outdir")
    ap.add_argument("--dpi", type=int, default=150)
    ap.add_argument("--first", type=int, default=1)
    ap.add_argument("--last", type=int, default=0, help="0 = 最終ページまで")
    ap.add_argument("--textdir", default=None,
                    help="テキスト抽出の出力先（既定: 一時ディレクトリ。成果物を汚さないため）")
    args = ap.parse_args()

    pdf = str(Path(args.pdf).resolve())
    outdir = Path(args.outdir)
    img_dir = outdir / "images"
    if args.textdir:
        txt_dir = Path(args.textdir)
    else:
        txt_dir = Path(tempfile.gettempdir()) / (Path(pdf).stem + "_text")
    img_dir.mkdir(parents=True, exist_ok=True)
    txt_dir.mkdir(parents=True, exist_ok=True)

    total = page_count(pdf)
    first = max(1, args.first)
    last = total if args.last <= 0 else min(args.last, total)

    # --- 画像化 ---
    tmp_prefix = str(img_dir / "_tmp")
    r = run(["pdftoppm", "-png", "-r", str(args.dpi),
             "-f", str(first), "-l", str(last), pdf, tmp_prefix])
    if r.returncode != 0:
        sys.exit(f"ERROR: pdftoppm 失敗: {r.stderr[:500]}")

    # pdftoppm の出力 (_tmp-1.png / _tmp-01.png 等) を page_NNN.png に正規化
    for f in sorted(img_dir.glob("_tmp-*.png")):
        n = int(f.stem.split("-")[-1])
        f.rename(img_dir / f"page_{n:03d}.png")

    # --- ページごとのテキスト抽出 ---
    empty_pages = 0
    garbled_pages = 0
    for n in range(first, last + 1):
        r = run(["pdftotext", "-f", str(n), "-l", str(n), "-layout", pdf, "-"])
        text = r.stdout.strip()
        (txt_dir / f"page_{n:03d}.txt").write_text(text + "\n", encoding="utf-8")
        if not text:
            empty_pages += 1
        else:
            # 制御文字・置換文字が多い場合はテキスト層が壊れている可能性
            bad = sum(1 for c in text if c == "�")
            letters = sum(1 for c in text if c.isalnum())
            if bad > 5 or (len(text) > 30 and letters < len(text) * 0.3):
                garbled_pages += 1

    n_pages = last - first + 1
    print(f"総ページ数: {total}")
    print(f"処理範囲: {first}-{last} ({n_pages}ページ)")
    print(f"画像出力: {img_dir}/page_{first:03d}.png ... page_{last:03d}.png ({args.dpi}dpi)")
    print(f"テキスト出力: {txt_dir}/")
    if empty_pages + garbled_pages > n_pages * 0.3:
        print("警告: テキスト層が空・破損しているページが多数あります"
              f" (空:{empty_pages} 破損疑い:{garbled_pages})。"
              "抽出テキストは信用せず、ページ画像の読み取りを主としてください。")
    else:
        print(f"テキスト層: おおむね良好 (空:{empty_pages} 破損疑い:{garbled_pages})")


if __name__ == "__main__":
    main()
