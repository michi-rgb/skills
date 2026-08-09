#!/usr/bin/env python3
"""PDF文書 → Markdown 変換の下ごしらえスクリプト。

依存: poppler-utils (pdftoppm/pdftotext/pdfinfo), pdfplumber, Pillow

サブコマンド:
  pages   ページ画像(PNG)とページごとのテキスト層を出力
  figures 図・グラフ領域を自動検出して切り出し画像を出力
  crop    ページ画像のピクセル座標を指定して手動で切り出し

使い方:
  python3 extract.py pages   input.pdf outdir [--dpi 150] [--first N] [--last N]
  python3 extract.py figures input.pdf outdir [--first N] [--last N] [--dpi 200]
  python3 extract.py crop    input.pdf outdir --page N --box x0,y0,x1,y1
                             [--box-dpi 150] [--dpi 200] [--suffix m1]

crop の --box は「pages が出力した --box-dpi 解像度のページ画像上のピクセル座標」
(left, top, right, bottom)。出力は --dpi 解像度で切り出される。
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


# ---------------------------------------------------------------- pages

def cmd_pages(args):
    pdf = str(Path(args.pdf).resolve())
    outdir = Path(args.outdir)
    img_dir = outdir / "pages"
    txt_dir = Path(tempfile.gettempdir()) / (Path(pdf).stem + "_text")
    img_dir.mkdir(parents=True, exist_ok=True)
    txt_dir.mkdir(parents=True, exist_ok=True)

    total = page_count(pdf)
    first = max(1, args.first)
    last = total if args.last <= 0 else min(args.last, total)

    tmp_prefix = str(img_dir / "_tmp")
    r = run(["pdftoppm", "-png", "-r", str(args.dpi),
             "-f", str(first), "-l", str(last), pdf, tmp_prefix])
    if r.returncode != 0:
        sys.exit(f"ERROR: pdftoppm 失敗: {r.stderr[:500]}")
    for f in sorted(img_dir.glob("_tmp-*.png")):
        n = int(f.stem.split("-")[-1])
        f.rename(img_dir / f"page_{n:03d}.png")

    empty = garbled = 0
    for n in range(first, last + 1):
        r = run(["pdftotext", "-f", str(n), "-l", str(n), "-layout", pdf, "-"])
        text = r.stdout.strip()
        (txt_dir / f"page_{n:03d}.txt").write_text(text + "\n", encoding="utf-8")
        if not text:
            empty += 1
        else:
            bad = sum(1 for c in text if c == "�")
            letters = sum(1 for c in text if c.isalnum())
            if bad > 5 or (len(text) > 30 and letters < len(text) * 0.3):
                garbled += 1

    n_pages = last - first + 1
    print(f"総ページ数: {total}")
    print(f"処理範囲: {first}-{last} ({n_pages}ページ)")
    print(f"ページ画像: {img_dir}/page_{first:03d}.png ... page_{last:03d}.png ({args.dpi}dpi)")
    print(f"テキスト層: {txt_dir}/")
    if empty + garbled > n_pages * 0.3:
        print(f"警告: テキスト層が空・破損のページが多数 (空:{empty} 破損疑い:{garbled})。"
              "抽出テキストは信用せず、ページ画像の読み取りを主としてください。")
    else:
        print(f"テキスト層: おおむね良好 (空:{empty} 破損疑い:{garbled})")


# ---------------------------------------------------------------- figures

def _merge(boxes, gap):
    """互いに gap pt 以内で接触するボックスをクラスタリングして統合する。"""
    boxes = [list(b) for b in boxes]
    changed = True
    while changed:
        changed = False
        out = []
        while boxes:
            a = boxes.pop()
            merged = False
            for b in out:
                if (a[0] - gap < b[2] and b[0] - gap < a[2] and
                        a[1] - gap < b[3] and b[1] - gap < a[3]):
                    b[0] = min(a[0], b[0]); b[1] = min(a[1], b[1])
                    b[2] = max(a[2], b[2]); b[3] = max(a[3], b[3])
                    merged = changed = True
                    break
            if not merged:
                out.append(a)
        boxes = out
    return boxes


def _crop_png(pdf, page_no, box_pt, dpi, out_path):
    """box_pt = (x0, top, x1, bottom) in PDF points."""
    s = dpi / 72.0
    x = max(0, int(box_pt[0] * s)); y = max(0, int(box_pt[1] * s))
    w = int((box_pt[2] - box_pt[0]) * s); h = int((box_pt[3] - box_pt[1]) * s)
    if w <= 0 or h <= 0:
        return False
    tmp = out_path.parent / (out_path.stem + "_tmp")
    r = run(["pdftoppm", "-png", "-r", str(dpi), "-f", str(page_no), "-l", str(page_no),
             "-x", str(x), "-y", str(y), "-W", str(w), "-H", str(h),
             pdf, str(tmp)])
    if r.returncode != 0:
        return False
    outs = sorted(tmp.parent.glob(tmp.name + "-*.png"))
    if not outs:
        return False
    outs[0].rename(out_path)
    for f in outs[1:]:
        f.unlink()
    return True


def cmd_figures(args):
    import pdfplumber

    pdf = str(Path(args.pdf).resolve())
    outdir = Path(args.outdir)
    img_dir = outdir / "images"
    img_dir.mkdir(parents=True, exist_ok=True)

    total = page_count(pdf)
    first = max(1, args.first)
    last = total if args.last <= 0 else min(args.last, total)

    found = 0
    with pdfplumber.open(pdf) as doc:
        for n in range(first, last + 1):
            page = doc.pages[n - 1]
            pw, ph = page.width, page.height
            cand = []
            # 埋め込みラスタ画像
            for im in page.images:
                cand.append((im["x0"], im["top"], im["x1"], im["bottom"]))
            # ベクター描画 (線・曲線・矩形)。罫線らしき全幅の水平線と
            # ページ枠らしき巨大矩形は除外
            for obj in page.lines + page.curves + page.rects:
                x0, x1 = obj["x0"], obj["x1"]
                t, b = obj["top"], obj["bottom"]
                w, h = x1 - x0, b - t
                if w > pw * 0.85 and h < 3:      # 水平罫線
                    continue
                if w * h > pw * ph * 0.85:       # ページ枠
                    continue
                cand.append((x0, t, x1, b))
            if not cand:
                continue

            clusters = _merge(cand, gap=8)
            # 図中のテキスト(軸ラベル等)を取り込むため、クラスタに重なる単語で拡張
            words = page.extract_words()
            for _ in range(2):
                for c in clusters:
                    for wd in words:
                        if (wd["x0"] < c[2] + 6 and c[0] - 6 < wd["x1"] and
                                wd["top"] < c[3] + 6 and c[1] - 6 < wd["bottom"]):
                            c[0] = min(c[0], wd["x0"]); c[1] = min(c[1], wd["top"])
                            c[2] = max(c[2], wd["x1"]); c[3] = max(c[3], wd["bottom"])
                clusters = _merge(clusters, gap=8)

            idx = 0
            for c in sorted(clusters, key=lambda c: (c[1], c[0])):
                w, h = c[2] - c[0], c[3] - c[1]
                if w < args.min_size or h < args.min_size:
                    continue
                if w * h > pw * ph * 0.9:
                    continue
                idx += 1
                pad = args.pad
                box = (max(0, c[0] - pad), max(0, c[1] - pad),
                       min(pw, c[2] + pad), min(ph, c[3] + pad))
                out = img_dir / f"fig_p{n:03d}_{idx}.png"
                if _crop_png(pdf, n, box, args.dpi, out):
                    found += 1
                    print(f"p.{n:3d}  {out.name}  bbox_pt=({box[0]:.0f},{box[1]:.0f},"
                          f"{box[2]:.0f},{box[3]:.0f})  {w:.0f}x{h:.0f}pt")
    print(f"---")
    print(f"検出した図候補: {found}個 -> {img_dir}/")
    print("注意: これは機械的な候補検出です。誤検出(罫線・表・飾り)や取りこぼしが"
          "あり得るため、必ず各画像をReadで確認し、不要なら削除、欠けていれば"
          " crop サブコマンドで切り直してください。")


# ---------------------------------------------------------------- crop

def cmd_crop(args):
    pdf = str(Path(args.pdf).resolve())
    img_dir = Path(args.outdir) / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    px = [float(v) for v in args.box.split(",")]
    if len(px) != 4:
        sys.exit("ERROR: --box は x0,y0,x1,y1 (左,上,右,下 ピクセル) で指定")
    s = 72.0 / args.box_dpi
    box_pt = (px[0] * s, px[1] * s, px[2] * s, px[3] * s)
    suffix = args.suffix or "m1"
    out = img_dir / f"fig_p{args.page:03d}_{suffix}.png"
    if _crop_png(pdf, args.page, box_pt, args.dpi, out):
        print(f"出力: {out}")
    else:
        sys.exit("ERROR: 切り出しに失敗しました")


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("pages")
    p.add_argument("pdf"); p.add_argument("outdir")
    p.add_argument("--dpi", type=int, default=150)
    p.add_argument("--first", type=int, default=1)
    p.add_argument("--last", type=int, default=0)
    p.set_defaults(func=cmd_pages)

    p = sub.add_parser("figures")
    p.add_argument("pdf"); p.add_argument("outdir")
    p.add_argument("--dpi", type=int, default=200)
    p.add_argument("--first", type=int, default=1)
    p.add_argument("--last", type=int, default=0)
    p.add_argument("--min-size", type=float, default=40,
                   help="この辺長(pt)未満のクラスタは無視")
    p.add_argument("--pad", type=float, default=6)
    p.set_defaults(func=cmd_figures)

    p = sub.add_parser("crop")
    p.add_argument("pdf"); p.add_argument("outdir")
    p.add_argument("--page", type=int, required=True)
    p.add_argument("--box", required=True)
    p.add_argument("--box-dpi", type=int, default=150,
                   help="--box の座標系のdpi (pagesのページ画像=150)")
    p.add_argument("--dpi", type=int, default=200)
    p.add_argument("--suffix", default=None)
    p.set_defaults(func=cmd_crop)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
