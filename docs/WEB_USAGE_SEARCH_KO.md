# 인터넷 이미지 사용처 검색 — API1.3.0

CF384의 AI 생성 판별과 **인터넷 역이미지 검색**을 하나의 요청으로 받습니다. 인터넷 검색은 TinEye의 검색 색인을 사용하며 CF384에 새 분류기를 학습하는 기능이 아닙니다.

**구현/검증 상태:** 로컬 CF384 추론과 검색 연결 코드를 구현하고 모의 제공자 응답으로 테스트했습니다. 실제 TinEye 계정/검색 키/크레딧을 사용한 검색은 실행하지 않았습니다. 실제 인터넷 검색 품질·탐지율은 아직 측정하지 않았습니다. 유료 가입·결제도 하지 않았습니다.

## 1. 기존 검색 키 설정

TinEye API는 유료 검색 서비스입니다. 사용할 계정의 키와 크레딧이 있어야 실제 검색할 수 있습니다. 무료 웹사이트 검색과 API 이용은 다릅니다. 이 프로그램은 가입/구매를 자동으로 하지 않습니다.

저장소 폴더 안에서, **이미 보유한 키**를 숨김 입력으로 저장합니다.

```sh
.venv/bin/python configure_web_search.py
```

Windows에서는 `.\.venv\Scripts\python.exe configure_web_search.py`입니다.

- 키는 `.runtime/tineye_api_key.txt`에 저장됩니다. Git에서 제외되며 macOS/Linux 권한은600입니다.
- `TINEYE_API_KEY` 환경변수가 있으면 이 파일보다 우선합니다.
- TinEye 키는 서버 전용입니다. 확장 프로그램/데모에는 기존 **로컬 CF384 API 키**만 입력합니다. 두 키를 혼동하지 마세요.
- 설정 명령은 외부 호출/검색/구매를 하지 않습니다.

## 2. 검색을 허용해 서버 실행

```sh
.venv/bin/python run_server.py --enable-web-search --web-search-max-calls 20
```

Windows:

```powershell
.\.venv\Scripts\python.exe run_server.py --enable-web-search --web-search-max-calls 20
```

`--enable-web-search`를 생략하면 기존 로컬 판별만 수행합니다. 대신 `CF384_WEB_SEARCH_ENABLED=1` 환경변수로 허용할 수도 있습니다. 서버를 켜는 것만으로 검색하지는 않습니다.

기본 제한은 프로세스 실행당 제공자 호출 시도20회, 분당5회, 실제 외부 호출 동시1개입니다. 같은 파일의 성공/검색 결과 없음 응답은 최대128개·1시간 메모리 캐시로 재사용합니다. 키 오류/통신 실패는 성공으로 캐시하지 않고60초 대기합니다. 서버 재시작 시 호출 카운터와 캐시는 초기화되므로 월간/계정 전체 예산 제한은 아닙니다. 오류·타임아웃도 시도 횟수에 포함하며 자동 재시도/페이지 추가 검색은 하지 않습니다. 제공자가 오류에도 크레딧을 차감할 수 있습니다.

## 3. 한 장으로 두 결과 받기

브라우저 `http://127.0.0.1:8000/demo`에서 로컬 API 키·이미지를 입력하고 **인터넷 사용처도 검색**을 선택합니다. 사용처 URL을 클릭할 수 있는 목록과 CF384 점수를 함께 표시합니다.

CLI:

```sh
.venv/bin/python client.py my_photo.jpg --web-search
```

확장 프로그램은 같은 multipart 업로드에 query만 추가합니다.

```http
POST /v1/predict?model=lowres&web_search=true
X-API-Key: <로컬 CF384 API 키>
```

JS 예제:

```js
const result = await predictBlob(blob, {apiKey: localApiKey, webSearch: true});
console.log(result.result);     // CF384 AI 생성 판별
console.log(result.web_usage);  // 인터넷 일치 후보와 사용처
```

별도 Python 라이브러리 설치는 추가로 필요하지 않습니다. HTTP 연동은 표준 라이브러리를 사용합니다.

## 응답 구조

아래 URL/숫자는 **실제 검색 결과가 아닌 형식 예시**입니다.

```json
{
  "web_usage": {
    "status": "matches_found",
    "provider": "tineye",
    "searched_at": "2026-11-23T00:00:00+00:00",
    "cached": false,
    "returned_matches": 1,
    "provider_matches_in_page": 1,
    "matches": [{
      "domain": "example.org",
      "image_url": "https://example.org/copy.jpg",
      "provider_score": 96.5,
      "backlinks": [{
        "page_url": "https://example.org/article",
        "image_url": "https://example.org/copy.jpg",
        "crawl_date": "2026-01-01"
      }]
    }]
  }
}
```

- `page_url`: 제공자가 보고한 사용처 페이지. 서버가 그 페이지를 다시 열어 현재 이미지를 확인한 것은 아닙니다.
- `image_url`: 제공자가 보고한 일치 이미지 주소.
- `provider_score`: 제공자의 이미지 일치 점수. **CF384 AI 점수나 진위 확률이 아닙니다.**
- `crawl_date`: 검색 서비스의 수집일 원문. **게시일/최초 사용일/소유권 증거가 아닙니다.**
- 최대10개 이미지 일치 후보, 후보당 최대30개 페이지 링크를 반환합니다. `provider_matches_in_page`는 이번 응답 페이지 안의 후보 수이며 인터넷 전체 사용 횟수가 아닙니다.

| status | 의미 |
|---|---|
|`not_requested`|요청에서 검색하지 않음(기본)|
|`disabled`|서버에서 외부 검색을 허용하지 않음|
|`not_configured`|검색은 허용했지만 키가 없음|
|`matches_found`|제공자 색인에서 일치 후보를 받음|
|`no_matches`|검색은 성공했으나 색인에서 후보가 없음|
|`error`|제공자 인증/통신/응답 오류. 검색 실패이며 미사용 판정이 아님|
|`rate_limited`|서버 호출/대기 제한에 걸려 검색하지 않음|

제공자 실패/미설정이어도 유효한 이미지의 CF384 결과는 HTTP200으로 반환합니다. **검색 상태는 반드시 `web_usage.status`로 확인**해야 합니다. 로컬 인증 실패·이미지 오류는 기존 HTTP4xx를 유지하며 외부 검색하지 않습니다.

인증된 `GET /v1/web-search/status`로 키 내용 없이 설정 여부·서버 호출 횟수·제한을 확인할 수 있습니다. `ready=true`는 로컬 설정이 갖춰졌다는 뜻이며, 실제 키 유효성/크레딧 잔량을 외부에서 확인했다는 뜻은 아닙니다.

## 데이터 전송과 한계

서버 허용 + 키 설정 + 요청의 `web_search=true`가 모두 있을 때만 외부 검색합니다. 전체 이미지를 EXIF 방향 보정 후 종횡비를 유지해 최대1600px/JPEG90으로 변환하고 메타데이터를 제외해 TinEye HTTPS 고정 주소로 보냅니다. CF384의 중앙 크롭 이미지는 보내지 않습니다. 원본 이미지/검색 결과를 디스크나 DB에 보존하지 않으며, 메모리 캐시에는 URL·점수·시간 등 검색 결과만 저장합니다. 외부 서비스의 데이터 처리에는 해당 서비스 정책이 적용됩니다.

**인터넷 전체를 빠짐없이 검색하는 기능은 아닙니다.** 비공개·로그인 페이지·미수집 사이트·삭제된 페이지·심한 변형 등은 누락될 수 있습니다. 일치 후보가 없다고 미사용을 확정하거나, 일치했다고 도용·AI 생성·원저작자를 확정하지 않습니다. CF384 판별과 재사용 후보는 독립된 결과입니다.

공식 출처: [TinEye API Python 라이브러리](https://github.com/TinEye/pytineye), [요청·응답 정의](https://github.com/TinEye/pytineye/blob/main/pytineye/api.py), [실제 검색에 계정과 크레딧이 필요하다는 안내](https://help.tineye.com/article/182-using-the-tineye-api-to-determine-if-an-image-is-a-stock-photo).

테스트는 `python -m pytest -q tests`로 실행합니다. 검색 테스트의 URL은 `example.org` 모의 데이터이며 실제 외부 서비스를 호출하지 않습니다.
