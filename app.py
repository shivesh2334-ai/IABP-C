import streamlit as st
import anthropic
import base64
from PIL import Image
import io
import json
from datetime import datetime

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
    .info-box {
        background-color: #eff6ff;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #3b82f6;
        margin-bottom: 1rem;
    }
    .checklist-item {
        padding: 0.5rem;
        margin: 0.3rem 0;
        background-color: #f9fafb;
        border-radius: 5px;
    }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    .status-optimal {
        color: #16a34a;
        font-weight: bold;
    }
    .status-warning {
        color: #ea580c;
        font-weight: bold;
    }
    .status-critical {
        color: #dc2626;
        font-weight: bold;
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
        'timing': '35-78',
        'augmentedPressure': '',
        'heliumPressure': '',
        'mode': 'AutoPilot',
        'trigger': 'ECG'
    }

if 'analysis' not in st.session_state:
    st.session_state.analysis = None

if 'api_key' not in st.session_state:
    st.session_state.api_key = ''

def compress_image(image, target_size_bytes=4_500_000):
    """
    Aggressively compress image to be under 4.5MB (safely below 5MB limit)
    Returns: (compressed_bytes, size_in_mb)
    """
    img = image.copy()
    
    if img.mode != 'RGB':
        if img.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'RGBA':
                background.paste(img, mask=img.split()[3])
            else:
                background.paste(img, mask=img.split()[1])
            img = background
        else:
            img = img.convert('RGB')
    
    max_width = 1280
    max_height = 720
    
    if img.size[0] > max_width or img.size[1] > max_height:
        img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
    
    for quality in [80, 70, 60, 50, 40, 30, 20, 15, 10]:
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=quality, optimize=True)
        buffer.seek(0)
        compressed_bytes = buffer.read()
        size = len(compressed_bytes)
        
        if size <= target_size_bytes:
            return compressed_bytes, size / (1024 * 1024)
    
    for scale in [0.9, 0.8, 0.7, 0.6, 0.5, 0.4]:
        new_size = (int(img.size[0] * scale), int(img.size[1] * scale))
        resized = img.resize(new_size, Image.Resampling.LANCZOS)
        
        buffer = io.BytesIO()
        resized.save(buffer, format='JPEG', quality=60, optimize=True)
        buffer.seek(0)
        compressed_bytes = buffer.read()
        size = len(compressed_bytes)
        
        if size <= target_size_bytes:
            return compressed_bytes, size / (1024 * 1024)
    
    img.thumbnail((640, 480), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=50, optimize=True)
    buffer.seek(0)
    compressed_bytes = buffer.read()
    return compressed_bytes, len(compressed_bytes) / (1024 * 1024)

# Header
st.markdown("""
<div class="main-header">
    <h1>🫀 IABP Monitor Analyzer</h1>
    <p>AI-Powered Intra-Aortic Balloon Pump Analysis & Clinical Decision Support</p>
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
    1. **Upload** an IABP monitor screenshot
    2. **Extract** parameters with AI vision
    3. **Analyze** comprehensive hemodynamics
    4. **Review** detailed clinical report
    5. **Check** safety protocols
    
    ### 🎯 Analysis Includes
    - System information extraction
    - Waveform assessment
    - Timing evaluation
    - Hemodynamic calculations
    - Clinical recommendations
    - Weaning readiness
    
    ### ⚠️ Disclaimer
    For clinical decision support only. Not a substitute for professional medical judgment.
    """)

# Main tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📸 Upload & Extract", 
    "⚙️ Parameters", 
    "📊 Comprehensive Analysis", 
    "✅ Safety Checklist"
])

# Tab 1: Upload Image
with tab1:
    st.header("Upload IABP Monitor Screenshot")
    
    st.markdown("""
    <div class="parameter-box">
        <strong>📸 Best Practices for Image Capture:</strong><br>
        • Capture the entire IABP monitor screen showing all waveforms<br>
        • Ensure ECG trace (top), arterial pressure (middle), and balloon pressure (bottom) are visible<br>
        • Include all numerical values: HR, BP, timing, helium pressure<br>
        • Good lighting, clear focus, minimal glare<br>
        • Screenshot is better than photo when possible
    </div>
    """, unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "Choose an image file",
        type=['png', 'jpg', 'jpeg', 'pdf'],
        help="Upload a clear image of the complete IABP monitor display"
    )
    
    if uploaded_file is not None:
        try:
            image_data = uploaded_file.read()
            uploaded_file.seek(0)
            image = Image.open(io.BytesIO(image_data))
            
            st.image(image, caption="Uploaded IABP Monitor", use_container_width=True)
            
            file_size_mb = len(image_data) / (1024 * 1024)
            
            if file_size_mb > 20:
                st.warning(f"""
                ⚠️ **Very Large File: {file_size_mb:.1f} MB**
                
                Recommended: Take a new screenshot at lower resolution for optimal processing.
                """)
            elif file_size_mb > 10:
                st.info(f"📊 File size: {file_size_mb:.2f} MB - Will apply compression")
            else:
                st.success(f"📊 File size: {file_size_mb:.2f} MB - Optimal for processing")
            
            st.caption(f"Dimensions: {image.size[0]} x {image.size[1]} pixels | Format: {image.format}")
        except Exception as e:
            st.error(f"Error loading image: {e}")
            image = None
        
        col1, col2 = st.columns(2)
        
        if image:
            with col1:
                if st.button("🤖 AI Vision: Extract All Parameters", type="primary", use_container_width=True):
                    if not st.session_state.api_key:
                        st.error("⚠️ Please enter your Anthropic API key in the sidebar")
                    else:
                        with st.spinner("Analyzing IABP monitor with AI vision..."):
                            try:
                                with st.status("Processing image...", expanded=True) as status:
                                    st.write("📦 Compressing image...")
                                    compressed_data, compressed_size = compress_image(image)
                                    
                                    actual_size = len(compressed_data)
                                    actual_size_mb = actual_size / (1024 * 1024)
                                    st.write(f"✅ Compressed to {actual_size_mb:.2f} MB")
                                    
                                    if actual_size > 5_000_000:
                                        raise ValueError(f"Image too large: {actual_size_mb:.2f} MB")
                                    
                                    st.write("🔄 Encoding...")
                                    img_base64 = base64.b64encode(compressed_data).decode()
                                    
                                    st.write("🤖 Analyzing with Claude Vision...")
                                    status.update(label="✅ Ready for AI analysis", state="complete")
                                
                                client = anthropic.Anthropic(api_key=st.session_state.api_key)
                                
                                message = client.messages.create(
                                    model="claude-sonnet-4-20250514",
                                    max_tokens=1500,
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
                                                    "text": """Analyze this IABP (Intra-Aortic Balloon Pump) monitor screen comprehensively.

Extract ALL visible parameters and return ONLY a JSON object with these exact keys (use empty string "" if not visible):

{
  "heartRate": "",
  "systolic": "",
  "diastolic": "",
  "map": "",
  "augmentedPressure": "",
  "pdap": "",
  "baedp": "",
  "paedp": "",
  "assistRatio": "",
  "balloonVolume": "",
  "timing": "",
  "heliumPressure": "",
  "mode": "",
  "trigger": "",
  "unassistedSystolic": "",
  "unassistedDiastolic": ""
}

Look for:
- Heart rate (typically labeled HR or bpm)
- Blood pressure values (SYS/DIA, MAP)
- Augmented/peak diastolic pressure
- Assist ratio (1:1, 1:2, 1:3)
- Balloon volume (cc)
- Timing percentages
- Helium pressure (psi)
- Mode (AutoPilot, Semi-Auto, Manual)
- Trigger source (ECG, Pressure, etc.)
- Any unassisted pressure readings

Be thorough and extract every visible numeric value."""
                                                }
                                            ]
                                        }
                                    ]
                                )
                                
                                response_text = message.content[0].text
                                clean_text = response_text.replace('```json', '').replace('```', '').strip()
                                extracted_params = json.loads(clean_text)
                                
                                for key, value in extracted_params.items():
                                    if value and key in st.session_state.parameters:
                                        st.session_state.parameters[key] = value
                                
                                st.success("✅ Parameters extracted successfully!")
                                
                                # Show extracted parameters
                                with st.expander("📋 Extracted Parameters", expanded=True):
                                    cols = st.columns(3)
                                    param_list = list(extracted_params.items())
                                    for idx, (key, value) in enumerate(param_list):
                                        with cols[idx % 3]:
                                            if value:
                                                st.metric(key, value)
                                
                                st.balloons()
                                
                            except Exception as e:
                                error_msg = str(e)
                                st.error(f"❌ Error: {error_msg}")
                                
                                if "exceeds 5 MB" in error_msg or "5242880" in error_msg:
                                    st.error("""
                                    🔴 **Image Too Large**
                                    
                                    Please try:
                                    1. Taking a screenshot instead of photo
                                    2. Lower resolution capture
                                    3. Manual parameter entry
                                    """)
            
            with col2:
                if st.button("✏️ Manual Parameter Entry", use_container_width=True):
                    st.info("💡 Switch to the 'Parameters' tab to input values manually")

# Tab 2: Parameters
with tab2:
    st.header("IABP Parameters Input")
    
    st.markdown("""
    <div class="parameter-box">
        <strong>📝 Complete Parameter Entry</strong><br>
        Enter all available IABP monitoring values for comprehensive hemodynamic analysis
    </div>
    """, unsafe_allow_html=True)
    
    # System Information Section
    st.subheader("🖥️ System Information")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.session_state.parameters['mode'] = st.selectbox(
            "Mode",
            options=['AutoPilot', 'Semi-Auto', 'Manual'],
            index=['AutoPilot', 'Semi-Auto', 'Manual'].index(st.session_state.parameters['mode']) if st.session_state.parameters['mode'] in ['AutoPilot', 'Semi-Auto', 'Manual'] else 0
        )
    
    with col2:
        st.session_state.parameters['trigger'] = st.selectbox(
            "Trigger Source",
            options=['ECG', 'Pressure', 'Pacer'],
            index=['ECG', 'Pressure', 'Pacer'].index(st.session_state.parameters['trigger']) if st.session_state.parameters['trigger'] in ['ECG', 'Pressure', 'Pacer'] else 0
        )
    
    with col3:
        st.session_state.parameters['heliumPressure'] = st.text_input(
            "Helium Pressure (psi)",
            value=st.session_state.parameters['heliumPressure'],
            placeholder="e.g., 132"
        )
    
    st.markdown("---")
    
    # Hemodynamic Parameters
    st.subheader("💓 Hemodynamic Parameters")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.session_state.parameters['heartRate'] = st.text_input(
            "Heart Rate (bpm)",
            value=st.session_state.parameters['heartRate'],
            placeholder="e.g., 81"
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
    
    with col2:
        st.session_state.parameters['map'] = st.text_input(
            "MAP (mmHg)",
            value=st.session_state.parameters['map'],
            placeholder="e.g., 94"
        )
        
        st.session_state.parameters['augmentedPressure'] = st.text_input(
            "Augmented/PDAP (mmHg)",
            value=st.session_state.parameters['augmentedPressure'],
            placeholder="e.g., 135"
        )
        
        st.session_state.parameters['pdap'] = st.text_input(
            "Peak Diastolic Aug Pressure (mmHg)",
            value=st.session_state.parameters['pdap'],
            placeholder="e.g., 135"
        )
    
    with col3:
        st.session_state.parameters['baedp'] = st.text_input(
            "BAEDP (mmHg)",
            value=st.session_state.parameters['baedp'],
            placeholder="e.g., 45"
        )
        
        st.session_state.parameters['paedp'] = st.text_input(
            "PAEDP (mmHg)",
            value=st.session_state.parameters['paedp'],
            placeholder="e.g., 52"
        )
    
    st.markdown("---")
    
    # IABP Settings
    st.subheader("⚙️ IABP Settings")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.session_state.parameters['assistRatio'] = st.selectbox(
            "Assist Ratio",
            options=['1:1', '1:2', '1:3'],
            index=['1:1', '1:2', '1:3'].index(st.session_state.parameters['assistRatio'])
        )
    
    with col2:
        st.session_state.parameters['balloonVolume'] = st.text_input(
            "Balloon Volume (cc)",
            value=st.session_state.parameters['balloonVolume'],
            placeholder="e.g., 40"
        )
    
    with col3:
        st.session_state.parameters['timing'] = st.text_input(
            "Timing (Inflation-Deflation %)",
            value=st.session_state.parameters['timing'],
            placeholder="e.g., 35-78"
        )
    
    st.markdown("---")
    
    if st.button("🧠 Generate Comprehensive AI Analysis", type="primary", use_container_width=True):
        if not st.session_state.api_key:
            st.error("⚠️ Please enter your Anthropic API key in the sidebar")
        elif not st.session_state.parameters['heartRate']:
            st.warning("⚠️ Please enter at least the heart rate to generate analysis")
        else:
            with st.spinner("Generating comprehensive IABP analysis..."):
                try:
                    # Calculate additional values
                    pulse_pressure = ""
                    augmentation_value = ""
                    
                    if st.session_state.parameters['systolic'] and st.session_state.parameters['diastolic']:
                        try:
                            pulse_pressure = int(st.session_state.parameters['systolic']) - int(st.session_state.parameters['diastolic'])
                        except:
                            pass
                    
                    if st.session_state.parameters['augmentedPressure'] and st.session_state.parameters['systolic']:
                        try:
                            augmentation_value = int(st.session_state.parameters['augmentedPressure']) - int(st.session_state.parameters['systolic'])
                        except:
                            pass
                    
                    prompt = f"""You are a cardiologist analyzing an Intra-Aortic Balloon Pump (IABP) based on the following parameters. Provide a comprehensive clinical analysis report in the exact format shown below.

# IABP COMPREHENSIVE ANALYSIS REPORT

## SYSTEM INFORMATION
- Date/Time: {datetime.now().strftime("%H:%M, %m/%d/%Y")}
- Mode: {st.session_state.parameters['mode']}
- Trigger: {st.session_state.parameters['trigger']}
- Helium Pressure: {st.session_state.parameters['heliumPressure']} psi
- Pump Status: Active

## CURRENT SETTINGS

Create a table with these parameters:
- Pump Status: On/Active
- Mode: {st.session_state.parameters['mode']}
- Timing: {st.session_state.parameters['timing']}%
- Trigger: {st.session_state.parameters['trigger']}
- Assist Ratio: {st.session_state.parameters['assistRatio']}
- Balloon Volume: {st.session_state.parameters['balloonVolume']} cc

## HEMODYNAMIC PARAMETERS

### Patient Vitals
- Heart Rate: {st.session_state.parameters['heartRate']} bpm
- Blood Pressure: {st.session_state.parameters['systolic']}/{st.session_state.parameters['diastolic']} mmHg
- Mean Arterial Pressure (MAP): {st.session_state.parameters['map']} mmHg
- Augmented Pressure (PDAP): {st.session_state.parameters['augmentedPressure'] or st.session_state.parameters['pdap']} mmHg
- BAEDP: {st.session_state.parameters['baedp']} mmHg
- PAEDP: {st.session_state.parameters['paedp']} mmHg

### Calculated Hemodynamics
- Calculate and show pulse pressure
- Calculate augmentation value (augmented - systolic)
- Calculate afterload reduction effectiveness (PAEDP - BAEDP)

## WAVEFORM ANALYSIS

Describe what should be observed for:

### 1. ECG Waveform Assessment
- Rhythm analysis
- Trigger quality
- Rate evaluation

### 2. Arterial Pressure Waveform
- Systolic pressure characteristics
- Diastolic augmentation quality
- End-diastolic pressure reduction
- Consistency of augmentation

### 3. Balloon Pressure Waveform
- Inflation/deflation pattern
- Pressure cycle completeness
- Waveform consistency

## TIMING ASSESSMENT

Analyze timing based on {st.session_state.parameters['timing']}:

### Inflation Timing
- Status: Evaluate if appropriate
- Clinical impact

### Deflation Timing  
- Status: Evaluate if appropriate
- Clinical impact
- Assess afterload reduction

## CLINICAL INTERPRETATION

### Overall Status: [OPTIMAL / SUBOPTIMAL / NEEDS ADJUSTMENT]

**Positive Findings:**
List all positive findings

**Concerns (if any):**
List any concerns

### Hemodynamic Benefits Assessment:
- Diastolic augmentation effectiveness
- Afterload reduction achievement
- Cardiac output support
- Coronary perfusion enhancement
- MAP adequacy

## RECOMMENDATIONS

### Immediate Management
Provide specific recommendations

### Monitoring Parameters
What to watch closely

### Optimization Strategies
If any adjustments needed

### Weaning Considerations
Assess readiness based on:
- Hemodynamic stability
- MAP maintenance
- Heart rate
- Augmentation dependency
- Clinical indicators

## SAFETY ALERTS

Check for and report:
- Any timing errors
- Hemodynamic instability signs
- Equipment issues
- Perfusion concerns
- Contraindication development

## SUMMARY

Provide a concise summary of:
1. Current IABP function status
2. Hemodynamic support adequacy
3. Key recommendations
4. Overall patient status

---

Use markdown formatting with:
- ## for main sections
- ### for subsections
- **bold** for important values
- ✓ or ✗ for status indicators
- Tables where appropriate
- Bullet points for lists
- Color coding suggestions: ✓ (good), ⚠️ (caution), ❌ (critical)

Be thorough, specific, and clinically relevant. Base all assessments on
