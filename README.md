# 🚀 Deployment Guide for IABP Monitor Analyzer

## Quick Start - GitHub to Streamlit Cloud

### Step 1: Prepare Your GitHub Repository

1. **Create a new repository** on GitHub:
   ```
   Repository name: iabp-monitor-analyzer
   Description: AI-powered IABP clinical decision support system
   Public or Private: Your choice
   Initialize with README: No (we'll add our own)
   ```

2. **Clone the repository** to your local machine:
   ```bash
   git clone https://github.com/YOUR-USERNAME/iabp-monitor-analyzer.git
   cd iabp-monitor-analyzer
   ```

3. **Create the following file structure**:
   ```
   iabp-monitor-analyzer/
   ├── app.py
   ├── requirements.txt
   ├── README.md
   ├── DEPLOYMENT_GUIDE.md
   └── .streamlit/
       └── config.toml
   ```

4. **Copy the files** from the artifacts into your repository:
   - Copy `app.py` content into `app.py`
   - Copy `requirements.txt` content into `requirements.txt`
   - Copy `README.md` content into `README.md`
   - Create `.streamlit` folder and copy `config.toml`

5. **Commit and push** to GitHub:
   ```bash
   git add .
   git commit -m "Initial commit: IABP Monitor Analyzer"
   git push origin main
   ```

### Step 2: Deploy to Streamlit Cloud

1. **Go to Streamlit Cloud**:
   - Visit https://streamlit.io/cloud
   - Sign in with your GitHub account

2. **Create New App**:
   - Click "New app" button
   - Select your repository: `YOUR-USERNAME/iabp-monitor-analyzer`
   - Branch: `main`
   - Main file path: `app.py`
   - App URL (optional): Choose a custom subdomain

3. **Configure Secrets** (Important for API Key):
   - Before deploying, click "Advanced settings"
   - Add your secrets in TOML format:
   ```toml
   ANTHROPIC_API_KEY = "your-anthropic-api-key-here"
   ```

4. **Deploy**:
   - Click "Deploy!"
   - Wait for deployment to complete (usually 2-3 minutes)
   - Your app will be live at: `https://your-app-name.streamlit.app`

### Step 3: Update Code to Use Secrets (Optional but Recommended)

Modify the API key section in `app.py`:

```python
# In the sidebar section, replace:
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Try to get API key from secrets first, fallback to user input
    default_api_key = ""
    try:
        default_api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
    except:
        pass
    
    if default_api_key:
        st.success("✅ API Key loaded from secrets")
        api_key = default_api_key
    else:
        api_key = st.text_input(
            "Anthropic API Key",
            type="password",
            help="Enter your Anthropic API key to use AI features"
        )
    
    st.session_state.api_key = api_key
```

## Alternative Deployment Options

### Option 1: Local Development

Perfect for testing and development:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py

# Open browser to http://localhost:8501
```

### Option 2: Docker Deployment

1. **Create Dockerfile**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

2. **Build and run**:
```bash
docker build -t iabp-analyzer .
docker run -p 8501:8501 -e ANTHROPIC_API_KEY=your-key iabp-analyzer
```

### Option 3: AWS/Azure/GCP Deployment

For enterprise deployment, you can use:
- **AWS Elastic Beanstalk** with Docker
- **Azure App Service** with Container
- **Google Cloud Run** with Container

## Environment Variables

Set these environment variables for production:

```bash
ANTHROPIC_API_KEY=your-anthropic-api-key
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
```

## Security Best Practices

### 1. API Key Management
- ✅ Never commit API keys to GitHub
- ✅ Use Streamlit Secrets for cloud deployment
- ✅ Use environment variables for other deployments
- ✅ Rotate keys regularly

### 2. Access Control
```python
# Add password protection (optional)
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["app_password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        return True

if check_password():
    # Main app code here
    pass
```

### 3. Rate Limiting
Consider implementing rate limiting for API calls:

```python
import time
from datetime import datetime, timedelta

if 'last_api_call' not in st.session_state:
    st.session_state.last_api_call = datetime.now()

def rate_limit_check():
    time_since_last = datetime.now() - st.session_state.last_api_call
    if time_since_last < timedelta(seconds=2):
        st.warning("Please wait before making another request")
        return False
    st.session_state.last_api_call = datetime.now()
    return True
```

## Monitoring & Analytics

### 1. Add Google Analytics (Optional)
```python
# Add to app.py header
import streamlit.components.v1 as components

def add_analytics():
    ga_code = """
    <!-- Google Analytics -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){dataLayer.push(arguments);}
      gtag('js', new Date());
      gtag('config', 'G-XXXXXXXXXX');
    </script>
    """
    components.html(ga_code, height=0)

add_analytics()
```

### 2. Usage Logging
```python
import logging

logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Log important events
logging.info(f"Analysis generated for HR: {parameters['heartRate']}")
```

## Troubleshooting

### Common Issues

**1. API Key Not Working**
- Verify key is correct in secrets
- Check Anthropic API status
- Ensure sufficient API credits

**2. Image Upload Fails**
- Check file size (max 10MB by default)
- Verify image format (PNG, JPG, JPEG)
- Try compressing the image

**3. Deployment Fails**
- Check requirements.txt for typos
- Ensure all dependencies are compatible
- Review Streamlit Cloud logs

**4. Slow Performance**
- Optimize image size before upload
- Use caching for repeated operations
- Consider upgrading Streamlit Cloud tier

### Debug Mode

Enable debug mode for development:

```python
# Add to app.py
DEBUG = True

if DEBUG:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🐛 Debug Info")
    st.sidebar.json(st.session_state.parameters)
```

## Maintenance

### Regular Updates

1. **Update dependencies** monthly:
```bash
pip install --upgrade streamlit anthropic Pillow
pip freeze > requirements.txt
```

2. **Monitor API changes**:
- Subscribe to Anthropic API updates
- Test new Claude models when available

3. **Review user feedback**:
- Monitor GitHub issues
- Collect user feedback
- Implement improvements

## Performance Optimization

### Caching Strategies

```python
@st.cache_data(ttl=3600)
def load_reference_data():
    # Load any reference data
    return data

@st.cache_resource
def initialize_client(api_key):
    return anthropic.Anthropic(api_key=api_key)
```

### Image Optimization

```python
def optimize_image(image, max_size=(1920, 1080)):
    image.thumbnail(max_size, Image.Resampling.LANCZOS)
    return image
```

## Support & Resources

- **Streamlit Docs**: https://docs.streamlit.io
- **Anthropic API Docs**: https://docs.anthropic.com
- **GitHub Issues**: Use for bug reports and features
- **Community Forum**: Streamlit Community Forum

## Cost Estimation

**Streamlit Cloud (Free Tier)**:
- 1 app
- Unlimited viewers
- Community support

**Anthropic API Costs**:
- Claude Sonnet: ~$3 per 1M input tokens
- Claude Vision: ~$3 per 1M input tokens + $0.80/image
- Estimate: ~$0.01-0.03 per analysis

**Recommendations**:
- Monitor usage in Anthropic Console
- Set up billing alerts
- Consider caching repeated analyses

## Next Steps

1. ✅ Deploy to Streamlit Cloud
2. ✅ Test all features thoroughly
3. ✅ Share with colleagues for feedback
4. ✅ Monitor usage and performance
5. ✅ Iterate based on user needs

---

**Need Help?** Open an issue on GitHub or contact support!
