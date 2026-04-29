# 🎥 YouTube AI Summarizer

An intelligent web application that summarizes YouTube videos with **clickable timestamps**, **AI-powered insights**, and **interactive UI**.

---

## 🚀 Features

- 🔹 Extracts transcript from any YouTube video  
- 🔹 Generates concise summaries using AI (Transformers)  
- 🔹 Clickable timestamps → jump to exact moment in video  
- 🔹 Dark-themed modern UI  
- 🔹 Video rating (positive vs negative sentiment)  
- 🔹 Recommended videos section  

---

## 🧠 Tech Stack

- Python (Flask)
- Hugging Face Transformers
- YouTube Transcript API
- HTML + CSS (Custom UI)
- JavaScript (for interactivity)

---

## ⚙️ How It Works

1. User inputs YouTube link  
2. System extracts transcript  
3. Text is chunked and processed  
4. AI model generates summary  
5. Each summary is mapped to timestamps  
6. Results displayed in interactive UI  

---

## 📦 Installation (Run Locally)

```bash
git clone https://github.com/yourusername/Youtube_AI_Summarizer.git
cd Youtube_AI_Summarizer
python -m venv myvenv
myvenv\Scripts\activate
pip install -r requirements.txt
python app.py
