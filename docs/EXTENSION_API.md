# 확장 프로그램 개발자용 API 계약

API v1.2.0 / 2026-11-19. 서버 코드는 완성되어 있으며, Chrome 확장 자체는 이 패키지의 구현 범위가 아니다.

저해상도추가: `model=lowres`로160~300px 축소 학습을 더한별도head를선택한다. 기본 대표 모델은 `lowres`로 변경했다. `model` 생략 시 최신 head를 사용한다. 명시적으로 `model=adapted`를 보내는 기존 확장은 이전 head를 계속 사용하므로 설정을 `lowres`로 바꿔야 한다. `scores.lowres`도항상반환하며, `selected_model`은`original/adapted/lowres`중하나다. 새모델파일을복사하고서버를재시작해야한다. 모델ID도변경되어확장캐시무효화가필요하다.

## 기본 설정

- 기본 URL: `http://127.0.0.1:8000`.
- 사용자 설정: API base URL, API 키, 대표 모델(`adapted`, `original`, `lowres`).
- 인증: `/v1/*`에 `X-API-Key: <사용자 키>`. 서버 터미널 옆에서 `python client.py --show-key`로 확인한다.
- 연결 확인: 인증 불필요 `GET /health`. 모델 준비가 완료된 뒤에만 status가ok로 응답한다.
- API 스키마: `GET /openapi.json`, 오프라인 사본 `openapi.json`.
- 동작 테스트: `/demo`, Swagger UI `/docs`.

기본 localhost는 확장을 실행하는 **사용자 컴퓨터 자체**다. 다른 사용자가 설치할 때 각자 Python 서버를 설치/실행해야 한다. 사용자A의 localhost 서버에 사용자B가 localhost로 접속할 수는 없다. 공용 LAN 서버를 선택했다면 서버IP와 그 서버 키를 사용한다.

## 확장 권한과 요청 위치

manifest의 서버 관련 host_permissions 예시:

```json
{"host_permissions": ["http://127.0.0.1/*", "http://localhost/*"]}
```

이것은 전체 manifest가 아니다. 사이트에서 이미지 찾기/content script 주입/이미지 원본 URL 접근에 필요한 별도 권한은 확장 개발자가 설계한다. LAN 서버면 그 IP에 대한 권한도 추가한다. 최소 범위를 사용한다.

content script가 이미지 식별정보를 service worker에 보내고, **확장 service worker/확장 페이지에서** 서버 요청을 수행하는 구성을 권장한다. API 키를 페이지 DOM에 붙이거나 페이지 스크립트에 전달하지 않는다. 서버는 페이지의 이미지 URL을 대신 fetch하지 않는다. 이미지 파일 bytes를 확보하는 기능은 확장 측에서 구현한다.

Chrome의 일반 웹페이지 LNA/loopback 정책과 확장 host_permissions는 다른 계층이다. 서버의 CORS 허용만으로 브라우저 권한을 대체할 수 없다. `Failed to fetch`이면 health 확인→확장 권한→Origin/확장ID→Chrome 버전/관리 정책/로컬 접근 권한 순으로 점검한다. 실제 확장 ID로 서버를 `--extension-id <id>` 실행하면 해당 Origin만 허용한다. 확장 재설치/개발 로딩 경로 변경으로 ID가 바뀌면 서버 설정도 갱신한다.

공식 문서: [확장 네트워크 요청](https://developer.chrome.com/docs/extensions/develop/concepts/network-requests), [host 권한](https://developer.chrome.com/docs/extensions/develop/concepts/declare-permissions), [로컬 네트워크 접근](https://developer.chrome.com/docs/modern-web-guidance/guides/security/local-network-access). 실제 Chrome 통합은 확장 구현 후 별도 검증한다.

## 요청

```http
POST /v1/predict?model=lowres
X-API-Key: <api-key>
Content-Type: multipart/form-data; boundary=<browser-generated>

file: <image bytes>
```

`file`은 정확히 한 개만 보낸다. JSON/base64/URL 필드는 받지 않는다. `model`은 query parameter로 `lowres`(기본), `original`, `adapted`. FormData 사용 시 **Content-Type을 직접 지정하지 않는다**. 브라우저가 올바른 boundary를 넣는다. 선택 결과와 별도로 세head의 점수를 반환한다.

입력 제한:10MiB/40MP. JPEG, PNG, WEBP, TIFF, BMP의 단일 정지 이미지만 지원한다. 투명 이미지는 RGB로 변환되며 웹페이지의 CSS 배경/필터까지 합성하는 API가 아니다. 작은 썸네일·스크린샷·애니메이션 프레임은 원본과 다른 데이터다. 가능한 한 원본 bytes를 보내고, 서버 전처리를 중복 적용하지 않는다. SVG/애니메이션/비디오 등은 우선 건너뛰는 정책을 권장한다.

## JavaScript 최소 예제

```js
async function detectImage(blob, apiKey, baseUrl = 'http://127.0.0.1:8000') {
  const data = new FormData();
  data.append('file', blob, 'image');
  const response = await fetch(`${baseUrl}/v1/predict?model=lowres`, {
    method: 'POST',
    headers: { 'X-API-Key': apiKey },
    body: data,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(`${response.status}: ${payload.error?.message ?? 'Request failed'}`);
  }
  return payload;
}
```

timeout/429 재시도 메타데이터를 포함한 함수는 `examples/extension_client.js`를 참고한다. 이 함수는 일반 JS 연동 예제이며 Chrome 확장을 설치·실행해 검증한 코드는 아니다.

## 응답 필드

실제 HTTP 실행 응답은 `examples/response.json`에합성테스트입력의응답예시를제공한다. 다음은 구조 설명이며 점수/시간은 입력마다 달라진다.

| 필드 | 의미 |
|---|---|
| `api_version` | 응답 계약 버전 |
| `request_id` | 요청마다 새로 생성하는 ID. 캐시 적중 시에도 다름 |
| `model_id` | 고정 가중치/후처리 조합의 식별자 |
| `selected_model` | 요청한 대표 모델 |
| `result.score_ai` | 대표 모델의0~1 점수. 보정된 확률 아님 |
| `result.prediction` | 생성1 / 실제0 |
| `result.label` | `ai_generated` 또는`real` |
| `scores.original` | 원본 head 결과 |
| `scores.adapted` | L2-SP+증강 평균 head 결과 |
| `scores.lowres` |160~300px 축소 view2개를 추가 학습한 평균 head 결과 |
| `threshold` | 고정0.5 |
| `score_kind` | `uncalibrated_model_score` |
| `cached` | 동일 원본 bytes의 기존 결과를 재사용했는지 |
| `image` | EXIF 보정 후 크기/원본 포맷/원본 bytes SHA256/용량 |
| `timing` | queue/preprocess/inference/total 밀리초 |
| `notice` | 진위 확정이 아니라는 안내 |

`timing.total_ms`는 endpoint의 처리 시간으로 브라우저 네트워크/전체 multipart 수신 시간까지 포함하는 종단 지연이 아니다. 캐시는 inference_ms=0이다. 첫 요청의 초기 실행은 이후 요청보다 느릴 수 있다. 작은 샘플의 시간은 처리량 벤치마크가 아니다.

표시 예: `AI 생성 추정 · 점수0.82`, `실제 촬영 추정 · 점수0.12`. 점수0.82를“82% 확률로 가짜”라고 표시하지 않는다. REAL/FAKE 두 라벨을 쓰더라도 UI 설명에는 **모델 추정**임을 넣는다. 서로 점수가 다르면 원본/개선 비교를 상세정보에서 보여줄 수 있다.

## 에러·재시도

일반 API 오류 형식:

```json
{"error":{"code":"invalid_api_key","message":"Supply a valid X-API-Key header."},"request_id":"..."}
```

| HTTP | 대표 code | 확장 동작 |
|---|---|---|
|401|invalid_api_key|키 설정 요청. 반복 자동 재시도하지 않음|
|403|origin_not_allowed|확장ID/Origin 설정 확인|
|400|empty_image/invalid_image/unexpected_form_fields|입력·폼 수정|
|413|file_too_large/request_too_large/image_too_large|크기 제한 초과로 건너뛰거나 입력 준비|
|415|unsupported_format/animated_or_multipage|지원 형식의 정지 이미지로 준비|
|422|invalid_request|file/model 계약 확인|
|429|server_busy|`Retry-After` 초 후 제한된 횟수만 재시도|
|500|inference_failed|사용자에게 서버 오류 표시. 서버 로그의request_id로 확인|

Host 검사 오류, CORS preflight 거절, Uvicorn의 연결 수 제한 등 전송 계층 오류는 위 JSON과 다를 수 있다. HTML/plain text 또는 JSON 파싱 실패도 처리한다. 서버가 꺼졌거나 브라우저 권한이 없으면 fetch 자체가 예외를 던진다. 키를 오류/분석 로그에 남기지 않는다.

## 화면 이미지 처리 권장 방식

1. 현재 보이는 이미지부터 수집(IntersectionObserver 등은 확장 담당).
2. DOM 요소 ID와 이미지 URL을 확장 내부 request ID로 연결.
3. 중복/너무 작은 아이콘/미지원 이미지는 건너뛰기.
4. 화면당 요청을1~2개씩 보내고, 빠르게 스크롤하면 불필요한 요청 취소.
5. 결과가 오면 해당 이미지 URL/요소가 여전히 같은지 확인 후 overlay 표시.
6. 서버 미실행은“연결 안 됨”, 미지원은“검사 불가”로 구분. 미검사를 real로 표시하지 않기.

서버도 SHA256 캐시를 사용하지만 전체 bytes를 보내야 캐시를 확인할 수 있다. 따라서 확장 자체의 URL/bytes 기반 캐시가 네트워크 비용을 줄인다. 서버 모델ID가 바뀌면 확장 캐시도 무효화한다. 점수는 이미지 내용과 인코딩/해상도에 민감하므로 URL이 같아도 서버 내용이 바뀐 경우 오래된 결과를 재사용하지 않도록 한다.
