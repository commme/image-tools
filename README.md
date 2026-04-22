# Image Tools

설치 없이 **브라우저에서 바로 쓰는** 이미지 편집 도구 + 무거운 AI 처리는 **로컬 Flask**.
어느 쪽이든 **파일이 외부 서버로 전송되지 않습니다.**

🌐 **웹 데모(설치 없음)**: https://commme.github.io/image-tools/

## 기능

| # | 기능 | 웹 | 로컬 | 비고 |
|---|------|:--:|:--:|------|
| 1 | 워터마크 추가 | ✅ | ✅ | Canvas 기반 |
| 2 | 이미지 분할 | ✅ | ✅ | 그리드 + ZIP |
| 3 | 이미지 합치기 | ✅ | ✅ | 가로/세로/그리드 |
| 4 | 텍스트 추가 | ✅ | ✅ | 위치/색/배경박스 |
| 5 | 업스케일링 | ✅ | ✅ | 2x/3x/4x + 샤픈 |
| 6 | 워터마크 제거 | ✅ | ✅ | 웹: 브러쉬 + 순수 JS edge-pull inpainting (의존성 0) · 로컬: opencv-python |
| 7 | 배경 제거 | ✅ | ✅ | 웹: @imgly/background-removal U²-Net ONNX (~40MB) · 로컬: rembg |
| 8 | 사람 제거 | ✅ | ✅ | 웹: U²-Net 마스크 + OpenCV.js inpaint · 로컬: rembg + opencv |

> v1.1부터 무거운 AI 처리(6~8)도 브라우저에서 실행됩니다 (ONNX/WebAssembly).
> 첫 실행 시 모델/라이브러리가 jsDelivr CDN에서 다운로드되어 브라우저에 캐시됩니다.
> 모든 연산은 사용자 디바이스에서 처리되며 서버 비용은 0원입니다.

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

## 변경이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| v1.0 | 2026-04-21 | 초기 Flask 웹앱 출시. 8가지 기능을 로컬에서 모두 지원 (Pillow + rembg + OpenCV) |
| v1.0.1 | 2026-04-21 | 정적 웹 데모(GitHub Pages) 추가. Canvas 기반 5개 기능 브라우저 실행, 무거운 3개는 로컬 안내 |
| **v1.1** | **2026-04-21** | **브라우저 ONNX 통합** — 모든 8개 기능을 브라우저에서 직접 실행. `@imgly/background-removal`(U²-Net) + OpenCV.js로 배경 제거·사람 제거·워터마크 제거가 웹에서도 작동. 서버 비용 0원, 첫 실행 시 모델 lazy 다운로드 후 브라우저 캐시 사용 |
| **v1.2** | **2026-04-22** | **UX 옵션 확장** — 워터마크/텍스트 **드래그로 위치 이동** · **글씨체 8종**(Pretendard / Noto Serif KR / 손글씨 / Georgia / Impact 등) · **굵기 4단계 + Italic** · 이미지 분할 **프리셋 버튼 7종**(1×2~4×4) · 이미지 합치기 **썸네일 + 누적 추가/개별 제거** |
| **v1.3** | **2026-04-22** | **미리보기 흐름 통일 + 버그 픽스** — 모든 "실행" 버튼 → **"👁 미리보기"** 로 변경 (확인 후 다운로드 2단계) · **텍스트 복제 현상 해결** (`showResult`에서 드래그 좌표 리셋) · **워터마크 제거 무한 버퍼링 해결** (`new cv.Mat.zeros` → `cv.Mat.zeros` 정정 + try/catch + OpenCV 로드 실패 메시지) |
| **v1.4** | **2026-04-22** | **분할/합치기/드래그 UX 추가 보강** — ① 워터마크 위치 기본값 **🖱 드래그 위치 (selected)** 로 변경 · ② **분할도 미리보기 후 다운로드** (그리드 가이드 라인 + ZIP은 다운로드 버튼 클릭 시 저장, `setPendingBlob` 추가) · ③ **메인 파일 선택 다중 지원** (2장 이상 선택 시 자동 '이미지 합치기' 모드로 전환 + 썸네일 적재) · ④ 워터마크 제거 OpenCV 로드 실패 시 **promise 캐시 초기화** (재시도 가능) |
| **v1.6** | **2026-04-22** | **워터마크 제거 브러쉬 모드 + 라이브 프리뷰 전환** — ① 워터마크 제거를 **드래그 사각형 → 브러쉬 페인팅**으로 변경, OpenCV.js(9MB) 의존 완전 제거 → **순수 JS edge-pull inpainting** (좌/우/상/하 4방향 가장 가까운 비마스크 픽셀 평균) · 1~3초 내 완료 · 무한 버퍼링 버그 근절 · ② 텍스트/워터마크 드래그 시 overlay ghost → **previewCanvas 라이브 렌더링**으로 전환 (배경 사라짐 버그 해결) · ③ 브러쉬 크기 슬라이더 5~120px + 마스크 지우기 버튼 추가 |
| **v1.5** | **2026-04-22** | **이동 전용 모드 + 합치기 비율 정규화** — ① 워터마크 텍스트도 드래그 한 번 안 해도 즉시 중앙 배치 (default fallback) · ② 분할 버튼 라벨에서 `+ ZIP` 제거 → "👁 분할 미리보기" · ③ 이미지 합치기 **비율 자동 정규화** (가로: 동일 높이로 스케일 / 세로: 동일 너비로 스케일 / 그리드: letterbox 셀에 비율 보존) · ④ **텍스트/워터마크 이동 시 복제 해결** — 미리보기 후 다시 드래그하면 원본으로 복원 후 ghost 표시 (commit은 다음 미리보기 클릭 시) · ⑤ 워터마크 제거 콘솔 로깅 추가 |

### 웹 vs 로컬 어떤 걸 써야 하나요?

| 상황 | 추천 |
|------|------|
| 한 번 빠르게 처리하고 싶음 | **웹** (https://commme.github.io/image-tools/) |
| 큰 이미지를 빠르게 처리 | **로컬** (Python/CPU 직접 사용) |
| 인터넷 없이 사용 | **로컬** |
| 모델 다운로드 트래픽 아끼고 싶음 | **로컬** (한 번만 받음) |
| 설치/세팅 귀찮음 | **웹** |

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
