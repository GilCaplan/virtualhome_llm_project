# 🤖 VirtualHome PDDL System - Core Implementation

**PDDL-centric system for autonomous household task execution with structured planning and LLM reasoning.**

## 📁 Core System

The system is implemented in a single comprehensive module:

### **PDDL VirtualHome System** (`pddl_virtualhome_system.py`)
- Complete 6-step PDDL-centric pipeline
- VirtualHome PDDL domain definition
- Scene-to-PDDL problem conversion
- Gemini LLM PDDL solver integration
- PDDL-to-VirtualHome script conversion
- Execution and state-based verification
- Automatic video generation

## 🚀 How It Works

**Pipeline**: Scene + Task → PDDL Problem → LLM Solves PDDL → PDDL to VH Script → Execute + Verify → Generate Video

1. **Load Scene + Task**: Load VirtualHome scene with dataset initial state and task description
2. **Create PDDL Problem**: Convert scene graph and task to structured PDDL problem with domain, objects, init, goal
3. **Solve with LLM**: Gemini 1.5 Flash solves PDDL problem and returns structured action plan
4. **Convert to VH Script**: Map PDDL actions to VirtualHome script commands with correct object IDs
5. **Execute**: Run VirtualHome script with recording and frame capture
6. **Verify Completion**: Compare initial vs final environment states to check task completion
7. **Generate Video**: Automatically create MP4 video from captured PNG frames

## 🎮 How to Run

### Run Complete PDDL Pipeline
```bash
cd core/
python3.13 pddl_virtualhome_system.py
# Runs Task 0 (Write an email) by default
```

### Run Specific Task
```python
from pddl_virtualhome_system import PDDLVirtualHomeSystem

api_key = 'AIzaSyDlNUlJOXiH_30MvY-mmSpWLVsezTG3kMQ'
simulator_path = '../macos_exec.2.2.4.app'
system = PDDLVirtualHomeSystem(simulator_path, api_key)

# Run specific task (0-9)
success = system.run_complete_pipeline(task_id=2)  # Go to toilet
```

## 📊 Task Verification

The system uses **environment state analysis** to verify actual task completion:

- **Email Tasks**: Checks if computer is turned ON after execution
- **Fridge Tasks**: Verifies fridge opened then properly closed
- **Navigation Tasks**: Confirms agent reached target location
- **Generic Tasks**: Analyzes significant environment changes

## 📁 Output Files

- `Output/pddl_task_*_Write_an_email.mp4` - **Automatically generated videos** of task execution
- `Output/pddl_task_*.png` - Individual PNG frame captures from VirtualHome execution

## ✅ Key Features

- **PDDL-Centric**: All reasoning through structured PDDL planning
- **LLM-Powered**: Gemini 1.5 Flash solves PDDL problems
- **State-Verified**: Checks actual environment changes, not just execution
- **Auto-Video**: Automatically generates MP4 videos from task execution
- **Object-Mapped**: Automatic mapping from PDDL to VirtualHome object IDs

## 🔧 Requirements

- Python 3.13+
- VirtualHome simulator (`macos_exec.2.2.4.app`)
- Google Gemini API key
- Dependencies: `google-generativeai`, `json`, `glob`, `subprocess`
- **FFmpeg** installed for video generation

## 📝 Example Result

```
Task 0: Write an email
PDDL Problem: Generated with 40 objects, 35 init conditions
PDDL Solution: 6-step plan from Gemini
VH Script: 8 actions with proper object IDs
Execution: SUCCESS
Verification: Computer turned ON, agent sitting
Video: pddl_task_0_Write_an_email.mp4 generated
```

The system demonstrates **pure PDDL-based task solving** with LLM reasoning - no hardcoded task-specific solutions.