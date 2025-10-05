#!/usr/bin/env python3
"""
Video Generator Module

This module generates videos from execution frames using FFmpeg.
It handles frame discovery, validation, and video compilation.
"""

import os
import glob
import subprocess


class VideoGenerator:
    """
    Generates videos from VirtualHome execution frames.

    Handles:
    - FFmpeg availability checking
    - Frame file discovery
    - Video generation and encoding
    """

    def __init__(self):
        """Initialize the video generator."""
        pass

    def generate_video(self, task, output_base_dir):
        """
        Generate video from execution frames.

        Args:
            task: Task dictionary
            output_base_dir: Base directory for output files

        Returns:
            bool: True if video generated successfully, False otherwise
        """
        print("Step 6: Generating video from execution")

        # Check FFmpeg availability
        if not self._check_ffmpeg():
            print("Skipping video generation (FFmpeg not installed)")
            return False

        try:
            # Check multiple output directories, including subdirectories
            # VirtualHome saves to: output_folder/file_name_prefix/0/Action_*.png
            possible_dirs = [
                os.path.join(output_base_dir, f"pddl_task_{task['id']}", '0'),  # VH subdirectory (most likely)
                os.path.join(output_base_dir, f"pddl_task_{task['id']}"),  # VH without /0
                os.path.join(output_base_dir, 'Output', f"pddl_task_{task['id']}", '0'),  # core/Output/task/0
                os.path.join(output_base_dir, '..', 'Output', f"pddl_task_{task['id']}", '0'),  # parent/Output/task/0
                output_base_dir  # core/ directory itself
            ]

            png_files = []
            output_dir = None

            # Search for PNG files in possible directories
            for dir_path in possible_dirs:
                if os.path.exists(dir_path):
                    # Try different naming patterns
                    patterns = [
                        "Action_*_normal.png",  # VirtualHome default format
                        "Action_*.png",
                        f"pddl_task_{task['id']}_*.png",
                        f"*task_{task['id']}*.png",
                        "*.png"
                    ]

                    for pattern in patterns:
                        found_files = glob.glob(os.path.join(dir_path, pattern))
                        if found_files:
                            png_files = found_files
                            output_dir = dir_path
                            print(f"Found {len(png_files)} PNG files in {dir_path} with pattern {pattern}")
                            break

                    if png_files:
                        break

            if not png_files:
                print("No PNG files found for video generation")
                print("Searched in directories:")
                for d in possible_dirs:
                    if os.path.exists(d):
                        print(f"  - {d}: {os.listdir(d)}")
                return False

            png_files = sorted(png_files)
            print(f"Found {len(png_files)} frames")

            # Ensure task-specific directory exists
            task_dir = os.path.join(output_base_dir, f"task_{task['id']}")
            os.makedirs(task_dir, exist_ok=True)

            # Generate video in task directory
            video_filename = f"{task['title'].replace(' ', '_')}.mp4"
            video_path = os.path.join(task_dir, video_filename)

            # Use glob pattern for FFmpeg input - more flexible than numeric patterns
            # This handles variable-width frame numbers (e.g., 0, 1, 2... or 0000, 0001, 0002...)
            first_file = os.path.basename(png_files[0])

            # Determine glob pattern based on filename structure
            if "Action_" in first_file and "_normal.png" in first_file:
                # VirtualHome format: Action_X_0_normal.png (X = variable-width number)
                glob_pattern = os.path.join(output_dir, "Action_*_0_normal.png")
            elif "Action_" in first_file:
                glob_pattern = os.path.join(output_dir, "Action_*.png")
            else:
                # Generic fallback
                base_name = first_file.split('_')[0]
                glob_pattern = os.path.join(output_dir, f"{base_name}_*.png")

            ffmpeg_cmd = [
                'ffmpeg', '-y',
                '-framerate', '3',
                '-pattern_type', 'glob',  # Enable glob pattern matching
                '-i', glob_pattern,  # Use glob pattern instead of numeric pattern
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',
                '-vf', 'scale=800:600',
                video_path
            ]

            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)

            if result.returncode == 0:
                if os.path.exists(video_path):
                    file_size = os.path.getsize(video_path) / (1024 * 1024)  # MB
                    print(f"Video generated successfully!")
                    print(f"   Path: {video_path}")
                    print(f"   Size: {file_size:.1f} MB")
                    print(f"   Frames: {len(png_files)}")

                    # Clean up PNG frames after successful video generation
                    import shutil
                    try:
                        # Remove the PNG frames directory
                        frames_dir = os.path.dirname(png_files[0])
                        parent_dir = os.path.dirname(frames_dir)  # pddl_task_{id}/0 -> pddl_task_{id}
                        if os.path.exists(parent_dir) and f"pddl_task_{task['id']}" in parent_dir:
                            shutil.rmtree(parent_dir)
                            print(f"   Cleaned up PNG frames")
                    except Exception as e:
                        print(f"   Warning: Could not clean up PNG frames: {e}")

                    return True
                else:
                    print(f"Video file not found after FFmpeg completion")
                    return False
            else:
                print(f"FFmpeg failed:")
                print(f"   Command: {' '.join(ffmpeg_cmd)}")
                print(f"   Error: {result.stderr}")
                return False

        except Exception as e:
            print(f"Video generation error: {e}")
            return False

    def _check_ffmpeg(self):
        """
        Check if FFmpeg is installed.

        Returns:
            bool: True if FFmpeg is available, False otherwise
        """
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                print(f"  ✅ FFmpeg found: {version_line}")
                return True
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        print("  ❌ FFmpeg not found")
        print("  Please install FFmpeg:")
        print("    macOS: brew install ffmpeg")
        print("    Ubuntu: apt-get install ffmpeg")
        print("    Windows: Download from https://ffmpeg.org/download.html")
        return False
