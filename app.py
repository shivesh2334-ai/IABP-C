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
    .info-box {
        background-color: #fef3c7;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #f59e0b;
        margin-bottom: 1rem;
    }
    .checklist-item {
        padding: 0.5rem;
        margin: 0.3rem 0;
        background-color: #f9fafb;
        border-radius: 5px;
    }
    .status-optimal {
        color: #16a34a;
        font-weight: bold;
    }
    .status-warning {
        color: #f59e0b;
        font-weight: bold;
    }
    .status-critical {
        color: #dc2626;
        font-weight: bold;
    }
    .metric-card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
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
        'augmentedPressure': '',
        'assistRatio': '1:1',
        'balloonVolume': '40',
        'inflationTiming': '',
        'deflationTiming': '',
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
    <p>Advanced AI-Powered Clinical Decision Support System for Intra-Aortic Balloon Pump Analysis</p>
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
    1. **Upload** an IABP monitor image or enter parameters
    2. **Extract** parameters with AI vision analysis
    3. **Analyze** to get comprehensive clinical report
    4. **Review** safety checklist and recommendations
    
    ### 🎯 Analysis Features
    - System information extraction
    - Hemodynamic parameter analysis
    - Waveform interpretation
    - Timing assessment
    - Clinical recommendations
    - Safety monitoring
    
    ### ⚠️ Disclaimer
    For clinical decision support only. Not a substitute for professional medical judgment.
    """)

# Main tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📸 Image Analysis", 
    "⚙️ Parameters & Settings", 
    "📊 Comprehensive Analysis", 
    "✅ Safety Checklist"
])

# Tab 1: Image Analysis
with tab1:
    st.header("IABP Monitor Image Analysis")
    
    st.markdown("""
    <div class="parameter-box">
        <strong>📸 AI-Powered Image Analysis:</strong><br>
        • Upload a clear image of the IABP monitor screen<br>
        • AI will extract system information, settings, and parameters<br>
        • Waveform analysis for timing optimization<br>
        • Comprehensive interpretation with clinical context
    </div>
    """, unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "Choose an IABP monitor image",
        type=['png', 'jpg', 'jpeg', 'pdf'],
        help="Upload a clear image showing monitor display with waveforms"
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
                ⚠️ **Very Large File Detected: {file_size_mb:.1f} MB**
                
                Files over 20MB are difficult to compress. Please use a lower resolution image.
                """)
            elif file_size_mb > 10:
                st.info(f"📊 File size: {file_size_mb:.2f} MB - Compression will be applied")
            else:
                st.success(f"📊 File size: {file_size_mb:.2f} MB - Optimal for processing")
            
            st.caption(f"Dimensions: {image.size[0]} x {image.size[1]} pixels | Format: {image.format}")
        except Exception as e:
            st.error(f"Error loading image: {e}")
            image = None
        
        col1, col2 = st.columns(2)
        
        if image:
            with col1:
                if st.button("🤖 Full AI Analysis with Image", type="primary", use_container_width=True):
                    if not st.session_state.api_key:
                        st.error("⚠️ Please enter your Anthropic API key in the sidebar")
                    else:
                        with st.spinner("Performing comprehensive analysis..."):
                            try:
                                with st.status("Processing image...", expanded=True) as status:
                                    st.write("📦 Compressing image...")
                                    compressed_data, compressed_size = compress_image(image)
                                    
                                    actual_size = len(compressed_data)
                                    actual_size_mb = actual_size / (1024 * 1024)
                                    st.write(f"✅ Compressed to {actual_size_mb:.2f} MB")
                                    
                                    if actual_size > 5_000_000:
                                        raise ValueError(f"Compressed image is {actual_size_mb:.2f} MB, exceeds 5MB limit")
                                    
                                    st.write("🔄 Converting to base64...")
                                    img_base64 = base64.b64encode(compressed_data).decode()
                                    
                                    st.write("🤖 Analyzing with Claude Vision...")
                                    status.update(label="✅ Image prepared", state="complete")
                                
                                client = anthropic.Anthropic(api_key=st.session_state.api_key)
                                
                                message = client.messages.create(
                                    model="claude-sonnet-4-20250514",
                                    max_tokens=4000,
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
                                                    "text": """You are a cardiologist specializing in IABP analysis. Analyze this IABP monitor screen comprehensively.

Provide a detailed analysis in the following format:

# IABP ANALYSIS REPORT

## SYSTEM INFORMATION
- Date/Time: [extract from screen]
- Helium Status: [pressure in psi and status]
- Battery: [status]
- ECG Lead: [which lead, mode]

## CURRENT SETTINGS
Create a table with:
- Pump Status
- Mode
- Timing (inflation-deflation %)
- Trigger source
- Assist Ratio
- Volume (cc and %)

## HEMODYNAMIC PARAMETERS

### Patient Vitals
- Heart Rate: [bpm and rhythm description]
- Blood Pressure: [systolic/diastolic mmHg]
- Mean Arterial Pressure (MAP): [mmHg]
- Augmented Pressure: [mmHg if visible]

### Calculated Hemodynamics
- Pulse Pressure
- Augmentation increase
- Any other relevant calculations

## WAVEFORM ANALYSIS

### 1. ECG Waveform (describe color and position)
- Rhythm assessment
- Quality for triggering
- Any abnormalities

### 2. Arterial Pressure Waveform
- Peak systolic pressure
- Diastolic augmentation quality
- End-diastolic pressure observations
- Consistency across beats

### 3. Balloon Pressure Waveform
- Inflation characteristics
- Deflation characteristics
- Pressure ranges
- Waveform morphology

## TIMING ASSESSMENT

### Inflation Timing
- Status: APPROPRIATE / EARLY / LATE
- Observations and reasoning
- Effect on augmentation

### Deflation Timing
- Status: APPROPRIATE / EARLY / LATE
- Observations and reasoning
- Effect on afterload reduction

## CLINICAL INTERPRETATION

### Overall Status
Indicate: OPTIMAL / SUBOPTIMAL / CONCERNING

### Positive Findings
List all good indicators (✓)

### Hemodynamic Benefits Achieved
List benefits with checkmarks (✓)

### Areas of Concern (if any)
List any issues with warnings (⚠️)

## RECOMMENDATIONS

### Immediate Management
1. Specific actionable items
2. Monitoring priorities
3. Clinical correlation needs

### Monitoring Parameters
- Key metrics to track
- Frequency of assessment
- Alert thresholds

### Weaning Considerations (if applicable)
- Readiness indicators
- Suggested approach
- Precautions

### Optimization Suggestions
- Timing adjustments if needed
- Settings modifications
- Troubleshooting steps

## SUMMARY
Provide a concise 2-3 sentence summary of the IABP function and patient status.

Use markdown formatting with ## for headers, bullet points, tables, and **bold** for emphasis. Include ✓ for positive findings and ⚠️ for concerns."""
                                                }
                                            ]
                                        }
                                    ]
                                )
                                
                                analysis_text = message.content[0].text
                                st.session_state.analysis = analysis_text
                                
                                # Try to extract parameters
                                try:
                                    extract_message = client.messages.create(
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
                                                        "text": """Extract parameters from this IABP monitor. Return ONLY a JSON object:
{
  "heartRate": "",
  "systolic": "",
  "diastolic": "",
  "map": "",
  "augmentedPressure": "",
  "assistRatio": "",
  "balloonVolume": "",
  "inflationTiming": "",
  "deflationTiming": "",
  "heliumPressure": "",
  "mode": "",
  "trigger": ""
}"""
                                                    }
                                                ]
                                            }
                                        ]
                                    )
                                    
                                    param_text = extract_message.content[0].text
                                    clean_param = param_text.replace('```json', '').replace('```', '').strip()
                                    extracted_params = json.loads(clean_param)
                                    
                                    for key, value in extracted_params.items():
                                        if value and key in st.session_state.parameters:
                                            st.session_state.parameters[key] = value
                                except:
                                    pass  # Parameters extraction is optional
                                
                                st.success("✅ Comprehensive analysis completed!")
                                st.balloons()
                                st.rerun()
                                
                            except Exception as e:
                                error_msg = str(e)
                                st.error(f"❌ Error: {error_msg}")
                                
                                if "5 MB" in error_msg or "5242880" in error_msg:
                                    st.error("""
                                    🔴 **Image Too Large**
                                    
                                    Please try:
                                    1. Lower resolution photo
                                    2. Screenshot instead of photo
                                    3. Manual parameter input
                                    """)
            
            with col2:
                if st.button("📊 Extract Parameters Only", use_container_width=True):
                    if not st.session_state.api_key:
                        st.error("⚠️ Please enter your Anthropic API key")
                    else:
                        with st.spinner("Extracting parameters..."):
                            try:
                                compressed_data, _ = compress_image(image)
                                img_base64 = base64.b64encode(compressed_data).decode()
                                
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
                                                    "text": """Extract all visible parameters from this IABP monitor. Return ONLY a JSON object with these keys (use empty string "" if not visible):
{
  "heartRate": "",
  "systolic": "",
  "diastolic": "",
  "map": "",
  "augmentedPressure": "",
  "assistRatio": "",
  "balloonVolume": "",
  "inflationTiming": "",
  "deflationTiming": "",
  "heliumPressure": "",
  "mode": "",
  "trigger": ""
}"""
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
                                
                                st.success("✅ Parameters extracted!")
                                st.info("💡 Go to 'Parameters & Settings' tab to review and edit")
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")

# Tab 2: Parameters & Settings
with tab2:
    st.header("IABP Parameters & Settings")
    
    st.markdown("""
    <div class="parameter-box">
        <strong>📝 Manual Parameter Input</strong><br>
        Enter or review extracted parameters from the IABP monitor
    </div>
    """, unsafe_allow_html=True)
    
    # System Information Section
    st.subheader("🖥️ System Information")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.session_state.parameters['mode'] = st.selectbox(
            "Operating Mode",
            options=['AutoPilot', 'Semi-Auto', 'Manual'],
            index=['AutoPilot', 'Auto' , 'Semi-Auto', 'Manual'].index(st.session_state.parameters['mode'])
        )
    
    with col2:
        st.session_state.parameters['trigger'] = st.selectbox(
            "Trigger Source",
            options=['ECG', 'Pressure', 'Pacer'],
            index=['ECG', 'Pressure', 'Pacer'].index(st.session_state.parameters['trigger'])
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
    col1, col2 = st.columns(2)
    
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
            "Augmented Diastolic Pressure (mmHg)",
            value=st.session_state.parameters['augmentedPressure'],
            placeholder="e.g., 135"
        )
    
    st.markdown("---")
    
    # Balloon Settings
    st.subheader("🎈 Balloon Settings")
    col1, col2, col3, col4 = st.columns(4)
    
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
        st.session_state.parameters['inflationTiming'] = st.text_input(
            "Inflation Timing (%)",
            value=st.session_state.parameters['inflationTiming'],
            placeholder="e.g., 35"
        )
    
    with col4:
        st.session_state.parameters['deflationTiming'] = st.text_input(
            "Deflation Timing (%)",
            value=st.session_state.parameters['deflationTiming'],
            placeholder="e.g., 78"
        )
    
    st.markdown("---")
    
    # Analysis Button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🧠 Generate Comprehensive Analysis", type="primary", use_container_width=True):
            if not st.session_state.api_key:
                st.error("⚠️ Please enter your Anthropic API key in the sidebar")
            elif not st.session_state.parameters['heartRate']:
                st.warning("⚠️ Please enter at least the heart rate to generate analysis")
            else:
                with st.spinner("Generating detailed cardiologist-level analysis..."):
                    try:
                        # Calculate derived values
                        pulse_pressure = ""
                        augmentation = ""
                        
                        if st.session_state.parameters['systolic'] and st.session_state.parameters['diastolic']:
                            try:
                                sys = float(st.session_state.parameters['systolic'])
                                dia = float(st.session_state.parameters['diastolic'])
                                pulse_pressure = f"{sys - dia:.0f}"
                            except:
                                pass
                        
                        if st.session_state.parameters['augmentedPressure'] and st.session_state.parameters['systolic']:
                            try:
                                aug = float(st.session_state.parameters['augmentedPressure'])
                                sys = float(st.session_state.parameters['systolic'])
                                augmentation = f"{aug - sys:.0f}"
                            except:
                                pass
                        
                        prompt = f"""You are an expert interventional cardiologist analyzing IABP therapy. Provide a comprehensive analysis following this exact structure:

# IABP ANALYSIS REPORT

## SYSTEM INFORMATION
- Operating Mode: {st.session_state.parameters['mode']}
- Trigger Source: {st.session_state.parameters['trigger']}
- Helium Pressure: {st.session_state.parameters['heliumPressure']} psi
- System Status: [Evaluate based on parameters]

## CURRENT SETTINGS

| Parameter | Value | Status |
|-----------|-------|--------|
| Pump Status | [Infer from data] | ✓ / ⚠️ |
| Mode | {st.session_state.parameters['mode']} | ✓ / ⚠️ |
| Timing | {st.session_state.parameters['inflationTiming']}-{st.session_state.parameters['deflationTiming']}% | ✓ / ⚠️ |
| Trigger | {st.session_state.parameters['trigger']} | ✓ / ⚠️ |
| Assist Ratio | {st.session_state.parameters['assistRatio']} | ✓ / ⚠️ |
| Volume | {st.session_state.parameters['balloonVolume']}cc | ✓ / ⚠️ |

## HEMODYNAMIC PARAMETERS

### Patient Vitals
- **Heart Rate:** {st.session_state.parameters['heartRate']} bpm [Interpret rhythm]
- **Blood Pressure:** {st.session_state.parameters['systolic']}/{st.session_state.parameters['diastolic']} mmHg
- **Mean Arterial Pressure (MAP):** {st.session_state.parameters['map']} mmHg
- **Augmented Pressure:** {st.session_state.parameters['augmentedPressure']} mmHg

### Calculated Hemodynamics
- **Pulse Pressure:** {pulse_pressure} mmHg {f"({st.session_state.parameters['systolic']}-{st.session_state.parameters['diastolic']})" if pulse_pressure else ""}
- **Augmentation:** {augmentation} mmHg above systolic {f"({st.session_state.parameters['augmentedPressure']}-{st.session_state.parameters['systolic']})" if augmentation else ""}
- **Perfusion Status:** [Evaluate based on MAP and vital signs]

## TIMING ASSESSMENT

### Inflation Timing ({st.session_state.parameters['inflationTiming']}%)
- **Status:** ✓ APPROPRIATE / ⚠️ EARLY / 🔴 LATE
- **Analysis:** [Detailed assessment of inflation timing]
- **Effect:** [Impact on coronary perfusion and augmentation]

### Deflation Timing ({st.session_state.parameters['deflationTiming']}%)
- **Status:** ✓ APPROPRIATE / ⚠️ EARLY / 🔴 LATE (CRITICAL)
- **Analysis:** [Detailed assessment of deflation timing]
- **Effect:** [Impact on afterload reduction]

## CLINICAL INTERPRETATION

### ✓ **OVERALL STATUS:** [OPTIMAL / SUBOPTIMAL / CONCERNING]

**Positive Findings:**
1. [List all favorable parameters with ✓]
2. [Hemodynamic stability indicators]
3. [Proper mechanical function]

### Hemodynamic Benefits Achieved:
- ✓ / ⚠️ Diastolic augmentation: [Assess quality]
- ✓ / ⚠️ Afterload reduction: [Assess effectiveness]
- ✓ / ⚠️ Coronary perfusion: [Estimate improvement]
- ✓ / ⚠️ Cardiac output support: [Evaluate]
- ✓ / ⚠️ End-organ perfusion: [Based on MAP]

### Areas Requiring Attention:
[List any concerns with ⚠️ or 🔴]

## RECOMMENDATIONS

### Immediate Management:
1. **[Action item]** - [Specific recommendation]
2. **[Monitoring priority]** - [What to watch]
3. **[Clinical correlation]** - [Assessment needed]

### Monitoring Parameters:
- [Key vital signs to track]
- [Frequency of assessment]
- [Alert thresholds]
- [Waveform quality checks]

### Timing Optimization (if needed):
- **Inflation:** [Specific adjustment recommendation]
- **Deflation:** [Specific adjustment recommendation]
- **Expected outcome:** [What improvement to expect]

### Weaning Considerations:
**Readiness Criteria:**
- [List criteria met/unmet]
- [Suggested weaning approach if ready]
- [Timeline considerations]

**When Ready to Wean:**
1. Reduce ratio: 1:1 → 1:2 → 1:3
2. Monitor hemodynamic stability
3. Assess native cardiac function
4. [Additional specific guidance]

### Safety Monitoring:
⚠️ **Critical Alerts:**
- [Any immediate safety concerns]
- [Limb perfusion status to monitor]
- [Balloon integrity indicators]
- [Timing error prevention]

## SUMMARY

[Provide 3-4 sentence comprehensive summary covering:
- Overall IABP function status
- Key hemodynamic findings
- Primary recommendations
- Patient stability assessment]

---

**Clinical Correlation Required:**
[Specific aspects requiring bedside assessment]

**Follow-up Timeline:**
[Suggested reassessment schedule]

Use markdown formatting extensively. Include ✓ for positive findings, ⚠️ for warnings, and 🔴 for critical concerns."""

                        client = anthropic.Anthropic(api_key=st.session_state.api_key)
                        
                        message = client.messages.create(
                            model="claude-sonnet-4-20250514",
                            max_tokens=4000,
                            messages=[
                                {
                                    "role": "user",
                                    "content": prompt
                                }
                            ]
                        )
                        
                        st.session_state.analysis = message.content[0].text
                        st.success("✅ Comprehensive analysis generated!")
                        st.balloons()
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Error generating analysis: {str(e)}")

# Tab 3: Comprehensive Analysis
with tab3:
    st.header("📊 Comprehensive Clinical Analysis")
    
    if st.session_state.analysis:
        st.markdown(f"""
        <div class="success-box">
            <strong>✅ Analysis Complete</strong><br>
            Expert cardiologist-level interpretation of IABP parameters and function
        </div>
        """, unsafe_allow_html=True)
        
        # Display the analysis
        st.markdown(st.session_state.analysis)
        
        st.markdown("---")
        
        # Action buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.download_button(
                label="📄 Download Full Report",
                data=st.session_state.analysis,
                file_name=f"iabp_analysis_{st.session_state.parameters.get('heartRate', 'report')}.md",
                mime="text/markdown",
                use_container_width=True
            )
        
        with col2:
            if st.button("🔄 Regenerate Analysis", use_container_width=True):
                st.session_state.analysis = None
                st.info("💡 Go to Parameters tab and click 'Generate Analysis' again")
                st.rerun()
        
        with col3:
            if st.button("📋 View Safety Checklist", use_container_width=True):
                st.info("💡 Switch to the 'Safety Checklist' tab")
        
        # Quick summary metrics if parameters available
        if st.session_state.parameters['heartRate']:
            st.markdown("---")
            st.subheader("📈 Quick Metrics Summary")
            
            metric_cols = st.columns(5)
            
            with metric_cols[0]:
                st.metric(
                    "Heart Rate",
                    f"{st.session_state.parameters['heartRate']} bpm" if st.session_state.parameters['heartRate'] else "N/A"
                )
            
            with metric_cols[1]:
                st.metric(
                    "Blood Pressure",
                    f"{st.session_state.parameters['systolic']}/{st.session_state.parameters['diastolic']}" if st.session_state.parameters['systolic'] else "N/A"
                )
            
            with metric_cols[2]:
                st.metric(
                    "MAP",
                    f"{st.session_state.parameters['map']} mmHg" if st.session_state.parameters['map'] else "N/A"
                )
            
            with metric_cols[3]:
                st.metric(
                    "Assist Ratio",
                    st.session_state.parameters['assistRatio']
                )
            
            with metric_cols[4]:
                st.metric(
                    "Timing",
                    f"{st.session_state.parameters['inflationTiming']}-{st.session_state.parameters['deflationTiming']}%" if st.session_state.parameters['inflationTiming'] else "N/A"
                )
    
    else:
        st.markdown("""
        <div class="info-box">
            <strong>📋 No Analysis Available</strong><br>
            To generate a comprehensive analysis:<br>
            1. Upload an IABP monitor image in the 'Image Analysis' tab, OR<br>
            2. Enter parameters manually in the 'Parameters & Settings' tab<br>
            3. Click 'Generate Comprehensive Analysis'
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📸 Go to Image Analysis", use_container_width=True):
                st.info("💡 Switch to the 'Image Analysis' tab")
        with col2:
            if st.button("⚙️ Go to Parameters", use_container_width=True):
                st.info("💡 Switch to the 'Parameters & Settings' tab")

# Tab 4: Safety Checklist (unchanged from original, but enhanced)
with tab4:
    st.header("✅ IABP Safety Checklist & Monitoring")
    
    st.markdown("""
    <div class="parameter-box">
        <strong>📋 Comprehensive Safety Protocol</strong><br>
        Systematic assessment checklist based on current evidence-based guidelines
    </div>
    """, unsafe_allow_html=True)
    
    # Initial Setup Verification
    with st.expander("✅ Initial Setup Verification", expanded=True):
        st.checkbox("Console plugged into AC power and turned on")
        st.checkbox("Helium tank ON with adequate supply (>1/4 full)")
        st.checkbox("Clear ECG signal with tall R wave visible")
        st.checkbox("Arterial pressure line connected and zeroed")
        st.checkbox("Catheter position verified on CXR (2nd-3rd intercostal space)")
        st.checkbox("Balloon volume set appropriately (typically 40cc at 100%)")
        st.checkbox("Assist ratio at 1:1 for initial full support")
        st.checkbox("Timing optimized (inflation 35-40%, deflation 75-80%)")
    
    # Hemodynamic Goals
    with st.expander("🎯 Hemodynamic Goals & Targets"):
        st.markdown("### Optimal IABP Function Indicators:")
        st.checkbox("✓ Diastolic augmentation > unassisted systolic pressure")
        st.checkbox("✓ End-diastolic pressure reduction evident")
        st.checkbox("✓ MAP maintained ≥65 mmHg (ideally 70-85 mmHg)")
        st.checkbox("✓ Adequate urine output (≥0.5 ml/kg/hr)")
        st.checkbox("✓ Heart rate <100 bpm (optimal for augmentation)")
        st.checkbox("✓ Cardiac index >2.0 L/min/m²")
        st.checkbox("✓ Normal lactate (<2 mmol/L)")
        st.checkbox("✓ Warm, well-perfused extremities")
    
    # Hourly Assessment
    with st.expander("🕐 Hourly Nursing Assessment"):
        st.markdown("### Vital Parameters:")
        st.checkbox("ECG rhythm, rate, and trigger stability")
        st.checkbox("Waveform analysis: arterial and balloon traces")
        st.checkbox("Blood pressure and MAP trending")
        st.checkbox("Heart rate and rhythm changes")
        
        st.markdown("### Vascular Assessment:")
        st.checkbox("Bilateral lower extremity pulses (DP, PT)")
        st.checkbox("Limb temperature and color comparison")
        st.checkbox("Capillary refill time (<2 seconds)")
        st.checkbox("Motor and sensory function")
        st.checkbox("Pain assessment (ischemic symptoms)")
        
        st.markdown("### Equipment Check:")
        st.checkbox("Insertion site: bleeding, hematoma, drainage")
        st.checkbox("Dressing clean, dry, and intact")
        st.checkbox("Console alarms functioning")
        st.checkbox("Helium tank level adequate")
        st.checkbox("Battery backup charged")
        st.checkbox("All connections secure")
    
    # Critical Safety Alerts
    with st.expander("⚠️ Critical Safety Alerts", expanded=True):
        st.markdown("""
        <div class="warning-box">
            <strong>🚨 IMMEDIATE ACTIONS REQUIRED FOR:</strong>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 🔴 NEVER Events:")
        st.checkbox("⚠️ Blood in helium tubing → STOP pump immediately")
        st.checkbox("⚠️ Balloon dormant >30 minutes → Thrombosis risk")
        st.checkbox("⚠️ Late deflation → MOST DANGEROUS timing error")
        st.checkbox("⚠️ Loss of distal pulses → Limb ischemia")
        st.checkbox("⚠️ Sudden hemodynamic deterioration")
        
        st.markdown("### Contraindications - Do Not Use:")
        st.markdown("""
        - ❌ Moderate to severe aortic regurgitation
        - ❌ Aortic dissection
        - ❌ Severe peripheral vascular disease
        - ❌ Uncontrolled sepsis
        - ❌ Uncontrolled bleeding
        """)
        
        st.markdown("### Signs of Complications:")
        st.markdown("""
        **Limb Ischemia (6 P's):**
        - Pain, Pallor, Pulselessness
        - Paresthesia, Paralysis, Poikilothermia
        
        **Balloon Rupture:**
        - Blood in helium tubing
        - Falling balloon pressure waveform baseline
        - Console alarm
        
        **Migration:**
        - Changes in waveform
        - New neurological symptoms
        - Abdominal/flank pain
        """)
    
    # Timing Optimization
    with st.expander("⏱️ Timing Assessment & Optimization"):
        st.markdown("### Correct Timing Indicators:")
        st.markdown("""
        ✅ **Optimal Inflation (Dicrotic Notch):**
        - Occurs at aortic valve closure
        - Creates sharp V in arterial waveform
        - Maximizes diastolic augmentation
        - Typical timing: 35-40%
        
        ✅ **Optimal Deflation (Pre-Systole):**
        - Just before next systolic upstroke
        - Maximizes afterload reduction
        - BAEDP lower than unassisted PAEDP
        - Typical timing: 75-80%
        """)
        
        st.markdown("### Timing Errors Recognition:")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **🔴 Early Inflation:**
            - Inflates before aortic valve closes
            - Truncated systolic peak
            - ⚠️ Increased afterload
            - ⚠️ Decreased stroke volume
            
            **🟡 Late Inflation:**
            - Inflates well after dicrotic notch
            - Suboptimal augmentation
            - ⚠️ Reduced coronary perfusion
            - Less efficient support
            """)
        
        with col2:
            st.markdown("""
            **🟡 Early Deflation:**
            - Deflates too soon in diastole
            - Suboptimal augmentation
            - ⚠️ Lost afterload reduction
            - Decreased efficiency
            
            **🔴 Late Deflation (CRITICAL):**
            - Remains inflated into systole
            - Widened assisted systolic peak
            - ⚠️⚠️ INCREASED afterload
            - ⚠️⚠️ Impeded ejection
            - ⚠️⚠️ Possible decompensation
            """)
    
    # Weaning Protocol
    with st.expander("📉 Weaning Criteria & Protocol"):
        st.markdown("### Readiness for Weaning:")
        st.checkbox("✓ Hemodynamically stable ×24 hours")
        st.checkbox("✓ No active ischemia or arrhythmias")
        st.checkbox("✓ Cardiac index ≥2.0 L/min/m² unassisted")
        st.checkbox("✓ MAP ≥65 mmHg on minimal pressors")
        st.checkbox("✓ Urine output adequate (≥0.5 ml/kg/hr)")
        st.checkbox("✓ Normal lactate and mixed venous saturation")
        st.checkbox("✓ Heart rate <100 bpm")
        st.checkbox("✓ Ventricular ectopy minimal (<6/min, unifocal)")
        
        st.markdown("### Weaning Steps:")
        st.markdown("""
        1. **Initial Reduction:** 1:1 → 1:2 ratio
           - Monitor for 2-4 hours
           - Assess hemodynamic stability
           
        2. **Further Reduction:** 1:2 → 1:3 ratio
           - Monitor for 2-4 hours
           - Evaluate cardiac function
           
        3. **Trial Period:** Maintain 1:3 ratio
           - Monitor closely ×24 hours
           - Ensure sustained stability
           
        4. **Pre-Removal:** Brief trial off (30 min)
           - With physician present
           - Continuous monitoring
           
        5. **Removal:** When cleared by cardiology
           - Ensure coagulation parameters acceptable
           - Post-removal monitoring protocol
        """)
        
        st.markdown("### ⚠️ Weaning Failure Signs:")
        st.markdown("""
        - Hypotension (MAP <60 mmHg)
        - Tachycardia (HR >110 bpm)
        - Chest pain or ECG changes
        - Decreased urine output
        - Rising lactate
        - Worsening oxygenation
        - New arrhythmias
        → Return to higher support level
        """)
    
    # Troubleshooting Guide
    with st.expander("🔧 Troubleshooting Quick Reference"):
        st.markdown("### Common Issues & Solutions:")
        
        trouble_col1, trouble_col2 = st.columns(2)
        
        with trouble_col1:
            st.markdown("""
            **Problem: Not Augmenting**
            - ✓ Check helium tank ON
            - ✓ Verify balloon volume 100%
            - ✓ Assess catheter position
            - ✓ Check for kinks in line
            - ✓ Verify assist ratio 1:1
            
            **Problem: Not Triggering**
            - ✓ Check ECG lead selection
            - ✓ Verify R wave amplitude
            - ✓ Switch to pressure trigger
            - ✓ Check for artifact
            - ✓ Adjust trigger sensitivity
            
            **Problem: High Pressure Alarm**
            - ✓ Check catheter kink
            - ✓ Assess for balloon wrapping
            - ✓ Verify proper position
            - ✓ Check patient movement
            """)
        
        with trouble_col2:
            st.markdown("""
            **Problem: Helium Leak**
            - ✓ Check all connections
            - ✓ Inspect tubing integrity
            - ✓ Monitor BPW baseline drift
            - ✓ Prepare for catheter change
            
            **Problem: Poor Waveforms**
            - ✓ Zero arterial line
            - ✓ Check transducer height
            - ✓ Flush arterial line
            - ✓ Verify trigger source
            - ✓ Adjust timing if needed
            
            **Problem: Irregular Augmentation**
            - ✓ Assess cardiac rhythm
            - ✓ Check for arrhythmias
            - ✓ Verify trigger consistency
            - ✓ Consider AutoPilot mode
            """)
    
    # Documentation Requirements
    with st.expander("📝 Documentation Requirements"):
        st.markdown("### Hourly Documentation:")
        st.markdown("""
        - Console settings (ratio, volume, timing)
        - Vital signs (HR, BP, MAP)
        - Waveform quality assessment
        - Vascular assessment findings
        - Insertion site condition
        - Helium tank level
        - Any alarms or interventions
        - Patient tolerance
        """)
        
        st.markdown("### Physician Notification Criteria:")
        st.markdown("""
        - ⚠️ Hemodynamic instability
        - ⚠️ New arrhythmias
        - ⚠️ Signs of limb ischemia
        - ⚠️ Blood in helium tubing
        - ⚠️ Equipment malfunction
        - ⚠️ Timing errors not self-correcting
        - ⚠️ Any acute change in patient status
        """)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #6b7280; padding: 2rem;">
    <p><strong>⚠️ Medical Disclaimer:</strong> This tool provides clinical decision support based on AI analysis of IABP parameters.</p>
    <p>It is not a substitute for professional medical judgment, clinical assessment, or direct patient care.</p>
    <p>All recommendations should be verified by qualified healthcare professionals.</p>
    <p style="margin-top: 1rem;">🫀 Powered by Claude AI (Anthropic) | Evidence-Based IABP Protocols</p>
    <p style="font-size: 0.9em; margin-top: 0.5rem;">Model: Claude Sonnet 4 | Last Updated: 2025</p>
</div>
""", unsafe_allow_html=True)
