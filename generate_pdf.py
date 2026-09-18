#!/usr/bin/env python3
"""Compile the LaTeX resume into a PDF.

Usage:
    python3 generate_pdf.py
    python3 generate_pdf.py --open
    python3 generate_pdf.py --serve
"""

from __future__ import annotations

import argparse
import http.server
import os
import shutil
import socket
import socketserver
import subprocess
import sys
import threading
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE = "Trevor_Decker_Resume.tex"
MACTEX_BIN = Path("/Library/TeX/texbin")
AUX_SUFFIXES = (
    ".aux",
    ".log",
    ".out",
    ".synctex.gz",
    ".fls",
    ".fdb_latexmk",
    ".toc",
)


def find_engine() -> list[str]:
    """Prefer latexmk (handles extra passes); fall back to pdflatex."""
    extra_path = str(MACTEX_BIN) if MACTEX_BIN.is_dir() else None
    search_path = None
    if extra_path:
        search_path = extra_path + os.pathsep + os.environ.get("PATH", "")

    latexmk = shutil.which("latexmk", path=search_path)
    if latexmk:
        return [latexmk, "-pdf", "-interaction=nonstopmode", "-halt-on-error"]

    pdflatex = shutil.which("pdflatex", path=search_path)
    if pdflatex:
        return [pdflatex, "-interaction=nonstopmode", "-halt-on-error"]

    sys.exit(
        "Could not find latexmk or pdflatex. Install MacTeX from "
        "https://tug.org/mactex/mactex-download.html"
    )


def clean_aux_files(source: Path) -> None:
    stem = source.with_suffix("")
    for suffix in AUX_SUFFIXES:
        aux = Path(str(stem) + suffix)
        if aux.exists():
            aux.unlink()


def pdf_http_url(pdf: Path, port: int) -> str:
    return f"http://127.0.0.1:{port}/{pdf.name}"


def is_serving_pdf(pdf: Path, port: int) -> bool:
    try:
        with urllib.request.urlopen(pdf_http_url(pdf, port), timeout=0.5) as response:
            return 200 <= response.status < 300
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
        return False


def find_free_port(start: int) -> int:
    for candidate in range(start, start + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", candidate))
            except OSError:
                continue
            return candidate
    sys.exit(f"Could not find a free port in {start}-{start + 19}.")


def serve_pdf(pdf: Path, port: int) -> tuple[str, bool]:
    """Serve the PDF over localhost. Returns (url, started_new_server)."""
    if is_serving_pdf(pdf, port):
        return pdf_http_url(pdf, port), False

    directory = pdf.parent

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

        def log_message(self, format, *args):
            return

    class ReuseTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    chosen_port = port
    try:
        httpd = ReuseTCPServer(("127.0.0.1", chosen_port), Handler)
    except OSError:
        chosen_port = find_free_port(port + 1)
        httpd = ReuseTCPServer(("127.0.0.1", chosen_port), Handler)

    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return pdf_http_url(pdf, chosen_port), True


def generate_pdf(
    source: Path, open_pdf: bool, keep_aux: bool, serve: bool, port: int
) -> Path:
    if not source.exists():
        sys.exit(f"Source file not found: {source}")

    engine = find_engine()
    command = engine + [source.name]
    uses_latexmk = "latexmk" in engine[0]
    passes = 1 if uses_latexmk else 2  # two pdflatex passes for page refs

    print(f"Compiling {source.name} with {Path(engine[0]).name}...")
    for pass_number in range(1, passes + 1):
        if passes > 1:
            print(f"  pass {pass_number}/{passes}")
        result = subprocess.run(
            command,
            cwd=source.parent,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
            sys.exit(f"LaTeX compilation failed (exit {result.returncode}).")

    pdf = source.with_suffix(".pdf")
    if not pdf.exists():
        sys.exit(f"Compilation finished but PDF was not created: {pdf}")

    if not keep_aux:
        clean_aux_files(source)

    print(f"Wrote {pdf}")

    url = pdf.resolve().as_uri()
    if serve:
        url, started_server = serve_pdf(pdf, port)
        print(f"View in browser: {url}")
        webbrowser.open(url)
        if not started_server:
            print("Using the server already running on that port.")
            return pdf
        print("Press Ctrl+C to stop the local server.")
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            print("\nStopped.")
    elif open_pdf:
        webbrowser.open(url)

    return pdf


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a PDF of the resume.")
    parser.add_argument(
        "--source",
        default=DEFAULT_SOURCE,
        help=f"LaTeX source file (default: {DEFAULT_SOURCE})",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the PDF in your default browser after it is generated.",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Serve the PDF at an http://localhost URL and open it in a browser.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port for --serve (default: 8765).",
    )
    parser.add_argument(
        "--keep-aux",
        action="store_true",
        help="Keep LaTeX auxiliary files (.aux, .log, .out, ...).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = Path(args.source)
    if not source.is_absolute():
        source = REPO_ROOT / source
    generate_pdf(
        source=source,
        open_pdf=args.open,
        keep_aux=args.keep_aux,
        serve=args.serve,
        port=args.port,
    )


if __name__ == "__main__":
    main()
