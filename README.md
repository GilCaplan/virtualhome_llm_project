# 🤖 VirtualHome PDDL-Centric Task Solver

**Complete PDDL-centric system for autonomous household task execution using structured planning and LLM reasoning.**

## 🎯 Quick Start

```bash
# Run the complete PDDL-centric pipeline
python3.13 core/pddl_virtualhome_system.py

# Test basic functionality
python3.13 tests/simple_test.py

# Understand apartment layout
python3.13 tests/diagnose_task.py

# View generated videos
python3.13 utils/video_viewer.py
```

> **All commands should be run from the project root directory**

## 📁 Project Structure

```
robotics/
├── 📂 core/                    # Main PDDL-centric system
│   ├── pddl_virtualhome_system.py  # Complete PDDL pipeline
│   └── README.md                    # Core system documentation
│
├── 📂 utils/                   # Utilities
│   ├── create_video.py             # PNG → MP4 video conversion
│   └── video_viewer.py             # Video viewing tool
│
├── 📂 tests/                   # Testing & diagnostics
│   ├── simple_test.py              # Basic functionality test
│   └── diagnose_task.py            # Apartment layout diagnostic
│
├── 📂 docs/                    # Documentation
│   └── CLAUDE.md                   # Complete system guide
│
├── 📂 Output/                  # Generated videos & recordings
├── 📂 virtualhome/             # VirtualHome dataset & simulator
└── README.md                   # This file
```

## 🧠 PDDL-Centric Architecture

The system implements a clean 6-step pipeline:

1. **Scene + Task Loading** → Load VirtualHome scene and task from dataset
2. **PDDL Problem Generation** → Convert scene graph and task to structured PDDL problem
3. **LLM PDDL Solving** → Gemini 1.5 Flash solves PDDL problem and returns structured plan
4. **PDDL → VirtualHome Conversion** → Convert PDDL actions to VirtualHome script commands
5. **Execution + Verification** → Execute script and verify completion through state analysis
6. **Video Generation** → Automatically create MP4 video from execution frames

## ✨ Key Features

- **🎯 PDDL-Centric**: All reasoning done through structured PDDL planning
- **🧠 LLM Integration**: Gemini 1.5 Flash for PDDL problem solving
- **🏠 Real Environment**: Full apartment simulation with VirtualHome
- **🎥 Auto Video**: Automatic MP4 generation from execution frames
- **✅ State Verification**: Compares environment states before/after execution
- **🔧 Object Mapping**: Automatic mapping from PDDL objects to scene IDs
- **🔄 Proper Cleanup**: PDDL domain includes responsible behavior constraints

## 🚀 Algorithm Pipeline

```
Task: "Write an email"
    ↓
PDDL Problem: (domain virtualhome) (problem write-an-email) with objects, initial state, goal
    ↓
Gemini Solves: (:plan (walk agent kitchen bedroom) (find-object agent computer bedroom) ...)
    ↓
VH Script: [WALK] <bedroom> (74), [FIND] <computer> (434), [SIT] <chair> (373) ...
    ↓
Execution: VirtualHome runs script with recording
    ↓
Verification: Check if computer turned ON, agent sitting, etc.
    ↓
Video: Auto-generated task_0_Write_an_email.mp4
```

## 🎮 PDDL Domain

The system includes a comprehensive VirtualHome PDDL domain with:

**Actions**: `walk`, `find-object`, `sit-down`, `switch-on`, `switch-off`, `touch-object`, `open-container`, `close-container`

**Predicates**: `at(agent, location)`, `sitting(agent)`, `on(appliance)`, `open(container)`, `accessible(object)`

**Types**: `agent`, `room`, `furniture`, `appliance`, `container`, `interactive-object`

## 📖 Documentation

See `core/README.md` for detailed technical documentation and API reference.

## 🎯 Example Tasks

- **Email Writing**: Walk to bedroom → Find chair → Sit → Turn on computer → Use keyboard
- **Food Storage**: Walk to kitchen → Open fridge → Store items → Close fridge
- **Navigation**: Move between rooms → Use doors → Reach target locations
- **Appliance Control**: Find appliances → Turn on/off → Proper cleanup

## 🔧 Requirements

- Python 3.13+
- VirtualHome simulator (`macos_exec.2.2.4.app`)
- Google Gemini API key
- FFmpeg for video generation
- Dependencies: `google-generativeai`

## 📝 Example Result

```
Task: Write an email
PDDL Problem: Generated with 40 objects, 35 init conditions
PDDL Solution: 6-step plan from Gemini
VH Script: 8 actions with proper object IDs
Execution: SUCCESS
Verification: Computer turned ON, agent sitting
Video: task_0_Write_an_email.mp4 generated
```

**The system demonstrates pure PDDL-based task solving with LLM reasoning - no hardcoded task-specific solutions.**