# VirtualHome Robotics LLM PDDL Task Solver

## 🎯 Complete Working Algorithm: Task → PDDL → Gemini → VirtualHome

This project implements a generalized task-solving system that uses PDDL planning and LLM reasoning to solve household tasks in VirtualHome.

## 🏗️ System Architecture

### Core Algorithm Flow:
1. **Task Input**: Any household task description (e.g., "Write an email")
2. **PDDL Generation**: Convert task to Planning Domain Definition Language
3. **LLM Reasoning**: Use Gemini to solve PDDL and generate action sequences
4. **Object Mapping**: Map generic objects to actual scene object IDs
5. **Action Validation**: Ensure all actions are supported by VirtualHome
6. **Execution**: Run actions in VirtualHome with video recording
7. **Verification**: Check actual task completion in environment

## 📁 Key Files

### Main Components:
- `task_solver.py` - Complete PDDL+LLM task solving algorithm
- `visual_demo.py` - Basic VirtualHome demo script
- `simple_test.py` - Test basic functionality with proper scene setup
- `diagnose_task.py` - Diagnostic tool showing apartment objects

### Utilities:
- `create_video.py` - Convert PNG sequences to MP4 videos
- `video_viewer.py` - View generated task videos
- `main.py` - Entry point (customizable)

## 🚀 Quick Start

### 1. Run Complete Task Solver:
```bash
python3.13 task_solver.py
```
**Features:**
- Solves any task from the dataset
- Full PDDL+Gemini reasoning pipeline
- Proper object mapping and validation
- Video recording with verification

### 2. Test Basic Functionality:
```bash
python3.13 simple_test.py
```
**Tests:** Basic agent movement and object interaction

### 3. Understand Apartment Layout:
```bash
python3.13 diagnose_task.py
```
**Shows:** Available objects, rooms, and object ID mappings

### 4. View Generated Videos:
```bash
python3.13 video_viewer.py
python3.13 create_video.py  # Convert PNG sequences to MP4
```

## 🎮 Dataset Structure

### Location: `virtualhome/virtualhome/dataset/programs_processed_precond_nograb_morepreconds/`

#### Key Directories:
- `executable_programs/` - Programs with scene-specific object IDs
- `init_and_final_graphs/` - Scene graphs for each task
- `withoutconds/` - Original task descriptions
- `initstate/` - Task preconditions

#### Available Scenes:
- TrimmedTestScene1_graph through TrimmedTestScene7_graph

#### Example Tasks:
- file1003_2.txt: "Write an email"
- file1004_2.txt: "Put groceries in Fridge"
- file1007_2.txt: "Go to toilet"

## ⚙️ Technical Details

### Object Mapping System:
The algorithm maps generic object names to actual scene IDs:
```
chair → ID 373
computer → ID 434
bedroom → ID 74
```

### Supported Actions:
- WALK, RUN, FIND, SIT, GRAB, PUT
- TOUCH, SWITCHON, SWITCHOFF
- OPEN, CLOSE

### Action Validation:
- Replaces unsupported actions (TYPE → TOUCH)
- Filters out non-essential actions (TURNTO, LOOKAT)
- Ensures proper action sequencing (FIND before SIT)

### Consequence Handling:
- Closes what you open (fridge, doors)
- Turns off appliances after use
- Maintains proper environment state

## 🎥 Video Output

Videos are generated in: `Output/task_*/`
- PNG sequences: Individual frame captures
- MP4 videos: Complete task recordings (via create_video.py)
- Scene info: JSON metadata for each recording

## 🔧 Configuration

### API Setup:
Set Gemini API key in `task_solver.py`:
```python
api_key = 'your_gemini_api_key_here'
```

### Scene Setup:
- Scene 0: TrimmedTestScene1_graph (default)
- Character starts in kitchen
- Task-specific scene graph loaded automatically

## ✅ Verified Working Features

1. **Generalized Task Solving**: Works on any household task
2. **PDDL+LLM Integration**: Proper reasoning and planning
3. **Object Mapping**: Automatic scene object discovery
4. **Action Execution**: Reliable VirtualHome integration
5. **Video Generation**: Complete task recordings
6. **Consequence Handling**: Proper cleanup behavior
7. **Multi-Task Support**: Can run on all dataset tasks

## 🏠 Apartment Layout

The system works with a fully furnished apartment containing:
- **Rooms**: Kitchen, bedroom, bathroom, living room, office
- **Furniture**: Chairs, desks, beds, tables
- **Appliances**: Computer, fridge, stove, microwave
- **Interactive Objects**: Keyboard, mouse, doors, books

Use `diagnose_task.py` to see complete object inventory and IDs.

## 📊 Success Metrics

- **Script Execution**: Actions execute without errors
- **Task Completion**: Environment state changes verified
- **Video Quality**: Clear agent movement and interactions
- **Object Interaction**: Proper finding, grabbing, using objects
- **Cleanup Behavior**: Maintains proper environment state

The algorithm successfully demonstrates **one-shot task solving** using PDDL+LLM reasoning without hardcoded solutions.