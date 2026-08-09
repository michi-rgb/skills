#!/usr/bin/env python3
"""スライドプラン(JSON) → .pptx → .pdf を一気通貫で生成し、QA用サムネイルも出す。

  python3 make_pdf.py plan.json out.pdf [--thumbs] [--dpi 110]

処理:
  1) build_deck.js で plan.json から out.pptx を生成
  2) LibreOffice(soffice) で out.pptx → out.pdf に変換
  3) --thumbs 指定時、out.pdf の全ページを 1枚のサムネイル格子に連結して
     out_thumbs.png（12枚ごとに分割）に出す。Readで一覧確認して崩れを直すため。

依存: node + pptxgenjs(グローバル), soffice(LibreOffice), pdftoppm, Pillow
"""
import argparse
import glob
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def build_pptx(plan, pptx_out):
    env = dict(os.environ)
    # グローバルnpmを見つけられるよう保険
    env["NODE_PATH"] = ":".join(filter(None, [
        env.get("NODE_PATH", ""),
        "/usr/local/lib/node_modules_global/lib/node_modules",
        "/usr/local/lib/node_modules", "/usr/lib/node_modules",
    ]))
    r = run(["node", str(HERE / "build_deck.js"), str(plan), str(pptx_out)], env=env)
    if r.returncode != 0 or not Path(pptx_out).exists():
        sys.exit(f"ERROR: build_deck.js 失敗:\n{r.stdout}\n{r.stderr}")
    print(r.stdout.strip())


def pptx_to_pdf(pptx_in, pdf_out):
    pdf_out = Path(pdf_out).resolve()
    # soffice は「変換先ディレクトリに <入力名>.pdf」を書き、既存ファイルの上書きに
    # 失敗することがある（前回のロック残りなど）。そこで必ず**空のtempディレクトリ**へ
    # 変換し、その結果を pdf_out に書き出す。こうすればロック競合や古い出力の残留と
    # 無縁になる。
    with tempfile.TemporaryDirectory() as prof, tempfile.TemporaryDirectory() as conv:
        r = run(["soffice", "--headless", f"-env:UserInstallation=file://{prof}",
                 "--convert-to", "pdf", "--outdir", conv, str(pptx_in)])
        produced = Path(conv) / (Path(pptx_in).stem + ".pdf")
        if not produced.exists():
            sys.exit(f"ERROR: soffice 変換失敗:\n{r.stdout}\n{r.stderr}")
        data = produced.read_bytes()
    # 既存 pdf_out はまず truncate 上書きを試み、ダメなら unlink して作り直す。
    try:
        with open(pdf_out, "wb") as f:
            f.write(data)
    except OSError:
        try:
            pdf_out.unlink()
        except OSError:
            pass
        with open(pdf_out, "wb") as f:
            f.write(data)
    print(f"PDF: {pdf_out}")


def make_thumbs(pdf, dpi=110):
    from PIL import Image
    pdf = Path(pdf)
    with tempfile.TemporaryDirectory() as td:
        run(["pdftoppm", "-png", "-r", str(dpi), str(pdf), str(Path(td) / "p")])
        pages = sorted(glob.glob(str(Path(td) / "p-*.png")))
        if not pages:
            print("WARN: サムネイル生成でページ画像が得られませんでした")
            return
        cols = 3
        per = 12
        stem = pdf.with_suffix("")
        made = []
        for gi in range(0, len(pages), per):
            group = pages[gi:gi + per]
            ims = [Image.open(p).convert("RGB") for p in group]
            tw = max(i.width for i in ims)
            th = max(i.height for i in ims)
            scale = 520 / tw
            tw, th = int(tw * scale), int(th * scale)
            ims = [i.resize((tw, th)) for i in ims]
            rows = math.ceil(len(ims) / cols)
            pad, lab = 12, 22
            W = cols * tw + (cols + 1) * pad
            H = rows * (th + lab) + (rows + 1) * pad
            canvas = Image.new("RGB", (W, H), "white")
            from PIL import ImageDraw
            d = ImageDraw.Draw(canvas)
            for k, im in enumerate(ims):
                r_, c_ = divmod(k, cols)
                x = pad + c_ * (tw + pad)
                y = pad + r_ * (th + lab) + lab
                canvas.paste(im, (x, y))
                d.text((x, y - lab + 4), f"p.{gi + k + 1}", fill="black")
            out = f"{stem}_thumbs{'' if gi == 0 else '_' + str(gi // per + 1)}.png"
            canvas.save(out)
            made.append(out)
        print("THUMBS: " + ", ".join(made))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("pdf_out")
    ap.add_argument("--thumbs", action="store_true")
    ap.add_argument("--dpi", type=int, default=110)
    ap.add_argument("--keep-pptx", action="store_true")
    args = ap.parse_args()

    pptx_out = Path(args.pdf_out).with_suffix(".pptx")
    build_pptx(args.plan, pptx_out)
    pptx_to_pdf(pptx_out, args.pdf_out)
    if args.thumbs:
        make_thumbs(args.pdf_out, args.dpi)
    if not args.keep_pptx:
        try:
            Path(pptx_out).unlink()
        except OSError:
            pass


if __name__ == "__main__":
    main()
