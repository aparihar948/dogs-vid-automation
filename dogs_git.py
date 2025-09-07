# pet_git.py (Adapted for GitHub Actions)
import os
import gspread
import google.generativeai as genai
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials
import time
import random
from moviepy.editor import *
import sys

# Import your YouTube upload functions
from upload_video import get_authenticated_service, upload_video, update_video_details

# --- SETUP AND AUTHENTICATION ---
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'credentials.json'
load_dotenv()
try:
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')
    print("✅ Gemini AI Authenticated Successfully.")
except Exception as e: sys.exit(f"❌ ERROR: Gemini AI Auth Failed. {e}")
try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    gspread_client = gspread.authorize(creds)
    sheet = gspread_client.open("pet_facts").sheet1
    print("✅ Google Sheets Authenticated and Opened Successfully.")
except Exception as e: sys.exit(f"❌ ERROR: Google Sheets Auth Failed. {e}")

# --- AI & AUTOMATION FUNCTIONS ---

def setup_environment():
    """Configure environment for GitHub Actions."""
    if os.getenv('GITHUB_ACTIONS'):
        print("🤖 Running in GitHub Actions automation mode")
        try:
            from moviepy.config import change_settings
            change_settings({"IMAGEMAGICK_BINARY": "/usr/bin/convert"})
            print("✅ ImageMagick configured for Linux")
        except Exception as e:
            print(f"⚠️ ImageMagick setup warning: {e}")

def get_user_choice():
    """Automatically select option 2 for automation."""
    if os.getenv('GITHUB_ACTIONS'):
        print("🚀 Auto-selecting option 2: Generate and Upload video")
        return '2'
    # Fallback for local testing
    return '1'

def create_quote_content() -> tuple[str, str, str]:
    """Generates a new, unique two-part fact about dog health and happiness."""
    print("🧠 Activating AI Dog Facts generator...")
    try:
        used_facts = sheet.col_values(1)[1:]
        history_list = "\n".join(f"- {fact}" for fact in used_facts)
        print(f"   Found {len(used_facts)} previously used facts.")
    except Exception as e:
        print(f"⚠️ Could not read sheet history: {e}")
        history_list = "None."
        used_facts = []

    MAX_ATTEMPTS = 5
    for attempt in range(MAX_ATTEMPTS):
        print(f"🤖 Attempt {attempt + 1}/{MAX_ATTEMPTS}: Generating a new, unique dog fact...")
        themes = [
            "a dog's body language", "the importance of mental stimulation for dogs",
            "a common food that is surprisingly safe for dogs", "a common food that is dangerous for dogs",
            "the science behind a dog's sense of smell", "how to tell if your dog is truly happy",
            "the meaning of different types of barks", "a simple tip for dog dental health",
            "why dogs sleep so much", "a sign of a healthy dog"
        ]
        chosen_theme = random.choice(themes)
        print(f"   Chosen Theme: {chosen_theme}")
        master_prompt = f"""
        You are an AI that creates simple, helpful, two-part facts or tips about keeping dogs healthy and happy.
        Your fact MUST be about the specific theme of: **{chosen_theme}**.
        CRITICAL RULES:
        1. Your language MUST be super simple and easy to understand for all dog owners.
        2. The first part must be a "hook". The second part must be the "reveal" or the helpful fact/tip.
        3. Do NOT generate a fact similar to any in the "PREVIOUSLY USED" list.
        4. Your ENTIRE response MUST be in the format: PART_1: [text] PART_2: [text] TITLE: [text]

        **PREVIOUSLY USED FACTS:**
        {history_list}
        """
        try:
            response = gemini_model.generate_content(master_prompt)
            part1 = response.text.split("PART_2:")[0].replace("PART_1:", "").strip()
            if part1 in used_facts:
                print("⚠️ AI generated a duplicate fact. Retrying...")
                continue
            part2 = response.text.split("TITLE:")[0].split("PART_2:")[1].strip()
            title = response.text.split("TITLE:")[1].strip()
            print("✅ New, unique fact generated!")
            return part1, part2, title
        except Exception as e:
            print(f"⚠️ Could not parse the AI's response. Retrying... Error: {e}")
    print("❌ Failed to generate a unique fact after multiple attempts.")
    return "Error", "Could not generate unique fact.", "Error"

def generate_extra_tags(title: str, quote_parts: str) -> list:
    """Uses AI to brainstorm a list of relevant SEO tags for the dog facts niche."""
    print("🤖 Brainstorming additional SEO tags for dog content...")
    prompt = f"""
    Based on the video title and content about dog facts, health, and care, generate 10-15 relevant YouTube tags.
    TITLE: {title}
    CONTENT: {quote_parts}
    RULES: Return ONLY a comma-separated list of tags (e.g., dog facts, pet care, puppy tips, shorts).
    """
    try:
        response = gemini_model.generate_content(prompt)
        tags = [tag.strip() for tag in response.text.split(',')]
        print(f"✅ Generated {len(tags)} extra tags.")
        return tags
    except Exception as e:
        print(f"⚠️ AI tag generation failed: {e}")
        return []

def generate_video_with_music(part1: str, part2: str, output_filename: str):
    """Generates a video and appends a 'like and subscribe' outro."""
    print(f"🎬 Generating main video content for '{output_filename}'...")
    
    MAIN_VIDEO_DURATION = 12
    MUSIC_FOLDER = 'pets_music'
    BACKGROUND_FOLDER = 'dogs_temp'
    OUTRO_FILENAME = "like_subscribe.mp4"
    
    # Get outro duration first
    try:
        outro_clip_path = os.path.join(BACKGROUND_FOLDER, OUTRO_FILENAME)
        temp_clip = VideoFileClip(outro_clip_path)
        OUTRO_DURATION = temp_clip.duration
        temp_clip.close()  # Important: close the temporary clip
        del temp_clip
    except Exception as e:
        sys.exit(f"❌ ERROR: Could not find '{OUTRO_FILENAME}'. Details: {e}")
        
    TOTAL_DURATION = MAIN_VIDEO_DURATION + OUTRO_DURATION

    # Select media files
    try:
        music_files = [f for f in os.listdir(MUSIC_FOLDER) if f.endswith('.mp3')]
        chosen_music_path = os.path.join(MUSIC_FOLDER, random.choice(music_files))
        print(f"🎵 Using music: {chosen_music_path}")
        
        video_files = sorted([f for f in os.listdir(BACKGROUND_FOLDER) 
                             if f.endswith(('.mp4', '.mov')) and f != OUTRO_FILENAME])
        if not video_files: 
            sys.exit(f"❌ ERROR: No background videos found.")

        state_file = os.path.join(BACKGROUND_FOLDER, 'last_video_index.txt')
        last_index = -1
        if os.path.exists(state_file):
            with open(state_file, 'r') as f:
                try: 
                    last_index = int(f.read())
                except (ValueError, TypeError): 
                    last_index = -1
        
        next_index = (last_index + 1) % len(video_files)
        chosen_video_path = os.path.join(BACKGROUND_FOLDER, video_files[next_index])
        with open(state_file, 'w') as f: 
            f.write(str(next_index))
        print(f"🔄 Sequentially selected video #{next_index + 1}: {chosen_video_path}")

    except Exception as e:
        sys.exit(f"❌ ERROR: Could not find media files. Details: {e}")

    # Create clips - all should be managed properly
    music_clip = None
    main_background = None
    final_outro = None
    final_video = None
    
    try:
        # Load and prepare music
        music_clip = AudioFileClip(chosen_music_path)
        if music_clip.duration < TOTAL_DURATION:
            music_clip = music_clip.fx(vfx.loop, duration=TOTAL_DURATION)
        else:
            music_clip = music_clip.subclip(0, TOTAL_DURATION)

        # Load and prepare background video
        background_clip = VideoFileClip(chosen_video_path)
        if background_clip.duration < MAIN_VIDEO_DURATION:
            background_clip = background_clip.loop(duration=MAIN_VIDEO_DURATION)
        
        main_background = background_clip.subclip(0, MAIN_VIDEO_DURATION).resize(height=1920).crop(
            x_center=background_clip.w/2, width=1080)
        
        # Close the original background clip as we have our processed version
        background_clip.close()
        del background_clip

        print("   Adding text layers...")
        # Create text elements
        heading_text = "Dog Facts"
        heading_bg = ColorClip(size=(int(1080 * 0.7), 110), color=(255, 255, 255)).set_position(
            ('center', int(1920 * 0.20))).set_duration(MAIN_VIDEO_DURATION)
        
        heading_clip = TextClip(heading_text, fontsize=75, color='black', 
                               font='Arial-Rounded-MT-Bold', size=heading_bg.size).set_position(
                               heading_bg.pos).set_duration(MAIN_VIDEO_DURATION)

        quote_clip1 = TextClip(part1, fontsize=80, color='white', 
                              font='Arial-Rounded-MT-Bold', stroke_color='black', 
                              stroke_width=3, size=(1080 * 0.9, None), 
                              method='caption').set_position('center').set_duration(6).fx(
                              vfx.fadein, 1).fx(vfx.fadeout, 0.5)
        
        quote_clip2 = TextClip(part2, fontsize=80, color='white', 
                              font='Arial-Rounded-MT-Bold', stroke_color='black', 
                              stroke_width=3, size=(1080 * 0.9, None), 
                              method='caption').set_position('center').set_start(6).set_duration(6).fx(
                              vfx.fadein, 0.5)

        # Create main video composite
        main_video = CompositeVideoClip([main_background, heading_bg, heading_clip, 
                                       quote_clip1, quote_clip2]).set_duration(MAIN_VIDEO_DURATION)

        print("   Adding 'Like & Subscribe' outro...")
        # Load outro video
        final_outro = VideoFileClip(outro_clip_path).resize(height=1920).crop(
            x_center=VideoFileClip(outro_clip_path).w/2, width=1080)
        
        # Concatenate main video and outro
        final_video = concatenate_videoclips([main_video, final_outro])
        final_video = final_video.set_audio(music_clip)

        print("   Compositing final video...")
        final_video.write_videofile(output_filename, fps=24, codec='libx264', 
                                   threads=2, preset='ultrafast')  # Use fewer threads for stability
        
        print(f"✅ Video saved successfully as {output_filename}")
        
    except Exception as e:
        print(f"❌ ERROR during video generation: {e}")
        raise e
    
    finally:
        # Clean up all resources
        try:
            if music_clip:
                music_clip.close()
                del music_clip
            if main_background:
                main_background.close()
                del main_background
            if final_outro:
                final_outro.close()
                del final_outro
            if final_video:
                final_video.close()
                del final_video
        except:
            pass  # Ignore cleanup errors

            
def log_to_sheet(part1, part2, title, filename, status):
    """Adds the details of the generated video to the Google Sheet."""
    print(f"✍️ Logging details to Google Sheet...")
    try:
        new_row = [part1, part2, title, filename, status]
        sheet.append_row(new_row)
        print("✅ Logged to Google Sheet successfully.")
    except Exception as e:
        print(f"⚠️ Could not log to Google Sheet. Details: {e}")

# --- MAIN EXECUTION BLOCK ---
if __name__ == "__main__":
    print("\n🚀 --- AI Pet Facts Video Factory ---")
    setup_environment()
    choice = get_user_choice()
    
    if choice == '2':
        part1, part2, title = create_quote_content()
        if part1 == "Error": sys.exit("❌ Failed to generate content.")
        print(f"✅ Content Generated: {title}")

        timestamp = int(time.time())
        output_filename = f"quote_{timestamp}.mp4"
        generate_video_with_music(part1, part2, output_filename)

        upload_status = "Generated Locally"
        try:
            youtube = get_authenticated_service()
            print("✅ YouTube Authentication Successful.")
            hashtags = "#shorts #dogfacts #pets #dog #cuteanimals"
            title_with_hashtags = f"{title} {hashtags}"
            
            description = f"{part1} {part2}\n\n{hashtags}"
            base_tags = ["dog facts", "pet care", "dog training", "puppy tips", "happy dog", "dog health", "animal facts", "cute dogs", "shorts"]
            ai_tags = generate_extra_tags(title, f"{part1} {part2}")
            final_tags = list(set(base_tags + ai_tags))

            print(f"🚀 Uploading '{output_filename}' to YouTube...")
            upload_video(
                youtube, file_path=output_filename, title=title_with_hashtags,
                description=description, tags=final_tags, privacy_status="public"
            )
            upload_status = "Uploaded to YouTube"
            print("✅ Video Uploaded Successfully!")

        except Exception as e:
            print(f"❌ ERROR: YouTube upload failed. Details: {e}")
            upload_status = f"YouTube Upload Failed: {e}"
        
        log_to_sheet(part1, part2, title, output_filename, upload_status)
        print("\n✅ --- All tasks completed. ---")
