# CF384 Local Image Detection API

**로컬 FastAPI 데모 실행:** 설치 → SerpApi 무료 검색 키 저장 → 서버 실행 → 로컬 API 키 확인 → 브라우저에서 사진 업로드 순서입니다. 확장 프로그램 없이 CF384 판별과 Google Lens 사용처 검색을 함께 시연합니다. **[터미널 명령어와 실행 순서](QUICK_START_KO.md)**.

**2026-11-23 / API 1.4.0:** 인터넷 사용처 검색을 **SerpApi Google Lens 무료 요금제 전용**으로 교체했습니다. 무료 요금제와 잔여 한도를 확인하지 못하면 검색을 차단하며 TinEye/유료 fallback은 사용하지 않습니다. CF384 가중치와 임계값은 그대로입니다. [무료 검색 설정](docs/WEB_USAGE_SEARCH_KO.md). 실제 계정 키가 없어 검색 품질 평가는 아직 미실행입니다.

CF384 기반의 로컬 정지 이미지 탐지 API입니다. 원본 분류기, L2-SP+증강 분류기, 160~300px 축소 학습 분류기의 점수를 한 번의 백본 추론으로 반환합니다. Chrome 확장 프로그램은 포함하지 않으며, 연결 예제와 API 명세를 제공합니다.

**이 저장소에는 실제 API 키, 가상환경, 사용자 사진, 평가 원본 데이터, 실행 로그, 대형 백본 가중치를 포함하지 않습니다.** 작은 학습 head 두 개는 `models/`에 포함합니다. 공식 CF384 백본은 아래 명령으로 다운로드합니다. 인증 기능과 `X-API-Key` 헤더 이름은 코드에 유지합니다.

[현재 적용 기술·전체 성능·이미지별 점수 변화](docs/CURRENT_MODEL_KO.md) · [지금까지 작업 요약](docs/WORK_SUMMARY_KO.md)

## 로컬 통합 데모 실행

아래 설치 명령의 `configure_web_search.py`에는 SerpApi Free 계정의 API 키를 숨김 입력합니다. 서버 시작 후에는 별도로 확인한 CF384 로컬 API 키를 데모에 입력합니다. 키 구분과 단계별 화면 사용법은 [간단 사용법](QUICK_START_KO.md)을 따르세요.

모든 명령은 저장소 폴더 안에서 실행합니다. 64비트 Python3.11을 권장합니다. GPU는 필수가 아닙니다.

### macOS

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python prepare_models.py --download
.venv/bin/python configure_web_search.py
.venv/bin/python run_server.py --enable-web-search
```

서버 터미널은 켜 두고, 새 터미널을 같은 폴더에서 엽니다.

```sh
.venv/bin/python client.py --show-key
```

http://127.0.0.1:8000/demo 에 접속해 키를 입력하고 사진을 선택합니다. 대표 결과는 **L2-SP + 증강 + 160~300px 학습 (기본)**이 자동 선택됩니다. 종료는 서버 터미널에서 Ctrl+C입니다.

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install torch==2.8.0 torchvision==0.23.0 --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe prepare_models.py --download
.\.venv\Scripts\python.exe configure_web_search.py
.\.venv\Scripts\python.exe run_server.py --enable-web-search
```

새 터미널에서:

```powershell
.\.venv\Scripts\python.exe client.py --show-key
```

Linux는 동일한 가상환경 구성을 사용하며, CPU 전용 PyTorch는 Windows 설치 예시의 공식 CPU wheel 경로를 사용할 수 있습니다. 실제 검증은 macOS/CPU에서 수행했고 Windows/Linux의 새 설치는 직접 검증하지 않았습니다.

처음 키는 각 설치 폴더의 `.runtime/api_key.txt`에 자동 생성됩니다. 이 폴더는 Git에서 제외됩니다. `CF384_API_KEY` 환경변수를 설정하면 파일보다 우선합니다. 키 문자열만 입력하고 `Bearer`나 `X-API-Key:`를 앞에 붙이지 마세요. 서버 시작 후 모델이 준비돼야 분석할 수 있습니다.

## 이번 업데이트 (2026-11-19 / API 1.2.0)

최신 `lowres`를 API·Python·JS·데모 기본값으로 적용했습니다. 가중치와 임계값 0.5는 그대로입니다. 기존 확장이 `model=adapted`를 명시한다면 `lowres`로 바꾸거나 query를 생략해야 합니다.

실제 웹 썸네일 64장(긴 변 160~280px)에서 기존 head 85.94% → 최신 head 90.63%, 실사 오탐 0/32 → 2/32였습니다. 추가 JPEG85에서는 최신 head 81.25%입니다. Google 썸네일은 아니며 작은 표본으로 웹 전체 성능을 보장하지 않습니다. [지금까지 작업 요약](docs/WORK_SUMMARY_KO.md) · [측정 CSV](docs/evaluation/web_thumbnail_metrics.csv).

## API

| URL | 역할 |
| --- | --- |
| `GET /health` | 준비 상태 |
| `GET /v1/model` | 모델 설명·SHA256·장치 |
| `GET /v1/web-search/status` | 외부 검색 설정·호출 한도 확인 |
| `POST /v1/predict` | 최신 lowres가 기본 결과 |
| `POST /v1/predict?model=adapted` | 기존 개선 head를 대표 결과로 선택 |
| `POST /v1/predict?model=lowres` | 축소 학습 head를 대표 결과로 선택 |
| `POST /v1/predict?model=original` | 원본 CF head를 대표 결과로 선택 |
| `GET /docs` | Swagger UI |
| `GET /openapi.json` | API 스키마 |

`/v1/*`는 `X-API-Key`가 필요하며, 예측 요청은 multipart의 `file` 필드 한 개를 받습니다. 기본 대표 모델은 `lowres`이며 모든 응답에 `original/adapted/lowres` 점수를 함께 반환합니다. 파일 한도는 10MiB/40MP이며 단일 JPEG/PNG/WEBP/TIFF/BMP를 지원합니다. API가 URL을 대신 다운로드하지 않습니다.

확장 개발자: [API 계약](docs/EXTENSION_API.md), [JS 예제](examples/extension_client.js), [OpenAPI](openapi.json).

## 동작과 운영

서버 시작 시 가중치 해시를 검사하고 한 번 로드합니다. EXIF/RGB → 512 bilinear/JPEG95 → Resize440/CenterCrop384 → ImageNet 정규화 → 동결 ViT-S/16 → 세 개의 선형 head 순서입니다. 각 head는 계수 384개 + 편향 1개입니다. 서버는 학습하지 않습니다.

기본 설정은 127.0.0.1:8000/CPU/worker 1개입니다. 추론은 1개씩 수행하며, 진행·대기는 최대 8개, 대기 5초 초과는 429입니다. SHA256 기반 128개 메모리 캐시가 있으며 이미지를 영구 저장하지 않습니다. 업로드 처리 중 임시 spool 파일은 사용될 수 있습니다.

```sh
.venv/bin/python run_server.py --port 8001
.venv/bin/python run_server.py --device auto
.venv/bin/python run_server.py --extension-id aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
```

확장 ID 미지정 시 인증된 Chrome 확장 Origin을 허용하며, 알려진 ID로 제한하는 것을 권장합니다. 일반 웹 Origin은 기본 차단합니다. 각 노트북에서 따로 실행하면 주소는 localhost지만 키는 각각 다릅니다. LAN 공유는 서버 바인딩·허용 Host/Origin 설정과 별도 전송 보안 검토가 필요합니다.

## 학습과 한계

기존 head는 동결 CF 특징에 L2-SP + 후처리 증강을 적용한 4개 fold head의 동일 평균입니다. lowres head는 기존 원본 + 2개 view에 160~300px 축소 2개 view를 추가 학습했습니다. API 1.2.0부터 lowres가 기본이며 이전 head는 비교용으로 명시 선택합니다.

저해상도 추가 후 기존 평가의 160px 정확도는 64.06 → 77.19%였지만 실제 사진 오탐도 1.88 → 15.63%로 증가했습니다. 이미 사용한 사진의 합성 축소 평가로, 새 웹 이미지 성능 보장이 아닙니다. 점수는 보정된 확률이나 진위 인증이 아닙니다. 세부 사항: [저해상도변경](docs/LOWRES_UPDATE.md), [동작원리](docs/HOW_IT_WORKS.md).

## 테스트

```sh
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q tests
```

테스트 이미지는 메모리에서 생성하므로 사용자 사진이 필요 없습니다. 실제 추론 테스트에는 위 공식 백본 다운로드가 필요하며 없으면 건너뜁니다. 원본 프로젝트에서는 API 회귀 테스트 17개, 실제 HTTP, 독립 ZIP 실행을 검증했습니다. 이 저장소의 작은 테스트 집합은 공개용 사본의 회귀 검사이며 탐지 정확도 벤치마크가 아닙니다.

## 이용 조건과 출처

공식 [CF384 모델 카드](https://huggingface.co/OwensLab/commfor-model-384)는 MIT를 명시합니다. 추가 head는 [CommunityForensics-Eval](https://huggingface.co/datasets/OwensLab/CommunityForensics-Eval) 부분집합으로 학습했고 원천 데이터의 CC-BY-NC-SA-4.0 및 개별 조건과 관련됩니다. 연구용으로 취급하며 상업 이용 전 원천 조건을 확인하세요. 저장소에 포함됐다는 이유로 제3자 권리를 새로 부여하지 않습니다. 출처와 SHA256은 `models/provenance.json`에 있습니다.
