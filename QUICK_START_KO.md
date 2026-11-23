# 로컬 실행 설명서: CF384 + Google Lens FastAPI 데모

API1.4.0 / 2026-11-23. **Python 서버를 켜고 브라우저에서 사진 한 장으로 AI 판별과 인터넷 사용처 검색을 확인하는 방법**입니다. 확장 프로그램 없이 사용할 수 있습니다.

**모든 명령은 `run_server.py`와 `requirements.txt`가 있는 폴더 안에서 실행합니다.** 로컬 `cf384_local_api` 또는 GitHub ZIP을 푼 해당 폴더에서 터미널을 여세요. 두 번째 터미널도 같은 폴더에서 엽니다.

이미 설치했다면 **1번을 건너뛰고 2번부터** 진행하세요. 검색 키도 저장했다면 **3번부터** 진행하면 됩니다.

## 1. 처음 한 번만: 설치와 모델 준비

64비트 Python3.11을 준비합니다. GitHub에서 받는다면 [저장소](https://github.com/gims43077/CF384)의 **Code → Download ZIP**을 풀고 `run_server.py`가 보이는 폴더에서 아래를 실행합니다.

### Mac

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python prepare_models.py --download
```

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install torch==2.8.0 torchvision==0.23.0 --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe prepare_models.py --download
```

`Verified:` 또는 `Prepared:`가 나오면 모델이 준비된 것입니다. 추가 학습은 필요하지 않습니다.

## 2. 처음 한 번만: Google Lens 검색 키 저장

Google Lens 검색은 **SerpApi Free 계정**을 통해 연결합니다. [SerpApi](https://serpapi.com/pricing)에서 Free 요금제로 가입하고 API 키를 확인하세요. Google/CF384/TinEye 키가 아닌 **SerpApi API 키**입니다.

Mac:

```sh
.venv/bin/python configure_web_search.py
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe configure_web_search.py
```

`SerpApi Free-plan API key (hidden):`가 나오면 키를 붙여 넣고 **Enter**를 누릅니다. 입력 중 화면에 아무것도 표시되지 않는 것이 정상입니다. `Provider key saved`가 나오면 완료입니다. 키는 `.runtime/serpapi_api_key.txt`에 저장됩니다.

유료 요금제 가입이나 검색 크레딧 구매는 필요하지 않습니다. 서버는 무료 요금제/잔여 한도를 확인하지 못하면 검색을 중단하며 유료 서비스로 전환하지 않습니다.

## 3. 터미널 1: 통합 FastAPI 서버 실행

Mac:

```sh
.venv/bin/python run_server.py --enable-web-search
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe run_server.py --enable-web-search
```

**`Application startup complete`가 나오면 준비 완료입니다. 이 터미널은 켜 두세요.** 이미 서버가 실행 중이면 먼저 해당 터미널에서Ctrl+C로 종료한 뒤 다시 실행합니다. 키를 새로 저장하거나 바꿨을 때도 서버를 재시작합니다.

## 4. 새 터미널 2: 데모에 입력할 로컬 API 키 확인

같은 서버 폴더에서 새 터미널을 열고 실행합니다.

Mac:

```sh
.venv/bin/python client.py --show-key
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe client.py --show-key
```

출력된 문자열을 복사합니다. 이것은 **CF384 로컬 서버 접속용 키**이며 2번의 SerpApi 키와 다릅니다.

| 키 | 어디에 입력하나요? |
|---|---|
|SerpApi API 키|2번의 터미널 숨김 입력. 외부 검색용|
|CF384 로컬 API 키|아래 브라우저 데모의 API 키 칸. 내 서버 접속용|

## 5. 브라우저에서 사진 한 장으로 시연

1. **http://127.0.0.1:8000/demo** 를 엽니다.
2. **API 키** 칸에 4번에서 확인한 **CF384 로컬 키**를 붙여 넣습니다. `Bearer`나 `X-API-Key:`를 붙이지 않습니다.
3. 사진 파일을 선택합니다.
4. 대표 결과는 기본값 **L2-SP + 증강 + 160~300px 학습**으로 둡니다.
5. **인터넷 사용처도 검색**을 체크합니다.
6. **이미지 분석**을 누릅니다.

화면에서 **AI 생성 판별 점수**와 **인터넷 일치 후보 링크/검색 상태**를 함께 확인합니다. CF384 점수는 진위 확정 확률이 아니며, 검색 결과가 없다고 인터넷 미사용을 확정할 수는 없습니다.

| 주소 | 용도 |
|---|---|
|http://127.0.0.1:8000/demo|사진 업로드와 결과 확인용 간단 화면|
|http://127.0.0.1:8000/health|서버 준비 상태 확인|
|http://127.0.0.1:8000/docs|FastAPI의 상세 요청 테스트 화면|

## 6. 다음부터 실행·종료·업데이트

설치와 키 저장을 반복할 필요 없이 **3번 서버 실행 →4번 로컬 키 확인 →5번 데모 접속**만 하면 됩니다. 종료는 서버 터미널에서 **Ctrl+C**입니다.

Git으로 받았다면 서버를 종료하고 같은 폴더에서 아래를 실행한 뒤 3번으로 다시 켭니다.

```sh
git pull --ff-only
```

ZIP으로 받았다면 최신 파일로 업데이트하되 `.venv`, `.runtime`, 다운로드한 `models/cf384.safetensors`는 유지하세요. 업데이트 후 브라우저도 새로고침합니다.

## 오류가 날 때

| 증상 | 확인 방법 |
|---|---|
|브라우저 연결 실패|서버 터미널이 켜져 있는지, `/health`가 열리는지 확인|
|`invalid_api_key`|SerpApi 키가 아닌 4번의 로컬 키를 입력했는지 확인|
|웹 검색 `disabled`|서버를 `--enable-web-search`로 실행했는지 확인|
|웹 검색 `not_configured`|2번으로 SerpApi 키 저장 후 서버 재시작|
|웹 검색 `blocked`|SerpApi Free 요금제와 잔여 한도 확인. 유료 결제로 전환하지 않음|
|웹 검색 `error`|외부 인증/통신 오류. CF384 점수와 별도로 검색 실패 상태 확인|
|이미 포트를 사용 중이라는 오류|기존 서버를Ctrl+C로 종료한 뒤 3번 재실행|

**Google Lens 없이 CF384만 확인하려면** 서버를 `run_server.py`로 실행하고 데모에서 인터넷 검색 체크를 끄면 됩니다. 이 경우 SerpApi 키 없이 사용할 수 있습니다.

실제 검색 품질·탐지율은 SerpApi 키 미설정으로 아직 미측정입니다. 로컬 API와 모의 검색 연결은 검증했으며 Windows 신규 설치는 이 Mac에서 직접 검증하지 않았습니다. 검색 제한·데이터 전송 등의 상세 내용은 [무료 검색 설정](docs/WEB_USAGE_SEARCH_KO.md)을 참고하세요.
