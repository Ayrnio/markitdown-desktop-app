from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, replace
from itertools import islice
import json
import os
import tempfile
from pathlib import Path
from urllib.parse import quote

import requests

from PySide6.QtCore import QThread, Signal

from markitdowngui.core.input_sources import is_web_url

IMAGE_EXTENSIONS = {".bmp", ".gif", ".jpeg", ".jpg", ".png", ".tiff", ".webp"}
DOCINTEL_IMAGE_EXTENSIONS = {".bmp", ".jpeg", ".jpg", ".png", ".tiff"}
PDF_EXTENSION = ".pdf"
PDF_RENDER_SCALE = 3.0
LOCAL_OCR_TIMEOUT_SECONDS = 60
DEFUDDLE_REQUEST_TIMEOUT_SECONDS = 30
DEFUDDLE_API_BASE_URL = "https://defuddle.md/"
AZURE_OCR_API_KEY_ENV_VAR = "AZURE_OCR_API_KEY"
CONVERSION_ERROR_PREFIX = "Error converting "
BACKEND_AZURE = "azure"
BACKEND_DEFUDDLE = "defuddle"
BACKEND_LOCAL = "local"
BACKEND_NATIVE = "native"
BACKEND_OPENAI_VISION = "openai_vision"

OCR_METHOD_AUTO = "auto"
OCR_METHOD_TESSERACT = "tesseract"
OCR_METHOD_OPENAI_VISION = "openai_vision"

@dataclass(frozen=True)
class ConversionOptions:
    """User-controlled conversion behavior."""

    ocr_enabled: bool = False
    # Skip MarkItDown/pdfminer PDF text layer; always use OCR backends (GUI-only; not a MarkItDown API).
    ocr_force_pdf: bool = False
    ocr_method: str = OCR_METHOD_AUTO
    docintel_endpoint: str = ""
    ocr_languages: str = ""
    tesseract_path: str = ""
    llm_base_url: str = ""
    llm_model: str = ""
    llm_saved_for_auto_ocr: bool = False
    llm_vision_system_prompt: str = ""
    page_progress: Callable[[int, int, bool], None] | None = None
    should_cancel: Callable[[], bool] | None = None
    openai_http_client: object | None = None

    @property
    def resolved_llm_vision_system_prompt(self) -> str:
        from markitdowngui.core.vision_prompt_defaults import (
            DEFAULT_VISION_SYSTEM_PROMPT,
        )

        t = (self.llm_vision_system_prompt or "").strip()
        return t if t else DEFAULT_VISION_SYSTEM_PROMPT

    @property
    def normalized_docintel_endpoint(self) -> str:
        return self.docintel_endpoint.strip()

    @property
    def normalized_ocr_languages(self) -> str:
        return self.ocr_languages.strip()

    @property
    def normalized_tesseract_path(self) -> str:
        return self.tesseract_path.strip()

    @property
    def normalized_llm_base_url(self) -> str:
        return self.llm_base_url.strip()

    @property
    def normalized_llm_model(self) -> str:
        return self.llm_model.strip()

    @property
    def normalized_ocr_method(self) -> str:
        m = (self.ocr_method or "").strip()
        if m in (OCR_METHOD_AUTO, OCR_METHOD_TESSERACT, OCR_METHOD_OPENAI_VISION):
            return m
        return OCR_METHOD_AUTO


def _llm_eligible_for_auto_ocr_chain(options: ConversionOptions) -> bool:
    """Use LM Studio in Automatic OCR only when Settings explicitly saved both fields."""
    if not options.llm_saved_for_auto_ocr:
        return False
    return bool(options.normalized_llm_base_url and options.normalized_llm_model)


@dataclass(frozen=True)
class ConversionOutcome:
    markdown: str
    backend: str = BACKEND_NATIVE


def format_conversion_error(file_path: str, error: Exception) -> str:
    return f"{CONVERSION_ERROR_PREFIX}{file_path}: {error}"


def _summarize_error(error: Exception) -> str:
    message = str(error).strip()
    return message or type(error).__name__


def _raise_ocr_failure(
    file_label: str,
    *,
    native_error: Exception | None = None,
    docintel_attempted: bool = False,
    docintel_error: Exception | None = None,
    local_error: Exception | None = None,
    openai_vision_error: Exception | None = None,
) -> str:
    if openai_vision_error is not None and local_error is not None:
        raise RuntimeError(
            f"OpenAI-compatible vision failed for the {file_label} ({_summarize_error(openai_vision_error)}), "
            f"and local OCR also failed ({_summarize_error(local_error)})."
        ) from openai_vision_error

    if openai_vision_error is not None:
        raise RuntimeError(
            f"OpenAI-compatible vision failed for the {file_label}: {_summarize_error(openai_vision_error)}"
        ) from openai_vision_error

    if docintel_error is not None and local_error is not None:
        raise RuntimeError(
            f"Azure OCR failed for the {file_label} ({_summarize_error(docintel_error)}), "
            f"and local OCR fallback also failed ({_summarize_error(local_error)})."
        ) from docintel_error

    if docintel_error is not None:
        raise RuntimeError(
            f"Azure OCR failed for the {file_label}: {_summarize_error(docintel_error)}"
        ) from docintel_error

    if docintel_attempted and local_error is not None:
        raise RuntimeError(
            f"Azure OCR did not extract text from the {file_label}, and local OCR fallback also failed "
            f"({_summarize_error(local_error)})."
        ) from local_error

    if native_error is not None and local_error is not None:
        raise RuntimeError(
            f"Native extraction failed for the {file_label} ({_summarize_error(native_error)}), "
            f"and local OCR fallback also failed ({_summarize_error(local_error)})."
        ) from native_error

    if native_error is not None:
        raise RuntimeError(
            f"Native extraction failed for the {file_label}: {_summarize_error(native_error)}"
        ) from native_error

    if local_error is not None:
        raise RuntimeError(
            f"Local OCR failed for the {file_label}: {_summarize_error(local_error)}"
        ) from local_error

    raise RuntimeError(f"OCR did not extract any text from the {file_label}.")


def _build_docintel_credential() -> tuple[object, str]:
    api_key = os.getenv(AZURE_OCR_API_KEY_ENV_VAR, "").strip()
    if api_key:
        from azure.core.credentials import AzureKeyCredential

        return AzureKeyCredential(api_key), "api_key"

    from azure.identity import DefaultAzureCredential

    return DefaultAzureCredential(), "azure_identity"


def test_azure_ocr_connection(options: ConversionOptions) -> str:
    endpoint = options.normalized_docintel_endpoint
    if not endpoint:
        raise RuntimeError("Set an Azure Document Intelligence endpoint first.")

    api_key = os.getenv(AZURE_OCR_API_KEY_ENV_VAR, "").strip()
    if not api_key:
        raise RuntimeError(
            "Set AZURE_OCR_API_KEY before using Test Azure OCR. This check validates API-key authentication only."
        )

    try:
        from azure.core.credentials import AzureKeyCredential
        from azure.ai.documentintelligence import DocumentIntelligenceAdministrationClient
    except ImportError as exc:
        raise RuntimeError(
            "Azure OCR testing requires azure-ai-documentintelligence to be installed."
        ) from exc

    client = DocumentIntelligenceAdministrationClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(api_key),
    )
    try:
        list(islice(client.list_models(), 1))
    finally:
        if hasattr(client, "close"):
            client.close()

    return "api_key"


@contextmanager
def _image_path_as_png_for_markitdown(file_path: str):
    """Yield a path MarkItDown's image converter accepts (.png/.jpeg/.jpg); remove temp PNG if created."""
    ext = Path(file_path).suffix.lower()
    if ext in {".jpg", ".jpeg", ".png"}:
        yield file_path
        return

    try:
        from PIL import Image, ImageOps
    except ImportError as exc:
        raise RuntimeError(
            "OpenAI-compatible vision extraction for this image type requires Pillow to be installed."
        ) from exc

    with Image.open(file_path) as image:
        prepared = ImageOps.exif_transpose(image).convert("RGB")
        fd, tmp = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        try:
            prepared.save(tmp, format="PNG")
            yield tmp
        finally:
            if os.path.isfile(tmp):
                os.unlink(tmp)


def _require_openai_vision_config(options: ConversionOptions) -> None:
    if not (options.normalized_llm_base_url and options.normalized_llm_model):
        raise RuntimeError(
            "OpenAI-compatible vision extraction requires an API base URL and model id "
            "under Local LLM (LM Studio) in Settings."
        )


def _openai_client_for_options(options: ConversionOptions) -> object:
    from openai import OpenAI

    kwargs: dict[str, object] = {
        "base_url": options.normalized_llm_base_url,
        "api_key": "lm-studio",
    }
    if options.openai_http_client is not None:
        kwargs["http_client"] = options.openai_http_client
    return OpenAI(**kwargs)


def _convert_image_with_openai_vision_ocr(file_path: str, options: ConversionOptions) -> str:
    from markitdowngui.core.llm_vision_chat import transcribe_image_file_openai_compatible
    from markitdowngui.core.vision_prompt_defaults import VISION_OCR_USER_MESSAGE

    _require_openai_vision_config(options)
    client = _openai_client_for_options(options)
    with _image_path_as_png_for_markitdown(file_path) as png_path:
        return transcribe_image_file_openai_compatible(
            client,
            options.normalized_llm_model,
            image_path=png_path,
            system_prompt=options.resolved_llm_vision_system_prompt,
            user_message=VISION_OCR_USER_MESSAGE,
            should_cancel=options.should_cancel,
        )


def _notify_pdf_page_progress(
    options: ConversionOptions,
    page_cur_1based: int,
    page_count: int,
    *,
    model_pending: bool = False,
) -> None:
    cb = options.page_progress
    if cb is not None and page_count > 0:
        cb(page_cur_1based, page_count, model_pending)


def _convert_pdf_with_openai_vision_ocr(file_path: str, options: ConversionOptions) -> str:
    from markitdowngui.core.llm_vision_chat import transcribe_image_file_openai_compatible
    from markitdowngui.core.vision_prompt_defaults import VISION_OCR_USER_MESSAGE

    _require_openai_vision_config(options)
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise RuntimeError(
            "OpenAI-compatible vision extraction for PDFs requires pypdfium2 to be installed."
        ) from exc

    client = _openai_client_for_options(options)
    system_prompt = options.resolved_llm_vision_system_prompt
    page_texts: list[str] = []
    pdf = pdfium.PdfDocument(file_path)
    try:
        page_count = len(pdf)
        for page_index in range(page_count):
            if options.should_cancel and options.should_cancel():
                break
            _notify_pdf_page_progress(
                options, page_index + 1, page_count, model_pending=True
            )
            page = pdf[page_index]
            bitmap = None
            tmp_path: str | None = None
            try:
                bitmap = page.render(scale=PDF_RENDER_SCALE)
                fd, tmp_path = tempfile.mkstemp(suffix=".png")
                os.close(fd)
                bitmap.to_pil().save(tmp_path, format="PNG")
                if options.should_cancel and options.should_cancel():
                    break
                page_md = transcribe_image_file_openai_compatible(
                    client,
                    options.normalized_llm_model,
                    image_path=tmp_path,
                    system_prompt=system_prompt,
                    user_message=VISION_OCR_USER_MESSAGE,
                    should_cancel=options.should_cancel,
                )
                _notify_pdf_page_progress(
                    options, page_index + 1, page_count, model_pending=False
                )
                if options.should_cancel and options.should_cancel():
                    break
                if page_md.strip():
                    page_texts.append(page_md.strip())
            finally:
                if tmp_path and os.path.isfile(tmp_path):
                    os.unlink(tmp_path)
                if bitmap is not None and hasattr(bitmap, "close"):
                    bitmap.close()
                if hasattr(page, "close"):
                    page.close()
    finally:
        if hasattr(pdf, "close"):
            pdf.close()

    return "\n\n".join(page_texts).strip()


def convert_file_with_details(
    file_path: str,
    options: ConversionOptions | None = None,
) -> ConversionOutcome:
    """Convert a single file to Markdown text and report which backend produced it."""
    effective_options = options or ConversionOptions()

    if is_web_url(file_path):
        return ConversionOutcome(
            markdown=_convert_url_with_defuddle(file_path),
            backend=BACKEND_DEFUDDLE,
        )

    extension = Path(file_path).suffix.lower()

    if not effective_options.ocr_enabled:
        return ConversionOutcome(
            markdown=_convert_with_markitdown(file_path, effective_options),
            backend=BACKEND_NATIVE,
        )

    if extension in IMAGE_EXTENSIONS:
        return _convert_image_with_ocr(file_path, effective_options, extension)

    if extension == PDF_EXTENSION:
        return _convert_pdf_with_ocr_fallback(file_path, effective_options)

    return ConversionOutcome(
        markdown=_convert_with_markitdown(file_path, effective_options),
        backend=BACKEND_NATIVE,
    )


def convert_file(file_path: str, options: ConversionOptions | None = None) -> str:
    """Convert a single file to Markdown text."""
    return convert_file_with_details(file_path, options).markdown


def _convert_image_with_ocr(
    file_path: str,
    options: ConversionOptions,
    extension: str,
) -> ConversionOutcome:
    method = options.normalized_ocr_method

    if method == OCR_METHOD_OPENAI_VISION:
        try:
            markdown = _convert_image_with_openai_vision_ocr(file_path, options)
            if markdown.strip():
                return ConversionOutcome(markdown=markdown, backend=BACKEND_OPENAI_VISION)
        except Exception as exc:
            raise RuntimeError(
                f"OpenAI-compatible vision extraction failed for the image: {_summarize_error(exc)}"
            ) from exc
        raise RuntimeError(
            "OpenAI-compatible vision extraction returned no text. Check the model, server, and image."
        )

    if method == OCR_METHOD_TESSERACT:
        local_error: Exception | None = None
        try:
            markdown = _convert_image_with_local_ocr(file_path, options)
            if markdown.strip():
                return ConversionOutcome(markdown=markdown, backend=BACKEND_LOCAL)
        except Exception as exc:
            local_error = exc
        return _raise_ocr_failure(
            "image",
            docintel_attempted=False,
            docintel_error=None,
            local_error=local_error,
        )

    docintel_error: Exception | None = None
    docintel_attempted = False

    if (
        options.normalized_docintel_endpoint
        and extension in DOCINTEL_IMAGE_EXTENSIONS
    ):
        docintel_attempted = True
        try:
            markdown = _convert_with_markitdown(
                file_path,
                options,
                use_docintel=True,
            )
            if markdown.strip():
                return ConversionOutcome(markdown=markdown, backend=BACKEND_AZURE)
        except Exception as exc:
            docintel_error = exc

    openai_vision_err: Exception | None = None
    if _llm_eligible_for_auto_ocr_chain(options):
        try:
            markdown = _convert_image_with_openai_vision_ocr(file_path, options)
            if markdown.strip():
                return ConversionOutcome(markdown=markdown, backend=BACKEND_OPENAI_VISION)
        except Exception as exc:
            openai_vision_err = exc

    local_error_tess: Exception | None = None
    try:
        markdown = _convert_image_with_local_ocr(file_path, options)
        if markdown.strip():
            return ConversionOutcome(markdown=markdown, backend=BACKEND_LOCAL)
    except Exception as exc:
        local_error_tess = exc

    return _raise_ocr_failure(
        "image",
        docintel_attempted=docintel_attempted,
        docintel_error=docintel_error,
        local_error=local_error_tess,
        openai_vision_error=openai_vision_err,
    )


def _convert_pdf_with_ocr_fallback(
    file_path: str,
    options: ConversionOptions,
) -> ConversionOutcome:
    method = options.normalized_ocr_method

    if method == OCR_METHOD_OPENAI_VISION:
        try:
            markdown = _convert_pdf_with_openai_vision_ocr(file_path, options)
            if markdown.strip():
                return ConversionOutcome(markdown=markdown, backend=BACKEND_OPENAI_VISION)
        except Exception as exc:
            raise RuntimeError(
                f"OpenAI-compatible vision extraction failed for the PDF: {_summarize_error(exc)}"
            ) from exc
        raise RuntimeError(
            "OpenAI-compatible vision extraction returned no text for the PDF. Check the model and server."
        )

    native_error: Exception | None = None
    if not options.ocr_force_pdf:
        try:
            markdown = _convert_with_markitdown(file_path, options)
            if markdown.strip():
                return ConversionOutcome(markdown=markdown, backend=BACKEND_NATIVE)
        except Exception as exc:
            native_error = exc

    if method == OCR_METHOD_TESSERACT:
        local_error_only: Exception | None = None
        try:
            markdown = _convert_pdf_with_local_ocr(file_path, options)
            if markdown.strip():
                return ConversionOutcome(markdown=markdown, backend=BACKEND_LOCAL)
        except Exception as exc:
            local_error_only = exc
        return _raise_ocr_failure(
            "PDF",
            native_error=native_error,
            docintel_attempted=False,
            docintel_error=None,
            local_error=local_error_only,
        )

    docintel_error: Exception | None = None
    docintel_attempted = False
    if options.normalized_docintel_endpoint:
        docintel_attempted = True
        try:
            markdown = _convert_with_markitdown(
                file_path,
                options,
                use_docintel=True,
            )
            if markdown.strip():
                return ConversionOutcome(markdown=markdown, backend=BACKEND_AZURE)
        except Exception as exc:
            docintel_error = exc

    openai_vision_err_pdf: Exception | None = None
    if _llm_eligible_for_auto_ocr_chain(options):
        try:
            markdown = _convert_pdf_with_openai_vision_ocr(file_path, options)
            if markdown.strip():
                return ConversionOutcome(markdown=markdown, backend=BACKEND_OPENAI_VISION)
        except Exception as exc:
            openai_vision_err_pdf = exc

    local_error: Exception | None = None
    try:
        markdown = _convert_pdf_with_local_ocr(file_path, options)
        if markdown.strip():
            return ConversionOutcome(markdown=markdown, backend=BACKEND_LOCAL)
    except Exception as exc:
        local_error = exc

    return _raise_ocr_failure(
        "PDF",
        native_error=native_error,
        docintel_attempted=docintel_attempted,
        docintel_error=docintel_error,
        local_error=local_error,
        openai_vision_error=openai_vision_err_pdf,
    )


def _convert_with_markitdown(
    file_path: str,
    options: ConversionOptions,
    *,
    use_docintel: bool = False,
    llm_prompt: str | None = None,
) -> str:
    # Delay heavy imports until conversion is requested.
    from markitdown import MarkItDown

    kwargs: dict[str, object] = {}
    if use_docintel and options.normalized_docintel_endpoint:
        kwargs["docintel_endpoint"] = options.normalized_docintel_endpoint
        kwargs["docintel_credential"], _auth_method = _build_docintel_credential()

    if options.normalized_llm_base_url and options.normalized_llm_model:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "Local LLM support requires the 'openai' package. "
                "Install it with: pip install openai"
            ) from exc
        kwargs["llm_client"] = OpenAI(
            base_url=options.normalized_llm_base_url,
            api_key="lm-studio",
        )
        kwargs["llm_model"] = options.normalized_llm_model
        if llm_prompt is not None:
            kwargs["llm_prompt"] = llm_prompt

    md = MarkItDown(**kwargs)
    result = md.convert(file_path)
    return result.text_content or ""


def _convert_url_with_defuddle(url: str) -> str:
    request_url = _build_defuddle_request_url(url)

    try:
        response = requests.get(
            request_url,
            timeout=DEFUDDLE_REQUEST_TIMEOUT_SECONDS,
        )
    except requests.Timeout as exc:
        raise RuntimeError(
            "Website conversion timed out while waiting for the Defuddle service."
        ) from exc
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Website conversion failed to reach the Defuddle service: {exc}"
        ) from exc

    if response.status_code == 429:
        raise RuntimeError(
            "Defuddle rate limit reached. The free tier allows up to 1,000 requests per month per IP."
        )

    if not response.ok:
        message = response.text.strip()
        raise RuntimeError(message or "Defuddle failed to convert the URL.")

    return response.text.strip()


def _build_defuddle_request_url(url: str) -> str:
    encoded_url = quote(url.strip(), safe="")
    return f"{DEFUDDLE_API_BASE_URL}{encoded_url}"


def _convert_image_with_local_ocr(file_path: str, options: ConversionOptions) -> str:
    try:
        from PIL import Image, ImageOps
    except ImportError as exc:
        raise RuntimeError("Local OCR requires Pillow to be installed.") from exc

    with Image.open(file_path) as image:
        prepared = ImageOps.exif_transpose(image).convert("RGB")
        return _run_tesseract_ocr(prepared, options)


def _convert_pdf_with_local_ocr(file_path: str, options: ConversionOptions) -> str:
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise RuntimeError(
            "Local PDF OCR requires pypdfium2 to be installed."
        ) from exc

    page_texts: list[str] = []
    pdf = pdfium.PdfDocument(file_path)
    try:
        page_count = len(pdf)
        for page_index in range(page_count):
            _notify_pdf_page_progress(
                options, page_index + 1, page_count, model_pending=False
            )
            page = pdf[page_index]
            bitmap = None
            try:
                bitmap = page.render(scale=PDF_RENDER_SCALE)
                page_text = _run_tesseract_ocr(bitmap.to_pil(), options)
                if page_text.strip():
                    page_texts.append(page_text.strip())
            finally:
                if bitmap is not None and hasattr(bitmap, "close"):
                    bitmap.close()
                if hasattr(page, "close"):
                    page.close()
    finally:
        if hasattr(pdf, "close"):
            pdf.close()

    return "\n\n".join(page_texts).strip()


def _run_tesseract_ocr(image, options: ConversionOptions) -> str:
    try:
        import pytesseract
    except ImportError as exc:
        raise RuntimeError("Local OCR requires pytesseract to be installed.") from exc

    if options.normalized_tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = options.normalized_tesseract_path
    else:
        pytesseract.pytesseract.tesseract_cmd = "tesseract"

    kwargs: dict[str, object] = {"timeout": LOCAL_OCR_TIMEOUT_SECONDS}
    if options.normalized_ocr_languages:
        kwargs["lang"] = options.normalized_ocr_languages

    try:
        return str(pytesseract.image_to_string(image, **kwargs)).strip()
    except Exception as exc:
        raise RuntimeError(
            "Local OCR failed. Install Tesseract or set its path in Settings."
        ) from exc


class ConversionWorker(QThread):
    # File-level progress. PDF page updates use a JSON string payload so Qt does not
    # mis-bind mixed-type multi-arg signals across thread boundaries on some builds.
    progress = Signal(int, int, str, bool)
    pdf_page_progress = Signal(str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(
        self,
        files: list[str],
        batch_size: int,
        options: ConversionOptions | None = None,
    ):
        super().__init__()
        self.files = files
        self.batch_size = batch_size
        self.options = options or ConversionOptions()
        self.failed_files: set[str] = set()
        self.processing_backends: dict[str, str] = {}
        self.is_paused = False
        self.is_cancelled = False
        self._http_client = None

    def request_cancel(self) -> None:
        """Stop the queue soon and try to abort the in-flight OpenAI-compatible HTTP call."""
        self.is_cancelled = True
        hc = getattr(self, "_http_client", None)
        if hc is None:
            return
        self._http_client = None
        try:
            hc.close()
        except Exception:
            pass

    def run(self) -> None:
        results: dict[str, str] = {}
        self.failed_files = set()
        self.processing_backends = {}

        total = len(self.files)
        if total == 0:
            self.finished.emit(results)
            return

        http_client = None
        if self.options.normalized_llm_base_url:
            import httpx

            http_client = httpx.Client(
                timeout=httpx.Timeout(connect=60.0, read=None, write=120.0, pool=60.0),
            )
        self._http_client = http_client
        threaded_opts = replace(
            self.options,
            openai_http_client=http_client,
            should_cancel=lambda: self.is_cancelled,
        )
        aborted = False
        try:
            for i in range(0, total, self.batch_size):
                if self.is_cancelled:
                    break

                batch = self.files[i : i + self.batch_size]
                for j, file_path in enumerate(batch):
                    while self.is_paused:
                        if self.is_cancelled:
                            aborted = True
                            break
                        self.msleep(100)
                    if aborted:
                        break

                    k = i + j
                    self.progress.emit(k, total, file_path, True)

                    def on_pdf_page(
                        page_cur: int, page_tot: int, model_pending: bool = False
                    ) -> None:
                        self.pdf_page_progress.emit(
                            json.dumps(
                                {
                                    "path": file_path,
                                    "c": page_cur,
                                    "t": page_tot,
                                    "p": model_pending,
                                }
                            )
                        )

                    opts = replace(threaded_opts, page_progress=on_pdf_page)
                    try:
                        outcome = convert_file_with_details(file_path, opts)
                        results[file_path] = outcome.markdown
                        self.processing_backends[file_path] = outcome.backend
                    except Exception as exc:
                        self.failed_files.add(file_path)
                        results[file_path] = format_conversion_error(file_path, exc)

                    self.progress.emit(k + 1, total, file_path, False)
                if aborted:
                    break

            self.finished.emit(results)
        finally:
            hc = getattr(self, "_http_client", None)
            self._http_client = None
            if hc is not None:
                try:
                    hc.close()
                except Exception:
                    pass
