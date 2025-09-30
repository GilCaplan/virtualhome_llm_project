#!/usr/bin/env python3

import os
import glob
import subprocess
import sys

def find_video_files():
    """Find all video-related files in Output directory"""
    base_dir = "/Users/USER/Desktop/University/Semester 6/robotics"

    # Look for Output directories
    output_dirs = []
    for root, dirs, files in os.walk(base_dir):
        if 'Output' in root or 'output' in root:
            output_dirs.append(root)

    print(f"Found {len(output_dirs)} output directories:")
    for dir_path in output_dirs:
        print(f"  {dir_path}")

        # List contents
        try:
            contents = os.listdir(dir_path)
            if contents:
                print(f"    Contents: {contents}")

                # Look for video files or subdirectories
                for item in contents:
                    item_path = os.path.join(dir_path, item)
                    if os.path.isdir(item_path):
                        sub_contents = os.listdir(item_path)
                        print(f"      {item}/: {sub_contents}")

                        # Check for video files or scene info
                        for sub_item in sub_contents:
                            sub_item_path = os.path.join(item_path, sub_item)
                            if os.path.isfile(sub_item_path):
                                if sub_item.endswith(('.mp4', '.avi', '.mov', '.json')):
                                    print(f"        📁 {sub_item_path}")
            else:
                print("    (empty)")
        except PermissionError:
            print("    (permission denied)")

def find_unity_output():
    """Look for unity simulator output directory"""
    unity_paths = [
        "/Users/USER/Desktop/University/Semester 6/robotics/virtualhome/virtualhome/simulation/unity_simulator/output",
        "/Users/USER/Desktop/University/Semester 6/robotics/virtualhome/virtualhome/simulation/unity_simulator/Output"
    ]

    for path in unity_paths:
        if os.path.exists(path):
            print(f"Found Unity output directory: {path}")
            try:
                contents = os.listdir(path)
                print(f"Contents: {contents}")

                for item in contents:
                    item_path = os.path.join(path, item)
                    if os.path.isdir(item_path):
                        sub_contents = os.listdir(item_path)
                        print(f"  {item}/: {sub_contents}")
            except Exception as e:
                print(f"Error reading {path}: {e}")

def play_video(video_path):
    """Play video using system default player"""
    try:
        if sys.platform == "darwin":  # macOS
            subprocess.run(["open", video_path])
        elif sys.platform == "linux":
            subprocess.run(["xdg-open", video_path])
        elif sys.platform == "win32":
            os.startfile(video_path)
        else:
            print(f"Please manually open: {video_path}")
    except Exception as e:
        print(f"Error opening video: {e}")

def main():
    print("=== VirtualHome Video Viewer ===")
    print("Searching for generated videos and output files...\n")

    # Check main Output directory
    find_video_files()

    print("\n" + "="*50)

    # Check Unity simulator output
    find_unity_output()

    print("\n" + "="*50)

    # Look for any video files in the project
    base_dir = "/Users/USER/Desktop/University/Semester 6/robotics"
    video_extensions = ['*.mp4', '*.avi', '*.mov', '*.mkv']

    all_videos = []
    for ext in video_extensions:
        videos = glob.glob(os.path.join(base_dir, "**", ext), recursive=True)
        all_videos.extend(videos)

    if all_videos:
        print(f"Found {len(all_videos)} video files:")
        for i, video in enumerate(all_videos):
            print(f"  {i+1}. {video}")

        try:
            choice = input(f"\nEnter number to play (1-{len(all_videos)}) or 'q' to quit: ")
            if choice.lower() != 'q':
                video_idx = int(choice) - 1
                if 0 <= video_idx < len(all_videos):
                    print(f"Playing: {all_videos[video_idx]}")
                    play_video(all_videos[video_idx])
                else:
                    print("Invalid selection")
        except (ValueError, KeyboardInterrupt):
            pass
    else:
        print("No video files found in the project directory")
        print("\nTip: Videos might be generated in:")
        print("- virtualhome/virtualhome/simulation/unity_simulator/output/")
        print("- Output/ directory")
        print("- Check if the script completed successfully before videos are generated")

if __name__ == "__main__":
    main()