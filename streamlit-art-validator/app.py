"""가짜 미술품(위작) 검증 서비스 - Streamlit + Hugging Face 이미지 분류 모델 2종"""

import streamlit as st
from PIL import Image
from transformers import pipeline

MODELS = {
    "umm-maybe/AI-image-detector": "umm-maybe/AI-image-detector",
    "Organika/sdxl-detector": "Organika/sdxl-detector",
}

FAKE_KEYWORDS = ("artificial", "ai", "fake", "generated", "synthetic")
REAL_KEYWORDS = ("human", "real", "authentic", "genuine")

st.set_page_config(page_title="가짜 미술품 검증 서비스", page_icon="🎨", layout="centered")


@st.cache_resource(show_spinner=False)
def load_pipelines():
    return {name: pipeline("image-classification", model=model_id) for name, model_id in MODELS.items()}


def fake_score(predictions):
    """예측 결과 중 '인공적/AI 생성' 쪽 라벨의 확률을 위작 지수로 사용."""
    for pred in predictions:
        if any(k in pred["label"].lower() for k in FAKE_KEYWORDS):
            return pred["score"]
    for pred in predictions:
        if any(k in pred["label"].lower() for k in REAL_KEYWORDS):
            return 1 - pred["score"]
    return max(predictions, key=lambda p: p["score"])["score"]


st.title("🎨 가짜 미술품(위작) 검증 서비스")
st.caption(
    "Hugging Face의 AI 생성 이미지 판별 모델 2종(umm-maybe/AI-image-detector, "
    "Organika/sdxl-detector)의 결과를 결합해 업로드한 이미지의 위작·AI 생성 가능성을 추정합니다."
)

with st.expander("⚠️ 사용 전 꼭 읽어주세요 (한계 안내)", expanded=True):
    st.markdown(
        """
- 이 서비스는 이미지가 **AI로 생성·합성되었을 가능성**을 탐지하는 오픈소스 분류 모델 2종의
  출력을 참고용으로 제공합니다.
- 안료 성분 분석, 캔버스·제작 연대 측정, 소장 이력(프로버넌스) 조사 같은 **전문 감정 절차를
  대체하지 않습니다.**
- 실제로 촬영·스캔된 진품 사진에도 오탐이 발생할 수 있습니다. 최종 판단은 반드시 전문가에게
  의뢰하세요.
        """
    )

uploaded = st.file_uploader("검증할 미술품 이미지를 업로드하세요", type=["jpg", "jpeg", "png", "webp"])

if uploaded:
    image = Image.open(uploaded).convert("RGB")
    st.image(image, caption="업로드한 이미지", use_container_width=True)

    with st.spinner("두 모델로 분석 중입니다... (최초 실행 시 모델 다운로드로 시간이 걸릴 수 있습니다)"):
        pipelines = load_pipelines()
        results = {name: pipe(image) for name, pipe in pipelines.items()}

    scores = {name: fake_score(preds) for name, preds in results.items()}
    combined = sum(scores.values()) / len(scores)

    st.subheader("검증 결과")
    if combined >= 0.66:
        st.error(f"🔴 위작(AI 생성) 가능성 높음 — 종합 위작 지수 {combined:.0%}")
    elif combined >= 0.33:
        st.warning(f"🟡 판단 불확실 — 종합 위작 지수 {combined:.0%}")
    else:
        st.success(f"🟢 진품 가능성 높음 — 종합 위작 지수 {combined:.0%}")

    st.markdown("#### 모델별 상세 결과")
    for name, preds in results.items():
        st.markdown(f"**{name}**")
        st.progress(scores[name], text=f"위작(AI 생성) 확률 {scores[name]:.1%}")
        st.json(preds)

    st.caption("종합 위작 지수 = 두 모델이 예측한 '인공적/AI 생성' 라벨 확률의 평균")

st.sidebar.header("모델 정보")
for name, model_id in MODELS.items():
    st.sidebar.markdown(f"- [{name}](https://huggingface.co/{model_id})")
st.sidebar.markdown("---")
st.sidebar.caption("두 모델 모두 실제(사진/전통 회화) 이미지와 AI 생성 이미지를 구분하도록 학습된 공개 모델입니다.")
