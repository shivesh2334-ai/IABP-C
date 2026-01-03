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
# CUSTOM CSS
# ===============================
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3a8a, #3b82f6);
        padding: 2rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 2rem;
    }
    .parameter-card {
        background-color: #f8fafc;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #3b82f6;
        margin-bottom: 1rem;
    }
    .stButton>button {
        border-radius: 8px;
    }
    .report-box {
        background-color: #ffffff;
        padding: 2rem;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
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
# ROBUST IMAGE COMPRESSION
# ===============================
def prepare_image_for_claude(image: Image.Image):
    """
    Progressively reduces image quality and resolution while checking the 
    actual Base64 string length to ensure it is under Anthropic's 5MB limit.
    """
    MAX_BYTES = 5_242_880  # 5MB hard limit
    SAFETY_LIMIT = 4_900_000 # Safety target
    
    # Ensure RGB (removes alpha channel size)
    img = image.convert("RGB")
    orig_w, orig_h = img.size
    
    scale = 1.0
    quality = 90
    
    while True:
        # Resize
        new_size = (int(orig_w * scale), int(orig_h * scale))
        resized_img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Save to buffer
        buf = io.BytesIO()
        resized_img.save(buf, format="JPEG", quality=quality, optimize=True)
        img_bytes = buf.getvalue()
        
        # Check Base64 Size
        img_base64 = base64.b64encode(img_bytes).decode("utf-8")
        current_size = len(img_base64)
        
        if current_size <= SAFETY_LIMIT:
            return img_base64, current_size / (1024 * 1024)
        
        # If too big, shrink scale by 15% and drop quality
        scale *= 0.85
        quality -= 10
        if quality < 20: quality = 20
        if scale < 0.1:
            raise ValueError("Image is too large to be compressed under 5MB.")

# ===============================
# HEADER
# ===============================
st.markdown("""
<div class="main-header">
    <h1>🫀 IABP Monitor Analyzer</h1>
    <p>Clinical Decision Support for Intra-Aortic Balloon Pump Management</p>
</div>
""", unsafe_allow_html=True)

# ===============================
# SIDEBAR
# ===============================
with st.sidebar:
    st.header("⚙️ Settings")
    st.session_state.api_key = st.text_input("Anthropic API Key", type="password", value=st.session_state.api_key)
    
    st.markdown("---")
    st.warning("⚠️ **Disclaimer:** For clinical decision support only. Not a substitute for professional medical judgment.")
    
    if st.button("Clear All Data", use_container_width=True):
        st.session_state.parameters = {k: "" for k in st.session_state.parameters}
        st.session_state.analysis = None
        st.rerun()

# ===============================
# MAIN TABS
# ===============================
tab1, tab2, tab3, tab4 = st.tabs([
    "📸 Monitor Upload", 
    "🔢 Verify Data", 
    "📊 AI Analysis", 
    "✅ Safety Checklist"
])

# -------------------------------
# TAB 1: UPLOAD
# -------------------------------
with tab1:
    st.subheader("Upload Monitor Image")
    uploaded_file = st.file_uploader("Select a photo of the IABP screen", type=["jpg", "jpeg", "png"])
    
    if uploaded_file:
        raw_img = Image.open(uploaded_file)
        st.image(raw_img, caption="Preview", use_container_width=True)
        
        if st.button("🤖 Analyze Image with Claude 3.5 Sonnet", type="primary", use_container_width=True):
            if not st.session_state.api_key:
                st.error("Please provide an API Key in the sidebar.")
            else:
                try:
                    with st.spinner("Compressing and processing image..."):
                        # Get verified safe Base64
                        b64_string, final_mb = prepare_image_for_claude(raw_img)
                        
                        client = anthropic.Anthropic(api_key=st.session_state.api_key)
                        
                        # System prompt for extraction
                        prompt = (
                            "Extract clinical values from this IABP monitor. "
                            "Return ONLY valid JSON with keys: "
                            "heartRate, systolic, diastolic, map, pdap, baedp, paedp, assistRatio, balloonVolume, timing. "
                            "If a value is not found, use an empty string."
                        )

                        message = client.messages.create(
                            model="claude-3-5-sonnet-20241022",
                            max_tokens=1000,
                            messages=[{
                                "role": "user",
                                "content": [
                                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64_string}},
                                    {"type": "text", "text": prompt}
                                ]
                            }]
                        )

                        # Parse JSON logic
                        raw_response = message.content[0].text
                        if "```json" in raw_response:
                            raw_response = raw_response.split("```json")[1].split("```")[0]
                        
                        data = json.loads(raw_response)
                        for k, v in data.items():
                            if v: st.session_state.parameters[k] = str(v)
                        
                        st.success(f"Success! Final payload size: {final_mb:.2f} MB. Please check the 'Verify Data' tab.")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error extracting data: {str(e)}")

# -------------------------------
# TAB 2: VERIFY
# -------------------------------
with tab2:
    st.subheader("Manual Review & Data Verification")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Hemodynamics**")
        st.session_state.parameters["heartRate"] = st.text_input("Heart Rate", st.session_state.parameters["heartRate"])
        st.session_state.parameters["systolic"] = st.text_input("Systolic (mmHg)", st.session_state.parameters["systolic"])
        st.session_state.parameters["diastolic"] = st.text_input("Diastolic (mmHg)", st.session_state.parameters["diastolic"])
        st.session_state.parameters["map"] = st.text_input("MAP", st.session_state.parameters["map"])
        st.session_state.parameters["pdap"] = st.text_input("PDAP (Augmentation)", st.session_state.parameters["pdap"])
    
    with col2:
        st.markdown("**Pump Settings**")
        st.session_state.parameters["baedp"] = st.text_input("BAEDP", st.session_state.parameters["baedp"])
        st.session_state.parameters["paedp"] = st.text_input("PAEDP", st.session_state.parameters["paedp"])
        st.session_state.parameters["assistRatio"] = st.selectbox("Assist Ratio", ["1:1", "1:2", "1:3"], 
                                                               index=["1:1", "1:2", "1:3"].index(st.session_state.parameters.get("assistRatio", "1:1")))
        st.session_state.parameters["balloonVolume"] = st.text_input("Balloon Volume (cc)", st.session_state.parameters["balloonVolume"])
        st.session_state.parameters["timing"] = st.text_input("Timing Info", st.session_state.parameters["timing"])

    if st.button("🧠 Generate Clinical Report", type="primary", use_container_width=True):
        if not st.session_state.api_key:
            st.error("API Key required.")
        else:
            try:
                with st.spinner("AI is analyzing waveforms and pressures..."):
                    client = anthropic.Anthropic(api_key=st.session_state.api_key)
                    analysis_prompt = f"""
                    Act as a Cardiac Intensivist. Analyze these Intra-Aortic Balloon Pump (IABP) parameters:
                    {json.dumps(st.session_state.parameters, indent=2)}

                    Provide:
                    1. ASSESSMENT: Hemodynamic stability and augmentation efficacy (PDAP vs Systolic).
                    2. AFTERLOAD REDUCTION: Evaluation of BAEDP vs PAEDP.
                    3. TIMING VERIFICATION: Are there signs of early/late inflation/deflation?
                    4. RECOMMENDATIONS: Specific adjustments.
                    """
                    
                    response = client.messages.create(
                        model="claude-3-5-sonnet-20241022",
                        max_tokens=1200,
                        messages=[{"role": "user", "content": analysis_prompt}]
                    )
                    st.session_state.analysis = response.content[0].text
                    st.rerun()
            except Exception as e:
                st.error(f"Analysis Error: {e}")

# -------------------------------
# TAB 3: ANALYSIS
# -------------------------------
with tab3:
    if st.session_state.analysis:
        st.markdown("<div class='report-box'>", unsafe_allow_html=True)
        st.markdown("### 📋 AI Clinical Interpretation")
        st.write(st.session_state.analysis)
        st.markdown("</div>", unsafe_allow_html=True)
        st.download_button("📥 Download Report", st.session_state.analysis, file_name="iabp_analysis.txt")
    else:
        st.info("Complete data extraction or manual entry in the previous tabs to see analysis.")

# -------------------------------
# TAB 4: SAFETY
# -------------------------------
with tab4:
    st.header("Critical Safety Checklist")
    st.markdown("Ensure all physical checks are completed:")
    
    c1, c2 = st.columns(2)
    with c1:
        st.checkbox("Helium tank has sufficient pressure")
        st.checkbox("No blood in the drive line (indicates rupture)")
        st.checkbox("Limb is warm and pulses are palpable/dopplerable")
    with c2:
        st.checkbox("PDAP (Augmentation) is higher than Systolic")
        st.checkbox("BAEDP is lower than PAEDP")
        st.checkbox("ECG trigger signal is stable and consistent")

# ===============================
# FOOTER
# ===============================
st.markdown("---")
st.caption("IABP Monitor Analyzer v1.2 | Powered by Claude 3.5 Sonnet Vision")
