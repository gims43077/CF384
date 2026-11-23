# 간단 사용법: CF384 서버와 Chrome 확장 연결하기

API1.4.0 / 2026-11-23. **모델은 Python 서버에서 실행하고, 확장은 이미지를 보내 결과를 표시합니다.** 이 저장소에는 서버와 연결 예제가 있으며 완성된 확장 프로그램은 포함하지 않습니다.

```text
Chrome 확장 → 내 컴퓨터의 Python 서버 → CF384 AI 판별
                                    → 인터넷 사용처 검색(선택)
Chrome 확장 ← 판별 점수·검색 상태·사용처 후보 링크
```

## 1. 준비

1. **64비트 Python 3.11**을 설치합니다.
2. 이 저장소의 **Code → Download ZIP**으로 내려받고 압축을 풉니다. Git을 쓰면 clone해도 됩니다.
3. **`run_server.py`와 `requirements.txt`가 있는 폴더 안에서 터미널을 엽니다.** 아래 명령은 모두 이 폴더 안에서 실행합니다. 새 터미널도 같은 폴더에서 여세요.

업데이트된 작은 분류기 가중치는 이미 포함되어 있어 **다시 학습할 필요가 없습니다.** 대형 CF384 백본만 아래 명령으로 공식 출처에서 받습니다. 실제 API 키는 각 컴퓨터에서 생성됩니다.

## 2. Mac

### 처음 한 번: 설치 + 가중치 다운로드

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python prepare_models.py --download
```

### 터미널 1: 서버 실행

```sh
.venv/bin/python run_server.py
```

`Application startup complete`가 나오면 준비 완료입니다. 이 터미널은 켜 둡니다.

### 새 터미널 2: API 키 확인

```sh
.venv/bin/python client.py --show-key
```

## 3. Windows PowerShell

### 처음 한 번: 설치 + 가중치 다운로드

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install torch==2.8.0 torchvision==0.23.0 --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe prepare_models.py --download
```

### 터미널 1: 서버 실행

```powershell
.\.venv\Scripts\python.exe run_server.py
```

`Application startup complete`가 나오면 준비 완료입니다. 이 터미널은 켜 둡니다.

### 새 터미널 2: API 키 확인

```powershell
.\.venv\Scripts\python.exe client.py --show-key
```

## 4. 브라우저에서 최신 저해상도 모델 사용

1. **http://127.0.0.1:8000/demo** 에 접속합니다.
2. 출력된 키 문자열만 **API 키** 칸에 붙여 넣습니다. `Bearer`나 `X-API-Key:`는 붙이지 않습니다.
3. **대표 결과 → `L2-SP + 증강 + 160~300px 학습 (기본)`**이 자동 선택되어 있는지 확인합니다.
4. 사진을 선택하고 **이미지 분석**을 누릅니다. 먼저 인터넷 검색을 선택하지 않고 CF384가 작동하는지 확인합니다.

**API1.2.0부터 최신 `lowres` 모델이 기본입니다.** 별도 선택 없이 사용하며 이전 모델과 비교할 때만 `adapted`를 선택합니다. 입력 크기에 따라 모델을 자동 전환하지는 않습니다.

확장 프로그램/API로 연결할 때도 다음 주소를 사용합니다. 파일 전송과 키 설정은 [API 설명서](docs/EXTENSION_API.md)를 참고하세요.

```http
POST /v1/predict
```

## 5. Chrome 확장 프로그램에 연결

1. 확장 개발자가 제공한 확장 프로그램을 설치합니다. 이 저장소만 다운로드해도 Chrome에 확장이 자동 설치되는 것은 아닙니다.
2. Python 서버를 켜 둡니다. 브라우저에서 `http://127.0.0.1:8000/health`가 열리는지 확인합니다.
3. 확장 설정 화면에 아래 두 값을 입력합니다. 설정 화면을 만드는 일은 확장 개발자 담당입니다.

| 확장 설정 | 입력값 |
|---|---|
|서버 주소|`http://127.0.0.1:8000`|
|로컬 API 키|같은 서버 폴더에서 `client.py --show-key`로 확인한 값|

4. 이미지가 있는 페이지에서 확장 프로그램의 분석 기능을 사용합니다. CF384 판별은 SerpApi 키 없이 사용할 수 있습니다.
5. 인터넷 사용처 검색은 아래 설정 후 사용자가 선택한 이미지에만 실행하는 구성을 권장합니다. 화면의 모든 이미지에 자동 검색하면 무료 한도가 빨리 소진됩니다.

**서버를 종료하면 확장의 분석도 중단됩니다.** 다른 사람이 사용할 때도 각자 컴퓨터에 서버를 설치·실행하고 각자의 로컬 API 키를 설정합니다. 개발자의 `localhost` 서버가 다른 사람 컴퓨터에서도 공유되는 방식은 아닙니다.

확장 개발자에게는 [이 저장소](https://github.com/gims43077/CF384), [연동 설명서](docs/EXTENSION_API.md), [JS 연결 함수](examples/extension_client.js)를 전달하세요.

## 6. 인터넷 사용처 검색도 연결하기 (선택)

두 키의 역할이 다릅니다.

| 키 | 저장/입력 위치 | 역할 |
|---|---|---|
|CF384 로컬 API 키|확장 설정 또는 `/demo`|내 Python 서버 접속|
|SerpApi Free 요금제 API 키|Python 서버에만 저장|외부 인터넷 검색|

**SerpApi 키를 확장 프로그램에 넣지 않습니다.** [SerpApi Free 계정](https://serpapi.com/pricing)의 키를 준비한 뒤 같은 서버 폴더에서 실행합니다. 이 과정은 요금제 가입·구매를 자동으로 하지 않습니다.

Mac:

```sh
.venv/bin/python configure_web_search.py
.venv/bin/python run_server.py --enable-web-search
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe configure_web_search.py
.\.venv\Scripts\python.exe run_server.py --enable-web-search
```

기존 서버가 실행 중이면 먼저Ctrl+C로 종료하세요. 설정 프로그램에 SerpApi 키를 숨김 입력한 뒤 새 서버를 실행합니다. 데모에서는 **인터넷 사용처도 검색**을 선택하고, 확장에서는 개발자가 제공한 사용처 검색 버튼을 사용합니다.

무료 요금제/잔여 한도를 확인하지 못하면 검색을 중단하며 유료 서비스로 전환하지 않습니다. 이때 CF384 결과는 유지됩니다. 일치 후보가 없다고 인터넷 미사용을 확정할 수는 없습니다. [무료 검색 설정 상세](docs/WEB_USAGE_SEARCH_KO.md).

## 7. 다음 실행과 업데이트

- 다음부터는 설치·다운로드 없이 위 **서버 실행 명령**만 사용합니다. 종료는 서버 터미널에서 **Ctrl+C**입니다.
- Git으로 받은 사람은 서버를 종료하고 같은 폴더에서 아래 명령을 실행한 뒤 서버를 다시 켭니다.

```sh
git pull --ff-only
```

- ZIP으로 받은 사람은 최신 ZIP의 파일을 기존 폴더에 덮어쓰되 **`.venv`, `.runtime`, 다운로드한 백본 파일은 유지**합니다.
- 업데이트 후에는 **서버 재시작 + 브라우저 새로고침**이 필요합니다. 최신 모델이 기본 선택되어 있는지 확인하세요. 기존 확장이 `model=adapted`를 명시한다면 `lowres`로 바꾸거나 query를 생략해야 합니다.
- `invalid_api_key`가 나오면 **지금 실행 중인 서버 폴더**에서 키 확인 명령을 다시 실행합니다.

각 노트북에서 서버를 따로 실행하며 API 키도 각각 다릅니다. 서버가 꺼져 있으면 분석되지 않습니다. 결과는 모델의 추정이며 이미지 진위를 확정하지 않습니다.

직접 검증한 환경은 macOS/CPU입니다. Windows 신규 설치는 이 컴퓨터에서 직접 검증하지 않았습니다.

서버·연결 함수·모의 검색 응답은 검증했지만, 실제 Chrome 확장 설치부터 화면 표시까지의 통합 검증은 확장 구현 후 별도로 해야 합니다. 실제 SerpApi 키를 사용한 검색 품질·탐지율은 아직 측정하지 않았습니다.
