# === app.py ===
from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
import pandas as pd
import os
import joblib
import requests
import smtplib
from email.message import EmailMessage

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

app = Flask(__name__)
app.secret_key = 'your_secret_key'

MODEL_PATH = 'model.pkl'
DATASET_PATH = 'cyberbullying_dataset_2025.csv'
USERS_PATH = 'users.csv'
YOUTUBE_API_KEY = 'AIzaSyCrGEFYNsHAMZhAaRd06VT79BzfVMz3q6c'  

EMAIL_SENDER = 'anujnaanujna398@gmail.com'
EMAIL_PASSWORD = 'hgvf mmaz hhpn kfrl'  

# --- CALM REPLIES ---
CALM_REPLIES = {
    "dumb": "Everyone has strengths. Let’s support each other.",
    "idiot": "We all make mistakes, but respect goes a long way.",
    "stupid": "Let’s stay constructive instead of name-calling.",
    "trash": "Let’s agree to disagree respectfully.",
    "ugly": "Looks don’t define worth. Let’s spread kindness.",
    "worthless": "That’s harsh. Everyone deserves compassion.",
    "delete yourself": "Let’s aim to be constructive rather than hurtful.",
    "pathetic": "We all struggle sometimes. Let's support each other.",
    "nobody wants you": "Everyone deserves to feel included.",
    "broken": "Let’s aim to build each other up, not tear down.",
    "wasting space": "Thanks for engaging. I’m always trying to improve.",
    "don’t ever post again": "Everyone deserves to express themselves.",
    "everything is stupid": "Let’s try to keep things thoughtful and helpful.",
    "loser": "Labels don’t define people. Everyone has value.",
    "hate you": "It’s better to share thoughts respectfully.",
    "shut up": "Everyone has the right to express themselves calmly.",
    "kill yourself": "That’s dangerous talk. Let’s be kinder with our words.",
    "disgusting": "Everyone deserves kindness and respect.",
    "clown": "We all have different styles — respect matters."

}

# --- Train model if not present ---
if not os.path.exists(MODEL_PATH):
    df = pd.read_csv(DATASET_PATH, encoding='latin1')
    vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
    X = vectorizer.fit_transform(df['content'])
    y = df['label']
    model = LogisticRegression(max_iter=200, random_state=42)
    model.fit(X, y)
    joblib.dump((vectorizer, model), MODEL_PATH)

# --- Ensure users file exists ---
if not os.path.exists(USERS_PATH):
    pd.DataFrame(columns=['email', 'password']).to_csv(USERS_PATH, index=False)

# --- Email report function ---
def send_report_email(recipient_email):
    msg = EmailMessage()
    msg['Subject'] = 'Your Cyberbullying Detection Report'
    msg['From'] = EMAIL_SENDER
    msg['To'] = recipient_email
    msg.set_content('Here is your Cyber-Bullying detection report attached.')

    with open('report.csv', 'rb') as f:
        msg.add_attachment(f.read(), maintype='application', subtype='octet-stream', filename='report.csv')

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
        smtp.send_message(msg)

# --- ROUTES ---

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        df = pd.read_csv(USERS_PATH)
        if not df[(df['email'] == email) & (df['password'] == password)].empty:
            session['user'] = email
            return redirect(url_for('home'))
        return render_template('login.html', error="❌ Invalid login credentials.")
    return render_template('login.html')

@app.route('/signup', methods=['POST'])
def signup():
    email = request.form['email']
    password = request.form['password']
    confirm = request.form['confirm_password']
    if password != confirm:
        return render_template('login.html', error="❌ Passwords do not match.")
    df = pd.read_csv(USERS_PATH)
    if email in df['email'].values:
        return render_template('login.html', error="❌ Email already exists.")
    pd.DataFrame([[email, password]], columns=['email', 'password']).to_csv(USERS_PATH, mode='a', header=False, index=False)
    return render_template('login.html', success="✅ Signup successful!")

@app.route('/home', methods=['GET', 'POST'])
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    result, level, detected_comments = "", "", []
    if request.method == 'POST':
        input_text = request.form.get('input_text')
        comments = [c.strip() for c in input_text.split('\n') if c.strip()]
        vectorizer, model = joblib.load(MODEL_PATH)
        preds = model.predict(vectorizer.transform(comments))
        for comment, prediction in zip(comments, preds):
            if prediction == 1:
                suggestion = next((r for k, r in CALM_REPLIES.items() if k in comment.lower()), "Try to respond positively.")
                detected_comments.append((comment, "Manual Entry", suggestion))
        level = 'high' if detected_comments else 'none'
        result = f"🔴 {len(detected_comments)} Unsafe Comment(s) Detected" if detected_comments else "✅ All comments are safe"
        if detected_comments:
            pd.DataFrame(detected_comments, columns=["Comment", "Source", "Suggested Reply"]).to_csv('report.csv', index=False)
            send_report_email(session['user'])
            flash("📧 Email report sent successfully.")
    return render_template('home.html', result=result, level=level, unsafe_comments=detected_comments)

@app.route('/download_report')
def download_report():
    if os.path.exists('report.csv'):
        return send_file('report.csv', as_attachment=True)
    return "❌ No report found. Please analyze comments first."

@app.route('/instagram', methods=['GET', 'POST'])
def instagram():
    if 'user' not in session:
        return redirect(url_for('login'))
    comments, result, level, unsafe_comments = [], "", "", []
    if request.method == 'POST':
        fake_comments = [
            "You're amazing!", "This is trash content.", "Nobody wants to see you post.",
            "Delete yourself from the internet.", "So inspiring!", "Dumbest video ever."
        ]
        vectorizer, model = joblib.load(MODEL_PATH)
        preds = model.predict(vectorizer.transform(fake_comments))
        for comment, pred in zip(fake_comments, preds):
            if pred == 1:
                suggestion = next((r for k, r in CALM_REPLIES.items() if k in comment.lower()), "Try to respond positively.")
                unsafe_comments.append((comment, "Instagram", suggestion))
                comments.append((comment, "Unsafe", suggestion))
            else:
                comments.append((comment, "Safe", ""))
        result = f"Analyzed {len(fake_comments)} comments."
        level = 'high' if any(p == 1 for p in preds) else 'none'
        if unsafe_comments:
            pd.DataFrame(unsafe_comments, columns=["Comment", "Source", "Suggested Reply"]).to_csv('report.csv', index=False)
            send_report_email(session['user'])
            flash("📧 Email report sent successfully.")
    return render_template('instagram.html', comments=comments, result=result, level=level, unsafe_comments=unsafe_comments)

@app.route('/twitter', methods=['GET', 'POST'])
def twitter():
    if 'user' not in session:
        return redirect(url_for('login'))

    tweet_url = ""
    comments, result, level, unsafe_comments = [], "", "", []

    if request.method == 'POST':
        tweet_url = request.form.get('tweet_url', '')
        fake_tweets = [
            "you are pathetici have seen seen.",
            "You're an inspiration!",  
            "Nobody wants to hear from you again.",
            "You are role model for youth.",
            "Wow, brilliant insight!", 
            "We are lucky to have you sir as PM."
        ]
        vectorizer, model = joblib.load(MODEL_PATH)
        preds = model.predict(vectorizer.transform(fake_tweets))

        for comment, pred in zip(fake_tweets, preds):
            if pred == 1:
                suggestion = next((reply for keyword, reply in CALM_REPLIES.items() if keyword.lower() in comment.lower()), "Try to respond positively.")
                unsafe_comments.append((comment, "Twitter", suggestion))
                comments.append((comment, "Unsafe", suggestion))
            else:
                comments.append((comment, "Safe", "✅ No issue"))

        result = f"Analyzed {len(fake_tweets)} tweets."
        level = 'high' if unsafe_comments else 'none'

        if unsafe_comments:
            pd.DataFrame(unsafe_comments, columns=["Comment", "Source", "Suggested Reply"]).to_csv('report.csv', index=False)
            send_report_email(session['user'])
            flash("📧 Email report sent successfully.")

    return render_template('twitter.html', tweet_url=tweet_url, comments=comments, result=result, level=level, unsafe_comments=unsafe_comments)

@app.route('/youtube', methods=['GET', 'POST'])
def youtube():
    if 'user' not in session:
        return redirect(url_for('login'))

    comments, result, level, unsafe_comments = [], "", "", []

    if request.method == 'POST':
        video_input = request.form.get('video_id', '').strip()
        if 'v=' in video_input:
            video_id = video_input.split('v=')[1].split('&')[0]
        elif 'youtu.be/' in video_input:
            video_id = video_input.split('youtu.be/')[1].split('?')[0]
        elif 'shorts/' in video_input:
            video_id = video_input.split('shorts/')[1].split('?')[0]
        else:
            video_id = video_input

        try:
            url = f"https://www.googleapis.com/youtube/v3/commentThreads?part=snippet&textFormat=plainText&videoId={video_id}&key={YOUTUBE_API_KEY}&maxResults=50"
            response = requests.get(url)
            data = response.json()
            if 'items' not in data:
                raise ValueError(str(data))
            raw_comments = [item['snippet']['topLevelComment']['snippet']['textDisplay'] for item in data['items']]
            vectorizer, model = joblib.load(MODEL_PATH)
            preds = model.predict(vectorizer.transform(raw_comments))
            for comment, pred in zip(raw_comments, preds):
                if pred == 1:
                    suggestion = next((r for k, r in CALM_REPLIES.items() if k in comment.lower()), "Try responding positively.")
                    unsafe_comments.append((comment, "Unsafe", suggestion))
                    comments.append((comment, "Unsafe", suggestion))
                else:
                    comments.append((comment, "Safe", "✅"))
            result = f"✅ Analyzed {len(raw_comments)} comments."
            level = 'high' if unsafe_comments else 'none'
            if unsafe_comments:
                pd.DataFrame(unsafe_comments, columns=["Comment", "Source", "Suggested Reply"]).to_csv('report.csv', index=False)
                send_report_email(session['user'])
                flash("📧 Email report sent successfully.")
        except Exception as e:
            result = f"❌ Error: {str(e)}"
            level = 'high'

    return render_template('youtube.html', comments=comments, result=result, level=level, unsafe_comments=unsafe_comments)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, port=8000)
