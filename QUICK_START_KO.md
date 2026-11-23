# 간단 사용법: GitHub에서 받아 최신 모델 실행하기

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
4. 사진을 선택하고 **로컬 서버로 분석**을 누릅니다.

**API1.2.0부터 최신 `lowres` 모델이 기본입니다.** 별도 선택 없이 사용하며 이전 모델과 비교할 때만 `adapted`를 선택합니다. 입력 크기에 따라 모델을 자동 전환하지는 않습니다.

확장 프로그램/API로 연결할 때도 다음 주소를 사용합니다. 파일 전송과 키 설정은 [API 설명서](docs/EXTENSION_API.md)를 참고하세요.

```http
POST /v1/predict
```

## 5. 다음 실행과 업데이트

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


## 인터넷에서 같은 이미지의 사용처 찾기 (선택)

기존 AI 판별은 그대로 사용할 수 있습니다. 인터넷 검색까지 필요하면 [인터넷 사용처 검색 설정](docs/WEB_USAGE_SEARCH_KO.md)을 따라 SerpApi Free 요금제 API 키를 설정하고 `run_server.py --enable-web-search`로 실행한 뒤 데모에서 검색 옵션을 선택하세요. 무료 요금제 잔여 한도 안에서 사용하며 미설정/유료 요금제에서는 실제 검색하지 않습니다. 제공자의 검색 색인 범위에서만 찾습니다.
