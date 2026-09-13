import os
import json
import subprocess
import asyncio
import google.generativeai as genai

async def run_video_pipeline(job_id: str, story: str, photo_paths: list, jobs: dict, base_url: str):
    try:
        job_dir = os.path.join("temp_uploads", job_id)
        num_scenes = len(photo_paths)
        
        # 1. Analyze Story with Gemini
        jobs[job_id].update({"progress": 0.1, "status_message": "AI से कहानी का विश्लेषण किया जा रहा है..."})
        scenes = await analyze_story_with_gemini(story, num_scenes)
        
        if len(scenes) != num_scenes:
            # Fallback if AI didn't match photo count perfectly
            scenes = scenes[:num_scenes]
            while len(scenes) < num_scenes:
                scenes.append({"narration": "...", "description": "Fallback scene"})

        # 2. Generate Audio (TTS)
        jobs[job_id].update({"progress": 0.3, "status_message": "आवाज़ और ऑडियो तैयार किया जा रहा है..."})
        audio_paths = []
        for i, scene in enumerate(scenes):
            audio_path = os.path.join(job_dir, f"audio_{i}.mp3")
            await generate_tts(scene.get("narration", ""), audio_path)
            audio_paths.append(audio_path)
        
        # 3. Render Individual Scenes with FFmpeg
        jobs[job_id].update({"progress": 0.6, "status_message": "तस्वीरों और एनिमेशन को जोड़ा जा रहा है..."})
        scene_videos = []
        for i in range(num_scenes):
            scene_video = os.path.join(job_dir, f"scene_{i}.mp4")
            render_scene(photo_paths[i], audio_paths[i], scene_video)
            scene_videos.append(scene_video)
            
        # 4. Concatenate Scenes
        jobs[job_id].update({"progress": 0.9, "status_message": "फाइनल वीडियो रेंडर हो रहा है..."})
        final_video_name = f"{job_id}.mp4"
        final_video_path = os.path.join("output_videos", final_video_name)
        concatenate_videos(scene_videos, final_video_path, job_dir)
        
        # 5. Complete
        absolute_video_url = f"{base_url}videos/{final_video_name}"
        
        jobs[job_id].update({
            "status": "COMPLETED",
            "progress": 1.0,
            "status_message": "वीडियो तैयार है!",
            "video_url": absolute_video_url
        })
        
    except Exception as e:
        jobs[job_id].update({
            "status": "FAILED",
            "progress": 0.0,
            "status_message": "वीडियो बनाने में विफल।",
            "error": str(e)
        })

async def analyze_story_with_gemini(story: str, num_scenes: int):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is missing on the server.")
        
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        'gemini-2.5-pro',
        generation_config={"response_mime_type": "application/json"}
    )
    
    prompt = f"""
    Analyze this Hindi story: "{story}"
    Divide it into exactly {num_scenes} sequential scenes.
    Return a JSON array of objects.
    Each object must have:
    "narration": "The exact Hindi text to be spoken for this scene."
    "description": "Visual description of the scene."
    """
    
    response = model.generate_content(prompt)
    
    # Clean and parse JSON
    text = response.text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(text)
    except Exception as e:
        print(f"Failed to parse AI response: {text}")
        raise ValueError("Failed to parse AI response into scenes.")

async def generate_tts(text: str, output_path: str):
    # Using edge-tts via command line as a robust, free TTS alternative for Hindi
    if not text or text.strip() == "" or text.strip() == "...":
        # Generate 1 second silent audio if no text
        subprocess.run(["ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "1", "-q:a", "9", "-acodec", "libmp3lame", output_path, "-y"], check=True)
        return

    cmd = [
        "edge-tts",
        "--voice", "hi-IN-MadhurNeural",
        "--text", text,
        "--write-media", output_path
    ]
    process = await asyncio.create_subprocess_exec(*cmd)
    await process.communicate()
    
    if not os.path.exists(output_path):
        subprocess.run(["ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "3", "-q:a", "9", "-acodec", "libmp3lame", output_path, "-y"], check=True)

def render_scene(image_path: str, audio_path: str, output_path: str):
    # FFmpeg: Combine image and audio, scale to 1080p, add zoom-in pan effect
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", image_path,
        "-i", audio_path,
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,zoompan=z='min(zoom+0.001,1.5)':d=1:s=1920x1080",
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest", output_path
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def concatenate_videos(video_paths: list, output_path: str, job_dir: str):
    list_file = os.path.join(job_dir, "list.txt")
    with open(list_file, "w") as f:
        for vp in video_paths:
            f.write(f"file '{os.path.abspath(vp)}'\n")
            
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", list_file,
        "-c", "copy",
        output_path
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
