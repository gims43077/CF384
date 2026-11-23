# 무료 인터넷 이미지 사용처 검색 — API 1.4.0

**추천·적용: SerpApi Google Lens 무료 요금제.** 2026-11-23 공식 요금표 기준 월 250회·시간당 50회입니다. Google 공식 API가 아닌 제3자 서비스입니다. CF384 가중치·기본 lowres 모델·임계값 0.5는 유지하고 인터넷 검색 연결만 교체했습니다. **TinEye 호출과 유료 서비스 fallback은 제거했습니다.**

## 한 번만 설정

1. [SerpApi](https://serpapi.com/)에서 **Free 요금제**로 가입하고 [API 키](https://serpapi.com/manage-api-key)를 확인합니다. 유료 요금제나 추가 크레딧은 구매할 필요가 없습니다.
2. `run_server.py`가 있는 폴더에서 아래를 실행하고 SerpApi 키를 숨김 입력합니다.

```sh
.venv/bin/python configure_web_search.py
```

Windows:

```powershell
.\.venv\Scripts\python.exe configure_web_search.py
```

키는 `.runtime/serpapi_api_key.txt`에 저장하며 Git에서 제외합니다. 환경변수 `SERPAPI_API_KEY`가 있으면 파일보다 우선합니다. 기존 TinEye 키는 읽지 않습니다. SerpApi 키는 서버에만 보관하고 브라우저/확장에는 기존 **로컬 CF384 API 키**를 입력합니다.

## 서버 실행과 사용

```sh
.venv/bin/python run_server.py --enable-web-search
```

Windows:

```powershell
.\.venv\Scripts\python.exe run_server.py --enable-web-search
```

`http://127.0.0.1:8000/demo`에서 **인터넷 사용처도 검색**을 선택하세요. CF384 AI 판별과 사용처 후보 링크를 함께 받습니다. 서버 옵션을 생략하면 로컬 판별만 수행합니다.

CLI:

```sh
.venv/bin/python client.py my_photo.jpg --web-search
```

확장 프로그램은 기존 파일 업로드 요청에 옵션만 추가합니다.

```http
POST /v1/predict?model=lowres&web_search=true
X-API-Key: <로컬 CF384 API 키>
```

```js
const result = await predictBlob(blob, {apiKey: localApiKey, webSearch: true});
console.log(result.result);     // 기존 CF384 점수
console.log(result.web_usage);  // 인터넷 사용처 검색 상태와 후보
```

## 무료 요금제 확인과 호출 제한

각 새 검색은 **무료 Account API 확인 → 이미지 업로드 → Lens exact_matches 검색** 순서입니다. 별도 이미지 공개 URL이나 유료 이미지 호스팅은 필요 없습니다.

- 무료 요금제, 월 요금 0, 잔여 무료 검색 수, 추가 유료 크레딧 0을 확인한 경우에만 업로드/검색합니다. 유료 요금제·한도 소진·확인 불가 시 `blocked`로 중단합니다. 계정 확인 API는 공식 문서상 무료이며 검색 할당량에 포함되지 않습니다.
- 요금제를 바꾸거나 크레딧을 구매하는 코드는 없습니다. TinEye 등 유료 제공자로 전환하지 않습니다.
- 기본 실행당 검색 파이프라인 시도 20회, 분당 5회·시간당 40회, 동시 외부 파이프라인 1개입니다. `--web-search-max-calls`로 세션 제한을 정할 수 있습니다. 제공자 자체의 계정 한도도 적용됩니다.
- 같은 파일의 성공 결과/후보 없음 응답은 최대 128개·1시간 메모리 캐시로 재사용합니다. 자동 재시도·다음 페이지 검색은 하지 않습니다.
- 서버 재시작 시 로컬 카운터는 초기화되지만, 매 검색마다 제공자 계정의 무료 잔여 한도를 다시 확인합니다. 계정 설정/다른 앱의 사용/제공자 정책은 운영자가 함께 관리해야 합니다.

## 반환값 읽는 방법

- `web_usage.provider`: `serpapi_google_lens`.
- `web_usage.matches[].backlinks[].page_url`: 제공자가 반환한 사용처 후보 페이지.
- `match_kind`: `provider_exact_match`. 픽셀 동일성이나 실제 페이지의 현재 이미지를 서버가 별도로 검증했다는 뜻은 아닙니다.
- `title`, `thumbnail_url`: 제공자의 제목/미리보기 주소. 서버가 그 주소를 다시 다운로드하지 않습니다.
- `image_url`: 제공자가 원본 이미지 주소를 준 경우만 반환합니다. 썸네일 주소를 원본 주소로 바꿔 적지 않습니다.
- `provider_score`: 근거 없는 유사도 수치를 만들지 않고 `null`입니다. CF384 AI 점수와 섞지 않습니다.
- `crawl_date`: 신뢰할 수 있는 수집일을 제공받지 않아 `null`입니다. 게시일·최초 사용일을 추측하지 않습니다.

| status | 의미 |
| --- | --- |
| `not_requested` | 인터넷 검색 요청 안 함(기본) |
| `disabled` | 서버 외부 검색 옵션 꺼짐 |
| `not_configured` | SerpApi 키 미설정 |
| `blocked` | 무료 요금제/한도 조건 불일치 또는 확인 불가 |
| `matches_found` | 제공자가 동일 이미지 일치 후보를 반환 |
| `no_matches` | 유효한 빈 exact_matches 응답 |
| `error` | 인증·통신·제공자 응답 오류 |
| `rate_limited` | 서버 호출/대기 제한 |

검색 실패/차단이어도 유효한 이미지의 CF384 결과는 HTTP 200으로 유지합니다. **반드시 `web_usage.status`를 확인하세요.** `GET /v1/web-search/status`는 키를 노출하지 않고 로컬 설정/한도를 보여줍니다. `ready=true`는 로컬 설정이 준비됐다는 뜻이며 계정/키를 외부에서 검증한 결과는 아닙니다.

## 전송·정확도·검증 범위

이미지는 EXIF 방향 보정 후 전체 종횡비를 유지해 최대 1600px/JPEG로 만들며 EXIF/GPS를 제거합니다. Image API의 500KB 한도에 맞춰 필요한 경우 JPEG 품질·해상도를 더 낮춰 480KB 이하로 보냅니다. CF384의 중앙 크롭 결과는 보내지 않습니다.

로컬 서버는 사진을 영구 저장하지 않습니다. SerpApi와 Google로 전달되는 데이터에는 각 서비스의 정책이 적용됩니다. 공식 문서는 업로드 image_id가 10분 후 만료된다고 설명하지만, 이것을 모든 외부 로그/검색 기록의 삭제 보장으로 해석하지 않습니다. 무료 요금제에서 Enterprise 전용 ZeroTrace가 적용된다고 주장하지 않습니다.

**인터넷 전체의 미사용/도용/원저작자를 확정하는 기능은 아닙니다.** 색인 누락·변형·비공개 페이지가 있고, exact_matches에도 확인이 필요한 후보가 있을 수 있습니다. 검색 결과가 없다고 미사용을 확정하지 않습니다.

현재 계정 키 없이 모의 응답과 로컬 API로 기능을 검증했습니다. 실제 무료 계정의 검색 품질·탐지율은 아직 측정하지 않았습니다. 유료 평가·가입·구매는 실행하지 않았습니다. 이전 TinEye 평가는 계속 보류합니다.

공식 문서: [무료 요금제](https://serpapi.com/pricing), [Account API](https://serpapi.com/account-api), [파일 업로드](https://serpapi.com/google-lens-upload-an-image), [Image API](https://serpapi.com/image-api), [동일 이미지 검색](https://serpapi.com/google-lens-exact-matches-api).

테스트: `python -m pytest -q tests`. 검색 응답은 모의 데이터이며 실제 인터넷 검색 성능 수치가 아닙니다.
