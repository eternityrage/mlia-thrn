import os
import json
import glob
import random
import requests
import shutil
import sys
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
from pathlib import Path
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# Import upload functions
try:
    from upload.upload_instagram import upload_to_instagram
    from upload.upload_threads import upload_to_threads
    from upload.upload_facebook import upload_to_facebook, upload_to_facebook_story
    from upload.upload_to_youtube import upload_to_youtube
except ImportError as e:
    print(f"Error importing upload modules: {e}")
    # Still want to proceed or stop?
    pass

PROCESSED_DIR = "Processed_Videos"
PUBLISHED_LOG = "published_videos.json"

def get_already_published():
    if os.path.exists(PUBLISHED_LOG):
        with open(PUBLISHED_LOG, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []


def get_repost_counts():
    """Count how many times each video has been posted."""
    published = get_already_published()
    counts = {}
    for entry in published:
        vname = entry.get("video_name", "")
        counts[vname] = counts.get(vname, 0) + 1
    return counts

def mark_as_published(video_name, metadata):
    published = get_already_published()
    published.append({
        "video_name": video_name,
        "metadata": metadata
    })
    with open(PUBLISHED_LOG, 'w', encoding='utf-8') as f:
        json.dump(published, f, indent=4)

def select_video(specific_video=None):
    published = [item["video_name"] for item in get_already_published()]
    all_videos = sorted(glob.glob(os.path.join(PROCESSED_DIR, "*.mp4")))

    if specific_video:
        # specific_video might be a full path or just a filename
        if os.path.exists(specific_video):
            # It's a full path
            vid_path = specific_video
            name = os.path.basename(specific_video)
        else:
            # It's just a filename, join with PROCESSED_DIR
            vid_path = os.path.join(PROCESSED_DIR, specific_video)
            name = specific_video

        if os.path.exists(vid_path):
            if name in published:
                post_count = sum(1 for p in published if p == name)
                print(f"🔄 Video {name} was already published ({post_count}x) - Re-publishing (recycling)")
            return vid_path, name
        else:
            print(f"❌ Error: Specific video {name} not found")
            return None, None

    # Find unpublished videos first
    unpublished = [(vid, os.path.basename(vid)) for vid in all_videos if os.path.basename(vid) not in published]

    if unpublished:
        vid, name = unpublished[0]
        return vid, name

    # All videos published - use weighted random selection (less posted = more likely)
    if all_videos:
        repost_counts = get_repost_counts()
        weights = []
        for vid in all_videos:
            name = os.path.basename(vid)
            count = repost_counts.get(name, 0)
            weight = max(1, 1000 // (3 ** min(count, 6)))
            weights.append(weight)

        selected_vid = random.choices(all_videos, weights=weights, k=1)[0]
        name = os.path.basename(selected_vid)
        post_count = repost_counts.get(name, 0)
        print(f"🎲 All videos published. Weighted random reuse (posted {post_count}x): {name}")
        return selected_vid, name

    return None, None

def generate_caption():
    import random
    import time

    api_key = os.getenv("POLLINATIONS_API_KEY")
    model = os.getenv("AI_MODEL", "openai")

    fallback_titles = [
        "3 Strength Training Mistakes Keeping You Small",
        "The Real Secret to Building Muscle at Any Age",
        "Why You're Not Seeing Gym Results (Fix This Today)",
        "Beginner's Guide to a Stronger, Healthier You",
        "Pre-Workout Nutrition — Eat This Before You Train",
        "5-Minute Mobility Routine to Feel Amazing",
        "How to Actually Enjoy Working Out (No More Dread)",
        "The Truth About Fitness No One Tells You",
        "Recovery Day Isn't Optional — Here's Why",
        "Train Smarter: Quality Over Quantity",
        "Healthy Living Habits That Changed Everything",
        "The Best Time to Train for Maximum Gains",
        "Why Sleep Is Your Secret Muscle-Building Weapon",
        "Travel-Friendly Workouts for Busy Lives",
        "Daily Motivation to Keep Showing Up for Yourself",
    ]

    fallback_descriptions = [
        "Fitness isn't about punishing yourself — it's about building a body and a life you love. Strength training, proper nutrition, and real recovery are the foundation of everything I teach. Whether you're just starting or levelling up, this one's for you. Drop a 💪 if you're committed to your fitness journey this year! #fitness #strengthtraining #gymmotivation #healthylifestyle #nutrition #wellness #personaltraining #workoutmotivation #musclebuilding #selfimprovement #maliyathornton",
        "The gym isn't about ego — it's about consistency. The people who see real results are the ones who show up daily, train with intention, and treat recovery like training. Small habits compound into a body that feels strong and moves well. Save this for your next workout. Comment what you're training today! 🏋️ #gym #fitnessjourney #strength #workouttips #musclegain #fitnesstips #healthyliving #wellness #dedication #dailyroutine #maliyathornton",
        "Nutrition wins half the battle before you even step into the gym. Eating clean, hitting your protein, and fueling around your workouts makes everything easier — more energy, better pumps, faster recovery. You can't out-train a bad diet. Start with one small change this week. Like if you agree! 🥗 #nutrition #healthyeating #fitnessfood #mealprep #proteinshake #cleaneating #gymlife #wellnessjourney #fitnessgoals #maliyathornton",
        "You don't need a perfect plan — you need to start. Movement, strength, and good nutrition are simple when you break them down. Focus on showing up, and the results follow. No more waiting for Monday. Start today. Save this for your gym day and share it with a friend who's been putting it off! ✨ #fitnessmotivation #beginnerfitness #getfit #workoutplan #healthylifestyle #strengthtraining #fitnessjourney #motivation #maliyathornton",
        "Recovery is where the muscle is built. Training breaks you down, but rest, sleep, and proper nutrition rebuild you stronger. Skipping recovery days isn't hustle — it's a mistake. Give your body what it needs and watch your progress explode. Drop a 🌿 if you're prioritising recovery this week! #recovery #restday #sleephacks #musclegrowth #wellness #fitnessscience #healthyliving #workoutrecovery #maliyathornton",
        "Feeling stuck in your fitness? It's usually one of three things: not enough protein, not enough sleep, or not enough consistency. Fix the fundamentals and everything changes. Keep it simple, keep showing up. Comment one thing you'll fix this week! 🚀 #fitnessmistakes #workouttips #healthytips #musclebuilding #nutritiontips #fitnesscoach #gymlife #wellnessjourney #maliyathornton",
        "Mobility isn't just for old people — it's the secret to moving well and staying pain-free for life. Five minutes of stretching and joint work daily keeps you training hard for decades. Your future self will thank you. Double tap if you stretch after your workouts! 🤸 #mobility #stretching #flexibility #jointhealth #longevity #wellness #fitnessroutine #movementismedicine #maliyathornton",
        "The best workout is the one you actually do. Stop chasing the perfect program and start being consistent. Train hard, eat right, sleep well, and repeat — that's the real formula. Simplicity wins. Save this for whenever you need a reminder. 💯 #fitnesssimplicity #workoutroutine #consistencyiskey #gymmotivation #healthylifestyle #strengthtraining #fitnesstips #maliyathornton",
        "Your body is a reflection of your daily habits. Small choices — the walk you take, the water you drink, the workouts you don't skip — add up to something massive. You don't need to be perfect, just consistent. Drop a 🌱 if you're building better habits today! #healthyhabits #fitnesslifestyle #wellness #dailyroutine #selfcare #healthjourney #motivation #maliyathornton",
        "Strength training isn't just about looking good — it's about feeling capable, confident, and powerful in your own body. Every rep builds resilience that carries into your whole life. Lifting changed everything for me. Like if lifting changed you too! 🏆 #strengthtraining #powerlifting #gymmotivation #confidence #musclebuilding #personaltrainer #fitnessjourney #empowerment #maliyathornton",
        "You can't pour from an empty cup. Wellness is more than workouts — it's sleep, stress management, time outdoors, and nourishing food. Take care of yourself first, then everything else gets easier. This is your reminder to rest without guilt. Comment below how you recharge! 🌸 #wellness #selfcare #mentalhealth #healthyliving #restday #mindfulness #balance #fitnesslifestyle #maliyathornton",
        "Fitness and travel go hand in hand. You don't lose all your progress on a trip — you adapt. Bodyweight workouts, hotel gyms, and smart nutrition keep you on track anywhere in the world. Stay active, stay focused, enjoy the journey. Share this with a friend who loves to travel! ✈️ #travelfitness #hotelworkout #bodyweighttraining #fittravel #healthylifestyle #adventure #wellnessjourney #maliyathornton",
        "Motivation gets you started — discipline keeps you going. On the days you don't feel like training, show up anyway. Those are the days that count the most. Future you is watching. Be the reason they're proud. Drop a 🔥 if you showed up for yourself today! #discipline #motivation #fitnessmindset #selfimprovement #dailygrind #gymlife #mentalstrength #maliyathornton",
        "Progress photos are the only honest judge. The scale lies, the mirror lies, but photos and strength gains never do. Track your progress the right way and watch your confidence grow. Consistency beats perfection every time. Save this for your journey. 📸 #fitnessprogress #progressnotperfection #transformation #gymresults #strengthgains #fitnessjourney #trackingprogress #maliyathornton",
        "Every expert was once a beginner. Nobody starts strong — everyone starts somewhere. The only failure is quitting. Keep showing up, keep learning, and keep pushing. Your future is being built in the workouts you don't skip. Comment your start date below! 💪 #beginnerfitness #nevergiveup #fitnessjourney #gymmotivation #strengthtraining #selfgrowth #healthylifestyle #maliyathornton",
    ]

    if not api_key:
        chosen_title = random.choice(fallback_titles)
        chosen_desc = random.choice(fallback_descriptions)
        print("Warning: POLLINATIONS_API_KEY not found. Using fallback captions.")
        return chosen_title, chosen_desc

    vibes = [
        "energetic and motivating — make viewers want to hit the gym right now",
        "authentic and coach-like — speak as a personal trainer giving honest, practical advice",
        "encouraging and uplifting — make people believe they can start today",
        "bold and straight-talking — call out the excuses people hide behind",
        "science-backed and smart — explain the why behind the workout and nutrition",
        "personal and inspiring — share real experiences from your own fitness journey",
        "warm and wellness-focused — emphasise health, recovery and loving your body",
    ]
    chosen_vibe = random.choice(vibes)

    prompt = (
        f"Write a completely unique, long, and captivating title and description for a short video "
        f"for the social media page 'Maliya Thornton'. "
        f"The page covers strength training, gym and fitness, nutrition and healthy living, wellness and recovery, "
        f"travel and lifestyle, and daily motivation. It's authentic, energetic, and speaks directly to people "
        f"who want to get stronger and live healthier. "
        f"Speak as an inspiring, credible fitness coach who makes people want to show up for themselves. "
        f"Make the vibe {chosen_vibe}. "
        f"The description should be LONG (4-6 sentences minimum), deeply engaging, and personal. "
        f"Include engagement calls-to-action such as: "
        f"- Like if this motivated you! "
        f"- Comment your fitness goal below! "
        f"- Share this with someone starting their fitness journey! "
        f"- Follow Maliya Thornton for daily fitness and wellness motivation! "
        f"Include relevant hashtags in ALL LOWERCASE such as #fitness #strengthtraining #gymmotivation #nutrition #healthyliving #wellness #recovery #workoutmotivation #healthylifestyle #personaltraining #fitnessjourney #motivation #selfimprovement #maliyathornton. "
        f"Return ONLY a valid JSON object in this format: {{\"title\": \"<title>\", \"description\": \"<description>\"}} "
        f"Do not include any other text or markdown block backticks."
    )

    url = "https://gen.pollinations.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.9,
        "seed": random.randint(1, 999999)
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=90)
        response.raise_for_status()
        data = response.json()
        content = data.get('choices', [{}])[0].get('message', {}).get('content', '')

        content = content.replace("```json", "").replace("```", "").strip()
        result = json.loads(content)

        chosen_title = random.choice(fallback_titles)
        chosen_desc = random.choice(fallback_descriptions)
        return result.get("title", chosen_title), result.get("description", chosen_desc)
    except Exception as e:
        print(f"Error generating caption: {e}")
        return random.choice(fallback_titles), random.choice(fallback_descriptions)

def main():
    print("=" * 60)
    print("🚀 DAILY AUTOMATION STARTING")
    print("=" * 60)
    
    specific_video = sys.argv[1] if len(sys.argv) > 1 else None
    video_path, video_name = select_video(specific_video)
    if not video_path:
        print("✅ No new videos found to publish. Exiting.")
        return
        
    print(f"👉 Selected Video: {video_name}")
    print("🧠 Generating caption via Pollination AI...")
    title, description = generate_caption()
    
    print(f"📝 Title: {title}")
    print(f"📝 Description:\n{description}")
    
    # Combined caption for platforms that use a single text field
    combined_caption = f"{title}\n\n{description}"
    
    success_flags = {
        "instagram_reel": False,
        "instagram_story": False,
        "facebook_reel": False,
        "facebook_story": False,
        "threads": False,
        "youtube": False
    }
    
    # Instagram Reels
    try:
        result = upload_to_instagram(video_path, combined_caption, is_story=False)
        if result and result.get('status') == 'skipped':
            print(f"⚠️  Instagram Reel: Skipped ({result.get('reason', 'No credentials')})")
        else:
            success_flags["instagram_reel"] = True
    except Exception as e:
        print(f"❌ Instagram Reel upload failed: {e}")
        
    # Instagram Stories
    try:
        result = upload_to_instagram(video_path, combined_caption, is_story=True)
        if result and result.get('status') == 'skipped':
            print(f"⚠️  Instagram Story: Skipped ({result.get('reason', 'No credentials')})")
        else:
            success_flags["instagram_story"] = True
    except Exception as e:
        print(f"❌ Instagram Story upload failed: {e}")
        
    # Facebook Reels
    try:
        result = upload_to_facebook(video_path, description, title=title)
        if result and result.get('status') == 'skipped':
            print(f"⚠️  Facebook Reel: Skipped ({result.get('reason', 'No credentials')})")
        else:
            success_flags["facebook_reel"] = True
    except Exception as e:
        print(f"❌ Facebook Reel upload failed: {e}")
        
    # Facebook Stories
    try:
        result = upload_to_facebook_story(video_path)
        if result and result.get('status') == 'skipped':
            print(f"⚠️  Facebook Story: Skipped ({result.get('reason', 'No credentials')})")
        else:
            success_flags["facebook_story"] = True
    except Exception as e:
        print(f"❌ Facebook Story upload failed: {e}")
        
    # Threads
    try:
        result = upload_to_threads(video_path, combined_caption)
        if result and result.get('status') == 'skipped':
            print(f"⚠️  Threads: Skipped ({result.get('reason', 'No credentials')})")
        else:
            success_flags["threads"] = True
    except Exception as e:
        print(f"❌ Threads upload failed: {e}")
        
    # YouTube Shorts
    try:
        upload_to_youtube(video_path, title, description, tags=["fitness", "strengthtraining", "gym", "workout", "nutrition", "healthyliving", "wellness", "recovery", "gymmotivation", "fitnessjourney", "healthylifestyle", "personaltraining", "motivation", "maliyathornton"])
        success_flags["youtube"] = True
    except Exception as e:
        print(f"❌ YouTube upload failed: {e}")
        
    # Record as published regardless of partial success,
    # to avoid repeating the same video. Alternatively, only record if fully successful.
    print("\n✅ Marking video as published.")
    
    # Check if this is a recycled video (already in published_videos.json)
    published_list = get_already_published()
    is_recycled = any(item["video_name"] == video_name for item in published_list)
    
    if is_recycled:
        print(f"   🔄 This is a recycled video (re-publishing)")
    
    mark_as_published(video_name, {
        "title": title,
        "description": description,
        "success_flags": success_flags,
        "recycled": is_recycled
    })
    
    # Move the published video to Published_Videos folder
    published_dir = "Published_Videos"
    if not os.path.exists(published_dir):
        os.makedirs(published_dir)
        
    try:
        dest_path = os.path.join(published_dir, video_name)
        shutil.move(video_path, dest_path)
        print(f"📦 Moved published video to {dest_path}")
    except Exception as e:
        print(f"❌ Failed to move published video: {e}")
    
    print("🎉 DAILY AUTOMATION COMPLETE")

if __name__ == "__main__":
    main()
