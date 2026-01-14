# CSV Loading Guide for ChatMMA

## Current Status

✅ **The Streamlit app is now live with sample data!**
- Visit: https://chatmma.streamlit.app
- Sample database includes 7 analysts and 16 predictions
- This allows you to test the chatbot while preparing your real data

## Loading Your Own Data

When you're ready to load your own CSV with 10 analysts and 13 fights (130 predictions), follow these steps:

### Step 1: Prepare Your CSV

Your CSV should have these columns:
```
date, analyst, platform, event, location, fight, weight class, pick, context
```

Example row:
```csv
2025-01-18,Alexander K. Lee,MMA Fighting,UFC Vegas 112,Las Vegas,Manel Kape vs Brandon Royval,Flyweight,Manel Kape,Kape's wrestling will control the fight
```

### Step 2: Run the Loader Script

1. **Save your CSV** as `ChatMMAPredictions.csv` in the chatmma directory
2. **Run the script** in Terminal:
   ```bash
   cd /path/to/chatmma
   python3 load_csv_fixed.py
   ```
3. **Check output** - you should see:
   ```
   ✓ Alexander K. Lee: Manel Kape for Manel Kape vs Brandon Royval
   ✓ Drake Riggs: Brandon Royval for Manel Kape vs Brandon Royval
   ...
   All data loaded!
   ```

The script handles:
- UTF-8 encoding issues from Numbers/Excel exports
- Creating events, fights, analysts, and predictions
- Mapping fighter names to picks automatically

### Step 3: Upload to GitHub

1. **Upload the database** to GitHub:
   - Go to https://github.com/sorarebaron/chatmma
   - Navigate to `data/` folder
   - Upload the new `chatmma.db` file (will replace the sample)
   - Commit with message: "Update database with real predictions"

2. **Wait 2 minutes** for Streamlit to redeploy automatically

3. **Test the chatbot** at https://chatmma.streamlit.app
   - Ask: "How many analysts do we have?"
   - Should say: "10 analysts"
   - Ask about a specific fight to see consensus

## Troubleshooting

### CSV Encoding Errors

If you get `csv.Error: line contains NUL` or encoding errors:
- The script already handles most encoding issues with `utf-8-sig` and `errors='ignore'`
- If it still fails, try re-exporting from Numbers as "CSV (UTF-8)"
- Or open the CSV in a text editor and save as UTF-8

### Pick Matching Issues

The script matches picks to fighters by checking if the fighter name appears in the pick column:
- "Manel Kape" → matches fighter_a if fighter_a is "Manel Kape"
- Works with partial matches too

If a pick can't be matched, you'll see:
```
Warning: Cannot match pick 'John Doe' to Manel Kape vs Brandon Royval
```

Just fix the pick name in your CSV and run the script again.

### Database Not Updating on Streamlit

After uploading to GitHub:
1. Wait 2 full minutes for redeploy
2. Hard refresh the browser (Cmd+Shift+R or Ctrl+F5)
3. Check if database updated by asking the chatbot

## Alternative: Use the Standalone Script

If you prefer, you can also use `create_db_standalone.py`:
1. Edit the script to add your real data (replace the sample data section)
2. Run: `python3 create_db_standalone.py`
3. Upload resulting `data/chatmma.db` to GitHub

## Need Help?

The sample database is working now, so you can test the chatbot functionality while you prepare your real CSV data. When ready, follow the steps above to load your 10 analysts and 13 fights.
