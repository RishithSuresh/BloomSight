"""Command-line interface for the BloomSight visual cryptography tools.

Subcommands::

    encrypt   split an image into shares
    decrypt   combine shares to recover an image
    demo      generate a sample secret, encrypt it and recover it

Run ``python -m visual_crypto <subcommand> --help`` for details.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Optional, Sequence

from PIL import Image, ImageDraw, ImageFont

from . import naor_shamir, theme, xor

_METHODS = ("xor", "naor-shamir")


def _save_share(share: Image.Image, path: Path, themed: bool, index: int) -> None:
    if themed:
        fg, bg = theme.palette_for(index)
        share = theme.apply_nature_tint(share, fg=fg, bg=bg)
    path.parent.mkdir(parents=True, exist_ok=True)
    share.save(path)


def _load_share_for_method(path: Path, method: str) -> Image.Image:
    img = Image.open(path)
    img.load()
    if method == "naor-shamir":
        # Themed tint -> de-tint via luminance threshold; native 1-bit
        # or grayscale shares are returned in mode "L" without dithering.
        if img.mode in ("RGB", "RGBA"):
            return theme.from_nature_tint(img)
        return img.convert("L")
    return img


def _cmd_encrypt(args: argparse.Namespace) -> int:
    src = Image.open(args.input)
    src.load()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.method == "xor":
        shares = xor.xor_encrypt(src, n_shares=args.shares, seed=args.seed)
    else:
        if args.shares != 2:
            raise SystemExit("naor-shamir only supports --shares 2")
        s1, s2 = naor_shamir.naor_shamir_encrypt(src, seed=args.seed)
        shares = [s1, s2]

    for i, share in enumerate(shares, start=1):
        _save_share(share, out_dir / f"share_{i}.png", args.themed, i - 1)

    print(theme.banner("BloomSight - Encrypt"))
    print(f"  method  : {args.method}")
    print(f"  shares  : {len(shares)} -> {out_dir}")
    print(f"  themed  : {args.themed}")
    return 0


def _cmd_decrypt(args: argparse.Namespace) -> int:
    paths = [Path(p) for p in args.shares]
    images = [_load_share_for_method(p, args.method) for p in paths]

    if args.method == "xor":
        recovered = xor.xor_decrypt(images)
    else:
        if len(images) != 2:
            raise SystemExit("naor-shamir requires exactly 2 shares")
        recovered = naor_shamir.naor_shamir_decrypt(images[0], images[1])
        if args.downsample:
            recovered = naor_shamir.downsample_revealed(recovered)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    recovered.save(out_path)

    print(theme.banner("BloomSight - Decrypt"))
    print(f"  method   : {args.method}")
    print(f"  combined : {len(images)} share(s)")
    print(f"  output   : {out_path}")
    return 0


def _make_demo_secret(size=(320, 160)) -> Image.Image:
    img = Image.new("L", size, color=255)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 56)
    except OSError:
        font = ImageFont.load_default()
    text = "BloomSight"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size[0] - tw) // 2, (size[1] - th) // 2 - bbox[1]),
              text, fill=0, font=font)
    return img


def _cmd_demo(args: argparse.Namespace) -> int:
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    secret = _make_demo_secret()
    secret.save(out_dir / "secret.png")

    s1, s2 = naor_shamir.naor_shamir_encrypt(secret, seed=42)
    _save_share(s1, out_dir / "share_1.png", themed=True, index=0)
    _save_share(s2, out_dir / "share_2.png", themed=True, index=1)

    stacked = naor_shamir.naor_shamir_decrypt(s1, s2)
    stacked.save(out_dir / "revealed_stacked.png")
    naor_shamir.downsample_revealed(stacked).save(out_dir / "revealed.png")

    xor_shares = xor.xor_encrypt(secret.convert("RGB"), n_shares=3, seed=7)
    for i, share in enumerate(xor_shares, start=1):
        _save_share(share, out_dir / f"xor_share_{i}.png",
                    themed=False, index=i - 1)
    xor.xor_decrypt(xor_shares).save(out_dir / "xor_recovered.png")

    print(theme.banner("BloomSight - Demo complete"))
    print(f"  output dir : {out_dir.resolve()}")
    print( "  files      : secret.png, share_1.png, share_2.png,")
    print( "               revealed_stacked.png, revealed.png,")
    print( "               xor_share_{1..3}.png, xor_recovered.png")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="visual_crypto",
                                description="BloomSight visual cryptography")
    sub = p.add_subparsers(dest="command", required=True)

    enc = sub.add_parser("encrypt", help="split an image into shares")
    enc.add_argument("--input", "-i", required=True, type=Path)
    enc.add_argument("--out", "-o", required=True, type=Path)
    enc.add_argument("--method", "-m", choices=_METHODS, default="xor")
    enc.add_argument("--shares", "-n", type=int, default=2)
    enc.add_argument("--themed", action="store_true",
                     help="paint shares with the BloomSight palette")
    enc.add_argument("--seed", type=int, default=None)
    enc.set_defaults(func=_cmd_encrypt)

    dec = sub.add_parser("decrypt", help="combine shares")
    dec.add_argument("--shares", "-s", required=True, nargs="+")
    dec.add_argument("--out", "-o", required=True, type=Path)
    dec.add_argument("--method", "-m", choices=_METHODS, default="xor")
    dec.add_argument("--downsample", action="store_true",
                     help="for naor-shamir: collapse 2x2 sub-blocks back")
    dec.set_defaults(func=_cmd_decrypt)

    demo = sub.add_parser("demo", help="run a full encrypt/decrypt example")
    demo.add_argument("--out", "-o", type=Path, default=Path("demo_output"))
    demo.set_defaults(func=_cmd_demo)

    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
