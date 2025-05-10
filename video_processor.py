# filepath: c:\Users\Hariom kumar\Desktop\videocutterAI\video_processor.py
import os
import time
import whisper
from google.generativeai import configure, GenerativeModel
import ffmpeg
import sqlite3
from datetime import datetime

class VideoProcessor:
    def __init__(self, clips_folder='clips'):
        max_retries = 3
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            try:
                print(f"Attempting to load Whisper model (attempt {retry_count + 1}/{max_retries})...")
                # Load model with specific configurations for CPU
                self.transcription_model = whisper.load_model(
                    name="base",
                    device="cpu",
                    download_root=os.path.join(os.path.expanduser("~"), ".cache", "whisper")
                )
                break
            except Exception as e:
                last_error = str(e)
                retry_count += 1
                print(f"Error loading model: {str(e)}")
                if retry_count < max_retries:
                    print("Retrying in 5 seconds...")
                    time.sleep(5)
        
        if retry_count == max_retries:
            raise Exception(f"Failed to load Whisper model after {max_retries} attempts. Last error: {last_error}")
        
        try:
            configure(api_key=os.getenv('GOOGLE_API_KEY'))
            self.gemini = GenerativeModel('gemini-2.0-flash')
        except Exception as e:
            raise Exception(f"Failed to initialize Gemini: {str(e)}")
            
        self.clips_folder = clips_folder
    
    def process_video(self, video_path):
        print("Starting video transcription...")
        transcript = self.transcribe_video(video_path)
        
        print("Analyzing highlights...")
        highlights = self.analyze_highlights(transcript)
        
        print("Generating clips...")
        clips = self.generate_clips(video_path, highlights)
        
        return clips
    
    def transcribe_video(self, video_path):
        # Configure transcription options for CPU
        options = {
            'fp16': False,  # Disable FP16 since we're on CPU
            'language': 'en',  # Set to English for better performance
            'task': 'transcribe',
            'beam_size': 3,  # Lower beam size for faster processing
            'best_of': 3,    # Lower best_of for faster processing
        }
        result = self.transcription_model.transcribe(video_path, **options)
        return result['text']
    
    def analyze_highlights(self, transcript):
        prompt = f"""Analyze this video transcript and identify 5 most highlight-worthy moments. 
        For each highlight, provide exact timestamp in [MM:SS] format and a brief, engaging description.
        Format each highlight as: [MM:SS] Description
        Example: [02:15] Key point about technology impact
        Transcript: {transcript}"""
        
        try:
            response = self.gemini.generate_content(prompt)
            return self.parse_gemini_response(response.text)
        except Exception as e:
            print(f"Error analyzing highlights: {str(e)}")
            # Return empty list in case of error
            return []
    
    def parse_gemini_response(self, response_text):
        highlights = []
        lines = [line.strip() for line in response_text.split('\n') if line.strip()]
        
        for line in lines:
            if ']' in line and '[' in line:
                try:
                    time_part = line[line.find('[')+1:line.find(']')]
                    description = line[line.find(']')+1:].strip()
                    
                    if ':' in time_part:
                        mins, secs = map(float, time_part.split(':'))
                        start_time = mins * 60 + secs
                        # Make clips 30 seconds for better highlight focus
                        end_time = start_time + 30
                        
                        highlights.append({
                            'start': max(0, start_time - 5),  # Start 5 seconds before the highlight
                            'end': min(end_time, start_time + 30),  # Maximum 30 seconds
                            'description': description
                        })
                except Exception as e:
                    print(f"Error parsing highlight: {str(e)}")
                    continue
                    
        return highlights[:5]  # Return top 5 highlights
    
    def generate_clips(self, video_path, highlights):
        if not highlights:
            print("No highlights found to generate clips")
            return []
        clips = []
        for i, highlight in enumerate(highlights, 1):
            try:
                output_path = os.path.join(self.clips_folder, f"clip_{i}_{datetime.now().timestamp():.0f}.mp4")
                print(f"Generating clip {i}/{len(highlights)}: {highlight['description'][:50]}...")
                start = float(highlight['start'])
                duration = float(highlight['end'] - highlight['start'])
                # 1. Extract the video segment
                segment_path = os.path.join(self.clips_folder, f"segment_{i}_{datetime.now().timestamp():.0f}.mp4")
                (
                    ffmpeg
                    .input(video_path, ss=start, t=duration)
                    .output(segment_path, acodec='aac', vcodec='libx264', preset='fast', strict='experimental')
                    .overwrite_output()
                    .run(quiet=True)
                )
                # 2. Generate an AI image for the highlight (simulate with Gemini text-to-image if available, else use a placeholder)
                ai_image_path = os.path.join(self.clips_folder, f"ai_image_{i}_{datetime.now().timestamp():.0f}.png")
                try:
                    # If you have an AI image API, call it here. For now, use ffmpeg to create a blank image with text.
                    ai_text = highlight.get('ai_text', highlight['description'])
                    ffmpeg.input('color=white:s=640x360', f='lavfi', t=2).drawtext(
                        text=ai_text,
                        fontfile='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
                        fontsize=24,
                        fontcolor='black',
                        x='(w-text_w)/2',
                        y='(h-text_h)/2'
                    ).output(ai_image_path, vframes=1).overwrite_output().run(quiet=True)
                except Exception as e:
                    print(f"Error generating AI image: {str(e)}")
                    ai_image_path = None
                # 3. Convert AI image to a short video
                ai_video_path = os.path.join(self.clips_folder, f"ai_video_{i}_{datetime.now().timestamp():.0f}.mp4")
                if ai_image_path:
                    (
                        ffmpeg.input(ai_image_path, loop=1, t=2)
                        .output(ai_video_path, vcodec='libx264', pix_fmt='yuv420p')
                        .overwrite_output()
                        .run(quiet=True)
                    )
                # 4. Concatenate AI video and segment
                concat_list = os.path.join(self.clips_folder, f"concat_{i}_{datetime.now().timestamp():.0f}.txt")
                with open(concat_list, 'w') as f:
                    if ai_image_path:
                        f.write(f"file '{ai_video_path}'\n")
                    f.write(f"file '{segment_path}'\n")
                (
                    ffmpeg.input(concat_list, format='concat', safe=0)
                    .output(output_path, c='copy')
                    .overwrite_output()
                    .run(quiet=True)
                )
                # 5. Add subtitles (burned-in) using ffmpeg drawtext
                subtitle_text = highlight.get('subtitle', highlight['description'])
                subtitled_output = os.path.join(self.clips_folder, f"clip_subtitled_{i}_{datetime.now().timestamp():.0f}.mp4")
                (
                    ffmpeg.input(output_path)
                    .drawtext(
                        text=subtitle_text,
                        fontfile='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
                        fontsize=24,
                        fontcolor='white',
                        borderw=2,
                        x='(w-text_w)/2',
                        y='h-50'
                    )
                    .output(subtitled_output, vcodec='libx264', acodec='aac', preset='fast')
                    .overwrite_output()
                    .run(quiet=True)
                )
                clips.append({
                    'path': subtitled_output,
                    'start': highlight['start'],
                    'end': highlight['end'],
                    'description': highlight['description']
                })
                # Cleanup temp files
                for f in [segment_path, ai_image_path, ai_video_path, output_path, concat_list]:
                    if f and os.path.exists(f):
                        try:
                            os.remove(f)
                        except Exception:
                            pass
            except Exception as e:
                print(f"Error generating clip {i}: {str(e)}")
                continue
        return clips
