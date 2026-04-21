"""
Image Tools Engine
  워터마크 추가/제거 · 이미지 분할/합치기 · 배경 제거 · 텍스트 추가
"""

import io
import math
import zipfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


# ── 1. 워터마크 추가 ────────────────────────────────────────

def add_watermark(
    img: Image.Image,
    text: str,
    opacity: int = 80,
    position: str = "center",
    font_size: int = 40,
    color: str = "#ffffff",
    tile: bool = False,
    custom_x: int = None,
    custom_y: int = None,
) -> Image.Image:
    """이미지에 텍스트 워터마크 추가"""
    base = img.convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except (OSError, IOError):
        font = ImageFont.load_default(size=font_size)

    # 색상 파싱 + 투명도 적용
    r, g, b = _hex_to_rgb(color)
    alpha = int(255 * opacity / 100)
    fill = (r, g, b, alpha)

    if tile:
        # 타일 모드: 전체에 반복
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        spacing_x = tw + 80
        spacing_y = th + 60
        for y in range(-th, base.height + th, spacing_y):
            for x in range(-tw, base.width + tw, spacing_x):
                draw.text((x, y), text, font=font, fill=fill)
    else:
        # 단일 위치
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if custom_x is not None and custom_y is not None:
            pos = (custom_x, custom_y)
        else:
            pos = _calc_position(base.size, (tw, th), position)
        draw.text(pos, text, font=font, fill=fill)

    return Image.alpha_composite(base, overlay).convert("RGB")


# ── 2. 워터마크 제거 (inpainting) ────────────────────────────

def _smart_inpaint(img_arr, mask_arr):
    """다중 패스 inpainting — 작은 영역부터 점진적으로 복원"""
    import cv2
    import numpy as np

    result = img_arr.copy()

    # 1패스: NS 알고리즘 (유체역학 기반, 텍스트 경계에 강함)
    result = cv2.inpaint(result, mask_arr, 5, cv2.INPAINT_NS)
    # 2패스: TELEA 알고리즘으로 보정
    result = cv2.inpaint(result, mask_arr, 3, cv2.INPAINT_TELEA)
    # 3패스: 경계 부드럽게
    blur_mask = cv2.GaussianBlur(mask_arr, (11, 11), 0)
    blur_mask = (blur_mask / 255.0).astype(np.float32)
    blended = cv2.GaussianBlur(result, (5, 5), 0)
    for c in range(3):
        result[:, :, c] = (result[:, :, c] * (1 - blur_mask * 0.3) +
                           blended[:, :, c] * blur_mask * 0.3).astype(np.uint8)

    return result


def remove_watermark(
    img: Image.Image,
    mask: Image.Image,
    radius: int = 10,
) -> Image.Image:
    """마스크 영역의 워터마크를 제거 (LaMa AI → OpenCV fallback)"""
    import numpy as np
    import cv2

    base = img.convert("RGB")
    m = mask.convert("L").resize(base.size)

    img_arr = np.array(base)
    mask_arr = np.array(m)

    _, mask_bin = cv2.threshold(mask_arr, 50, 255, cv2.THRESH_BINARY)

    kernel = np.ones((max(3, radius // 2), max(3, radius // 2)), np.uint8)
    mask_dilated = cv2.dilate(mask_bin, kernel, iterations=2)

    result_arr = _smart_inpaint(img_arr, mask_dilated)
    return Image.fromarray(result_arr)


# ── 2b. 워터마크 자동 감지 + 제거 ─────────────────────────────

def auto_remove_watermark(
    img: Image.Image,
    sensitivity: int = 50,
) -> tuple[Image.Image, Image.Image]:
    """밝은 반투명 워터마크를 자동 감지하여 제거. (result, mask) 반환"""
    import numpy as np
    import cv2

    base = img.convert("RGB")
    arr = np.array(base)

    # 그레이스케일 + 엣지 검출로 텍스트 패턴 찾기
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

    # 밝은 영역 감지 (워터마크는 보통 밝은 반투명 텍스트)
    thresh = 255 - sensitivity  # sensitivity 높을수록 더 많이 감지
    _, bright = cv2.threshold(gray, thresh, 255, cv2.THRESH_BINARY)

    # 엣지 검출 (텍스트는 엣지가 많음)
    edges = cv2.Canny(gray, 100, 200)

    # 밝은 영역 AND 엣지 근처 = 워터마크 후보
    # 엣지를 팽창시켜서 텍스트 영역 확보
    kernel_edge = np.ones((5, 5), np.uint8)
    edges_dilated = cv2.dilate(edges, kernel_edge, iterations=3)

    # 밝은 영역과 엣지 영역의 교집합
    mask = cv2.bitwise_and(bright, edges_dilated)

    # 노이즈 제거 + 마스크 확장
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.dilate(mask, kernel, iterations=3)

    # 너무 작은 영역 제거 (노이즈)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_area = (arr.shape[0] * arr.shape[1]) * 0.0005  # 이미지 면적의 0.05%
    clean_mask = np.zeros_like(mask)
    for c in contours:
        if cv2.contourArea(c) > min_area:
            cv2.drawContours(clean_mask, [c], -1, 255, -1)

    if np.sum(clean_mask) == 0:
        return base, Image.fromarray(clean_mask)

    result_arr = _smart_inpaint(arr, clean_mask)
    return Image.fromarray(result_arr), Image.fromarray(clean_mask)


# ── 2c. 사람 제거 (rembg 마스크 + inpainting) ────────────────

def remove_person(img: Image.Image) -> tuple[Image.Image, Image.Image]:
    """이미지에서 사람(전경)을 감지하고 제거. (result, mask) 반환"""
    import numpy as np
    import cv2

    try:
        from rembg import remove
    except ImportError:
        raise ImportError("rembg 미설치: pip install rembg[cpu]")

    base = img.convert("RGB")

    # rembg로 전경(사람) 마스크 추출
    import io as _io
    buf_in = _io.BytesIO()
    img.save(buf_in, "PNG")
    result_bytes = remove(buf_in.getvalue())
    fg = Image.open(_io.BytesIO(result_bytes)).convert("RGBA")

    # 알파 채널 = 전경 마스크 (사람이 있는 부분)
    alpha = np.array(fg.split()[3])

    # 마스크 이진화: 사람 영역 (알파 > 128)
    _, person_mask = cv2.threshold(alpha, 128, 255, cv2.THRESH_BINARY)

    # 마스크 확장 (경계 깔끔하게)
    kernel = np.ones((5, 5), np.uint8)
    person_mask = cv2.dilate(person_mask, kernel, iterations=3)

    arr = np.array(base)
    result_arr = _smart_inpaint(arr, person_mask)

    return Image.fromarray(result_arr), Image.fromarray(person_mask)


# ── 2d. 업스케일링 ───────────────────────────────────────────

def upscale_image(
    img: Image.Image,
    scale: float = 2,
    sharpen: int = 50,
) -> Image.Image:
    """이미지 크기 조절 — 확대/축소 (LANCZOS + Unsharp Mask 선명화)"""
    base = img.convert("RGB")
    new_w = max(1, round(base.width * scale))
    new_h = max(1, round(base.height * scale))

    # LANCZOS 리샘플링 (가장 고품질 보간법)
    upscaled = base.resize((new_w, new_h), Image.LANCZOS)

    # Unsharp Mask 선명화
    if sharpen > 0:
        radius = 2.0 + (scale - 1) * 0.5
        percent = sharpen * 3
        threshold = 2
        upscaled = upscaled.filter(
            ImageFilter.UnsharpMask(radius=radius, percent=percent, threshold=threshold)
        )

    return upscaled


# ── 3. 이미지 분할 ──────────────────────────────────────────

def split_image(
    img: Image.Image,
    rows: int = 2,
    cols: int = 2,
) -> list[Image.Image]:
    """이미지를 rows x cols 그리드로 분할"""
    w, h = img.size
    cell_w = w // cols
    cell_h = h // rows
    pieces = []

    for r in range(rows):
        for c in range(cols):
            box = (c * cell_w, r * cell_h, (c + 1) * cell_w, (r + 1) * cell_h)
            pieces.append(img.crop(box))

    return pieces


def split_to_zip(img: Image.Image, rows: int, cols: int, stem: str = "split") -> bytes:
    """분할 결과를 ZIP 바이트로 반환"""
    pieces = split_image(img, rows, cols)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, piece in enumerate(pieces):
            img_buf = io.BytesIO()
            piece.save(img_buf, "PNG")
            zf.writestr(f"{stem}_{i+1:02d}.png", img_buf.getvalue())
    return buf.getvalue()


# ── 4. 이미지 합치기 ─────────────────────────────────────────

def merge_images(
    images: list[Image.Image],
    direction: str = "horizontal",
    gap: int = 0,
    bg_color: str = "#ffffff",
) -> Image.Image:
    """여러 이미지를 하나로 합치기"""
    if not images:
        raise ValueError("이미지가 없습니다")

    bg = _hex_to_rgb(bg_color)

    if direction == "horizontal":
        total_w = sum(im.width for im in images) + gap * (len(images) - 1)
        max_h = max(im.height for im in images)
        result = Image.new("RGB", (total_w, max_h), bg)
        x = 0
        for im in images:
            result.paste(im.convert("RGB"), (x, (max_h - im.height) // 2))
            x += im.width + gap

    elif direction == "vertical":
        max_w = max(im.width for im in images)
        total_h = sum(im.height for im in images) + gap * (len(images) - 1)
        result = Image.new("RGB", (max_w, total_h), bg)
        y = 0
        for im in images:
            result.paste(im.convert("RGB"), ((max_w - im.width) // 2, y))
            y += im.height + gap

    elif direction == "grid":
        cols = math.ceil(math.sqrt(len(images)))
        rows = math.ceil(len(images) / cols)
        cell_w = max(im.width for im in images)
        cell_h = max(im.height for im in images)
        total_w = cols * cell_w + gap * (cols - 1)
        total_h = rows * cell_h + gap * (rows - 1)
        result = Image.new("RGB", (total_w, total_h), bg)
        for i, im in enumerate(images):
            r, c = divmod(i, cols)
            x = c * (cell_w + gap) + (cell_w - im.width) // 2
            y = r * (cell_h + gap) + (cell_h - im.height) // 2
            result.paste(im.convert("RGB"), (x, y))
    else:
        raise ValueError(f"direction은 horizontal/vertical/grid 중 하나: {direction}")

    return result


# ── 5. 배경 제거 ─────────────────────────────────────────────

def remove_background(img: Image.Image) -> Image.Image:
    """AI 기반 배경 제거 (rembg)"""
    try:
        from rembg import remove
    except ImportError:
        raise ImportError("rembg 미설치: pip install rembg[gpu] 또는 pip install rembg")

    # PIL Image → bytes → rembg → PIL Image
    buf_in = io.BytesIO()
    img.save(buf_in, "PNG")
    buf_out = remove(buf_in.getvalue())
    return Image.open(io.BytesIO(buf_out)).convert("RGBA")


# ── 6. 텍스트 추가 ──────────────────────────────────────────

def add_text(
    img: Image.Image,
    text: str,
    x: int = 50,
    y: int = 50,
    font_size: int = 40,
    color: str = "#ffffff",
    bg_color: str = None,
    padding: int = 8,
    rotation: int = 0,
    font_name: str = "",
    bold: bool = True,
) -> Image.Image:
    """이미지에 텍스트 오버레이 (회전, 폰트 지정, Bold 지원)"""
    base = img.convert("RGBA")

    # 폰트 로드
    font = None
    bold_suffix = "bd" if bold else ""
    if font_name:
        # 시스템 폰트 탐색 (bold 변형 우선)
        candidates = []
        if bold:
            candidates += [
                f"C:/Windows/Fonts/{font_name}bd.ttf",
                f"C:/Windows/Fonts/{font_name} Bold.ttf",
                f"C:/Windows/Fonts/{font_name}-Bold.ttf",
            ]
        candidates += [
            f"C:/Windows/Fonts/{font_name}.ttf",
            f"C:/Windows/Fonts/{font_name}.ttc",
        ]
        for fp in candidates:
            try:
                font = ImageFont.truetype(fp, font_size)
                break
            except (OSError, IOError):
                continue
        if not font:
            try:
                font = ImageFont.truetype(font_name, font_size)
            except (OSError, IOError):
                pass
    if not font:
        try:
            default_font = "arialbd.ttf" if bold else "arial.ttf"
            font = ImageFont.truetype(default_font, font_size)
        except (OSError, IOError):
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except (OSError, IOError):
                font = ImageFont.load_default(size=font_size)

    r, g, b = _hex_to_rgb(color)

    # 텍스트를 별도 레이어에 그린 후 회전
    bbox_test = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), text, font=font)
    tw, th = bbox_test[2] - bbox_test[0] + padding * 2, bbox_test[3] - bbox_test[1] + padding * 2

    txt_layer = Image.new("RGBA", (tw + padding * 2, th + padding * 2), (0, 0, 0, 0))
    txt_draw = ImageDraw.Draw(txt_layer)

    if bg_color:
        br, bg_g, bb = _hex_to_rgb(bg_color)
        txt_draw.rectangle([0, 0, tw + padding, th + padding], fill=(br, bg_g, bb, 180))

    txt_draw.text((padding, padding), text, font=font, fill=(r, g, b, 255))

    # 회전
    if rotation != 0:
        txt_layer = txt_layer.rotate(-rotation, expand=True, resample=Image.BICUBIC)

    # 합성
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    paste_x = x - txt_layer.width // 2
    paste_y = y - txt_layer.height // 2
    overlay.paste(txt_layer, (paste_x, paste_y), txt_layer)

    return Image.alpha_composite(base, overlay).convert("RGB")


# ── 유틸리티 ─────────────────────────────────────────────────

def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def _calc_position(
    img_size: tuple[int, int],
    text_size: tuple[int, int],
    position: str,
    margin: int = 20,
) -> tuple[int, int]:
    iw, ih = img_size
    tw, th = text_size

    positions = {
        "center": ((iw - tw) // 2, (ih - th) // 2),
        "top-left": (margin, margin),
        "top-right": (iw - tw - margin, margin),
        "bottom-left": (margin, ih - th - margin),
        "bottom-right": (iw - tw - margin, ih - th - margin),
    }
    return positions.get(position, positions["center"])
