# Image Tools

로컬에서 실행하는 이미지 편집 도구. **파일이 외부 서버로 전송되지 않습니다.**

## 기능

| # | 기능 | 설명 |
|---|------|------|
| 1 | 워터마크 추가 | 텍스트 워터마크, 투명도/위치/크기 조절, 타일 모드 |
| 2 | 워터마크 제거 | 마우스로 영역 칠하면 주변 픽셀로 자연스럽게 채움 |
| 3 | 이미지 분할 | 행/열 지정 그리드 분할, ZIP 다운로드 |
| 4 | 이미지 합치기 | 가로/세로/그리드, 간격 조절 |
| 5 | 배경 제거 | AI 기반 (rembg U2-Net), 투명 PNG 출력 |
| 6 | 텍스트 추가 | 위치/크기/색상 지정, 배경 박스 옵션 |

---

## 빠른 시작

### 🪟 Windows (1-클릭)
```
git clone https://github.com/commme/image-tools.git
cd image-tools
start.bat
```

### 🍎 Mac / 🐧 Linux
```bash
git clone https://github.com/commme/image-tools.git
cd image-tools
./start.sh
```

### 수동 실행 (개발자용)
```bash
pip install -r requirements.txt
py web.py
```

필요 패키지: Pillow, Flask, rembg[cpu], opencv-python-headless

> 배경 제거 첫 실행 시 AI 모델(176MB) 자동 다운로드

---

## 실행

```bash
py web.py
```

→ http://localhost:5001 접속

---

## 보안 사항

- 모든 처리는 **로컬에서만** 실행됩니다. 파일이 외부 서버로 전송되지 않습니다.
- 웹 서버는 `127.0.0.1`에서만 접근 가능합니다.
- 이미지는 메모리에서 처리되며 디스크에 저장되지 않습니다.
- DOM 조작 시 innerHTML 대신 createElement/textContent 사용 (XSS 방지).
- 업로드 파일은 MIME 타입 검증 + `secure_filename`으로 처리됩니다.
- Flask 디버그 모드는 기본 OFF (필요 시 `DEBUG=1 py web.py`).
- 공용 네트워크에서 실행하지 마세요 (인증 없음).

---

## 개인정보 처리방침

본 도구는 다음 원칙으로 사용자 데이터를 처리합니다.

| 항목 | 내용 |
|------|------|
| **수집 데이터** | 사용자가 업로드한 이미지 파일 (요청 시점에만) |
| **처리 위치** | 사용자 PC의 로컬 Flask 서버 (`127.0.0.1` 전용) |
| **저장 여부** | **저장하지 않음** — 처리 후 메모리에서 즉시 폐기 |
| **외부 전송** | 없음 (배경제거 AI 모델도 로컬 실행) |
| **제3자 공유** | 없음 |
| **로그** | Flask 표준 access log만 (사용자 PC 콘솔에만 출력) |
| **삭제 방법** | 브라우저 종료 또는 서버 종료 시 자동 폐기 |

> `_uploads/` 폴더는 향후 확장용 빈 폴더이며 실제 사용되지 않습니다 (`.gitignore` 처리됨).

---

## AI로 만드는 프롬프트

```
Python + Flask로 이미지 편집 웹 도구를 만들어줘.

[기능]
1. 워터마크 추가: 텍스트, 투명도, 위치(중앙/모서리/타일), 크기, 색상
2. 워터마크 제거: 캔버스에 마우스로 영역 칠하기 → 가우시안 블러 inpainting
3. 이미지 분할: 행×열 그리드, 미리보기, ZIP 다운로드
4. 이미지 합치기: 여러 이미지, 가로/세로/그리드, 간격 조절
5. 배경 제거: rembg (U2-Net AI 모델), 투명 PNG 출력
6. 텍스트 추가: 좌표 지정, 크기/색상, 배경 박스 옵션

[구조]
- engine.py: Pillow 기반 이미지 처리 함수
- web.py: Flask 서버, 각 기능별 API 엔드포인트
- templates/index.html: 탭 UI, 드래그앤드롭, 미리보기+다운로드
- 서버 127.0.0.1 전용, 다크 모드

[보안]
- innerHTML 금지 → createElement/textContent 사용
- 파일은 메모리에서만 처리, 디스크 저장 안함
```

---

## 라이선스

MIT License — © 2026 COMMME. All rights reserved.

| 라이브러리 | 라이선스 | 용도 |
|-----------|---------|------|
| [Pillow](https://python-pillow.org/) | HPND | 이미지 처리 |
| [Flask](https://flask.palletsprojects.com/) | BSD-3-Clause | 웹 서버 |
| [rembg](https://github.com/danielgatis/rembg) | MIT | AI 배경 제거 |
| [onnxruntime](https://onnxruntime.ai/) | MIT | AI 모델 실행 |
| [opencv-python-headless](https://opencv.org/) | Apache-2.0 | 워터마크/사람 제거 inpainting |

> 이 프로젝트는 Claude Code (Anthropic)의 도움으로 제작되었습니다.
