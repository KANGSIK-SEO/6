---
title: Fake Art Validator
emoji: 🎨
colorFrom: red
colorTo: yellow
sdk: streamlit
sdk_version: "1.38.0"
app_file: app.py
pinned: false
---

# 🎨 가짜 미술품(위작) 검증 서비스

Streamlit 기반 데모 앱입니다. 고객이 미술품 이미지를 업로드하면 Hugging Face의
AI 생성 이미지 판별 모델 2종을 함께 실행해 위작(AI 생성) 가능성을 추정합니다.

- [Ateeqq/ai-vs-human-image-detector](https://huggingface.co/Ateeqq/ai-vs-human-image-detector) (Apache-2.0)
- [dima806/ai_vs_human_generated_image_detection](https://huggingface.co/dima806/ai_vs_human_generated_image_detection) (Apache-2.0)

두 모델의 "인공적/AI 생성" 확률 중 더 높은 값을 종합 위작 지수로 사용하고,
모델별 상세 결과도 함께 보여줍니다. (평균이 아니라 최댓값을 쓰는 이유: 두 모델 중
하나만 강하게 의심해도 놓치지 않기 위함)

> ⚠️ 이 서비스는 참고용 스크리닝 도구입니다. 안료 분석, 연대 측정, 소장 이력
> 조사 등 전문 감정 절차를 대체하지 않습니다.

## 로컬 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Hugging Face Spaces로 배포해서 공유 링크 받기

1. https://huggingface.co/new-space 에서 새 Space를 만듭니다.
   - SDK: **Streamlit** 선택
   - Space 이름 예: `fake-art-validator`
2. 새로 만든 Space 저장소를 클론합니다.
   ```bash
   git clone https://huggingface.co/spaces/<your-username>/fake-art-validator
   ```
3. 이 폴더(`streamlit-art-validator/`)에 있는 `app.py`, `requirements.txt`,
   `README.md`를 클론한 Space 저장소 루트로 복사합니다.
4. 커밋 후 푸시합니다.
   ```bash
   git add .
   git commit -m "Add fake art validator app"
   git push
   ```
5. 몇 분 뒤 아래 주소가 활성화되며, 이 링크를 그대로 고객에게 공유하면 됩니다.
   ```
   https://huggingface.co/spaces/<your-username>/fake-art-validator
   ```

Space는 무료 CPU 하드웨어로도 동작하지만, 최초 요청 시 두 모델(수백 MB)을
다운로드하므로 첫 실행은 다소 느릴 수 있습니다.

## Streamlit Community Cloud로 배포하는 경우

이 저장소를 GitHub 계정으로 https://share.streamlit.io 에 연결하고,
main file path를 `streamlit-art-validator/app.py`로 지정하면 됩니다.
