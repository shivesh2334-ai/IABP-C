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
    margin-bottom: 1rem;
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
        "timing": ""
    }

if "analysis" not in st.session_state:
    st.session_state.analysis = None

if "api_key" not in st.session_state:
    st.session_state.api_key = ""

# ===============================
# IMAGE UTILITIES
# ===============================
def prepare_image_for_claude(image: Image.Image):
    """
    Compresses image so the resulting Base64 string is < 5MB.
    Target binary size is ~3.7 MB because Base64 encoding adds ~33% overhead.
    """
    MAX_BINARY_SIZE = 3.7 * 1024 * 1024 
    MAX_DIM = (1568, 1568)

    img = image.convert("RGB")
    img.thumbnail(MAX_DIM, Image.Resampling.LANCZOS)

    for quality in [85, 70, 50, 30]:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        binary_data = buf.getvalue()
        
        if len(binary_data) <= MAX_BINARY_SIZE:
            img_base64 = base64.b64encode(binary_data).decode("utf-8")
            return img_base64, len(img_base64) / (1024 * 1024)

    raise ValueError("Unable to compress image sufficiently for API limits.")

# ===============================
# HEADER
# ===============================
st.markdown("""
<div class="main-header">
    <h1>🫀 IABP Monitor Analyzer</h1>
    <p>AI-Powered Clinical Decision Support for Intra-Aortic Balloon Pump Management</p>
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
    This tool is for educational and clinical decision support purposes only. 
    Final clinical decisions must be made by qualified medical personnel.
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
    uploaded_file = st.file_uploader("Choose a clear photo of the IABP monitor screen", type=["jpg", "jpeg", "png"])

    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Image", use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🤖 Extract Parameters with AI", type="primary", use_container_width=True):
                if not st.session_state.api_key:
                    st.error("Please enter your Anthropic API Key in the sidebar.")
                else:
                    try:
                        with st.spinner("Processing image and extracting data..."):
                            img_base64, size_mb = prepare_image_for_claude(image)
                            
                            client = anthropic.Anthropic(api_key=st.session_state.api_key)
                            
                            prompt = """Extract clinical values from this IABP monitor. 
                            Return ONLY a JSON object with these keys: 
                            heartRate, systolic, diastolic, map, pdap, baedp, paedp, assistRatio, balloonVolume, timing.
                            If a value is not visible, leave it as an empty string."""

                            message = client.messages.create(
                                model="claude-3-5-sonnet-20241022",
                                max_tokens=1000,
                                messages=[{
                                    "role": "user",
                                    "content": [
                                        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": img_base64}},
                                        {"type": "text", "text": prompt}
                                    ]
                                }]
                            )

                            # Clean and parse JSON
                            raw_res = message.content[0].text
                            if "```json" in raw_res:
                                raw_res = raw_res.split("```json")[1].split("```")[0]
                            
                            extracted_data = json.loads(raw_res)
                            
                            for key in st.session_state.parameters:
                                if key in extracted_data and extracted_data[key]:
                                    st.session_state.parameters[key] = str(extracted_data[key])
                            
                            st.success(f"Successfully extracted parameters! (Payload: {size_mb:.2f} MB)")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error extracting parameters: {str(e)}")

        with col2:
            st.info("After extraction, verify the values in the 'Parameters' tab.")

# ===============================
# TAB 2 – PARAMETERS
# ===============================
with tab2:
    st.header("Verify & Edit Parameters")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Hemodynamics")
        st.session_state.parameters["heartRate"] = st.text_input("Heart Rate (BPM)", st.session_state.parameters["heartRate"])
        st.session_state.parameters["systolic"] = st.text_input("Systolic (mmHg)", st.session_state.parameters["systolic"])
        st.session_state.parameters["diastolic"] = st.text_input("Diastolic (mmHg)", st.session_state.parameters["diastolic"])
        st.session_state.parameters["map"] = st.text_input("MAP (mmHg)", st.session_state.parameters["map"])
        st.session_state.parameters["pdap"] = st.text_input("PDAP (Peak Diastolic Augmented Pressure)", st.session_state.parameters["pdap"])

    with col2:
        st.subheader("IABP Settings")
        st.session_state.parameters["baedp"] = st.text_input("BAEDP (Balloon Aortic End Diastolic Pressure)", st.session_state.parameters["baedp"])
        st.session_state.parameters["paedp"] = st.text_input("PAEDP (Patient Aortic End Diastolic Pressure)", st.session_state.parameters["paedp"])
        st.session_state.parameters["assistRatio"] = st.selectbox("Assist Ratio", ["1:1", "1:2", "1:3"], 
                                                               index=["1:1", "1:2", "1:3"].index(st.session_state.parameters.get("assistRatio", "1:1")))
        st.session_state.parameters["balloonVolume"] = st.text_input("Balloon Volume (cc)", st.session_state.parameters["balloonVolume"])
        st.session_state.parameters["timing"] = st.text_input("Timing Info", st.session_state.parameters["timing"])

    if st.button("🧠 Generate Clinical Analysis", type="primary", use_container_width=True):
        if not st.session_state.api_key:
            st.error("API key missing.")
        else:
            try:
                with st.spinner("Analyzing hemodynamics..."):
                    client = anthropic.Anthropic(api_key=st.session_state.api_key)
                    analysis_prompt = f"""
                    As a cardiology expert, analyze these IABP parameters:
                    {json.dumps(st.session_state.parameters, indent=2)}

                    Provide a structured report including:
                    1. Hemodynamic Assessment (Augmentation effectiveness)
                    2. Timing Evaluation (Compare PDAP/Systolic and BAEDP/PAEDP)
                    3. Potential Optimization suggestions
                    4. Immediate Safety Concerns
                    """
                    
                    response = client.messages.create(
                        model="claude-3-5-sonnet-20241022",
                        max_tokens=1500,
                        messages=[{"role": "user", "content": analysis_prompt}]
                    )
                    st.session_state.analysis = response.content[0].text
                    st.rerun()
            except Exception as e:
                st.error(f"Analysis failed: {e}")

# ===============================
# TAB 3 – ANALYSIS
# ===============================
with tab3:
    if st.session_state.analysis:
        st.markdown("<div class='success-box'>AI Analysis Result</div>", unsafe_allow_html=True)
        st.markdown(st.session_state.analysis)
        st.download_button("📥 Download Analysis", st.session_state.analysis, file_name="iabp_report.txt")
    else:
        st.info("Provide parameters and click 'Generate Clinical Analysis' in the Parameters tab.")

# ===============================
# TAB 4 – SAFETY
# ===============================
with tab4:
    st.header("Critical Safety Checklist")
    cols = st.columns(2)
    with cols[0]:
        st.checkbox("Balloon is NOT dormant (must cycle at least every 30 mins)")
        st.checkbox("PDAP is higher than Systolic (Effective Augmentation)")
        st.checkbox("BAEDP is lower than PAEDP (Reduced Afterload)")
    with cols[1]:
        st.checkbox("No blood observed in the helium drive line (Balloon Rupture)")
        st.checkbox("Peripheral pulses present in the cannulated limb")
        st.checkbox("MAP is > 65 mmHg or per institutional target")

# ===============================
# FOOTER
# ===============================
st.markdown("""
---
<div style="text-align:center;color:#6b7280; font-size: 0.8rem;">
Powered by Anthropic Claude 3.5 Sonnet • Developed for Clinical Decision Support
</div>
""", unsafe_allow_html=True)
