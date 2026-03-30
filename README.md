[README](README_en.md)

# Markdown Alchemy

**Turn anything into Markdown — beautifully.**

Markdown Alchemy is a desktop GUI for Microsoft's [MarkItDown](https://github.com/microsoft/markitdown), built with **PySide6** and **QFluentWidgets**. Drop your files, paste a URL, and walk away with clean, structured Markdown — no terminal required.

<img width="1660" height="1088" alt="image" src="https://github.com/user-attachments/assets/d412599f-343c-4f87-8408-57ce27ef325d" />
<img width="1667" height="1096" alt="image" src="https://github.com/user-attachments/assets/a811277a-9594-4bdb-9656-9c7e674a7e7d" />
<img width="1669" height="1093" alt="image" src="https://github.com/user-attachments/assets/fa5f1d53-da30-453f-a092-3261fd09cb3c" />

## Why Markdown Alchemy?

Most conversion tools give you a CLI and wish you luck. Markdown Alchemy gives you a modern Fluent-style interface with drag-and-drop queuing, real-time progress, live preview, and batch export — so you can convert dozens of documents in a single session without switching windows.

## Fork Attribution

**Markdown Alchemy** ([repository](https://github.com/Ayrnio/MarkdownAlchemy)) is a **fork** of **[markitdown-gui](https://github.com/imadreamerboy/markitdown-gui)** by [Jonas / imadreamerboy](https://github.com/imadreamerboy). The upstream project laid an excellent foundation; this fork ships a maintained variant with deeper UX polish, expanded theming, and additional conversion options.

## What's New in This Fork

- **Live progress dashboard** — elapsed time, document count, and per-document page counter update in real time.
- **Perfect Dark theme** — a refined dark palette with custom nav/title chrome, a centered content column on ultrawide displays, and assorted layout polish.
- **OpenAI-compatible vision OCR** — use any server that speaks the **OpenAI HTTP API** for chat with **image inputs** (local runtimes, gateways, or hosted proxies). Configure base URL, vision-capable model id, and optional system prompt in Settings. An optional **"always OCR PDFs"** toggle skips embedded text for stubborn scans. Azure and Tesseract flows from upstream are still available.
- **Cancellation that actually cancels** — tearing down in-flight HTTP requests where applicable, with clearer PDF and model progress feedback.
- **Add Folder** — imports top-level files from a directory (no recursive subfolder crawl), respecting the active file-type filter in the queue view.
- **Extended i18n** — English and Chinese (zh_CN) strings cover every new UI element.

All upstream features listed below still apply unless noted.

## Features

### Conversion & Workflow
- Queue-based file workflow with drag-and-drop support.
- Paste `http://` or `https://` URLs to convert web articles to Markdown via the hosted [Defuddle](https://defuddle.md/) API.
- Batch conversion with start, pause/resume, cancel, and granular progress feedback.

### Preview & Export
- Results view with per-file selection and live Markdown preview.
- Toggle between **rendered** and **raw** Markdown views.
- Export as a single combined file or individual files.
- Quick actions: copy Markdown, save output, return to queue, or start fresh.

### OCR
- Optional OCR for scanned PDFs and images — **Azure Document Intelligence**, **local Tesseract**, or **OpenAI-compatible vision** (fork addition).

### Settings & Customization
- Output folder, batch size, header style, table style, OCR provider, and theme mode (**Light / Dark / System / Perfect Dark**).
- Built-in shortcuts dialog, update-check action, and about dialog.

## Getting Started

### Prebuilt Binaries

Grab the latest installer from the [**Releases**](https://github.com/Ayrnio/MarkdownAlchemy/releases) tab. The original **markitdown-gui** also publishes its own [Releases](https://github.com/imadreamerboy/markitdown-gui/releases) for the unmodified app.

### Run from Source

**Prerequisites:** Python `3.10+` and [`uv`](https://github.com/astral-sh/uv) (recommended).

```sh
uv sync
uv run python -m markitdowngui.main
```

Or with pip:

```sh
pip install -e .[dev]
python -m markitdowngui.main
```

## OCR Configuration

OCR is **optional** and **disabled by default**.

- **Tesseract (local):** Install the binary from the [official Tesseract project](https://github.com/tesseract-ocr/tesseract). If it isn't on your `PATH`, set the executable path in Settings.
- **Azure Document Intelligence:** Enter your endpoint in Settings. For API-key auth, set the `AZURE_OCR_API_KEY` environment variable; otherwise the app falls back to `DefaultAzureCredential`. Azure offers [500 free pages/month](https://azure.microsoft.com/en-us/products/ai-foundry/tools/document-intelligence#Pricing) at the time of writing.
- **OpenAI-compatible vision:** Point the app at any **OpenAI API–compatible** endpoint that supports **vision** in chat; configure base URL, model, and prompt in Settings as documented in-app. You are responsible for any service you use.

## Website URL Conversion

- The app sends pasted URLs to `https://defuddle.md/<url>` and stores the returned Markdown in the normal results view.
- Responses typically include YAML frontmatter metadata when available.
- Per the [Defuddle Terms](https://defuddle.md/terms), unauthenticated requests are limited to **1,000 per month per IP** (as of March 14, 2026). Because requests originate from the desktop app, this limit applies to your network IP.
- Requires an active internet connection and depends on Defuddle's availability.

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+O` | Open files |
| `Ctrl+S` | Save output |
| `Ctrl+C` | Copy output |
| `Ctrl+P` | Pause / resume |
| `Ctrl+B` | Start conversion |
| `Ctrl+L` | Clear queue |
| `Ctrl+K` | Show shortcuts |
| `Esc` | Cancel conversion |

## Building a Standalone Executable

```sh
uv pip install -e .[dev]
pyinstaller MarkItDown.spec --clean --noconfirm
```

The default spec produces an `onedir` app under `dist/`. Edit `MarkItDown.spec` to rename the output folder or executable to **Markdown Alchemy**.

## Contributing

1. **Fork** this repository (or upstream, if your change belongs there) and create a branch.
2. Install dev dependencies: `uv pip install -e .[dev]`
3. Make your changes.
4. Run tests: `uv run pytest -q`
5. Open a pull request with a clear summary — and note whether the same fix should go **upstream** to [markitdown-gui](https://github.com/imadreamerboy/markitdown-gui).

## License

Licensed under **GPLv3 for non-commercial use**. Commercial use requires a separate commercial license, in accordance with the non-commercial licensing requirements of `PySide6-Fluent-Widgets` (`qfluentwidgets`).

## Credits

- **[markitdown-gui](https://github.com/imadreamerboy/markitdown-gui)** — the original PySide6 / QFluentWidgets GUI wrapper for MarkItDown and this fork's starting point.
- **[MarkItDown](https://github.com/microsoft/markitdown)** — [MIT License](https://opensource.org/licenses/MIT)
- **[PySide6](https://www.qt.io/qt-for-python)** — [LGPLv3 License](https://www.gnu.org/licenses/lgpl-3.0.html)
- **[PySide6-Fluent-Widgets / QFluentWidgets](https://qfluentwidgets.com/)**
- Navigation toggle glyph derived from the **Lucide** [infinity](https://lucide.dev/icons/infinity) icon — [ISC License](https://lucide.dev/license)