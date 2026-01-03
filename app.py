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
# CSS / STYLING
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
.stTabs [data-baseweb="tab-list"] {
    gap: 24px;
}
.stTabs [data-baseweb="tab"] {
    height: 50px;
    white-space: pre-wrap;
    background-color: #f8fafc;
    border-radius: 4px 4px 0px 0px;
    gap: 1px;
    padding-top: 10px;
    padding-bottom: 10px;
}
.stTabs [aria-selected="true"] {
    background-color: #eff6ff;
    border-bottom: 3px solid #3b82f6 !important;
}
</style>
""", unsafe_allow_html=True)

# ===============================
# SESSION STATE INITIALIZATION
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
    Progressively reduces image quality and resolution until 
    the Base64 payload is safely under 5MB.
    """
    MAX_BASE64_SIZE = 5 * 1024 * 1024  # 5 Million characters/bytes
    SAFETY_MARGIN = 0.95
    TARGET_SIZE = MAX_BASE64_SIZE * SAFETY_MARGIN

    # Start with original dimensions
    orig_w, orig_h = image.size
    
    # Try combinations of quality and scaling
    # We prioritize keeping a reasonable resolution for text extraction
    for scale in [1.0, 0.8, 0.6, 0.5, 0.4]:
        for quality in [85, 70, 50, 30]:
            # Resize
            new_w = int(orig_w * scale)
            new_h = int(orig_h * scale)
            img_resized = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            # Save to buffer
            buf = io.BytesIO()
            img_resized.convert("RGB").save(buf, format="JPEG", quality=quality, optimize=True)
            img_bytes = buf.getvalue()
            
            # Encode and check size
            img_base64 = base64.b64encode(img_bytes).decode("utf-8")
            if len(img_base64) <= TARGET_SIZE:
                return img_base64, len(img_base64) / (1024 * 1024)
                
    raise ValueError("Could not compress image sufficiently. Please use a smaller file.")

# ===============================
# UI - HEADER
# ===============================
st.markdown("""
<div class="main-header">
    <h1>🫀 IABP Monitor Analyzer</h1>
    <p>Clinical Decision Support • AI-Powered Waveform Analysis</p>
</div>
""", unsafe_allow_html=True)

# ===============================
# UI - SIDEBAR
# ===============================
with st.sidebar:
    st.header("⚙️ Settings")
    st.session_state.api_key = st.text_input("Anthropic API Key", type="password", value=st.session_state.api_key)
    
    st.markdown("---")
    st.info("""
    **Instructions:**
    1. Upload a clear photo of the IABP monitor.
    2. Click 'Extract' to pull values automatically.
    3. Verify data in 'Parameters' tab.
    4. Generate full clinical analysis.
    """)
    
    if st.button("Reset All Data"):
        for key in st.session_state.parameters:
            st.session_state.parameters[key] = ""
        st.session_state.analysis = None
        st.rerun()

# ===============================
# MAIN TABS
# ===============================
tab1, tab2, tab3, tab4 = st.tabs([
    "📸 Image Upload", 
    "🔢 Parameters", 
    "📊 AI Analysis", 
    "✅ Safety Checklist"
])

# -------------------------------
# TAB 1: IMAGE UPLOAD
# -------------------------------
with tab1:
    uploaded_file = st.file_uploader("Upload IABP Monitor Screenshot/Photo", type=["jpg", "jpeg", "png"])
    
    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, caption="Monitor Preview", use_container_width=True)
        
        if st.button("🤖 AI Extraction (OCR + Vision)", type="primary", use_container_width=True):
            if not st.session_state.api_key:
                st.error("Missing API Key. Please provide it in the sidebar.")
            else:
                try:
                    with st.spinner("Compressing and analyzing image..."):
                        # Get safe base64
                        b64_string, size_mb = prepare_image_for_claude(img)
                        
                        client = anthropic.Anthropic(api_key=st.session_state.api_key)
                        
                        prompt = """Analyze this IABP (Intra-Aortic Balloon Pump) monitor image. 
                        Extract values and return ONLY valid JSON. 
                        Keys: heartRate, systolic, diastolic, map, pdap, baedp, paedp, assistRatio, balloonVolume, timing.
                        Note: 
                        - pdap is often 'Augmentation' or the highest peak.
                        - baedp is 'Balloon Aortic End Diastolic Pressure'.
                        - paedp is 'Patient Aortic End Diastolic Pressure'.
                        """

                        response = client.messages.create(
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

                        # Clean response text
                        res_text = response.content[0].text
                        if "```json" in res_text:
                            res_text = res_text.split("```json")[1].split("```")[0]
                        
                        extracted = json.loads(res_text)
                        
                        # Merge extracted data into session state
                        for k, v in extracted.items():
                            if v: st.session_state.parameters[k] = str(v)
                        
                        st.success(f"Extraction successful! (Payload size: {size_mb:.2f} MB)")
                        st.rerun()

                except Exception as e:
                    st.error(f"❌ Analysis failed: {str(e)}")

# -------------------------------
# TAB 2: PARAMETERS
# -------------------------------
with tab2:
    st.header("Hemodynamic Values")
    st.write("Verify the values extracted by AI or enter them manually.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.parameters["heartRate"] = st.text_input("Heart Rate (bpm)", st.session_state.parameters["heartRate"])
        st.session_state.parameters["systolic"] = st.text_input("Systolic Pressure (mmHg)", st.session_state.parameters["systolic"])
        st.session_state.parameters["diastolic"] = st.text_input("Diastolic Pressure (mmHg)", st.session_state.parameters["diastolic"])
        st.session_state.parameters["map"] = st.text_input("Mean Arterial Pressure (MAP)", st.session_state.parameters["map"])
    
    with col2:
        st.session_state.parameters["pdap"] = st.text_input("PDAP (Augmentation)", st.session_state.parameters["pdap"])
        st.session_state.parameters["baedp"] = st.text_input("BAEDP (Balloon End Diastolic)", st.session_state.parameters["baedp"])
        st.session_state.parameters["paedp"] = st.text_input("PAEDP (Patient End Diastolic)", st.session_state.parameters["paedp"])
        st.session_state.parameters["assistRatio"] = st.selectbox("Assist Ratio", ["1:1", "1:2", "1:3"], 
                                                               index=["1:1", "1:2", "1:3"].index(st.session_state.parameters.get("assistRatio", "1:1")))

    if st.button("🧠 Generate Clinical Interpretation", type="primary", use_container_width=True):
        if not st.session_state.api_key:
            st.error("API Key required.")
        else:
            try:
                with st.spinner("Running clinical analysis..."):
                    client = anthropic.Anthropic(api_key=st.session_state.api_key)
                    
                    analysis_prompt = f"""As a Cardiac Intensivist, evaluate these IABP parameters:
                    {json.dumps(st.session_state.parameters, indent=2)}

                    Please provide:
                    1. ASSESSMENT: Is augmentation effective? (PDAP vs Systolic)
                    2. AFTERLOAD REDUCTION: Is the pump reducing afterload? (BAEDP vs PAEDP)
                    3. TIMING: Check for early/late inflation or deflation.
                    4. RECOMMENDATIONS: Adjustments to timing or volume.
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

# -------------------------------
# TAB 3: ANALYSIS DISPLAY
# -------------------------------
with tab3:
    if st.session_state.analysis:
        st.markdown("### 📋 AI Clinical Report")
        st.info(st.session_state.analysis)
        st.download_button("Download Report (.txt)", st.session_state.analysis, file_name="iabp_analysis.txt")
    else:
        st.warning("No analysis generated yet. Please go to the Parameters tab.")

# -------------------------------
# TAB 4: SAFETY CHECKLIST
# -------------------------------
with tab4:
    st.header("IABP Safety Standards")
    st.markdown("Confirm the following safety checks manually:")
    
    st.checkbox("Helium Line: No blood or condensation observed.")
    st.checkbox("Limb Check: Pedal pulses present and leg is warm/pink.")
    st.checkbox("Trigger: No 'Trigger Loss' or 'No Signal' alarms.")
    st.checkbox("Augmentation: PDAP is higher than Systolic.")
    st.checkbox("Afterload: BAEDP is lower than PAEDP.")
    st.checkbox("Dormancy: Pump has not been off/dormant for >30 minutes.")

# ===============================
# FOOTER
# ===============================
st.markdown("---")
st.caption("⚠️ Clinical Decision Support System: Not a replacement for professional medical judgment.")
