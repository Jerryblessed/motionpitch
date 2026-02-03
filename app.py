import os
import json
import sys
import uuid
import time
import logging
from datetime import datetime, timedelta
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, as_completed

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, g
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image

# --- Import BaseModel for Structured Outputs ---
from pydantic import BaseModel

# --- GOOGLE GENAI SDK ---
from google import genai
from google.genai import types

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'hackathon_winner_secret_key_ultra')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///motionPitch_ultra.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# --- GEMINI SETUP ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY not found! Please set it in .env file")
    sys.exit(1)

client = genai.Client(api_key=GEMINI_API_KEY)

# MODEL MAPPINGS - Using Gemini 3 Series
MODEL_PRO = "gemini-3-pro-preview"
MODEL_FLASH = "gemini-3-flash-preview"
MODEL_IMAGE = "gemini-3-pro-image-preview"
MODEL_VIDEO = "veo-3.1-generate-preview"

# --- CACHING GLOBAL ---
cached_architect_name = None

# --- DATABASE MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    name = db.Column(db.String(100))
    presentations = db.relationship('Presentation', backref='owner', lazy=True)

class Presentation(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    title = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    slides_data = db.Column(db.JSON)
    has_video = db.Column(db.Boolean, default=False)

with app.app_context():
    db.create_all()

# --- AI SERVICES ---

class AIService:
    
    @staticmethod
    def get_cached_architect():
        """
        Implements CONTEXT CACHING for Gemini 3 Pro.
        """
        global cached_architect_name
        
        system_instruction = """
        You are an expert Presentation Architect utilizing the Gemini 3 Pro model capabilities.
        Your goal is to plan distinct, high-impact, cinematic presentations.

        # CORE OPERATIONAL RULES
        1. **Fact Checking:** ALWAYS use the Google Search tool to verify statistics, dates, and recent events.
        2. **Mathematical Precision:** Use the Code Execution tool for any calculations (financial projections, market growth percentages).
        3. **Context Awareness:** If a PDF is provided, analyze it deeply using File Search capabilities. If a URL is provided, browse it.

        # VISUAL PROMPT ENGINEERING (CRITICAL)
        When defining 'visual_prompt', do not simply describe the object. You must describe the CAMERA, LIGHTING, and STYLE.
        - **Bad:** "A picture of a robot."
        - **Good:** "Cinematic close-up of a humanoid robot's eye reflecting a neon city, 85mm lens, f/1.8, bokeh, cyberpunk aesthetic, volumetric lighting, hyper-realistic, 8k resolution."
        
        # VIDEO PROMPT ENGINEERING (Veo 3.1)
        When defining 'video_prompt', focus on MOTION and FLUIDITY.
        - **Bad:** "A car driving."
        - **Good:** "Drone shot tracking a red sports car speeding along a coastal highway at sunset, motion blur, lens flare, 4k, cinematic color grading."

        # SLIDE CONTENT STRUCTURE
        1. **The Hook (Slide 1):** Short, punchy title (<7 words). No subtext. Just impact.
        2. **The Problem:** Emotional connection, using data points (verified via Search).
        3. **The Solution:** Clear value proposition.
        4. **The Evidence:** Market data, graphs (describe the graph for the image generator).
        5. **The Climax:** A powerful call to action.

        # FEW-SHOT EXAMPLES (REFERENCE FOR STYLE)

        [Example 1: Topic "The Future of Space Travel"]
        Slide 1:
          Title: "Mars: The Next Harbor"
          Content: "Humanity is no longer earth-bound. The technology to colonize the red planet exists today."
          Visual: "Wide cinematic shot of the Starship rocket on a Martian launchpad, two moons visible in the sky, dusty red atmosphere, dramatic shadows."
          Video: "Slow pan upwards of a massive rocket engine igniting, dust billowing, raw power, 4k."

        [Example 2: Topic "Sustainable Fashion"]
        Slide 1:
          Title: "Fabric of the Future"
          Content: "The fashion industry produces 10% of global carbon emissions. Bio-textiles are the answer."
          Visual: "Macro photography of mushroom leather texture, soft natural lighting, green and brown earth tones, high detail."

        [Example 3: Topic "Quantum Computing"]
        Slide 1:
          Title: "Beyond Binary"
          Content: "Traditional computers think in 0s and 1s. Quantum computers think in infinite possibilities."
          Visual: "Abstract representation of a qubit, glowing gold and blue energy strands, dark background, futuristic visualization."

        # FINAL INSTRUCTIONS
        - Ensure the tone is professional yet visionary (like a TED Talk).
        - Avoid corporate jargon.
        - If the user asks for a specific slide count, adhere to it strictly.
        - Ensure every slide has a unique visual prompt.
        """
        
        if not cached_architect_name:
            try:
                cache = client.caches.create(
                    model=MODEL_PRO,
                    config=types.CreateCachedContentConfig(
                        contents=[system_instruction],
                        ttl="3600s"
                    )
                )
                cached_architect_name = cache.name
                logger.info(f"✅ Created Context Cache: {cache.name}")
            except Exception as e:
                logger.warning(f"Cache creation failed (using standard prompt): {e}")
                return None 
        return cached_architect_name

    @staticmethod
    def generate_image(prompt, slide_index):
        """Generate image using Gemini 3 Pro Image (Nano Banana Pro)"""
        try:
            logger.info(f"🎨 Generating image for slide {slide_index + 1}")
            
            response = client.models.generate_content(
                model=MODEL_IMAGE,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=['IMAGE'],
                    image_config=types.ImageConfig(
                        aspect_ratio="16:9",
                        image_size="2K"
                    )
                )
            )

            # Extract image from response
            image_parts = [part for part in response.parts if part.inline_data]
            
            if not image_parts:
                logger.error(f"No image generated for slide {slide_index + 1}")
                return slide_index, None, None
            
            # Convert to PIL Image and save
            img = image_parts[0].as_image()
            filename = f"img_{uuid.uuid4()}.png"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            img.save(filepath)
            
            logger.info(f"✅ Image saved: {filename}")
            return slide_index, filename, filepath

        except Exception as e:
            logger.error(f"Image Generation Error for slide {slide_index + 1}: {e}")
            return slide_index, None, None

    @staticmethod
    def generate_video(image_path, prompt):
        """Generate video using Veo 3.1"""
        try:
            logger.info(f"🎥 Starting video generation with Veo 3.1")
            
            # Read the image file
            with open(image_path, "rb") as f:
                image_bytes = f.read()
            
            # Create image input for Veo
            image_input = types.Image(image_bytes=image_bytes, mime_type='image/png')
            
            # Generate video with Veo 3.1
            operation = client.models.generate_videos(
                model=MODEL_VIDEO,
                prompt=f"Cinematic 4k. {prompt}",
                image=image_input,
                config=types.GenerateVideosConfig(
                    aspect_ratio="16:9",
                    resolution="720p",
                    duration_seconds=8
                )
            )
            
            # Poll until video is ready
            logger.info("⏳ Waiting for video generation to complete...")
            poll_count = 0
            max_polls = 120  # 10 minutes max
            
            while not operation.done and poll_count < max_polls:
                time.sleep(5)
                operation = client.operations.get(operation)
                poll_count += 1
                
                if poll_count % 6 == 0:  # Log every 30 seconds
                    logger.info(f"Still generating video... ({poll_count * 5}s elapsed)")
            
            if not operation.done:
                logger.error("Video generation timeout")
                return None
            
            # Check if video was generated
            if not operation.response or not operation.response.generated_videos:
                logger.error("No video in response")
                return None
            
            # Download the video
            video_obj = operation.response.generated_videos[0]
            filename = f"veo_{uuid.uuid4()}.mp4"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Download video using the client
            client.files.download(file=video_obj.video, file_path=filepath)
            
            logger.info(f"✅ Video saved: {filename}")
            return url_for('static', filename=f'uploads/{filename}', _external=True)
            
        except Exception as e:
            logger.error(f"Video Generation Error: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    @staticmethod
    def plan_presentation(topic, slide_count, pdf_path=None, url_link=None):
        """Plan presentation using Gemini 3 Pro with Search and Code Execution"""
        logger.info(f"🧠 Planning with Gemini 3 Pro (Thinking + Search + Tools)...")
        
        # Define structured output schema
        class Slide(BaseModel):
            title: str
            content: str
            visual_prompt: str
            video_prompt: str

        class PresentationSchema(BaseModel):
            title: str
            slides: list[Slide]

        # Configure tools
        tools = [
            types.Tool(google_search=types.GoogleSearch()), 
            types.Tool(code_execution=types.ToolCodeExecution()) 
        ]
        
        # Construct prompt
        contents = []
        user_prompt = f"Topic: {topic}. Length: {slide_count} slides."
        
        if url_link:
            user_prompt += f"\n\nContext URL: {url_link} (Browse this site for content)."
        
        if pdf_path:
            # Upload file for Gemini Native File Search
            try:
                file_ref = client.files.upload(path=pdf_path)
                while file_ref.state.name == "PROCESSING":
                    time.sleep(1)
                    file_ref = client.files.get(name=file_ref.name)
                contents.append(file_ref)
                user_prompt += "\n\nRefer to the uploaded PDF file for facts."
            except Exception as e:
                logger.error(f"PDF upload failed: {e}")

        contents.append(user_prompt)

        # Use cached system prompt if available
        cached_name = AIService.get_cached_architect()
        
        try:
            response = client.models.generate_content(
                model=MODEL_PRO,
                contents=contents,
                config=types.GenerateContentConfig(
                    tools=tools,
                    response_mime_type="application/json",
                    response_schema=PresentationSchema.model_json_schema(),
                    cached_content=cached_name,
                    thinking_config=types.ThinkingConfig(thinking_level="high")
                )
            )
            
            return json.loads(response.text)
            
        except Exception as e:
            logger.error(f"Planning Error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

# --- HELPERS ---
@app.before_request
def load_user():
    g.user = None
    if 'user_id' in session: 
        g.user = db.session.get(User, session['user_id'])

def guest_limit_check(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user: 
            return f(*args, **kwargs)
        usage = session.get('guest_usage', 0)
        if usage >= 15: 
            return jsonify({'success': False, 'error': 'Guest limit reached (15). Please Register!'}), 403
        return f(*args, **kwargs)
    return decorated_function

# --- ROUTES ---

@app.route('/')
def index():
    my_pres = []
    if g.user: 
        my_pres = Presentation.query.filter_by(user_id=g.user.id).order_by(Presentation.created_at.desc()).all()
    return render_template('index.html', user=g.user, guest_usage=session.get('guest_usage', 0), presentations=my_pres)

@app.route('/register', methods=['POST'])
def register():
    data = request.form
    if User.query.filter_by(email=data['email']).first(): 
        return "Email taken <a href='/'>Back</a>"
    hashed = generate_password_hash(data['password'])
    user = User(email=data['email'], name=data['name'], password_hash=hashed)
    db.session.add(user)
    db.session.commit()
    session['user_id'] = user.id
    return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
def login():
    data = request.form
    user = User.query.filter_by(email=data['email']).first()
    if user and check_password_hash(user.password_hash, data['password']):
        session['user_id'] = user.id
        return redirect(url_for('index'))
    return "Invalid <a href='/'>Back</a>"

@app.route('/logout')
def logout(): 
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/generate', methods=['POST'])
@guest_limit_check
def generate():
    topic = request.form.get('topic')
    slide_count = int(request.form.get('slide_count', 3))
    enable_video = request.form.get('enable_video') == 'true'
    url_link = request.form.get('url_link')
    pdf_file = request.files.get('pdf_file')
    
    if not g.user: 
        session['guest_usage'] = session.get('guest_usage', 0) + 1

    pdf_path = None
    if pdf_file and pdf_file.filename:
        filename = secure_filename(f"doc_{uuid.uuid4()}.pdf")
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        pdf_file.save(pdf_path)

    # 1. PLAN
    socketio.emit('log', {'msg': f'🧠 Gemini 3 Pro (Thinking): Planning deck...'})
    if url_link: 
        socketio.emit('log', {'msg': f'🌐 Browsing URL Context: {url_link}'})
    if pdf_path: 
        socketio.emit('log', {'msg': f'📂 Analyzing PDF File Content...'})

    plan = AIService.plan_presentation(topic, slide_count, pdf_path, url_link)
    
    if not plan: 
        return jsonify({'success': False, 'error': 'Planning Failed'}), 500

    slides = [None] * len(plan['slides'])
    
    # 2. BATCH IMAGE GENERATION
    socketio.emit('log', {'msg': f'⚡ Starting Parallel Image Generation (Batch Mode)...'})
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_slide = {
            executor.submit(AIService.generate_image, s['visual_prompt'], i): s 
            for i, s in enumerate(plan['slides'])
        }
        
        for future in as_completed(future_to_slide):
            idx, img_url, local_path = future.result()
            s_data = plan['slides'][idx]
            
            if img_url is None:
                # Generate a placeholder if image generation failed
                img_url = 'placeholder.png'
                media_type = 'image'
            else:
                media_url = url_for('static', filename=f'uploads/{img_url}', _external=True)
                media_type = 'image'
                
                socketio.emit('log', {'msg': f'🎨 Slide {idx+1}: Image Ready.'})

                # Video generation for first slide only
                if enable_video and idx == 0 and s_data.get('video_prompt') and local_path:
                    socketio.emit('log', {'msg': f'🎥 Slide {idx+1}: Veo 3.1 Animating (Wait ~60s)...'})
                    video_url = AIService.generate_video(local_path, s_data['video_prompt'])
                    if video_url:
                        media_url = video_url
                        media_type = 'video'
                        socketio.emit('log', {'msg': f'✅ Slide {idx+1}: Video Complete!'})

            slides[idx] = {
                'title': s_data['title'],
                'content': s_data['content'],
                'media_url': media_url if img_url else url_for('static', filename='placeholder.png'),
                'media_type': media_type
            }

    # 3. SAVE
    new_pres = Presentation(
        id=str(uuid.uuid4()),
        title=plan['title'],
        slides_data=slides,
        user_id=g.user.id if g.user else None,
        has_video=enable_video
    )
    db.session.add(new_pres)
    db.session.commit()
    
    socketio.emit('log', {'msg': '🚀 Generation Complete! Redirecting...'})
    return jsonify({'success': True, 'redirect': url_for('viewer', pid=new_pres.id)})

@app.route('/viewer/<pid>')
def viewer(pid):
    pres = db.session.get(Presentation, pid)
    if not pres: 
        return "Not Found", 404
    return render_template('viewer.html', pres=pres)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
