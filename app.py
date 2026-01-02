import streamlit as st
import anthropic
import base64
from PIL import Image
import io
import json

# Page configuration
st.set_page_config(
    page_title="IABP Monitor Analyzer",
    page_icon="🫀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #2563eb 0%, #4f46e5 100%);
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
        margin-bottom: 1rem;
    }
    .warning-box {
        background-color: #fef2f2;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #dc2626;
        margin-bottom: 1rem;
    }
    .success-box {
        background-color: #f0fdf4;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #16a34a;
        margin-bottom: 1rem;
    }
    .checklist-item {
        padding: 0.5rem;
        margin: 0.3rem 0;
        background-color: #f9fafb;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'parameters' not in st.session_state:
    st.session_state.parameters = {
        'heartRate': '',
        'systolic': '',
        'diastolic': '',
        'map': '',
        'pdap': '',
        'baedp': '',
        'paedp': '',
        'assistRatio': '1:1',
        'balloonVolume': '40',
        'timing': '35-78'
    }

if 'analysis' not in st.session_state:
    st.session_state.analysis = None

if 'api_key' not in st.session_state:
    st.session_state.api_key = ''

def compress_image(image, max_size_mb=9.5):
    """
    Compress image to be under the specified size in MB while maintaining readability
    """
    # Start with a reasonable quality
    quality = 95
    
    # Convert to RGB if necessary
    if image.mode in ('RGBA', 'LA', 'P'):
        background = Image.new('RGB', image.size, (255, 255, 255))
        if image.mode == 'P':
            image = image.convert('RGBA')
        background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
        image = background
    
    # Resize if image is very large
    max_dimension = 1920
    if max(image.size) > max_dimension:
        ratio = max_dimension / max(image.size)
        new_size = tuple(int(dim * ratio) for dim in image.size)
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    
    # Compress until under size limit
    while quality > 20:
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=quality, optimize=True)
        size_mb = buffer.tell() / (1024 * 1024)
        
        if size_mb <= max_size_mb:
            buffer.seek(0)
            return buffer.getvalue(), size_mb
        
        quality -= 5
    
    # If still too large, resize more aggressively
    scale_factor = 0.8
    while max(image.size) > 800:
        new_size = tuple(int(dim * scale_factor) for dim in image.size)
        image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=85, optimize=True)
        size_mb = buffer.tell() / (1024 * 1024)
        
        if size_mb <= max_size_mb:
            buffer.seek(0)
            return buffer.getvalue(), size_mb
    
    buffer.seek(0)
    return buffer.getvalue(), size_mb

# Header
st.markdown("""
<div class="main-header">
    <h1>🫀 IABP Monitor Analyzer</h1>
    <p>AI-Powered Clinical Decision Support System</p>
</div>
""", unsafe_allow_html=True)

# Sidebar for API key
with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input(
        "Anthropic API Key",
        type="password",
        value=st.session_state.api_key,
        help="Enter your Anthropic API key to use AI features"
    )
    st.session_state.api_key = api_key
    
    st.markdown("---")
    st.markdown("""
    ### 📚 Quick Guide
    1. **Upload** an IABP monitor image
    2. **Extract** parameters with AI or input manually
    3. **Analyze** to get clinical recommendations
    4. **Review** safety checklist
    
    ### ⚠️ Disclaimer
    For clinical decision support only. Not a substitute for professional medical judgment.
    """)

# Main tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📸 Upload Image", 
    "⚙️ Parameters", 
    "📊 AI Analysis", 
    "✅ Safety Checklist"
])

# Tab 1: Upload Image
with tab1:
    st.header("Upload IABP Monitor Image")
    
    uploaded_file = st.file_uploader(
        "Choose an image file",
        type=['png', 'jpg', 'jpeg'],
        help="Upload a clear image of the IABP monitor screen"
    )
    
    if uploaded_file is not None:
        # Display image
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded IABP Monitor", use_container_width=True)
        
        # Show original file size
        file_size_mb = uploaded_file.size / (1024 * 1024)
        st.info(f"📊 Original file size: {file_size_mb:.2f} MB")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🤖 Extract Parameters with AI", type="primary", use_container_width=True):
                if not st.session_state.api_key:
                    st.error("⚠️ Please enter your Anthropic API key in the sidebar")
                else:
                    with st.spinner("Compressing and analyzing image..."):
                        try:
                            # Compress image
                            compressed_data, compressed_size = compress_image(image)
                            st.success(f"✅ Image compressed to {compressed_size:.2f} MB")
                            
                            # Convert to base64
                            img_base64 = base64.b64encode(compressed_data).decode()
                            
                            # Call Claude API
                            client = anthropic.Anthropic(api_key=st.session_state.api_key)
                            
                            message = client.messages.create(
                                model="claude-sonnet-4-20250514",
                                max_tokens=1000,
                                messages=[
                                    {
                                        "role": "user",
                                        "content": [
                                            {
                                                "type": "image",
                                                "source": {
                                                    "type": "base64",
                                                    "media_type": "image/jpeg",
                                                    "data": img_base64,
                                                },
                                            },
                                            {
                                                "type": "text",
                                                "text": """Analyze this IABP monitor screen and extract the following parameters. Return ONLY a JSON object with these exact keys (use empty string "" if value not visible):
{
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
                                    }
                                ]
                            )
                            
                            # Extract response
                            response_text = message.content[0].text
                            clean_text = response_text.replace('```json', '').replace('```', '').strip()
                            extracted_params = json.loads(clean_text)
                            
                            # Update session state
                            for key, value in extracted_params.items():
                                if value:
                                    st.session_state.parameters[key] = value
                            
                            st.success("✅ Parameters extracted successfully!")
                            st.balloons()
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"❌ Error extracting parameters: {str(e)}")
                            st.info("💡 Tip: Try taking a clearer photo or input parameters manually")
        
        with col2:
            if st.button("✏️ Manual Input", use_container_width=True):
                st.info("Switch to the Parameters tab to input values manually")

# Tab 2: Parameters
with tab2:
    st.header("IABP Parameters")
    
    st.markdown("""
    <div class="parameter-box">
        <strong>📝 Enter Parameters</strong><br>
        Input the values from the IABP monitor for comprehensive analysis
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.session_state.parameters['heartRate'] = st.text_input(
            "Heart Rate (bpm)",
            value=st.session_state.parameters['heartRate'],
            placeholder="e.g., 80"
        )
        
        st.session_state.parameters['systolic'] = st.text_input(
            "Systolic BP (mmHg)",
            value=st.session_state.parameters['systolic'],
            placeholder="e.g., 114"
        )
        
        st.session_state.parameters['diastolic'] = st.text_input(
            "Diastolic BP (mmHg)",
            value=st.session_state.parameters['diastolic'],
            placeholder="e.g., 52"
        )
        
        st.session_state.parameters['map'] = st.text_input(
            "MAP (mmHg)",
            value=st.session_state.parameters['map'],
            placeholder="e.g., 94"
        )
        
        st.session_state.parameters['pdap'] = st.text_input(
            "PDAP - Peak Diastolic Augmented Pressure (mmHg)",
            value=st.session_state.parameters['pdap'],
            placeholder="e.g., 135"
        )
    
    with col2:
        st.session_state.parameters['baedp'] = st.text_input(
            "BAEDP - Balloon Aortic End-Diastolic Pressure (mmHg)",
            value=st.session_state.parameters['baedp'],
            placeholder="e.g., 45"
        )
        
        st.session_state.parameters['paedp'] = st.text_input(
            "PAEDP - Patient Aortic End-Diastolic Pressure (mmHg)",
            value=st.session_state.parameters['paedp'],
            placeholder="e.g., 52"
        )
        
        st.session_state.parameters['assistRatio'] = st.selectbox(
            "Assist Ratio",
            options=['1:1', '1:2', '1:3'],
            index=['1:1', '1:2', '1:3'].index(st.session_state.parameters['assistRatio'])
        )
        
        st.session_state.parameters['balloonVolume'] = st.text_input(
            "Balloon Volume (cc)",
            value=st.session_state.parameters['balloonVolume'],
            placeholder="e.g., 40"
        )
        
        st.session_state.parameters['timing'] = st.text_input(
            "Timing (%)",
            value=st.session_state.parameters['timing'],
            placeholder="e.g., 35-78"
        )
    
    st.markdown("---")
    
    if st.button("🧠 Generate AI Analysis", type="primary", use_container_width=True):
        if not st.session_state.api_key:
            st.error("⚠️ Please enter your Anthropic API key in the sidebar")
        elif not st.session_state.parameters['heartRate']:
            st.warning("⚠️ Please enter at least the heart rate to generate analysis")
        else:
            with st.spinner("Analyzing parameters..."):
                try:
                    prompt = f"""As a critical care expert, analyze this IABP therapy based on the following parameters:

Heart Rate: {st.session_state.parameters['heartRate']} bpm
Systolic BP: {st.session_state.parameters['systolic']} mmHg
Diastolic BP: {st.session_state.parameters['diastolic']} mmHg
MAP: {st.session_state.parameters['map']} mmHg
Peak Diastolic Augmented Pressure (PDAP): {st.session_state.parameters['pdap']} mmHg
Balloon Aortic End-Diastolic Pressure (BAEDP): {st.session_state.parameters['baedp']} mmHg
Patient Aortic End-Diastolic Pressure (PAEDP): {st.session_state.parameters['paedp']} mmHg
Assist Ratio: {st.session_state.parameters['assistRatio']}
Balloon Volume: {st.session_state.parameters['balloonVolume']} cc
Timing: {st.session_state.parameters['timing']}%

Provide a comprehensive analysis including:

1. HEMODYNAMIC ASSESSMENT
- Overall status evaluation
- Adequacy of augmentation (PDAP should ideally exceed unassisted systolic)
- Afterload reduction effectiveness (BAEDP should be lower than PAEDP)

2. TIMING EVALUATION
- Assessment of current timing settings
- Signs of early/late inflation or deflation
- Recommendations for optimization

3. CLINICAL INDICATORS
- Patient stability markers
- Potential complications to monitor
- Signs requiring immediate intervention

4. OPTIMIZATION RECOMMENDATIONS
- Specific timing adjustments if needed
- Balloon volume considerations
- Weaning readiness assessment

5. TROUBLESHOOTING ALERTS
- Any concerning patterns
- Equipment functionality concerns
- Safety considerations

Format your response with clear sections using markdown headers (##) and bullet points for easy clinical reference."""

                    client = anthropic.Anthropic(api_key=st.session_state.api_key)
                    
                    message = client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=2000,
                        messages=[
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ]
                    )
                    
                    st.session_state.analysis = message.content[0].text
                    st.success("✅ Analysis generated successfully!")
                    st.balloons()
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error generating analysis: {str(e)}")

# Tab 3: AI Analysis
with tab3:
    st.header("Clinical Analysis Report")
    
    if st.session_state.analysis:
        st.markdown(f"""
        <div class="success-box">
            <strong>✅ Analysis Complete</strong><br>
            Generated based on current IABP parameters
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(st.session_state.analysis)
        
        st.markdown("---")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            st.download_button(
                label="📄 Download Report",
                data=st.session_state.analysis,
                file_name="iabp_analysis_report.txt",
                mime="text/plain"
            )
    else:
        st.info("📋 No analysis available yet. Please input parameters and generate analysis in the Parameters tab.")

# Tab 4: Safety Checklist
with tab4:
    st.header("IABP Safety Checklist")
    
    st.markdown("""
    <div class="parameter-box">
        <strong>📋 Essential Monitoring and Safety Protocols</strong><br>
        Use this checklist for systematic patient assessment and equipment verification
    </div>
    """, unsafe_allow_html=True)
    
    # Initial Setup Verification
    with st.expander("✅ Initial Setup Verification", expanded=True):
        st.checkbox("Console plugged into AC power and turned on")
        st.checkbox("Helium tank ON with adequate supply (>1/4 full)")
        st.checkbox("Clear ECG signal with tall R wave visible")
        st.checkbox("Arterial pressure line connected and zeroed")
        st.checkbox("Catheter position verified on CXR (2nd-3rd intercostal space)")
        st.checkbox("Balloon volume set to 100% (typically 40cc)")
        st.checkbox("Assist ratio at 1:1 for initial support")
    
    # Hemodynamic Goals
    with st.expander("🎯 Hemodynamic Goals"):
        st.checkbox("PDAP > Unassisted systolic pressure (optimal augmentation)")
        st.checkbox("BAEDP < PAEDP (effective afterload reduction)")
        st.checkbox("MAP maintained >65 mmHg")
        st.checkbox("Adequate urine output (>30 ml/hr)")
        st.checkbox("Heart rate <100 bpm (ideal for weaning)")
        st.checkbox("Cardiac index >2 L/min/m²")
    
    # Hourly Assessment
    with st.expander("🕐 Hourly Assessment"):
        st.checkbox("ECG rhythm and trigger stability")
        st.checkbox("Waveform analysis for timing accuracy")
        st.checkbox("Vital signs and hemodynamic parameters")
        st.checkbox("Lower extremity pulses and perfusion")
        st.checkbox("Neurovascular status of both legs")
        st.checkbox("Insertion site for bleeding or hematoma")
        st.checkbox("Console alarms and helium level")
    
    # Critical Safety Alerts
    with st.expander("⚠️ Critical Safety Alerts", expanded=True):
        st.markdown("""
        <div class="warning-box">
            <strong>🚨 IMMEDIATE ACTIONS REQUIRED</strong>
        </div>
        """, unsafe_allow_html=True)
        
        st.checkbox("NEVER allow balloon to remain dormant >30 minutes (thrombosis risk)")
        st.checkbox("Blood in tubing = STOP and notify physician immediately")
        st.checkbox("Watch for limb ischemia: pain, pallor, pulselessness, paresthesia")
        st.checkbox("Monitor for balloon rupture signs: falling BPW baseline, blood in tubing")
        st.checkbox("Late deflation = MOST DANGEROUS timing error")
        st.checkbox("Contraindicated in aortic insufficiency and aortic dissection")
    
    # Weaning Criteria
    with st.expander("📉 Weaning Criteria"):
        st.checkbox("No signs of hypoperfusion")
        st.checkbox("Cardiac index ≥2 L/min/m²")
        st.checkbox("Urine output >30 ml/hr")
        st.checkbox("Minimal inotrope requirement")
        st.checkbox("Heart rate <100 bpm")
        st.checkbox("Ventricular ectopy <6/min, unifocal")
        st.checkbox("No angina present")
    
    # Troubleshooting Quick Reference
    with st.expander("🔧 Troubleshooting Quick Reference"):
        st.markdown("""
        **Not augmenting:**
        - Check helium ON, balloon volume 100%, catheter position
        
        **Not triggering:**
        - Verify ECG lead selection, check for artifact
        
        **High pressure alarm:**
        - May indicate catheter kink or wrapped balloon
        
        **Helium leak:**
        - Check all connections, monitor BPW baseline
        
        **Poor waveforms:**
        - Adjust trigger sensitivity or switch trigger source
        """)
    
    # Timing Error Recognition
    with st.expander("⏱️ Timing Error Recognition"):
        st.markdown("""
        **Early Inflation:**
        - Balloon inflates before aortic valve closes
        - Consequence: Reduced stroke volume, decreased cardiac output
        
        **Late Inflation:**
        - Balloon inflates well after aortic valve closes
        - Consequence: Suboptimal augmentation, reduced coronary perfusion
        
        **Early Deflation:**
        - Balloon deflates too early in diastole
        - Consequence: Lost afterload reduction benefit
        
        **Late Deflation (MOST DANGEROUS):**
        - Balloon remains inflated as ventricle ejects
        - Consequence: Increased afterload, impeded stroke volume, clinical deterioration
        """)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #6b7280; padding: 2rem;">
    <p>⚠️ <strong>Medical Disclaimer:</strong> This tool is for clinical decision support only 
