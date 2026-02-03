# MotionPitch - Cinematic Agentic Presentations

An AI-powered presentation generator using Google's Gemini 3 Pro, Gemini 3 Image, and Veo 3.1 models.

## Features

🧠 **Gemini 3 Pro (The Brain)**
- Advanced reasoning with thinking capabilities
- Google Search grounding for factual accuracy
- Code execution for mathematical precision
- Context caching for efficient repeated queries

🎨 **Gemini 3 Image (The Eyes)**
- High-quality 2K/4K image generation
- Brand-consistent visual generation
- Cinematic prompt engineering

🎥 **Veo 3.1 (The Motion)**
- Image-to-video generation
- 720p cinematic backgrounds
- 8-second video clips with audio

## Multi-Model Pipeline

| Model | Responsibility |
|-------|----------------|
| **Gemini 3 Pro** | Search Grounding, Code Execution, JSON orchestration |
| **Gemini 3 Image** | Brand-consistent visual generation |
| **Veo 3.1** | Image-to-video cinematic backgrounds |

## Installation

1. Navigate to the motionpitch directory:
```bash
cd motionpitch
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your environment variables:
```bash
cp .env.template .env
# Edit .env and add your GEMINI_API_KEY
```

4. Run the application:
```bash
python app.py
```

5. Open your browser to `http://localhost:5000`

## Getting Your API Key

1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create a new API key
3. Copy the key to your `.env` file
4. Hackthon testing team could use AIzaSyDJNMs88CBMrCDKwDhsw2JzcqO9CrjWY_U
   
## Architectural diagram

![Architectural Diagram](./static/ArchitecturalDiagram/architectural_image.png)

## Usage

1. Enter a topic for your presentation
2. (Optional) Add a URL for context or upload a PDF
3. Choose the number of slides
4. Enable Veo 3.1 for video on the first slide (adds ~60s processing time)
5. Click "Generate Presentation"

## Guest Mode

- Guests can generate up to 15 presentations
- Register for unlimited access

## Technologies

- **Backend**: Flask, Flask-SocketIO, SQLAlchemy
- **AI Models**: Google Gemini 3 Pro, Gemini 3 Image, Veo 3.1
- **Frontend**: Vanilla JavaScript, Socket.IO
- **Database**: SQLite

## Architecture

```
motionpitch/
├── app.py              # Main Flask application
├── static/
│   ├── css/           # Stylesheets
│   ├── js/            # JavaScript files
│   └── uploads/       # Generated images and videos
├── templates/         # HTML templates
├── requirements.txt   # Python dependencies
└── .env              # Environment variables (create from .env.template)
```

## License

MIT License - See LICENSE file for details

## Support

For issues or questions, please open an issue on GitHub.
