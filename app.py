import streamlit as st
import anthropic
import base64
from PIL import Image
import io
import json

# ===============================
# PAGE CONFIG
# ===============================
st.set_page_config(
    page_title="IABP Monitor Analyzer",
    page_icon="🫀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===============================
# CSS
# ===============================
st.markdown("""
<style>
.main-header {
    background: linear-gradient(90deg, #2563eb, #4f46e5);
    padding: 2rem;
    border-radius: 10px;
    color: white;
    margin-bottom: 2rem;
}
.parameter-box {
    background-color: #f0f9ff;
    padding: 1rem;
    border-radius: 8px;
    border-left: 4px solid #2563eb;
}
.success-box {
    background-color: #f0fdf4;
    padding: 1rem;
    border-radius: 8px;
    border-left: 4px solid #16a34a;
}
.warning-box {
    background-color: #fef2f2;
    padding: 1rem;
    border-radius: 8px;
    border-left: 4px solid #dc2626;
}
</style>
""", unsafe_allow_html=True)

# ===============================
# SESSION STATE
# ===============================
if "parameters" not in st.session_state:
    st.session_state.parameters = {
        "heartRate": "",
        "systolic": "",
        "diastolic": "",
        "map": "",
        "pdap": "",
        "baedp": "",
        "paedp": "",
        "assistRatio": "1:1",
        "balloonVolume": "40",
        "timing": "35-78"
    }

if "analysis" not in st.session_state:
    st.session_state.analysis = None

if "api_key" not in st.session_state:
    st.session_state.api_key = ""

# ===============================
# IMAGE COMPRESSION (SAFE)
# ===============================

    
def prepare_image_for_claude(image: Image.Image):
    """
    HARD guarantee: Base64 < 5 MB
    """
    MAX_BASE64 = 5_200_000  # safety margin
    MAX_DIM = (1024, 768)

    img = image.convert("RGB")
    img.thumbnail(MAX_DIM, Image.Resampling.LANCZOS)

    for quality in range(75, 20, -5):
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        jpeg_bytes = buf.getvalue()

        # Encode FIRST
        img_base64 = base64.b64encode(jpeg_bytes).decode("utf-8")
        base64_size = len(img_base64)

        if base64_size <= MAX_BASE64:
            return img_base64, base64_size / (1024 * 1024)

    raise ValueError("Unable to reduce image below Claude Base64 limit")
# ===============================
# HEADER
# ===============================
st.markdown("""
<div class="main-header">
    <h1>🫀 IABP Monitor Analyzer</h1>
    <p>AI-Powered Clinical Decision Support</p>
</div>
""", unsafe_allow_html=True)

# ===============================
# SIDEBAR
# ===============================
with st.sidebar:
    st.header("⚙️ Configuration")
    st.session_state.api_key = st.text_input(
        "Anthropic API Key",
        type="password",
        value=st.session_state.api_key
    )

    st.markdown("""
    ---
    ### ⚠️ Disclaimer
    Clinical decision support only.
    Not a substitute for physician judgment.
    """)

# ===============================
# TABS
# ===============================
tab1, tab2, tab3, tab4 = st.tabs([
    "📸 Upload Image",
    "⚙️ Parameters",
    "📊 AI Analysis",
    "✅ Safety Checklist"
])

# ===============================
# TAB 1 – IMAGE UPLOAD
# ===============================
with tab1:
    st.header("Upload IABP Monitor Image")

    uploaded_file = st.file_uploader(
        "Upload monitor image",
        type=["jpg", "jpeg", "png"]
    )

    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, use_container_width=True)

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🤖 Extract Parameters with AI", type="primary", use_container_width=True):
                if not st.session_state.api_key:
                    st.error("Enter API key in sidebar")
                    st.stop()

                try:
                    jpeg, jpeg_mb = compress_image_for_claude(image)
                    img_base64, base64_mb = prepare_image_for_claude(image)

st.info(f"✅ Base64 payload size: {base64_mb:.2f} MB")

# ONLY now call Claude
message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1000,
    messages=[{
        "role": "user",
        "content": [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": img_base64
                }
            },
            {
                "type": "text",
                "text": "...your prompt..."
            }
        ]
    }]
)
  "heartRate": "",
  "systolic": "",
  "diastolic": "",
  "map": "",
  "pdap": "",
  "baedp": "",
  "paedp": "",
  "assistRatio": "",
  "balloonVolume": "",
  "timing": ""
}"""
                                }
                            ]
                        }]
                    )

                    clean = response.content[0].text.replace("```json", "").replace("```", "")
                    extracted = json.loads(clean)

                    for k, v in extracted.items():
                        if v:
                            st.session_state.parameters[k] = v

                    st.success("✅ Parameters extracted")
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ {e}")

        with col2:
            if st.button("✏️ Manual Input", use_container_width=True):
                st.info("Use Parameters tab")

# ===============================
# TAB 2 – PARAMETERS
# ===============================
with tab2:
    st.header("IABP Parameters")

    col1, col2 = st.columns(2)

    for field in ["heartRate", "systolic", "diastolic", "map", "pdap"]:
        with col1:
            st.session_state.parameters[field] = st.text_input(
                field.upper(), st.session_state.parameters[field]
            )

    for field in ["baedp", "paedp", "balloonVolume", "timing"]:
        with col2:
            st.session_state.parameters[field] = st.text_input(
                field.upper(), st.session_state.parameters[field]
            )

    st.session_state.parameters["assistRatio"] = st.selectbox(
        "Assist Ratio",
        ["1:1", "1:2", "1:3"],
        index=["1:1", "1:2", "1:3"].index(st.session_state.parameters["assistRatio"])
    )

    if st.button("🧠 Generate AI Analysis", type="primary", use_container_width=True):
        if not st.session_state.api_key:
            st.error("API key missing")
            st.stop()

        prompt = f"""
Analyze IABP therapy:

{json.dumps(st.session_state.parameters, indent=2)}

Provide:
- Hemodynamic assessment
- Timing evaluation
- Optimization suggestions
- Safety alerts
"""

        client = anthropic.Anthropic(api_key=st.session_state.api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        st.session_state.analysis = response.content[0].text
        st.rerun()

# ===============================
# TAB 3 – ANALYSIS
# ===============================
with tab3:
    if st.session_state.analysis:
        st.markdown("<div class='success-box'>Analysis Complete</div>", unsafe_allow_html=True)
        st.markdown(st.session_state.analysis)
        st.download_button(
            "📄 Download",
            st.session_state.analysis,
            "iabp_analysis.txt"
        )
    else:
        st.info("No analysis generated")

# ===============================
# TAB 4 – SAFETY
# ===============================
with tab4:
    st.header("IABP Safety Checklist")
    st.checkbox("Balloon never dormant >30 min")
    st.checkbox("PDAP > systolic")
    st.checkbox("BAEDP < PAEDP")
    st.checkbox("MAP > 65 mmHg")
    st.checkbox("No limb ischemia")
    st.checkbox("No blood in helium line")

# ===============================
# FOOTER
# ===============================
st.markdown("""
---
<div style="text-align:center;color:#6b7280">
⚠️ Clinical decision support only • Powered by Claude AI
</div>
""", unsafe_allow_html=True)
