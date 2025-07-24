# Trigger-Aware Workflow Implementation

## Problem Solved

**Before**: The system was fetching the latest image immediately after camera connection and repeating every 7 seconds, instead of waiting for Line 0 hardware triggers.

**After**: The system now properly waits for Line 0 hardware triggers, captures only when triggered, processes the captured image, shows results, and then waits for the next trigger.

## Changes Made

### 1. New API Endpoints (`ml_api/views.py`)

#### `start_trigger_inspection()`
- **URL**: `POST /api/ml/inspection/start-trigger/`
- **Purpose**: Initializes camera connection and enables trigger mode
- **Returns**: Status indicating camera is ready and waiting for Line 0 trigger

#### `poll_trigger_results()`
- **URL**: `GET /api/ml/inspection/poll-trigger/`
- **Purpose**: Polls for new trigger results without immediately capturing
- **Returns**: Either "waiting for trigger" or "new result available"

### 2. Enhanced HikrobotCameraManager

#### New Methods Added:
- `clear_old_trigger_results()` - Prevents confusion from old trigger summaries
- `wait_for_next_trigger()` - Blocking wait for trigger events
- Enhanced trigger summary with precise timestamps

#### Improved Trigger Processing:
- Better timestamp handling for result detection
- Unix timestamps for precise timing comparisons
- Enhanced logging for trigger workflow completion

### 3. New UI Template (`ml_api/templates/ml_api/trigger_inspection.html`)

#### Features:
- **Real-time Status Updates**: Shows current trigger mode status
- **Polling-Based Results**: Polls for trigger results instead of immediate capture
- **Automatic Workflow**: After results, automatically starts next inspection
- **Test Trigger Button**: Software trigger for testing without hardware
- **Countdown Timer**: 7-second countdown before next inspection starts

### 4. Updated URL Configuration (`ml_api/urls.py`)

```python
# New trigger-aware workflow endpoints
path('inspection/start-trigger/', start_trigger_inspection, name='start_trigger_inspection'),
path('inspection/poll-trigger/', poll_trigger_results, name='poll_trigger_results'),
path('inspection/trigger/', trigger_inspection_page, name='trigger_inspection_page'),
```

### 5. Test Script (`test_trigger_workflow.py`)

Comprehensive testing script that:
- Tests camera connection
- Verifies trigger mode activation
- Simulates the complete workflow
- Sends software triggers for testing

## How the New Workflow Works

### Step 1: Start Inspection
```javascript
// Frontend calls
POST /api/ml/inspection/start-trigger/
```
- Connects camera if not connected
- Enables trigger mode (Line 0 monitoring)
- Returns "waiting for trigger" status

### Step 2: Wait for Trigger
```javascript
// Frontend polls every second
GET /api/ml/inspection/poll-trigger/
```
- Checks for new trigger results
- Returns either "still waiting" or "new result found"
- Does NOT capture images immediately

### Step 3: Trigger Detection
When Line 0 hardware signal is received:
- `HikrobotCameraManager._monitor_trigger_signal()` detects it
- Image is captured automatically
- Full YOLOv8 processing workflow executes
- Results are saved to database and files
- Trigger summary is created with timestamp

### Step 4: Results Display
- Polling detects new trigger summary
- Results are displayed to user
- 7-second countdown starts

### Step 5: Next Inspection
- After countdown, process repeats
- Camera remains in trigger mode
- System waits for next Line 0 signal

## Usage Instructions

### Option 1: Use New UI Page
1. Visit: `http://localhost:8000/api/ml/inspection/trigger/`
2. Click "Start New Inspection"
3. Send Line 0 hardware trigger signal
4. View results and wait for automatic restart

### Option 2: API Integration
```python
# Start trigger inspection
response = requests.post('/api/ml/inspection/start-trigger/')

# Poll for results
while True:
    response = requests.get('/api/ml/inspection/poll-trigger/')
    data = response.json()
    
    if data['new_result']:
        # Display results
        print(f"Result: {data['result']}")
        break
    elif data['waiting']:
        # Keep waiting
        time.sleep(1)
```

### Option 3: Test with Software Trigger
```python
# For testing without hardware trigger
requests.post('/api/ml/camera/trigger/test/')
```

## Testing the Implementation

### 1. Run Test Script
```bash
python test_trigger_workflow.py
```

### 2. Check Trigger Mode Status
```bash
curl http://localhost:8000/api/ml/camera/trigger/status/
```

### 3. Monitor Live Triggers
```bash
python test_trigger_mode.py
```

## Key Differences from Before

| Before | After |
|--------|-------|
| `get_current_frame_base64()` called immediately | `poll_trigger_results()` waits for actual triggers |
| 7-second timer fetched new images | 7-second timer waits for next trigger setup |
| No hardware trigger dependency | Requires Line 0 hardware signal |
| Continuous image fetching | Event-driven capture only |

## File Structure

```
ml_api/
├── views.py                           # Enhanced with trigger-aware endpoints
├── urls.py                           # New trigger workflow URLs
├── templates/ml_api/
│   └── trigger_inspection.html       # New trigger-aware UI
└── ...

test_trigger_workflow.py              # Comprehensive workflow test
TRIGGER_WORKFLOW_IMPLEMENTATION.md    # This documentation
```

## Expected Behavior Now

1. **Click "Start New Inspection"** → Camera connects, trigger mode enabled
2. **System waits** → No image capture until Line 0 signal
3. **Line 0 triggered** → Image captured and processed automatically
4. **Results displayed** → Same YOLOv8 processing as before
5. **7-second countdown** → Prepares for next trigger
6. **Process repeats** → Waits for next Line 0 signal

## Troubleshooting

### If triggers aren't detected:
1. Check camera connection: `GET /api/ml/camera/status/`
2. Verify trigger mode: `GET /api/ml/camera/trigger/status/`
3. Test with software trigger: `POST /api/ml/camera/trigger/test/`
4. Run test script: `python test_trigger_workflow.py`

### If results don't appear:
1. Check trigger summaries folder: `media/camera_captures/trigger_summaries/`
2. Verify database entries: Check `SimpleInspection` table
3. Check logs for trigger processing messages

The implementation now correctly waits for Line 0 hardware triggers instead of immediately fetching images, solving the original problem while maintaining all existing functionality.