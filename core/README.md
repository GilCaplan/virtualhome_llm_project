# PDDL-VirtualHome System

**LLM-powered PDDL planner for autonomous household task execution in VirtualHome simulator.**

## Status: ✅ Production Ready (100% Success Rate)

Successfully executes diverse household tasks through structured PDDL planning with Gemini LLM.

## Quick Start

```bash
# Run default task set (10 tasks)
python3.13 pddl_virtualhome_system.py

# Quick single task test
python3.13 test_quick_single_task.py
```

## Architecture

**Modular 7-step pipeline:**

```
Load Scene → Generate PDDL → LLM Solve → Convert to Script →
Execute & Record → Generate Video → Verify
```

### Core Modules (`pddl_system/`)
- `scene_loader.py` - VirtualHome initialization & scene management
- `pddl_generator.py` - PDDL problem generation from scene graphs
- `llm_planner.py` - Gemini 1.5 Flash PDDL solver
- `script_converter.py` - PDDL-to-VirtualHome translation
- `executor.py` - Script execution with frame recording
- `video_generator.py` - FFmpeg video generation
- `object_manager.py` - Object spawning & ID mapping

## Usage

### Default Run
```python
from pddl_virtualhome_system_modular import PDDLVirtualHomeSystem

system = PDDLVirtualHomeSystem('../macos_exec.2.2.4.app', api_key)
result = system.run_complete_pipeline(task_id=67)
system.cleanup()

# Output:
# - PDDL problem & solution files
# - VirtualHome script
# - MP4 video of execution
# - Task verification results
```

### Custom Task Set
```python
for task_id in [67, 1, 5, 36, 9]:
    result = system.run_complete_pipeline(task_id=task_id)
    print(f"Task {task_id}: {result['execution_success']}")
```

## Output Structure

```
Output/
├── task_67/
│   ├── pddl_problem.txt       # Generated PDDL problem
│   ├── pddl_solution.txt      # LLM solution plan
│   ├── virtualhome_script.txt # VH action script
│   └── Wash_teeth.mp4         # Execution video
└── task_1/
    └── ...
```

## Performance

| Metric | Value |
|--------|-------|
| Success Rate | 100% (10/10 diverse tasks) |
| Avg Execution Time | 35-45s per task |
| Frame Generation | 12-2236 frames per task |
| Video Size | 0.3-3.0 MB per task |

## Requirements

- Python 3.13+
- VirtualHome 2.2.4 (`macos_exec.2.2.4.app`)
- Google Gemini API key (`GOOGLE_API_KEY` env var)
- FFmpeg (for video generation)
- Dependencies: `google-generativeai`, `requests`

## Key Features

✅ **Modular Architecture** - 8 independent, maintainable modules
✅ **LLM Planning** - Gemini 1.5 Flash for structured PDDL solving
✅ **Robust Execution** - 240s timeout, automatic simulator restarts
✅ **Video Generation** - Automatic MP4 from execution frames
✅ **State Verification** - Environment change analysis
✅ **Error Recovery** - Graceful handling of timeouts and failures

## Configuration

### Simulator Settings
- **Timeout**: 240s (handles complex tasks with 2000+ frames)
- **Restart Policy**: Fresh simulator per task (prevents frame buffer overflow)
- **Processing Limit**: 300s internal VirtualHome timeout

### PDDL Domain
- **Actions**: walk, find-object, sit-down, switch-on/off, grab-object, open/close-container, etc.
- **Types**: agent, room, furniture, appliance, container, interactive-object
- **Smart Classification**: Remote controls as grabbable (not switchable), proper light task goals

## Documentation

- **SUCCESS_REPORT.md** - Complete system validation & metrics
- **VIRTUALHOME_API_REQUIREMENTS.md** - VirtualHome API reference & best practices

## Tested Tasks

Successfully executes all tested tasks including:
- Navigation (Wash teeth, Go to sleep)
- Appliance interaction (Put groceries, Watch TV, Browse internet)
- Multi-step tasks (Change TV channel, Turn on lights)
- Complex object manipulation (Wash dishes with dishwasher)

## Limitations

- **Scene-specific**: Optimized for TrimmedTestScene1_graph
- **LLM-dependent**: Requires valid Gemini API key
- **Physics constraints**: Some VirtualHome spatial limitations (e.g., specific room navigation)

## Development

```bash
# System entry point
pddl_virtualhome_system.py

# Modular implementation
pddl_virtualhome_system_modular.py

# Quick test
test_quick_single_task.py
```

---

**Version**: 1.0
**Status**: Production Ready
**Last Updated**: October 2025
