# Simplified Keystroke Dynamics System - User Guide

## 🎯 Overview

Your keystroke dynamics system now features a **clean, simplified interface** designed for ease of use while maintaining all powerful analysis features. This guide walks you through the new simplified workflow.

---

## 📋 What's New (Simplified Features)

### ✅ Combined Login/Register
- **Single page** for both login and registration
- Switch between **Login** and **Register** tabs easily
- No password required on signup (email optional)
- Password-based fallback authentication if models unavailable

### ✅ Optional Predictions
- Live statistics **always visible** as you type
- **"Analyze Pattern" button is optional** (not required)
- Type naturally without forcing analysis
- Results only show when you click to analyze

### ✅ Clean Dashboard
- Quick statistics at a glance
- Typing speed and consistency trends
- Session history with results
- No unnecessary technical details

### ✅ Simple Profile
- Account information in one place
- Your statistics summary
- Quick navigation to all features

---

## 🚀 Getting Started (5 Minutes)

### Step 1: Run the Application

```bash
# Make sure you're in the keystroke_project directory
python app_auth.py
```

Output:
```
 * Running on http://127.0.0.1:5000
```

Then open your browser to: **http://localhost:5000**

---

### Step 2: Create an Account

You'll see the **login page** with two tabs:

**📝 Register Tab:**
- **Username** (required) - your unique identifier
- **Password** (required) - your login password
- **Email** (optional) - can skip this

Click "Register" → You're now logged in!

**💡 Already have an account?** Use the "Login" tab instead.

---

### Step 3: Start Typing Analysis

1. Click **"⌨️ Analyze"** button in the header
2. You'll see **live statistics** that update as you type:
   - ⏱️ Duration
   - 📊 Typing Speed
   - ⏸️ Hold Time
   - 📈 Consistency Score

**You can stop here if you just want to see your typing metrics!**

---

### Step 4: Optional - Get Predictions

If you want to see stress analysis:

1. Type at least 3 characters naturally
2. Click **"📊 Optional: Analyze Pattern"**
3. See results:
   - 🤖 **Random Forest** prediction
   - ⚡ **XGBoost** prediction
   - 🎯 **Ensemble** prediction (recommended)
4. Each includes a confidence percentage

---

### Step 5: View Your History

1. Click **"📊 Dashboard"** in the header
2. See your statistics:
   - Total typing sessions
   - Average typing speed
   - Consistency score
   - Session distribution chart
3. View your recent sessions in the table

---

### Step 6: Check Your Profile

1. Click **"👤 Profile"** in the header
2. See your account information:
   - Username and email
   - Member since date
   - Account status
   - Your best statistics

---

## 🎮 Page Navigation

All pages have a **header with quick links**:

- **⌨️ Analyze** - Go to typing analyzer
- **📊 Dashboard** - View statistics and history
- **👤 Profile** - Manage your account
- **🚪 Logout** - Exit and go back to login

---

## 💾 Your Data

### Automatically Saved
Every time you use the typing analyzer:
- ✅ All keystrokes are analyzed
- ✅ Session metrics are calculated
- ✅ Results are saved to your account
- ✅ History appears in Dashboard

### Privacy
- Your data is **only visible to you**
- Requires login to access your sessions
- Sessions stored privately to your username

---

## 🔑 Password Fallback Mode

**What if the AI models fail?**

The system includes **password-based authentication** as a backup:
- Type your **username** and **password**
- If you don't have an account, it creates one automatically
- No need for the typing analysis to authenticate
- Always works, regardless of model status

---

## 📊 Understanding Your Results

### Live Statistics (Always Visible)

| Metric | Meaning |
|--------|---------|
| **Duration** | Total time you've been typing (seconds) |
| **Typing Speed** | Characters per second |
| **Hold Time** | Average key press duration (milliseconds) |
| **Consistency** | How regular your typing pattern is (0-100%) |

### Predictions (When You Click Analyze)

| Model | What It Does |
|-------|------------|
| **Random Forest** | Analyzes 200 decision trees of your pattern |
| **XGBoost** | Uses gradient boosting for pattern detection |
| **Ensemble** | Combines both models (most reliable) |

**Results:**
- 🟢 **Regular** (Low Stress) - Normal typing pattern
- 🔴 **Stressed** (High Stress) - Unusual typing pattern detected

Each result shows **confidence %** - how sure the model is.

---

## ⚙️ Customization Options

### Want to Adjust?

**Minimum typing characters before analysis:**
- Current: 3 characters
- Edit in: `templates/typing_simple.html` line ~180
- Change `if (keystrokeData.holdTimes.length < 3)` to any number

**Want to hide optional analysis button?**
- Edit in: `templates/typing_simple.html` 
- Remove or comment out the analyze button

**Want different colors?**
- Edit in: `static/style.css`
- Search for color codes like `#667eea` (purple), `#2ecc71` (green), `#e74c3c` (red)

---

## 🐛 Troubleshooting

### "Database already exists" error
- This is normal - delete `keystroke_db.db` and restart if needed

### Models not predicting correctly
- Models improve with more typing data
- 10+ sessions recommended for good patterns
- Try the **password authentication** as backup

### Predictions look weird
- Take longer typing samples (5+ seconds)
- Try typing naturally without stress
- Compare your "normal" vs "stressed" patterns

### Page won't load
- Make sure Flask is running: `python app_auth.py`
- Check browser console: Press F12, look for errors
- Verify port 5000 is not in use by another app

---

## 📁 File Structure

```
keystroke_project/
├── app_auth.py                    # Main application (run this)
├── templates/
│   ├── login_simple.html          # Login/Register page (combined)
│   ├── typing_simple.html         # Typing analyzer (optional analysis)
│   ├── dashboard_simple.html      # Your statistics
│   └── profile_simple.html        # Your profile
├── static/
│   └── style.css                  # All styling
├── keystroke_db.db                # Your data (created automatically)
├── outputs/models/                # Trained ML models
│   ├── stress_random_forest.pkl
│   ├── stress_xgboost.pkl
│   └── auth_models.pkl
└── datasets/                      # Training data
    └── content.csv
```

---

## 🔐 Security Notes

### Passwords
- Stored as SHA256 hashes (not plain text)
- Never shared or logged
- Reset by creating new account with same username

### Sessions
- Auto-expire after 7 days of inactivity
- Logout ends session immediately
- Delete account removes all your data permanently

### Data
- Stored locally in SQLite database
- Not uploaded anywhere
- Only accessible with your login

---

## 🎯 Quick Tips

1. **Build a baseline**: Type 5-10 times to establish your "normal" pattern
2. **Compare patterns**: Type once relaxed, once stressed - see the difference
3. **Check dashboard often**: Understand your typing trends
4. **Use password backup**: If you forget your typing pattern, just use password
5. **Longer sessions**: 5+ seconds of typing gives better analysis

---

## ❓ FAQ

### Q: Do I have to analyze every time I type?
**A:** No! Live statistics are always visible. Analysis is optional.

### Q: Can multiple people use this?
**A:** Yes! Each person registers their own account. Data is separate.

### Q: What if the models predict differently?
**A:** This is normal. Use the **Ensemble** prediction (combines both) as most reliable.

### Q: How accurate is the stress detection?
**A:** Depends on training data. Improves with more of your typing samples.

### Q: Can I export my data?
**A:** Currently saved in SQLite. Can be exported via Dashboard or direct database access.

---

## 📞 Support

**If something doesn't work:**

1. Check the console for errors (F12 in browser)
2. Restart Flask: `Ctrl+C` then `python app_auth.py`
3. Clear browser cache: Ctrl+Shift+Delete
4. Check `keystroke_project` folder exists with all files

---

## 🎉 You're All Set!

Your simplified keystroke dynamics system is ready to use:

✅ **Simple login** with one page  
✅ **Optional predictions** - analyze if you want  
✅ **Clean dashboard** - see your stats  
✅ **Secure** - password-backed authentication  
✅ **Fast** - live statistics update instantly  

Enjoy your keystroke analysis! 🎯

---

**Happy Typing!** ⌨️
