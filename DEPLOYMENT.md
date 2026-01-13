# ChatMMA Deployment Guide

## Option 1: Run Locally (Easiest)

### Prerequisites
- Python 3.8 or higher
- Claude API key

### Steps

1. **Clone the repository:**
```bash
git clone https://github.com/sorarebaron/chatmma.git
cd chatmma
git checkout claude/review-chatmma-plan-WuDYx
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Set up your API key (choose ONE method):**

**Method A: Environment Variable (Recommended)**
```bash
# Mac/Linux
export CLAUDE_API_KEY="your-api-key-here"

# Windows PowerShell
$env:CLAUDE_API_KEY="your-api-key-here"

# Windows Command Prompt
set CLAUDE_API_KEY=your-api-key-here
```

**Method B: Config file**
```bash
cp config.yaml.template config.yaml
# Edit config.yaml and add your API key
```

4. **Initialize database:**
```bash
python scripts/init_database.py
python scripts/load_to_db.py --events --sources
```

5. **Run Streamlit app:**
```bash
streamlit run streamlit_app.py
```

Your browser will open to `http://localhost:8501` 🎉

---

## Option 2: Deploy to Streamlit Cloud (Free!)

### Prerequisites
- GitHub account
- Claude API key

### Steps

1. **Push code to GitHub:**
   - Make sure your repository is public or you have Streamlit Cloud access
   - **NEVER commit config.yaml with your API key!**

2. **Go to Streamlit Cloud:**
   - Visit https://share.streamlit.io
   - Sign in with GitHub
   - Click "New app"

3. **Configure deployment:**
   - Repository: `sorarebaron/chatmma`
   - Branch: `claude/review-chatmma-plan-WuDYx`
   - Main file path: `streamlit_app.py`

4. **Add your API key (SECURE):**
   - Click "Advanced settings"
   - Under "Secrets", paste:
   ```toml
   CLAUDE_API_KEY = "sk-ant-api03-YOUR-KEY-HERE"
   ```

5. **Deploy:**
   - Click "Deploy!"
   - Wait 2-3 minutes
   - Your app will be live at: `https://your-app-name.streamlit.app`

---

## Option 3: Deploy to Other Platforms

### Heroku
```bash
# Add Procfile
echo "web: streamlit run streamlit_app.py --server.port=$PORT" > Procfile

# Set config var
heroku config:set CLAUDE_API_KEY=your-key-here

# Deploy
git push heroku main
```

### Railway
1. Connect GitHub repo
2. Add environment variable: `CLAUDE_API_KEY`
3. Railway auto-deploys

### Render
1. Connect GitHub repo
2. Set environment variable: `CLAUDE_API_KEY`
3. Set start command: `streamlit run streamlit_app.py`

---

## Security Best Practices

✅ **DO:**
- Use environment variables or Streamlit secrets for API keys
- Use `.gitignore` to exclude `config.yaml`
- Keep your API key private

❌ **DON'T:**
- Commit `config.yaml` with your API key to GitHub
- Share your API key in screenshots or logs
- Use your API key in public repositories without protection

---

## Troubleshooting

### "Module not found" errors
```bash
pip install --upgrade -r requirements.txt
```

### Streamlit won't start
```bash
# Check Python version
python --version  # Should be 3.8+

# Reinstall Streamlit
pip uninstall streamlit
pip install streamlit
```

### "Database not found" error
```bash
python scripts/init_database.py
```

### API key not working
- Verify key is correct
- Check you have credits at console.anthropic.com
- Make sure environment variable is set

---

## Using the App

### Chat Page
- Ask questions about fights and fighters
- Get consensus predictions weighted by analyst accuracy
- View detailed reasoning

### Analytics Page
- See analyst performance rankings
- View accuracy rates and prediction records
- Track recent events

### Process Event Page
- Select an event from fights.yaml
- Fetch articles and YouTube transcripts
- Extract predictions with Claude
- Load to database

---

## Cost Estimate

- **Extraction**: ~$0.003 per source
- **Chat queries**: ~$0.01 per question
- **Monthly**: ~$1-2 for typical usage

With Streamlit Cloud free tier + Claude API = Total cost ~$2/month! 🎉

---

## Next Steps

1. Process historical events (UFC 320-323)
2. Build analyst accuracy records
3. Test with UFC Vegas 112 (holdout event)
4. Share your app URL with friends!

Need help? Check the README.md or open a GitHub issue.
