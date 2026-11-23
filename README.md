# CF384 Local Image Detection API

**2026-11-23 / API1.4.0:** 인터넷 사용처 검색을 **SerpApi Google Lens 무료 요금제 전용**으로 교체했습니다. 무료 요금제와 잔여 한도를 확인하지 못하면 검색을 차단하며 TinEye/유료 fallback은 사용하지 않습니다. CF384 가중치와 임계값은 그대로입니다. [무료 검색 설정](docs/WEB_USAGE_SEARCH_KO.md). 실제 계정 키가 없어 검색 품질 평가는 아직 미실행입니다.

CF384 기반의 로컬 정지 이미지 탐지 API입니다. 원본 분류기, L2-SP+증강 분류기, 160~300px 축소 학습 분류기의 점수를 한 번의 백본 추론으로 반환합니다. Chrome 확장 프로그램은 포함하지 않으며, 연결 예제와 API 명세를 제공합니다.

**이 저장소에는 실제 API 키, 가상환경, 사용자 사진, 평가 원본 데이터, 실행 로그, 대형 백본 가중치를 포함하지 않습니다.** 작은 학습 head 두 개는 `models/`에 포함합니다. 공식 CF384 백본은 아래 명령으로 다운로드합니다. 인증 기능과 `X-API-Key` 헤더 이름은 코드에 유지합니다.

## 실행

모든 명령은 저장소 폴더 안에서 실행합니다. 64비트 Python3.11을 권장합니다. GPU는 필수가 아닙니다.

### macOS

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python prepare_models.py --download
.venv/bin/python run_server.py
```

서버 터미널은 켜 두고, 새 터미널을 같은 폴더에서 엽니다.

```sh
.venv/bin/python client.py --show-key
```

http://127.0.0.1:8000/demo 에 접속해 키를 입력하고 사진을 선택합니다. 대표 결과는 **L2-SP + 증강 + 160~300px 학습 (기본)**이 자동 선택됩니다. 종료는 서버 터미널에서Ctrl+C입니다.

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install torch==2.8.0 torchvision==0.23.0 --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe prepare_models.py --download
.\.venv\Scripts\python.exe run_server.py
```

새 터미널에서:

```powershell
.\.venv\Scripts\python.exe client.py --show-key
```

Linux는 동일한가상환경구성을사용하며, CPU전용PyTorch는Windows설치예시의공식CPU wheel경로를사용할수있습니다. 실제검증은macOS/CPU에서수행했고Windows/Linux의새설치는직접검증하지않았습니다.

처음키는각설치폴더의`.runtime/api_key.txt`에자동생성됩니다. 이폴더는Git에서제외됩니다. `CF384_API_KEY`환경변수를설정하면파일보다우선합니다. 키문자열만입력하고`Bearer`나`X-API-Key:`를앞에붙이지마세요. 서버시작후모델이준비돼야분석할수있습니다.

## 이번 업데이트 (2026-11-19 / API1.2.0)

최신 `lowres`를 API·Python·JS·데모 기본값으로 적용했습니다. 가중치와 임계값0.5는 그대로입니다. 기존 확장이 `model=adapted`를 명시한다면 `lowres`로 바꾸거나 query를 생략해야 합니다.

실제 웹 썸네일64장(긴 변160~280px)에서 기존 head85.94% → 최신 head90.63%, 실사 오탐0/32 →2/32였습니다. 추가JPEG85에서는 최신 head81.25%입니다. Google 썸네일은 아니며 작은 표본으로 웹 전체 성능을 보장하지 않습니다. [지금까지 작업 요약](docs/WORK_SUMMARY_KO.md) · [측정 CSV](docs/evaluation/web_thumbnail_metrics.csv).

## API

| URL | 역할 |
|---|---|
|`GET /health`|준비상태|
|`GET /v1/model`|모델설명·SHA256·장치|
|`GET /v1/web-search/status`|외부 검색 설정·호출 한도 확인|
|`POST /v1/predict`|최신 lowres가 기본 결과|
|`POST /v1/predict?model=adapted`|기존개선head를대표결과로선택|
|`POST /v1/predict?model=lowres`|축소학습head를대표결과로선택|
|`POST /v1/predict?model=original`|원본CFhead를대표결과로선택|
|`GET /docs`|Swagger UI|
|`GET /openapi.json`|API스키마|

`/v1/*`는`X-API-Key`가필요하며, 예측요청은multipart의`file`필드한개를받습니다. 기본대표모델은`lowres`, 모든응답에`original/adapted/lowres`점수를함께반환합니다. 파일10MiB/40MP한도, 단일JPEG/PNG/WEBP/TIFF/BMP지원. API가URL을대신다운로드하지않습니다.

확장개발자: [API계약](docs/EXTENSION_API.md), [JS예제](examples/extension_client.js), [OpenAPI](openapi.json).

## 동작과 운영

서버시작시가중치해시를검사하고한번로드합니다. EXIF/RGB →512bilinear/JPEG95 → Resize440/CenterCrop384 → ImageNet정규화 → 동결ViT-S/16 → 세개선형head순서입니다. 각head는384계수+편향1개입니다. 서버는학습하지않습니다.

기본127.0.0.1:8000/CPU/worker1개입니다. 추론1개씩, 진행·대기최대8개, 대기5초초과는429입니다. SHA256기반128개메모리캐시가있으며이미지를영구저장하지않습니다. 업로드처리중임시spool파일은사용될수있습니다.

```sh
.venv/bin/python run_server.py --port 8001
.venv/bin/python run_server.py --device auto
.venv/bin/python run_server.py --extension-id aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
```

확장ID미지정시인증된Chrome확장Origin을허용하며, 알려진ID로제한하는것을권장합니다. 일반웹Origin은기본차단합니다. 각노트북에서따로실행하면주소는localhost지만키는각각다릅니다. LAN공유는서버바인딩·허용Host/Origin설정과별도전송보안검토가필요합니다.

## 학습과 한계

기존head는동결CF특징에L2-SP+후처리증강을적용한4fold head의동일평균입니다. lowres head는기존원본+2view에160~300px축소2view를추가학습했습니다. API1.2.0부터 lowres가 기본이며 이전 head는 비교용으로 명시 선택합니다.

저해상도추가후기존평가160px정확도는64.06→77.19%였지만실제사진오탐도1.88→15.63%로증가했습니다. 이미사용한사진의합성축소평가로,새웹이미지성능보장이아닙니다. 점수는보정된확률/진위인증이아닙니다. 세부사항: [저해상도변경](docs/LOWRES_UPDATE.md), [동작원리](docs/HOW_IT_WORKS.md).

## 테스트

```sh
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q tests
```

테스트이미지는메모리에서생성하므로사용자사진이필요없습니다. 실제추론테스트에는위공식백본다운로드가필요하며없으면건너뜁니다. 원본프로젝트에서는API회귀테스트17개,실제HTTP,독립ZIP실행을검증했습니다. 이저장소의작은테스트집합은공개용사본의회귀검사이며탐지정확도벤치마크가아닙니다.

## 이용 조건과 출처

공식[CF384모델카드](https://huggingface.co/OwensLab/commfor-model-384)는MIT를명시합니다. 추가head는[CommunityForensics-Eval](https://huggingface.co/datasets/OwensLab/CommunityForensics-Eval)부분집합으로학습했고원천데이터의CC-BY-NC-SA-4.0및개별조건과관련됩니다. 연구용으로취급하며상업이용전원천조건을확인하세요. 저장소에포함됐다는이유로제3자권리를새로부여하지않습니다. 출처와SHA256은`models/provenance.json`에있습니다.
