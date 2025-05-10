from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
import os
from werkzeug.utils import secure_filename
import sqlite3
from datetime import datetime
from video_processor import VideoProcessor
import threading
from dotenv import load_dotenv

def adapt_datetime(ts):
    return ts.isoformat()

def convert_datetime(val):
    return datetime.fromisoformat(val)

# Register the adapter and converter
sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("datetime", convert_datetime)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev')  # Change this in production
app.config['UPLOAD_FOLDER'] = os.path.abspath('uploads')
app.config['CLIPS_FOLDER'] = os.path.abspath('clips')
app.config['TRANSCRIPTS_FOLDER'] = os.path.abspath('transcripts')
app.config['DATABASE'] = os.path.abspath('videos.db')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'mp4', 'avi', 'mov', 'mkv'}

# Create required directories if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['CLIPS_FOLDER'], exist_ok=True)
os.makedirs(app.config['TRANSCRIPTS_FOLDER'], exist_ok=True)

# Database initialization
def init_db():
    conn = sqlite3.connect(app.config['DATABASE'], detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS videos
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  filename TEXT,
                  upload_date DATETIME,
                  status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS clips
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  video_id INTEGER,
                  clip_path TEXT,
                  start_time REAL,
                  end_time REAL,
                  description TEXT,
                  FOREIGN KEY(video_id) REFERENCES videos(id))''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('upload.html')

# Add after init_db()
@app.route('/upload', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return redirect(url_for('index'))
    
    file = request.files['video']
    if file.filename == '':
        return redirect(url_for('index'))
    
    if not allowed_file(file.filename):
        flash('File type not allowed')
        return redirect(url_for('index'))
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
      # Store in database
    conn = sqlite3.connect(app.config['DATABASE'], detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    c.execute('INSERT INTO videos (filename, upload_date, status) VALUES (?, ?, ?)',
              (filename, datetime.now(), 'uploaded'))
    video_id = c.lastrowid
    conn.commit()
    conn.close()
    
    # Start background processing
    processor = VideoProcessor()
    threading.Thread(target=process_video_background, args=(video_id, filepath)).start()
    
    return redirect(url_for('status', video_id=video_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def process_video_background(video_id, filepath):
    conn = sqlite3.connect(app.config['DATABASE'], detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    
    def update_status(status):
        c.execute('UPDATE videos SET status=? WHERE id=?', (status, video_id))
        conn.commit()
    
    try:
        update_status('initializing')
        
        try:
            processor = VideoProcessor()
        except Exception as e:
            update_status(f'error: Failed to initialize video processor: {str(e)}')
            return
            
        update_status('transcribing')
        
        try:
            clips = processor.process_video(filepath)
        except Exception as e:
            update_status(f'error: Failed to process video: {str(e)}')
            return
            
        update_status('saving_clips')
        
        # Store clips in database
        for clip in clips:
            try:
                c.execute('''INSERT INTO clips 
                           (video_id, clip_path, start_time, end_time, description)
                           VALUES (?, ?, ?, ?, ?)''',
                         (video_id, clip['path'], clip['start'], 
                          clip['end'], clip['description']))
            except Exception as e:
                update_status(f'error: Failed to save clip: {str(e)}')
                return
        
        update_status('processed')
        conn.commit()
        
    except Exception as e:
        update_status(f'error: Unexpected error: {str(e)}')
    finally:
        conn.close()

@app.route('/status/<int:video_id>')
def status(video_id):
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    c.execute('SELECT v.status, v.filename FROM videos v WHERE v.id=?', (video_id,))
    result = c.fetchone()
    
    if not result:
        return {'status': 'unknown'}
    
    status, filename = result
    
    if status == 'processed':
        c.execute('SELECT COUNT(*) FROM clips WHERE video_id=?', (video_id,))
        clip_count = c.fetchone()[0]
        return {
            'status': status,
            'filename': filename,
            'clips': clip_count,
            'redirect': url_for('dashboard', video_id=video_id)
        }
    
    return {'status': status, 'filename': filename}

@app.route('/clips/<path:filename>')
def serve_clip(filename):
    return send_from_directory(app.config['CLIPS_FOLDER'], filename)

# Add after status route
@app.route('/dashboard/<int:video_id>')
def dashboard(video_id):
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    
    # Get video info
    c.execute('SELECT * FROM videos WHERE id=?', (video_id,))
    video = c.fetchone()
    
    if not video:
        flash('Video not found', 'error')
        return redirect(url_for('index'))
    
    # Get clips
    c.execute('SELECT * FROM clips WHERE video_id=?', (video_id,))
    clips = c.fetchall()
    
    # Convert clip paths to URLs
    formatted_clips = []
    for clip in clips:
        clip_filename = os.path.basename(clip[2])
        clip_url = url_for('serve_clip', filename=clip_filename)
        formatted_clips.append({
            'id': clip[0],
            'video_id': clip[1],
            'url': clip_url,
            'start_time': clip[3],
            'end_time': clip[4],
            'description': clip[5]
        })
    
    conn.close()
    
    return render_template('dashboard.html', 
                          video=video,
                          clips=formatted_clips)

if __name__ == '__main__':
    app.run(debug=True)