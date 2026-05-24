from __future__ import annotations

import base64
import hashlib
import html
import mimetypes
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from app.core.config import EXPORTS_DIR, PROJECT_ROOT


NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}


def docx_to_html_preview(file_path: str | Path, max_body_children: int = 500) -> str:
    path = Path(file_path)
    if not path.exists():
        return _wrap_error("Word 文件不存在，无法预览。")
    if path.suffix.lower() != ".docx":
        return _wrap_error("当前仅支持 .docx 文件预览。")

    try:
        with zipfile.ZipFile(path) as docx:
            rels = _read_relationships(docx)
            root = ET.fromstring(docx.read("word/document.xml"))
            body = root.find("w:body", NS)
            if body is None:
                raise ValueError("未找到 Word 文档正文。")

            fragments: list[str] = []
            for index, child in enumerate(list(body), start=1):
                if index > max_body_children:
                    fragments.append('<p class="docx-preview-note">文档较长，后续内容已省略。请下载原始 Word 查看完整内容。</p>')
                    break
                if child.tag == f"{{{NS['w']}}}p":
                    fragments.append(_paragraph_html(child, docx, rels))
                elif child.tag == f"{{{NS['w']}}}tbl":
                    fragments.append(_table_html(child))
            content = "\n".join(fragments) or '<p class="docx-preview-note">文档正文为空。</p>'
    except Exception as exc:
        content = f'<div class="docx-preview-error">Word 预览失败：{html.escape(str(exc))}</div>'

    return _wrap_page(
        content,
        notice="当前为降级 HTML 预览，不能完全代表 Word 原始格式、分页和图片位置。建议安装 LibreOffice 后使用高保真 PDF 预览。",
    )


def docx_to_best_preview(file_path: str | Path, pdf_url: str) -> str:
    path = Path(file_path)
    if path.suffix.lower() == ".pdf":
        return _wrap_pdf_page(pdf_url)
    try:
        get_docx_pdf_preview_path(file_path)
        return _wrap_pdf_page(pdf_url)
    except Exception as exc:
        fallback = docx_to_html_preview(file_path) if path.suffix.lower() == ".docx" else _wrap_error(
            "当前报告需要 LibreOffice 转换后才能预览。请检查运行环境中的 LibreOffice 是否可用。"
        )
        return fallback.replace(
            "</body>",
            f'<div class="docx-convert-warning">未能生成高保真 PDF 预览：{html.escape(str(exc))}</div></body>',
        )


def get_docx_pdf_preview_path(file_path: str | Path) -> Path:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError("报告文件不存在，无法生成预览。")
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return path
    if suffix not in {".docx", ".doc"}:
        raise ValueError("当前仅支持 .docx、.doc 和 .pdf 文件预览。")

    cache_dir = EXPORTS_DIR / "previews"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.sha1(f"{path.resolve()}|{path.stat().st_mtime_ns}|{path.stat().st_size}".encode("utf-8")).hexdigest()
    cached_pdf = cache_dir / f"{cache_key}.pdf"
    if cached_pdf.exists() and cached_pdf.stat().st_size > 0:
        return cached_pdf

    converter = _find_office_converter()
    if converter:
        _convert_with_soffice(path, cached_pdf, converter)
        return cached_pdf

    if _try_convert_with_word_com(path, cached_pdf):
        return cached_pdf

    raise RuntimeError("未检测到可用的 LibreOffice 或系统文档转换能力，无法生成高保真 PDF 预览。")


def _convert_with_soffice(path: Path, cached_pdf: Path, converter: str) -> None:
    with tempfile.TemporaryDirectory(prefix="aigrader_docx_preview_") as tmp_dir_name:
        tmp_dir = Path(tmp_dir_name)
        completed = subprocess.run(
            [
                converter,
                "--headless",
                "--nologo",
                "--nofirststartwizard",
                "--convert-to",
                "pdf",
                "--outdir",
                str(tmp_dir),
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        generated = list(tmp_dir.glob("*.pdf"))
        if completed.returncode != 0 or not generated:
            error_text = (completed.stderr or completed.stdout or "转换程序未生成 PDF 文件。").strip()
            raise RuntimeError(f"Word 转 PDF 失败：{error_text[:300]}")
        shutil.copyfile(generated[0], cached_pdf)


def _find_office_converter() -> str | None:
    status = get_preview_converter_status()
    if status["available"] and status["kind"] in {"env", "bundled_libreoffice", "system_libreoffice"}:
        return status["path"]
    if status["available"] and status["kind"] == "bundled_archive":
        extracted = _extract_bundled_libreoffice()
        return str(extracted) if extracted else None
    return None


def get_preview_converter_status() -> dict:
    configured = os.getenv("AIGRADER_OFFICE_CONVERTER")
    candidates = [
        ("env", configured),
        ("bundled_libreoffice", _bundled_runtime_soffice()),
        ("bundled_libreoffice", PROJECT_ROOT / "runtime" / "libreoffice" / "program" / "soffice.exe"),
        ("bundled_libreoffice", PROJECT_ROOT / "runtime" / "LibreOffice" / "program" / "soffice.exe"),
        ("bundled_libreoffice", PROJECT_ROOT / "runtime" / "LibreOfficePortable" / "App" / "libreoffice" / "program" / "soffice.exe"),
        ("bundled_libreoffice", PROJECT_ROOT / "tools" / "libreoffice" / "program" / "soffice.exe"),
    ]
    for kind, candidate in candidates:
        if candidate and Path(candidate).exists():
            return {
                "available": True,
                "kind": kind,
                "path": str(Path(candidate)),
                "message": "已检测到文档预览转换器，可生成更接近原始 Word 版式的 PDF 预览。",
            }
    archive = PROJECT_ROOT / "runtime" / "libreoffice.zip"
    if archive.exists():
        return {
            "available": True,
            "kind": "bundled_archive",
            "path": str(archive),
            "message": "已检测到内置 LibreOffice 压缩包，首次预览时会自动解压并用于生成 PDF 预览。",
        }
    system_candidates = [
        shutil.which("soffice"),
        shutil.which("libreoffice"),
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]
    for candidate in system_candidates:
        if candidate and Path(candidate).exists():
            return {
                "available": True,
                "kind": "system_libreoffice",
                "path": str(Path(candidate)),
                "message": "已检测到系统 LibreOffice 转换器，可生成更接近原始 Word 版式的 PDF 预览。",
            }
    if _is_word_com_available():
        return {
            "available": True,
            "kind": "system_word",
            "path": "",
            "message": "未检测到内置 LibreOffice，但检测到系统 Word 自动化能力，可作为兜底转换方案。",
        }
    return {
        "available": False,
        "kind": "none",
        "path": "",
        "message": "未检测到内置文档转换器。Word 预览将降级为 HTML 预览，版式可能不准确。",
    }


def _extract_bundled_libreoffice() -> Path | None:
    archive = PROJECT_ROOT / "runtime" / "libreoffice.zip"
    target = _bundled_runtime_soffice().parents[1]
    soffice = target / "program" / "soffice.exe"
    if soffice.exists():
        return soffice
    if not archive.exists():
        return None

    temp_target = PROJECT_ROOT / ".runtime" / "libreoffice_extracting"
    if temp_target.exists():
        shutil.rmtree(temp_target, ignore_errors=True)
    temp_target.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(temp_target)
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
        shutil.move(str(temp_target), str(target))
    finally:
        if temp_target.exists():
            shutil.rmtree(temp_target, ignore_errors=True)
    return soffice if soffice.exists() else None


def _bundled_runtime_soffice() -> Path:
    configured = os.getenv("AIGRADER_LIBREOFFICE_RUNTIME_DIR")
    if configured:
        return Path(configured).expanduser().resolve() / "program" / "soffice.exe"
    return PROJECT_ROOT / "runtime" / "libreoffice" / "program" / "soffice.exe"


def _is_word_com_available() -> bool:
    if os.name != "nt":
        return False
    try:
        import pythoncom  # type: ignore  # noqa: F401
        import win32com.client  # type: ignore  # noqa: F401
        return True
    except Exception:
        return False


def _try_convert_with_word_com(path: Path, output_pdf: Path) -> bool:
    if os.name != "nt":
        return False
    try:
        import pythoncom  # type: ignore
        import win32com.client  # type: ignore
    except Exception:
        return False

    word = None
    try:
        pythoncom.CoInitialize()
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        document = word.Documents.Open(str(path.resolve()), ReadOnly=True)
        try:
            document.SaveAs(str(output_pdf.resolve()), FileFormat=17)
        finally:
            document.Close(False)
        return output_pdf.exists() and output_pdf.stat().st_size > 0
    except Exception:
        try:
            if output_pdf.exists():
                output_pdf.unlink()
        except Exception:
            pass
        return False
    finally:
        if word is not None:
            try:
                word.Quit()
            except Exception:
                pass
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass


def _read_relationships(docx: zipfile.ZipFile) -> dict[str, str]:
    rels: dict[str, str] = {}
    try:
        root = ET.fromstring(docx.read("word/_rels/document.xml.rels"))
    except Exception:
        return rels
    for rel in root:
        rel_id = rel.attrib.get("Id")
        target = rel.attrib.get("Target")
        if rel_id and target:
            rels[rel_id] = target.lstrip("/") if target.startswith("/") else f"word/{target}".replace("\\", "/")
    return rels


def _paragraph_html(element: ET.Element, docx: zipfile.ZipFile, rels: dict[str, str]) -> str:
    parts: list[str] = []
    for node in element.iter():
        if node.tag == f"{{{NS['w']}}}t":
            parts.append(html.escape(node.text or ""))
        elif node.tag == f"{{{NS['w']}}}tab":
            parts.append("&emsp;")
        elif node.tag == f"{{{NS['w']}}}br":
            parts.append("<br>")
        elif node.tag == f"{{{NS['a']}}}blip":
            rel_id = node.attrib.get(f"{{{NS['r']}}}embed")
            image_path = rels.get(rel_id or "")
            data_url = _image_data_url(docx, image_path) if image_path else None
            if data_url:
                parts.append(f'<div class="docx-image-wrap"><img src="{data_url}" /></div>')

    content = "".join(parts).strip()
    return f"<p>{content}</p>" if content else '<p class="docx-empty">&nbsp;</p>'


def _table_html(element: ET.Element) -> str:
    rows = []
    for tr in element.findall("w:tr", NS):
        cells = []
        for tc in tr.findall("w:tc", NS):
            value = html.escape(_cell_text(tc)).replace("\n", "<br>")
            cells.append(f"<td>{value}</td>")
        rows.append(f"<tr>{''.join(cells)}</tr>")
    return f"<table>{''.join(rows)}</table>"


def _cell_text(cell: ET.Element) -> str:
    texts = []
    for text_node in cell.iter(f"{{{NS['w']}}}t"):
        if text_node.text:
            texts.append(text_node.text)
    return "\n".join(texts)


def _image_data_url(docx: zipfile.ZipFile, image_path: str) -> str | None:
    try:
        data = docx.read(image_path)
    except KeyError:
        return None
    mime_type = mimetypes.guess_type(image_path)[0] or "image/png"
    encoded = base64.b64encode(data).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def _wrap_error(message: str) -> str:
    return _wrap_page(f'<div class="docx-preview-error">{html.escape(message)}</div>')


def _wrap_pdf_page(pdf_url: str) -> str:
    safe_url = html.escape(pdf_url, quote=True)
    return f"""
    <html>
    <head>
      <meta charset="utf-8" />
      <style>
        html, body {{
          margin: 0;
          width: 100%;
          height: 100%;
          background: #e5e7eb;
          color: #0f172a;
          font-family: "Microsoft YaHei", Arial, sans-serif;
        }}
        .preview-header {{
          padding: 10px 14px;
          background: #ecfeff;
          border-bottom: 1px solid #bae6fd;
          color: #075985;
          font-size: 14px;
        }}
        .pdf-frame {{
          display: block;
          width: 100%;
          height: calc(100% - 43px);
          border: 0;
          background: #fff;
        }}
      </style>
    </head>
    <body>
      <div class="preview-header">已使用本机 Office/LibreOffice 转换为 PDF 预览，版式通常更接近原始 Word 报告。</div>
      <iframe class="pdf-frame" src="{safe_url}"></iframe>
    </body>
    </html>
    """


def _wrap_page(content: str, notice: str | None = None) -> str:
    notice_html = f'<div class="docx-preview-banner">{html.escape(notice)}</div>' if notice else ""
    return f"""
    <html>
    <head>
      <meta charset="utf-8" />
      <style>
        body {{
          margin: 0;
          background: #e5e7eb;
          color: #111827;
          font-family: "Microsoft YaHei", "SimSun", Arial, sans-serif;
          line-height: 1.65;
        }}
        .docx-page {{
          box-sizing: border-box;
          max-width: 860px;
          min-height: 1080px;
          margin: 18px auto;
          padding: 54px 64px;
          background: white;
          border: 1px solid #d1d5db;
          box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12);
        }}
        p {{
          margin: 0 0 10px 0;
          word-break: break-word;
        }}
        table {{
          border-collapse: collapse;
          width: 100%;
          margin: 12px 0;
          table-layout: fixed;
        }}
        td {{
          border: 1px solid #9ca3af;
          padding: 6px 8px;
          vertical-align: top;
          word-break: break-word;
        }}
        .docx-image-wrap {{
          margin: 10px 0;
          text-align: center;
        }}
        .docx-image-wrap img {{
          max-width: 100%;
          max-height: 760px;
          object-fit: contain;
        }}
        .docx-preview-error {{
          padding: 16px;
          color: #b91c1c;
          background: #fef2f2;
          border: 1px solid #fecaca;
          border-radius: 6px;
        }}
        .docx-preview-note {{
          color: #64748b;
          background: #f8fafc;
          border: 1px dashed #cbd5e1;
          padding: 10px;
        }}
        .docx-preview-banner,
        .docx-convert-warning {{
          max-width: 860px;
          box-sizing: border-box;
          margin: 18px auto 0 auto;
          padding: 12px 14px;
          color: #92400e;
          background: #fffbeb;
          border: 1px solid #facc15;
          border-radius: 8px;
          font-weight: 700;
        }}
        .docx-convert-warning {{
          margin: 0 auto 18px auto;
        }}
      </style>
    </head>
    <body>
      {notice_html}
      <div class="docx-page">{content}</div>
    </body>
    </html>
    """
