# 🚀 How to Run ChatMMA (Super Simple)

## For Non-Programmers - Just 4 Steps!

### Step 1: Download the Code
1. Go to: https://github.com/sorarebaron/chatmma
2. Click the green "Code" button
3. Click "Download ZIP"
4. Extract the ZIP file to your Desktop

### Step 2: Install Python
**Windows:**
1. Go to: https://www.python.org/downloads/
2. Click "Download Python"
3. Run the installer
4. **IMPORTANT**: Check the box "Add Python to PATH"
5. Click "Install Now"

**Mac:**
1. Open Terminal (press Command + Space, type "Terminal")
2. Type: `python3 --version`
3. If you see a version number, you're good!
4. If not, download from python.org

### Step 3: Set Up (One Time Only)

**Windows:**
1. Open the chatmma folder you extracted
2. Right-click empty space and choose "Open in Terminal" (or "Open PowerShell window here")
3. Type these commands (press Enter after each):
```
pip install streamlit anthropic pyyaml requests beautifulsoup4 youtube-transcript-api pandas plotly
python scripts/init_database.py
```

**Mac:**
1. Open Terminal
2. Type: `cd ~/Desktop/chatmma` (or wherever you extracted it)
3. Type these commands (press Enter after each):
```
pip3 install streamlit anthropic pyyaml requests beautifulsoup4 youtube-transcript-api pandas plotly
python3 scripts/init_database.py
```

### Step 4: Run the App

**Windows:**
In the same terminal window, type:
```
streamlit run streamlit_app.py
```

**Mac:**
In Terminal, type:
```
streamlit run streamlit_app.py
```

**Your web browser will automatically open!** 🎉

The app will be at: http://localhost:8501

---

## Using the App

### First Time Setup:
1. When the app opens, you'll see a sidebar on the left
2. It will ask for your Claude API key
3. Paste your API key: `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`
4. That's it! Now you can use the app

### Three Sections:

**💬 Chat Tab:**
- Type questions like: "Who wins UFC 323 main event?"
- Get instant answers with analyst predictions
- See which analysts are most accurate

**📊 Analytics Tab:**
- See rankings of all analysts
- View accuracy rates
- Track events and predictions

**⚙️ Process Event Tab:**
- Select an event (like "UFC 323")
- Click the buttons to:
  1. Fetch Content (downloads articles/videos)
  2. Extract Predictions (AI analyzes them)
  3. Load to Database (saves the data)

---

## Troubleshooting

### "streamlit is not recognized"
Try:
```
python -m pip install streamlit
```

### Can't find Terminal/PowerShell?
**Windows**: Press Windows Key + R, type `cmd`, press Enter
**Mac**: Press Command + Space, type `Terminal`, press Enter

### App won't open?
Make sure you're in the chatmma folder:
```
cd chatmma
```
Then try running again.

### Need Help?
Just message me! I'll walk you through it.

---

## Quick Reference

**Start the app:**
```
streamlit run streamlit_app.py
```

**Stop the app:**
Press `Ctrl + C` in the terminal

**Restart the app:**
Stop it, then run the start command again

---

That's it! You now have a full web interface for ChatMMA - no coding required! 🥊
