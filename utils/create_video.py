#!/usr/bin/env python3

import os
import subprocess
import glob
import sys

def create_video_from_pngs(png_dir, output_video):
    """Convert PNG sequence to MP4 video using ffmpeg"""

    # Check if ffmpeg is available
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: ffmpeg not found. Install with: brew install ffmpeg")
        return False

    try:
        # Find all PNG files
        png_files = glob.glob(os.path.join(png_dir, "Action_*.png"))
        if not png_files:
            print(f"No Action_*.png files found in {png_dir}")
            return False

        # Sort by action number
        png_files.sort(key=lambda x: int(x.split('Action_')[1].split('_')[0]))
        print(f"Found {len(png_files)} PNG frames")

        # Create video using ffmpeg
        # Use the directory pattern and let ffmpeg handle the sequence
        png_pattern = os.path.join(png_dir, "Action_%04d_0_normal.png")

        cmd = [
            'ffmpeg', '-y',  # -y to overwrite output file
            '-framerate', '5',  # 5 fps
            '-i', png_pattern,
            '-vf', 'scale=640:480',  # Scale to reasonable size
            '-pix_fmt', 'yuv420p',  # Ensure compatibility
            '-c:v', 'libx264',
            output_video
        ]

        print(f"Creating video: {output_video}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"✅ Video created successfully: {output_video}")
            return True
        else:
            print(f"❌ Error creating video: {result.stderr}")
            return False

    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    base_dir = "/Users/USER/Desktop/University/Semester 6/robotics/Output"

    if not os.path.exists(base_dir):
        print(f"Output directory not found: {base_dir}")
        return

    print("=== VirtualHome Video Creator ===")
    print("Converting PNG sequences to MP4 videos...\n")

    # Find all task directories
    task_dirs = []
    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)
        if os.path.isdir(item_path) and item.startswith('task_'):
            task_dirs.append((item, item_path))

    if not task_dirs:
        print("No task directories found")
        return

    created_videos = []

    for task_name, task_path in task_dirs:
        print(f"Processing task: {task_name}")

        # Look for subdirectories with PNG files
        for sub_item in os.listdir(task_path):
            sub_path = os.path.join(task_path, sub_item)
            if os.path.isdir(sub_path):
                # Check if this directory has PNG files
                png_files = glob.glob(os.path.join(sub_path, "Action_*.png"))
                if png_files:
                    # Create video for this sequence
                    video_name = f"{task_name}_{sub_item}.mp4"
                    video_path = os.path.join(base_dir, video_name)

                    if create_video_from_pngs(sub_path, video_path):
                        created_videos.append(video_path)
                    print()

    print("="*50)
    if created_videos:
        print(f"Created {len(created_videos)} videos:")
        for video in created_videos:
            print(f"  📹 {video}")

        # Offer to play the first video
        if sys.platform == "darwin":  # macOS
            try:
                choice = input(f"\nPlay first video? (y/n): ")
                if choice.lower() == 'y':
                    subprocess.run(["open", created_videos[0]])
            except KeyboardInterrupt:
                pass
    else:
        print("No videos were created")

if __name__ == "__main__":
    main()