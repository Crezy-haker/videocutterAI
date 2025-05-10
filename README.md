# VideoCutterAI 🎬🤖

![Royal AI Video Highlights](https://images.unsplash.com/photo-1464983953574-0892a716854b?auto=format&fit=crop&w=1200&q=80)

**VideoCutterAI** is an AI-powered web tool that automatically finds and generates highlight clips from your videos. Upload a video, and let the app transcribe, analyze, and create beautiful highlight reels with AI-generated visuals and subtitles.

---

## Features

- 🎥 **Automatic Video Transcription** using OpenAI Whisper
- 🧠 **Highlight Detection** with Google Gemini AI
- ✂️ **Clip Generation** with smooth transitions
- 🖼️ **AI-generated Visuals** for each highlight
- 📝 **Burned-in Subtitles** for accessibility
- 💾 **Downloadable Highlight Clips**
- 🦾 **Modern Flask Web App**

---

## Royal & Modern UI

![Royal UI](https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=1200&q=80)

The interface is clean, modern, and inspired by royal blue and gold themes for a premium feel.

---

## Quickstart 🚀

1. **Clone the repo:**
   ```sh
   git clone https://github.com/yourusername/videocutterAI.git
   cd videocutterAI
   ```
2. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```
3. **Set up environment variables:**
   - Copy `.env.example` to `.env` and add your API keys:
     - `GOOGLE_API_KEY` (for Gemini)
     - `FLASK_SECRET_KEY` (any random string)
4. **Run the app:**
   ```sh
   python app.py
   ```
5. **Open in browser:**
   - Go to [http://localhost:5000](http://localhost:5000)

---

## Environment Variables

Create a `.env` file in the root directory:

```
GOOGLE_API_KEY=your_google_gemini_api_key
FLASK_SECRET_KEY=your_flask_secret_key
```

---

## Project Structure

```
├── app.py                # Flask app
├── video_processor.py    # AI video processing logic
├── requirements.txt      # Python dependencies
├── templates/            # HTML templates
├── static/               # CSS/JS/Images
├── uploads/              # Uploaded videos
├── clips/                # Generated highlight clips
├── transcripts/          # Video transcripts
├── .env.example          # Example environment file
├── .gitignore            # Git ignore rules
```

---

## Credits & Inspiration

- [Unsplash](https://unsplash.com/) for royalty-free images
- [OpenAI Whisper](https://github.com/openai/whisper)
- [Google Gemini](https://ai.google/discover/gemini/)
- [ffmpeg-python](https://github.com/kkroening/ffmpeg-python)

---

## License

MIT License. See [LICENSE](LICENSE) for details.
