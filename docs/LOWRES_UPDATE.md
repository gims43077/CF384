# 160~300px 작은 이미지용 head 추가

2026-11-18 업데이트. API1.1.0 / 패키지모델ID `cf384-l2sp-aug-lowres-mean4-20261118`.

## 사용법

서버를Ctrl+C로종료하고다시실행한뒤브라우저를새로고침한다. `/demo`의`대표 결과`에서 **160~300px 축소 학습 추가 후보**를선택한다. 기존`adapted`기본값은유지하므로새head를쓰려면명시적으로선택해야한다.

API:

```http
POST /v1/predict?model=lowres
X-API-Key: <기존 키>
```

입력은기존과같은multipart`file`필드다. CLI는프로젝트폴더안에서:

```sh
.venv/bin/python client.py my_small_photo.jpg --model lowres
```

Windows:

```powershell
.\.venv\Scripts\python.exe client.py my_small_photo.jpg --model lowres
```

## 학습에서 달라진 것

- CF384백본은그대로동결, 선형head의385개파라미터만다시학습했다.
- 기존원본+aug0+aug1을보존하고,160~300px로축소하는lowres0/lowres1을추가했다.
- 각view는좌우반전50% → 한변160~300정수균일축소 → JPEG60~95를50%확률로적용 → 실제API처럼512/JPEG95 → CF전처리다.
- 원본280장/fold에서입력view840→1400개. 독립사진1400장을확보한것은아니다.
- λ=.01/.1/1/10을train에서학습하고, val의50%기존3조건평균+50%lowres2조건평균으로선택했다. threshold.5고정. test를보며λ/임계값을맞추지않았다.
- 4개foldhead를동일비율평균한새가중치를`models/l2sp_aug_lowres_mean.npz`에저장했다. 기존`l2sp_aug_mean.npz`와원본CF는교체하지않았다.
- 세분류기는같은CF특징을사용하므로이미지당큰백본을추가로실행하지않는다. API는입력크기로모델을자동선택하지않는다.

## 측정 결과

작은test입력은기존이미지를해당한변으로축소/JPEG85로저장한뒤API512/JPEG95전처리한합성열화다. 실제웹썸네일을새로수집한평가는아니다.

| 입력 | 기존개선head | 축소추가head |
|---|---:|---:|
|기존4계열,160px|64.06%|77.19%|
|기존4계열,224px|80.63%|85.94%|
|기존4계열,300px|89.38%|91.56%|
|기존4계열,기본512|94.69%|95.31%|
|외부100장재사용,160px|50%|67%|
|외부100장재사용,224px|56%|72%|
|외부100장재사용,300px|66%|74%|
|외부100장재사용,기본512|81%|84%|

외부100장은학습/선택에는사용하지않았지만과거평가에서이미본사진이다. 기존4계열의실제40장도fold간반복되므로대규모독립검증이아니다. 원본CF의학습노출은미확인이다.

**오탐 tradeoff:** 기존4계열160px 조건에서실제사진오탐은1.88→15.63%로늘었고AI누락은70→30%로줄었다. ROC-AUC도.8283→.8864로개선됐지만,정확도상승만으로오탐문제가해결됐다고볼수없다. 기본512조건FPR은두head모두3.75%였다.

160px외부조건에서새head의실제오탐은4%,AI누락은62%다. 정확도가개선됐어도작은이미지의생성흔적이사라지는문제는남는다. 점수만으로진위를확정하거나확대가정보를복구했다고해석하지않는다. 저해상도후보의실제사진오탐/기본조건tradeoff도전체표에서확인해야한다.

## 재현과검증

실험은`ai_image_eval/lowres_adaptation/`에별도로저장했다. `extract_features.py`, `train_evaluate.py`, `PROTOCOL.md`, `LowRes_Head_Training.ipynb`가추출/학습/설정/재현을담고있다. `results/per_family.csv`, `external_metrics.csv`는전체지표와혼동행렬, `predictions.csv`, `external_predictions.csv`, `image_changes.csv`는이미지별점수다.

API의기존2개점수일치검사는유지하고,160px파일의새lowres점수를실험특징캐시계산과대조하는테스트를추가했다. 모델파일의SHA256도검사한다. 원본프로젝트의실제HTTP/독립실행검증로그는공개사본에포함하지않았다. 서버요청중학습/다운로드는하지않는다.
