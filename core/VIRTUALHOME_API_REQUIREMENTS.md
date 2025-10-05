# VirtualHome API Requirements & Limitations

## Simulator Configuration

### Timeout Settings
- **Default timeout**: 30 seconds (too short for complex tasks)
- **Recommended timeout**: 240 seconds
- **Location**: `comm_unity.UnityCommunication.timeout_wait`
- **Setting**: `self.comm.timeout_wait = 240` after initialization

### Recorder Frame Limits
- **Issue**: Simulator has internal frame counter that accumulates across tasks
- **Symptom**: "Recorder 0: Max frame number exceeded 0" error
- **Solution**: Restart simulator between tasks (disable reuse)
- **Impact**: Slightly slower (2s startup per task) but prevents crashes

### Processing Time Limit
- **Parameter**: `processing_time_limit` in `render_script()`
- **Recommended value**: 300 seconds
- **Purpose**: Internal VirtualHome processing timeout

## render_script() Parameters

Required parameters for PNG frame generation:

```python
execution_success, message = comm.render_script(
    script,                          # VirtualHome action list
    recording=True,                  # REQUIRED: Enable frame recording
    find_solution=True,              # Try to complete partial scripts
    frame_rate=3,                    # Frames per second
    camera_mode=["PERSON_FROM_BACK"], # Camera perspective
    file_name_prefix="task_X",       # Output file prefix
    output_folder="Output/",         # REQUIRED: Where to save frames
    processing_time_limit=300,       # Internal processing timeout (seconds)
    skip_execution=False,            # Must be False to execute
    image_synthesis=["normal"],      # REQUIRED: Frame image type
    save_pose_data=False             # Optional: Save character pose data
)
```

### Critical Parameters
1. **recording=True** - Without this, no frames are generated
2. **output_folder** - Must specify, or frames go to default location
3. **image_synthesis=["normal"]** - Generates the Action_*_normal.png files

### Frame Output
- **Pattern**: `Action_{N}_0_normal.png` where N is variable-width (0, 1, ..., 9, 10, ...)
- **Location**: `{output_folder}/{file_name_prefix}/0/`
- **Cameras**: Multiple cameras create subdirectories (0, 1, 2, ...)

## Action Constraints

### Invalid Actions
These PDDL actions may generate but fail in VirtualHome:

1. **SWITCHON on non-appliances**
   - ❌ `[SWITCHON] <remotecontrol>` - Remote is grabbable, not switchable
   - ❌ `[SWITCHON] <furniture>` - Furniture can't be switched
   - ✅ `[SWITCHON] <tv>`, `[SWITCHON] <computer>` - Appliances work

2. **Navigation to inaccessible rooms**
   - ❌ `[WALK] <livingroom>` - May have collision/pathfinding issues
   - ✅ `[WALK] <bathroom>`, `[WALK] <bedroom>` - Usually accessible

3. **Object type mismatches**
   - Objects must have appropriate properties for actions
   - Check `properties` field in scene graph

### Common VirtualHome Error Messages

| Error | Meaning | Solution |
|-------|---------|----------|
| `Script is impossible to execute` | Action preconditions not met or invalid action | Revise PDDL domain/problem |
| `Max frame number exceeded` | Recorder buffer full | Restart simulator |
| `Read timed out. (read timeout=N)` | HTTP request exceeded N seconds | Increase `timeout_wait` |
| `Path partially completed` | Navigation failed due to collision | Spatial constraint, not code bug |

## Scene Graph API

### Getting Environment Graph
```python
success, scene_graph = comm.environment_graph()
```

**Returns**:
- `success`: Boolean indicating if graph was retrieved
- `scene_graph`: Dictionary with structure:
  ```python
  {
      'nodes': [
          {
              'id': 123,                    # Object instance ID
              'class_name': 'fridge',       # Object type
              'category': 'Furniture',      # Category
              'properties': ['CAN_OPEN', 'CONTAINERS'],  # Interaction properties
              'states': ['CLOSED'],         # Current states
              'bounding_box': {...}         # 3D position/size
          },
          ...
      ],
      'edges': [...]  # Spatial relationships
  }
  ```

### Object ID Mapping
- **ID = 1**: Fallback ID when object not found in scene
- **ID > 1**: Valid object instance in scene
- Use ID for actions: `<char0> [FIND] <fridge> (306)`

## Simulator Lifecycle

### Initialization
```python
comm = comm_unity.UnityCommunication(
    file_name=simulator_path,
    port="8080"
)
comm.timeout_wait = 240  # Set timeout AFTER initialization
```

### Reset Scene
```python
comm.reset(0)  # Reset to empty scene
comm.expand_scene(initial_graph)  # Load scene graph
comm.add_character('Chars/Male2', initial_room='kitchen')
```

### Cleanup
```python
comm.close()  # Terminate simulator process
```

## Best Practices

### 1. Always Restart Simulator Between Tasks
```python
if self.comm is not None:
    self.comm.close()
    self.comm = None
# Then reinitialize
```

### 2. Validate Scene Graph Before Use
```python
if scene_graph is None:
    print("Error: scene_graph is None")
    return None

if 'nodes' not in scene_graph or scene_graph['nodes'] is None:
    print("Error: scene_graph has no 'nodes'")
    return None
```

### 3. Check Object IDs Before Spawning
```python
for obj_name, obj_id in script_objects_with_ids.items():
    if obj_id == 1:  # Fallback ID = object not found
        print(f"Warning: {obj_name} not in scene")
```

### 4. Handle Timeouts Gracefully
```python
try:
    success, message = comm.render_script(...)
except UnityCommunicationException as e:
    if "Read timed out" in str(e):
        print("Task exceeded timeout, restarting simulator...")
        comm.close()
        # Reinitialize
```

### 5. Use Glob Patterns for Frame Detection
```python
# ❌ Numeric pattern - fails for variable-width numbers
input_pattern = os.path.join(output_dir, "Action_%04d_0_normal.png")

# ✅ Glob pattern - works for all frame counts
glob_pattern = os.path.join(output_dir, "Action_*_0_normal.png")
```

## Performance Characteristics

### Typical Execution Times
- Simple tasks (1-3 actions): 5-15 seconds
- Medium tasks (4-6 actions): 30-60 seconds
- Complex tasks (7+ actions): 60-180 seconds

### Frame Counts
- Simple navigation: 20-50 frames
- Object interaction: 100-500 frames
- Complex multi-step: 1000-2500 frames

### Memory Usage
- Each frame: ~50-100 KB
- 1000 frames: ~50-100 MB disk space
- Video (H.264): 1-3 MB per 1000 frames

## Known Issues

1. **Living Room Navigation**
   - Spatial constraint in default scene
   - Many tasks fail with "Path partially completed"
   - Not a code bug - VirtualHome scene limitation

2. **Remote Control**
   - Classified as grabbable, not switchable
   - `SWITCHON` action fails
   - Use `GRAB` and `TOUCH` instead

3. **Fridge Object Type**
   - Sometimes classified as `furniture` instead of `appliance`
   - May cause PDDL type errors
   - Solution: Declare as `container` type

4. **LLM Timeouts**
   - Gemini API may timeout on complex tasks (60s)
   - Retry mechanism handles this
   - 3 attempts before failure

## Version Info

- **VirtualHome Version**: 2.2.4
- **Unity Backend**: Batchmode (headless)
- **HTTP API**: Port 8080 (default)
- **Python API**: `unity_simulator.comm_unity`

## References

- VirtualHome Documentation: http://virtual-home.org
- Scene Graphs: TrimmedTestScene1_graph (default)
- Task Dataset: programs_processed_precond_nograb_morepreconds
