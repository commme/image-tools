"""
Image Tools Web UI
  워터마크 추가/제거 · 이미지 분할/합치기 · 배경 제거 · 텍스트 추가

실행:
  py web.py          # http://localhost:5001
"""

import sys
import os
import io
import json
import base64
import zipfile
import tempfile
from pathlib import Path
from flask import Flask, request, send_file, jsonify, render_template
from werkzeug.utils import secure_filename

from PIL import Image, UnidentifiedImageError
from engine import (
    add_watermark, remove_watermark, auto_remove_watermark, remove_person,
    split_image, split_to_zip, merge_images,
    remove_background, add_text, upscale_image,
)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100MB


@app.errorhandler(ValueError)
def _value_error(e):
    return jsonify({"error": str(e)}), 400


ALLOWED_MIMES = {"image/png", "image/jpeg", "image/webp", "image/bmp", "image/gif", "image/tiff"}


def _read_image(file) -> Image.Image:
    """Validate MIME + open safely. Raises ValueError on invalid input."""
    if file.mimetype and file.mimetype not in ALLOWED_MIMES:
        raise ValueError(f"지원하지 않는 파일 형식입니다: {file.mimetype}")
    try:
        return Image.open(file.stream).copy()
    except (UnidentifiedImageError, OSError) as e:
        raise ValueError(f"이미지를 열 수 없습니다: {e}")


def _safe_stem(filename: str | None) -> str:
    """Sanitize filename → safe stem for download_name (prevents RTL/control char injection)."""
    if not filename:
        return "image"
    safe = secure_filename(filename) or "image"
    return Path(safe).stem or "image"


def _send_image(img: Image.Image, name: str, fmt: str = "PNG") -> any:
    buf = io.BytesIO()
    if fmt.upper() == "JPEG" and img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    elif fmt.upper() == "JPEG" and img.mode != "RGB":
        img = img.convert("RGB")
    img.save(buf, fmt)
    buf.seek(0)
    mime = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}
    return send_file(buf, mimetype=mime.get(fmt, "image/png"), as_attachment=True, download_name=name)


def _send_preview(img: Image.Image) -> dict:
    """이미지를 base64로 인코딩하여 미리보기용 JSON 반환"""
    buf = io.BytesIO()
    preview = img.copy()
    # 미리보기는 800px 이내로 축소
    if max(preview.size) > 800:
        preview.thumbnail((800, 800))
    preview.save(buf, "PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return {"preview": f"data:image/png;base64,{b64}", "width": img.width, "height": img.height}


@app.route("/")
def index():
    return render_template("index.html")


# ── 1. 워터마크 추가 ────────────────────────────────────────

@app.route("/api/watermark/add", methods=["POST"])
def api_watermark_add():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "파일이 없습니다"}), 400

    img = _read_image(file)
    text = request.form.get("text", "SAMPLE")
    opacity = int(request.form.get("opacity", 80))
    position = request.form.get("position", "center")
    font_size = int(request.form.get("fontSize", 40))
    color = request.form.get("color", "#ffffff")
    tile = request.form.get("tile", "false") == "true"

    # 드래그로 지정한 좌표가 있으면 사용
    drag_x = request.form.get("x")
    drag_y = request.form.get("y")
    if drag_x is not None and drag_y is not None:
        position = "custom"

    result = add_watermark(img, text, opacity, position, font_size, color, tile,
                           custom_x=int(drag_x) if drag_x else None,
                           custom_y=int(drag_y) if drag_y else None)

    preview = request.form.get("preview", "false") == "true"
    if preview:
        return jsonify(_send_preview(result))

    ext = request.form.get("format", "png").lower()
    fmt_map = {"png": "PNG", "jpg": "JPEG", "webp": "WEBP"}
    fmt = fmt_map.get(ext, "PNG")
    stem = _safe_stem(file.filename)
    return _send_image(result, f"{stem}_watermarked.{ext}", fmt)


# ── 2. 워터마크 제거 ────────────────────────────────────────

@app.route("/api/watermark/remove", methods=["POST"])
def api_watermark_remove():
    file = request.files.get("file")
    mask_data = request.form.get("mask")
    if not file or not mask_data:
        return jsonify({"error": "파일과 마스크가 필요합니다"}), 400

    img = _read_image(file)
    # 마스크는 base64 PNG
    mask_bytes = base64.b64decode(mask_data.split(",")[-1])
    mask = Image.open(io.BytesIO(mask_bytes))
    radius = int(request.form.get("radius", 10))

    result = remove_watermark(img, mask, radius)

    preview = request.form.get("preview", "false") == "true"
    if preview:
        return jsonify(_send_preview(result))

    stem = _safe_stem(file.filename)
    return _send_image(result, f"{stem}_cleaned.png", "PNG")


# ── 3. 이미지 분할 ──────────────────────────────────────────

@app.route("/api/split", methods=["POST"])
def api_split():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "파일이 없습니다"}), 400

    img = _read_image(file)
    rows = int(request.form.get("rows", 2))
    cols = int(request.form.get("cols", 2))

    preview = request.form.get("preview", "false") == "true"
    if preview:
        pieces = split_image(img, rows, cols)
        previews = []
        for i, p in enumerate(pieces):
            buf = io.BytesIO()
            thumb = p.copy()
            thumb.thumbnail((200, 200))
            thumb.save(buf, "PNG")
            b64 = base64.b64encode(buf.getvalue()).decode()
            previews.append({"index": i + 1, "src": f"data:image/png;base64,{b64}"})
        return jsonify({"pieces": previews, "total": len(pieces)})

    stem = _safe_stem(file.filename)
    zip_bytes = split_to_zip(img, rows, cols, stem)
    return send_file(
        io.BytesIO(zip_bytes),
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"{stem}_split_{rows}x{cols}.zip",
    )


# ── 2b. 워터마크 자동 감지+제거 ──────────────────────────────

@app.route("/api/watermark/auto-remove", methods=["POST"])
def api_watermark_auto():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "파일이 없습니다"}), 400

    img = _read_image(file)
    sensitivity = int(request.form.get("sensitivity", 50))

    result, mask = auto_remove_watermark(img, sensitivity)

    preview = request.form.get("preview", "false") == "true"
    if preview:
        prev = _send_preview(result)
        # 마스크도 미리보기로 함께 전송
        mask_buf = io.BytesIO()
        mask_rgb = mask.convert("RGB") if mask.mode != "RGB" else mask
        mask_rgb.save(mask_buf, "PNG")
        prev["mask"] = "data:image/png;base64," + base64.b64encode(mask_buf.getvalue()).decode()
        return jsonify(prev)

    stem = _safe_stem(file.filename)
    return _send_image(result, f"{stem}_no_watermark.png", "PNG")


# ── 2c. 사람 제거 ────────────────────────────────────────────

@app.route("/api/remove-person", methods=["POST"])
def api_remove_person():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "파일이 없습니다"}), 400

    img = _read_image(file)

    try:
        result, mask = remove_person(img)
    except ImportError as e:
        return jsonify({"error": str(e)}), 500

    preview = request.form.get("preview", "false") == "true"
    if preview:
        return jsonify(_send_preview(result))

    stem = _safe_stem(file.filename)
    return _send_image(result, f"{stem}_no_person.png", "PNG")


# ── 2e. 업스케일링 ───────────────────────────────────────────

@app.route("/api/upscale", methods=["POST"])
def api_upscale():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "파일이 없습니다"}), 400

    img = _read_image(file)
    scale = float(request.form.get("scale", 2))
    sharpen = int(request.form.get("sharpen", 50))

    result = upscale_image(img, scale, sharpen)

    preview = request.form.get("preview", "false") == "true"
    if preview:
        prev = _send_preview(result)
        prev["origSize"] = f"{img.width}x{img.height}"
        prev["newSize"] = f"{result.width}x{result.height}"
        return jsonify(prev)

    stem = _safe_stem(file.filename)
    return _send_image(result, f"{stem}_{scale}x.png", "PNG")


# ── 3b. 커스텀 분할 (가이드라인 좌표 기반) ────────────────────

@app.route("/api/split-custom", methods=["POST"])
def api_split_custom():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "파일이 없습니다"}), 400

    img = _read_image(file)
    h_lines_str = request.form.get("hLines", "")  # "0.33,0.66" (비율)
    v_lines_str = request.form.get("vLines", "")

    h_ratios = [float(x) for x in h_lines_str.split(",") if x.strip()] if h_lines_str else []
    v_ratios = [float(x) for x in v_lines_str.split(",") if x.strip()] if v_lines_str else []

    w, h = img.size
    h_cuts = sorted([0] + [int(r * h) for r in h_ratios] + [h])
    v_cuts = sorted([0] + [int(r * w) for r in v_ratios] + [w])

    pieces = []
    for ri in range(len(h_cuts) - 1):
        for ci in range(len(v_cuts) - 1):
            box = (v_cuts[ci], h_cuts[ri], v_cuts[ci + 1], h_cuts[ri + 1])
            pieces.append(img.crop(box))

    preview = request.form.get("preview", "false") == "true"
    if preview:
        previews = []
        cols = len(v_cuts) - 1
        for i, p in enumerate(pieces):
            buf = io.BytesIO()
            thumb = p.copy()
            thumb.thumbnail((200, 200))
            thumb.save(buf, "PNG")
            b64 = base64.b64encode(buf.getvalue()).decode()
            previews.append({"index": i + 1, "src": f"data:image/png;base64,{b64}"})
        return jsonify({"pieces": previews, "total": len(pieces), "cols": cols})

    stem = _safe_stem(file.filename)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, piece in enumerate(pieces):
            img_buf = io.BytesIO()
            piece.save(img_buf, "PNG")
            zf.writestr(f"{stem}_{i+1:02d}.png", img_buf.getvalue())
    buf.seek(0)
    return send_file(buf, mimetype="application/zip", as_attachment=True,
                     download_name=f"{stem}_custom_split.zip")


# ── 4. 이미지 합치기 ─────────────────────────────────────────

@app.route("/api/merge", methods=["POST"])
def api_merge():
    files = request.files.getlist("files")
    if len(files) < 2:
        return jsonify({"error": "2개 이상의 이미지가 필요합니다"}), 400

    images = [_read_image(f) for f in files]
    direction = request.form.get("direction", "horizontal")
    gap = int(request.form.get("gap", 0))
    bg_color = request.form.get("bgColor", "#ffffff")

    result = merge_images(images, direction, gap, bg_color)

    preview = request.form.get("preview", "false") == "true"
    if preview:
        return jsonify(_send_preview(result))

    return _send_image(result, f"merged_{direction}.png", "PNG")


# ── 5. 배경 제거 ─────────────────────────────────────────────

@app.route("/api/remove-bg", methods=["POST"])
def api_remove_bg():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "파일이 없습니다"}), 400

    img = _read_image(file)

    try:
        result = remove_background(img)
    except ImportError as e:
        return jsonify({"error": str(e)}), 500

    preview = request.form.get("preview", "false") == "true"
    if preview:
        return jsonify(_send_preview(result))

    stem = _safe_stem(file.filename)
    return _send_image(result, f"{stem}_nobg.png", "PNG")


# ── 6. 텍스트 추가 ──────────────────────────────────────────

@app.route("/api/text", methods=["POST"])
def api_text():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "파일이 없습니다"}), 400

    img = _read_image(file)
    text = request.form.get("text", "텍스트")
    x = int(request.form.get("x", 50))
    y = int(request.form.get("y", 50))
    font_size = int(request.form.get("fontSize", 40))
    color = request.form.get("color", "#ffffff")
    bg_color = request.form.get("bgColor", "")

    rotation = int(request.form.get("rotation", 0))
    font_name = request.form.get("font", "")
    bold = request.form.get("bold", "true") == "true"
    result = add_text(img, text, x, y, font_size, color, bg_color or None, rotation=rotation, font_name=font_name, bold=bold)

    preview = request.form.get("preview", "false") == "true"
    if preview:
        return jsonify(_send_preview(result))

    ext = request.form.get("format", "png").lower()
    fmt_map = {"png": "PNG", "jpg": "JPEG", "webp": "WEBP"}
    fmt = fmt_map.get(ext, "PNG")
    stem = _safe_stem(file.filename)
    return _send_image(result, f"{stem}_text.{ext}", fmt)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5001
    print(f"\n  Image Tools")
    print(f"  http://localhost:{port}\n")
    debug_mode = os.environ.get("DEBUG", "0") == "1"
    app.run(host="127.0.0.1", port=port, debug=debug_mode)
