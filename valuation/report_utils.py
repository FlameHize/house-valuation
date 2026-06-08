"""报告生成工具 — Markdown → HTML → weasyprint PDF → pymupdf → PIL → PNG"""
import datetime
import os
import io
import markdown as md_lib
import weasyprint
import pymupdf
from PIL import Image as PILImage

REPORT_DIR = "reports"

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @page {{ size: A4; margin: 1.8cm; }}
  body {{ font-family: "WenQuanYi Micro Hei", "Noto Sans CJK SC", sans-serif;
          font-size: 11pt; line-height: 1.7; color: #333; }}
  h1 {{ font-size: 20pt; text-align: center; color: #1a1a1a; margin-bottom: 4pt; }}
  h2 {{ font-size: 16pt; color: #2c3e50; border-bottom: 2px solid #3498db;
        padding-bottom: 3pt; margin-top: 18pt; }}
  h3 {{ font-size: 13pt; color: #2c3e50; margin-top: 12pt; }}
  table {{ border-collapse: collapse; width: 100%; margin: 8pt 0; font-size: 10pt; }}
  th, td {{ border: 1px solid #ccc; padding: 5pt 8pt; text-align: center; }}
  th {{ background-color: #3498db; color: white; font-weight: bold; }}
  tr:nth-child(even) {{ background-color: #f8f9fa; }}
  strong {{ color: #2c3e50; }}
  blockquote {{ border-left: 4px solid #e74c3c; margin: 10pt 0; padding: 6pt 12pt;
               background-color: #fdf2f2; color: #666; font-size: 10pt; }}
  hr {{ border: none; border-top: 1px solid #eee; margin: 12pt 0; }}
  p {{ margin: 6pt 0; }}
  .chart {{ text-align: center; margin: 12pt 0; }}
  .chart img {{ max-width: 100%; height: auto; }}
</style>
</head>
<body>
{body}
</body>
</html>"""


def md_to_png(markdown_text, filename, extra_html=None, save_to_disk=False):
    """将 Markdown 文本渲染为 PNG 图片。返回 (文件名, PNG字节)。"""
    html_body = md_lib.markdown(markdown_text, extensions=["tables", "fenced_code"])
    if extra_html:
        html_body += extra_html
    html_full = HTML_TEMPLATE.format(body=html_body)

    pdf_data = weasyprint.HTML(string=html_full).write_pdf()
    doc = pymupdf.open("pdf", pdf_data)
    pages = [doc[i].get_pixmap(dpi=200) for i in range(doc.page_count)]
    total_h = sum(p.height for p in pages)
    canvas = PILImage.new("RGB", (pages[0].width, total_h))
    y = 0
    for p in pages:
        img = PILImage.frombytes("RGB", (p.width, p.height), p.samples)
        canvas.paste(img, (0, y))
        y += p.height
    doc.close()

    if save_to_disk:
        os.makedirs(REPORT_DIR, exist_ok=True)
        canvas.save(os.path.join(REPORT_DIR, filename))

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return filename, buf.getvalue()


def fig_to_html(fig):
    """将 matplotlib Figure 转为嵌入 HTML 的 base64 img 标签。"""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    import base64
    data = base64.b64encode(buf.getvalue()).decode()
    return f'<div class="chart"><img src="data:image/png;base64,{data}"/></div>'
