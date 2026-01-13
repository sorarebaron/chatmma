# Deploying ChatMMA v2.0 to Streamlit Cloud

## 🚀 Quick Deployment to chatmma.streamlit.app

### Step 1: Prepare Your Database

Since Streamlit Cloud is stateless, you need to include your database in the repository OR use an external database.

#### Option A: Include Database in Repo (Easiest for MVP)

```bash
# Make sure your database is populated
python scripts/init_db.py
python scripts/load_predictions.py --event "UFC 323"

# Commit the database
git add data/chatmma.db
git commit -m "Add populated database for deployment"
git push
```

**Note:** This works for small databases (<100MB). For larger databases, use Option B.

#### Option B: Use External Database (Future)

For production, consider using:
- Supabase (PostgreSQL)
- PlanetScale (MySQL)
- Railway (PostgreSQL)

You'll need to modify the database connection in the scripts.

### Step 2: Configure Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Click "New app"
4. Select your repository: `sorarebaron/chatmma`
5. Select branch: `claude/enhance-mma-chatbot-v9tbv` (or merge to main first)
6. Main file path: `streamlit_app.py`
7. Click "Deploy"

### Step 3: Add Your API Key

1. Once deployed, click "⚙️ Settings" in the Streamlit Cloud dashboard
2. Click "Secrets" tab
3. Add your secret:

```toml
ANTHROPIC_API_KEY = "sk-ant-api03-YOUR-KEY-HERE"
```

4. Click "Save"
5. App will automatically restart

### Step 4: Update Custom Domain

If you already have `chatmma.streamlit.app`:

1. Go to your app settings in Streamlit Cloud
2. Click "Settings" → "General"
3. The custom domain should remain `chatmma.streamlit.app`
4. If it changed, you may need to reconfigure it

If you DON'T have the custom domain yet:

1. In app settings, go to "Settings" → "General"
2. Under "Custom subdomain", enter: `chatmma`
3. Your app will be available at `chatmma.streamlit.app`

## 🔧 Local Testing

Before deploying, test locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Set API key
export ANTHROPIC_API_KEY="your-key-here"

# Or create .streamlit/secrets.toml:
mkdir -p .streamlit
cat > .streamlit/secrets.toml <<EOF
ANTHROPIC_API_KEY = "your-key-here"
EOF

# Run Streamlit locally
streamlit run streamlit_app.py
```

Visit http://localhost:8501 to test.

## 📊 Database Considerations for Streamlit Cloud

### Current Setup (Included Database)

**Pros:**
- Simple - just commit and deploy
- No external dependencies
- Works great for MVP

**Cons:**
- Database is read-only on Streamlit Cloud (file system is ephemeral)
- Need to redeploy to update predictions
- Limited to small databases

### Recommended Workflow

1. **Development:** Update database locally
2. **Commit:** Add updated database to git
3. **Deploy:** Push to trigger Streamlit Cloud rebuild

```bash
# Update predictions locally
python scripts/load_predictions.py --event "UFC Vegas 112"

# Commit updated database
git add data/chatmma.db
git commit -m "Update predictions for UFC Vegas 112"
git push

# Streamlit Cloud will automatically redeploy
```

### Future: External Database

For a production app where you want to update predictions without redeploying:

1. Set up a PostgreSQL database (Supabase is free tier)
2. Modify `query_optimizer.py` to support PostgreSQL
3. Add database credentials to Streamlit secrets
4. Update database remotely via admin script

## 🎨 Customization

### Theming

Edit `.streamlit/config.toml`:

```toml
[theme]
primaryColor = "#FF4B4B"  # Red accent color
backgroundColor = "#FFFFFF"  # White background
secondaryBackgroundColor = "#F0F2F6"  # Light gray
textColor = "#262730"  # Dark text
font = "sans serif"
```

### Layout

Edit `streamlit_app.py` to customize:
- Header and tagline
- Sidebar content
- Example questions
- Footer

## 🐛 Troubleshooting

### Error: "ANTHROPIC_API_KEY not found"

**Solution:** Add API key to Streamlit secrets (Settings → Secrets)

### Error: "Database not found"

**Solution:** Make sure `data/chatmma.db` is committed to your repository

```bash
git add data/chatmma.db
git commit -m "Add database"
git push
```

### Error: Module import errors

**Solution:** Make sure `requirements.txt` is committed and includes all dependencies

### App is slow to load

**Solution:**
- Use `@st.cache_resource` for expensive operations (already implemented)
- Consider reducing database size
- Use external database for large datasets

### Database updates don't show

**Solution:** Streamlit Cloud caches the file system. To force refresh:
1. Push a new commit
2. Or restart the app in Streamlit Cloud dashboard

## 🔄 Updating from v1 to v2

If you have an existing Streamlit app at `chatmma.streamlit.app`:

### Option 1: Update in Place (Recommended)

1. Merge this branch to your main branch:
```bash
git checkout main
git merge claude/enhance-mma-chatbot-v9tbv
git push origin main
```

2. Streamlit Cloud will automatically redeploy
3. Your domain `chatmma.streamlit.app` will now show v2.0

### Option 2: Deploy as New Branch

1. Keep `main` as v1
2. Deploy `claude/enhance-mma-chatbot-v9tbv` as a separate app
3. Test thoroughly
4. Then switch the domain to the new app

## 📈 Monitoring Costs

The Streamlit app tracks costs in the sidebar:
- Total queries
- Total cost
- Average cost per query

**Expected costs:**
- v1: ~$0.01 per query
- v2: ~$0.001 per query (10x cheaper!)

## 🎯 Post-Deployment Checklist

- [ ] App loads at chatmma.streamlit.app
- [ ] API key is configured in secrets
- [ ] Database is accessible
- [ ] Sample questions work
- [ ] Cost tracking displays correctly
- [ ] Chat history persists during session
- [ ] No console errors

## 📞 Support

If you encounter issues:
1. Check Streamlit Cloud logs (Settings → Logs)
2. Test locally first: `streamlit run streamlit_app.py`
3. Verify database exists: `ls -lh data/chatmma.db`
4. Check all dependencies: `pip install -r requirements.txt`

---

**Ready to deploy?** Just push your changes and configure your API key in Streamlit Cloud secrets!
