# pet_git.py (GitHub Actions Compatible)
import os
import gspread
import google.generativeai as genai
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials
import time
import random
from moviepy.editor import *
from moviepy.config import change_settings
from google.generativeai.types import GenerationConfig
import sys
from upload_video import get_authenticated_service, upload_video, update_video_details

# --- SETUP AND AUTHENTICATION ---
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'credentials.json'
load_dotenv()

try:
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')
    print("✅ Gemini AI Authenticated Successfully.")
except Exception as e: 
    sys.exit(f"❌ ERROR: Gemini AI Auth Failed. {e}")

try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    gspread_client = gspread.authorize(creds)
    sheet = gspread_client.open("pet_facts").sheet1
    print("✅ Google Sheets Authenticated and Opened Successfully.")
except Exception as e: 
    sys.exit(f"❌ ERROR: Google Sheets Auth Failed. {e}")

# --- AI & AUTOMATION FUNCTIONS ---

def setup_environment():
    """Configure environment for GitHub Actions."""
    if os.getenv('GITHUB_ACTIONS'):
        print("🤖 Running in GitHub Actions automation mode")
        try:
            change_settings({"IMAGEMAGICK_BINARY": "/usr/bin/convert"})
            print("✅ ImageMagick configured for Linux")
        except Exception as e:
            print(f"⚠️ ImageMagick setup warning: {e}")
    else:
        # Local environment setup
        try:
            change_settings({"IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"})
            print("✅ ImageMagick configured for Windows")
        except Exception:
            print("⚠️ ImageMagick path not configured. Text may fail.")

def get_user_choice():
    """Automatically select option 2 for GitHub Actions, prompt locally."""
    if os.getenv('GITHUB_ACTIONS'):
        print("🚀 Auto-selecting option 2: Generate and Upload video")
        return '2'
    else:
        print("\n--- AI YouTube Shorts Factory ---")
        print("1: Generate a new video and save it locally.")
        print("2: Generate, Upload, and Update a new video on YouTube.")
        return input("Enter your choice (1 or 2): ")

def create_quote_content() -> tuple[str, str, str]:
    """Generates a new, unique two-part fact about dog health and happiness."""
    print("🧠 Activating AI Dog Facts generator...")
    
    try:
        print("📚 Reading previously generated facts from Google Sheet...")
        used_facts = sheet.col_values(1)[1:] 
        history_list = "\n".join(f"- {fact}" for fact in used_facts)
        print(f"  Found {len(used_facts)} previously used facts.")
    except Exception as e:
        print(f"⚠️ Could not read sheet history, proceeding without it. Error: {e}")
        used_facts = []
        history_list = "None."
        
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
        print(f"  Chosen Theme: {chosen_theme}")

        master_prompt = f"""
        You are an AI that creates simple, helpful, two-part facts or tips about keeping dogs healthy and happy.
        Your fact MUST be about the specific theme of: **{chosen_theme}**.

        CRITICAL RULES:
        1. Your language MUST be super simple and easy to understand for all dog owners.
        2. The first part must be a "hook" that makes the reader curious.
        3. The second part must be the "reveal" or the helpful fact/tip.
        4. Do NOT generate a fact that is similar to any in the "PREVIOUSLY USED" list.
        5. Your ENTIRE response MUST be in the format below, with nothing else.

        **GOOD EXAMPLES OF THE REQUIRED STYLE:**
        * EXAMPLE 1 (Theme: dog health): `PART_1: A dog's nose isn't just for sniffing…\nPART_2: …it can also indicate their health. A wet nose often means they're well-hydrated.\nTITLE: The Secret of a Wet Nose`
        * EXAMPLE 2 (Theme: dog happiness): `PART_1: When your dog wags its tail to the right…\nPART_2: …it's usually a sign of happiness. A wag to the left can mean they're feeling insecure.\nTITLE: The Secret Language of Tail Wags`

        **PREVIOUSLY USED FACTS:**
        {history_list}

        **YOUR REQUIRED OUTPUT FORMAT:**
        PART_1:
        [The first part of the fact]

        PART_2:
        [The second part of the fact]

        TITLE:
        [The video title]
        """
        
        generation_config = GenerationConfig(temperature=0.8)
        response = gemini_model.generate_content(master_prompt, generation_config=generation_config)
        
        try:
            part1 = response.text.split("PART_2:")[0].replace("PART_1:", "").strip()
            if part1 in used_facts:
                print(f"⚠️ AI generated a duplicate fact. Retrying...")
                continue
            part2 = response.text.split("TITLE:")[0].split("PART_2:")[1].strip()
            title = response.text.split("TITLE:")[1].strip()
            print("✅ New, unique fact generated!")
            return part1, part2, title
        except Exception as e:
            print(f"⚠️ Could not parse the AI's response on this attempt. Retrying... Error: {e}")
            
    print(f"❌ Failed to generate a unique fact after {MAX_ATTEMPTS} attempts.")
    return "Error", "Could not generate unique fact.", "Error"

def generate_extra_tags(title: str, quote_parts: str) -> list:
    """Uses AI to brainstorm a list of relevant SEO tags for the dog facts niche."""
    print("🤖 Brainstorming additional SEO tags for dog content...")
    prompt = f"""
Based on the following video title and content about dog facts, health, and care, generate a list of 10-15 relevant, popular, and SEO-friendly YouTube tags.

TITLE: {title}
CONTENT: {quote_parts}

RULES:
- Return ONLY a comma-separated list of tags.
- Do not use hashtags (#).
- Include a mix of broad and specific tags (e.g., dog facts, pet care, dog training, puppy tips, happy dog, dog health, animal facts, cute dogs, shorts).

Your comma-separated list of tags:
"""
    try:
        generation_config = GenerationConfig(temperature=0.7)
        response = gemini_model.generate_content(prompt, generation_config=generation_config)
        tags = [tag.strip() for tag in response.text.split(',')]
        print(f"✅ Generated {len(tags)} extra tags.")
        return tags
    except Exception as e:
        print(f"⚠️ AI tag generation failed: {e}")
        return []

def generate_video_with_music(part1: str, part2: str, output_filename: str):
    """Generates a video and appends a 'like and subscribe' outro."""
    print(f"🎬 Generating main video content for '{output_filename}'...")
    
    # --- 1. Define Durations ---
    MAIN_VIDEO_DURATION = 12
    MUSIC_FOLDER = 'pets_music'
    BACKGROUND_FOLDER = 'dogs_temp'
    OUTRO_FILENAME = "like_subscribe.mp4"
    
    # Get outro duration
    try:
        outro_clip_path = os.path.join(BACKGROUND_FOLDER, OUTRO_FILENAME)
        outro_clip_for_duration = VideoFileClip(outro_clip_path)
        OUTRO_DURATION = outro_clip_for_duration.duration
        outro_clip_for_duration.close()
        del outro_clip_for_duration
    except Exception as e:
        sys.exit(f"❌ ERROR: Could not find '{OUTRO_FILENAME}' in '{BACKGROUND_FOLDER}' folder. Details: {e}")
        
    TOTAL_DURATION = MAIN_VIDEO_DURATION + OUTRO_DURATION

    # --- 2. Select and Prepare Media ---
    try:
        available_music = [f for f in os.listdir(MUSIC_FOLDER) if f.endswith('.mp3')]
        chosen_music_path = os.path.join(MUSIC_FOLDER, random.choice(available_music))
        print(f"🎵 Using music: {chosen_music_path}")
        
        available_videos = sorted([f for f in os.listdir(BACKGROUND_FOLDER) 
                                 if f.endswith(('.mp4', '.mov')) and f != OUTRO_FILENAME])
        if not available_videos: 
            sys.exit(f"❌ ERROR: No background videos found in '{BACKGROUND_FOLDER}'.")
        
        # Sequential video selection
        state_file = os.path.join(BACKGROUND_FOLDER, 'last_video_index.txt')
        last_index = -1
        if os.path.exists(state_file):
            with open(state_file, 'r') as f: 
                try:
                    last_index = int(f.read() or -1)
                except (ValueError, TypeError):
                    last_index = -1
        
        next_index = (last_index + 1) % len(available_videos)
        chosen_video_path = os.path.join(BACKGROUND_FOLDER, available_videos[next_index])
        with open(state_file, 'w') as f: 
            f.write(str(next_index))
        print(f"🔄 Sequentially selected video #{next_index + 1}: {chosen_video_path}")

    except Exception as e:
        sys.exit(f"❌ ERROR: Could not find media files. Details: {e}")

    # Initialize clips to None for proper cleanup
    music_clip = None
    background_clip = None
    main_background = None
    outro_clip = None
    final_video = None

    try:
        # --- 3. Load and Prepare Clips ---
        music_clip = AudioFileClip(chosen_music_path).set_duration(TOTAL_DURATION)
        
        background_clip = VideoFileClip(chosen_video_path)
        if background_clip.duration < MAIN_VIDEO_DURATION:
            background_clip = background_clip.loop(duration=MAIN_VIDEO_DURATION)
        main_background = background_clip.subclip(0, MAIN_VIDEO_DURATION).resize(height=1920).crop(
            x_center=background_clip.w/2, width=1080)

        # --- 4. Create Main Content Layers ---
        print("   Adding text layers...")
        heading_text = "Dogs Facts"
        box_width = int(1080 * 0.7)
        box_height = 110
        final_position = ('center', int(1920 * 0.20))
        
        heading_bg = ColorClip(size=(box_width, box_height), color=(255, 255, 255)).set_position(
            final_position).set_duration(MAIN_VIDEO_DURATION)
        heading_clip = TextClip(heading_text, fontsize=75, color='black', font='Arial-Bold', 
                               size=heading_bg.size).set_position(final_position).set_duration(MAIN_VIDEO_DURATION)

        part1_duration, part2_start_time, part2_duration = 6, 6, 6
        quote_clip1 = TextClip(part1, fontsize=80, color='white', font='Arial-Bold', 
                              stroke_color='black', stroke_width=3, size=(1080 * 0.9, None), 
                              method='caption').set_position('center').set_duration(part1_duration).fx(
                              vfx.fadein, 1).fx(vfx.fadeout, 0.5)
        quote_clip2 = TextClip(part2, fontsize=80, color='white', font='Arial-Bold', 
                              stroke_color='black', stroke_width=3, size=(1080 * 0.9, None), 
                              method='caption').set_position('center').set_start(part2_start_time).set_duration(
                              part2_duration).fx(vfx.fadein, 0.5)

        # --- 5. Composite the Main Video ---
        main_video = CompositeVideoClip([main_background, heading_bg, heading_clip, 
                                       quote_clip1, quote_clip2]).set_duration(MAIN_VIDEO_DURATION)

        # --- 6. Load the Outro Clip ---
        print("   Adding 'Like & Subscribe' outro...")
        outro_clip = VideoFileClip(outro_clip_path).resize(height=1920).crop(
            x_center=VideoFileClip(outro_clip_path).w/2, width=1080)
        
        # --- 7. Concatenate Main Video and Outro ---
        final_video = concatenate_videoclips([main_video, outro_clip])
        final_video = final_video.set_audio(music_clip)

        # --- 8. Write Final File ---
        print("   Compositing final video...")
        final_video.write_videofile(output_filename, fps=24, codec='libx264', 
                                   threads=2, preset='ultrafast')
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
            if background_clip:
                background_clip.close()
                del background_clip
            if main_background:
                main_background.close()
                del main_background
            if outro_clip:
                outro_clip.close()
                del outro_clip
            if final_video:
                final_video.close()
                del final_video
        except:
            pass

def log_to_sheet(part1: str, part2: str, title: str, filename: str, status: str):
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
    
    # This block runs for both choices, as both need a quote and a video file
    if choice == '1' or choice == '2':
        # --- Stage 1: Generate Content ---
        part1, part2, title = create_quote_content()
        if part1 == "Error": 
            sys.exit("❌ Failed to generate content.")
        
        if not os.getenv('GITHUB_ACTIONS'):
            print(f"\n  Part 1: {part1}\n  Part 2: {part2}\n  Title: {title}")
        else:
            print(f"✅ Content Generated: {title}")
        
        # --- Stage 2: Generate Video File ---
        run_id = int(time.time())
        video_filename = f"quote_{run_id}.mp4"
        generate_video_with_music(part1, part2, video_filename)

        # --- Stage 3: UPLOAD and UPDATE (only if choice is 2) ---
        upload_status = "Generated Locally"
        if choice == '2':
            print("\n--- Starting YouTube Upload & Update Process ---")
            try:
                # Get authenticated YouTube service
                youtube_service = get_authenticated_service()
                print("✅ YouTube Authentication Successful.")
                
                # Define hashtags and create title
                hashtags = "#shorts #ytshorts #dogs #dogsfacts #Quickfeelfact"
                title_with_hashtags = f"{title} {hashtags}"
                print(f"  Uploading with title: {title_with_hashtags}")
                
                # Create description
                description = f"{part1}\n\n{part2}\n\n{hashtags}"
                
                # Base tags
                base_tags = ["dogs", "facts", "shorts", "ytshorts", "dog facts", "pet care", 
                           "dog training", "puppy tips", "happy dog", "dog health", "animal facts", "cute dogs"]
                
                # Generate additional tags with AI
                ai_tags = generate_extra_tags(title, f"{part1} {part2}")
                final_tags = list(set(base_tags + ai_tags))
                
                print(f"🚀 Uploading '{video_filename}' to YouTube...")
                video_id = upload_video(
                    youtube_service=youtube_service,
                    file_path=video_filename,
                    title=title_with_hashtags,
                    description=description,
                    tags=final_tags,
                    privacy_status='public'
                )
                
                if video_id:
                    # Update video with additional details if needed
                    update_video_details(youtube_service, video_id, final_tags)
                    upload_status = f"UPLOADED_PUBLIC_ID:{video_id}"
                    print("✅ Video Uploaded Successfully!")
                else:
                    raise Exception("Upload failed, video ID not received.")

            except Exception as e:
                print(f"❌ An error occurred during the YouTube upload phase: {e}")
                upload_status = f"UPLOAD_FAILED: {e}"
        
        # Log to sheet
        log_to_sheet(part1, part2, title, video_filename, upload_status)
        print("\n✅ --- All tasks completed. ---")
        
    else:
        print("Invalid choice.")