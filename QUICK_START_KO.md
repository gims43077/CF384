# 간단 사용법

모든명령은저장소폴더안에서실행합니다. 사진·API키·백본가중치는저장소에포함하지않습니다.

## Mac

최초설치와공식백본다운로드:

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python prepare_models.py --download
```

터미널1:

```sh
.venv/bin/python run_server.py
```

같은폴더의새터미널2:

```sh
.venv/bin/python client.py --show-key
```

http://127.0.0.1:8000/demo 접속→키입력→본인사진선택→분석. 작은사진은대표결과에서160~300px후보선택.

## Windows PowerShell

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install torch==2.8.0 torchvision==0.23.0 --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe prepare_models.py --download
.\.venv\Scripts\python.exe run_server.py
```

같은폴더의새터미널2:

```powershell
.\.venv\Scripts\python.exe client.py --show-key
```

종료는서버터미널Ctrl+C. 다음부터는설치/다운로드없이서버실행만합니다. 실제검증환경은macOS/CPU이며Windows신규설치는직접실행하지않았습니다.
