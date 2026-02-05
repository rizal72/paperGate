# Time Machine Screen for paperGate

## Overview

The Time Machine screen provides real-time monitoring of macOS Time Machine backups stored on a Raspberry Pi TimeCapsule server.

## Architecture

```
Mac (Time Machine Client)
         ↓ (SMB3)
Raspberry Pi (TimeCapsule-Pi)
    ↓
External USB Drive (/mnt/timecapsule)
    ↓
MBP16diRiccardo.sparsebundle
    ├── com.apple.TimeMachine.Results.plist  ← INAFFIDABILE (always Running=true)
    └── com.apple.TimeMachine.SnapshotHistory.plist  ← AFFIDABILE (true backup data)
```

### TimeCapsule-Pi Integration

- **Server**: Samba 4.x with vfs_fruit module for macOS compatibility
- **Protocol**: SMB3 (forced, SMB1 disabled)
- **Storage**: External USB drive formatted ext4 (916 GB total capacity)
- **Quota**: 1TB configured in `/etc/samba/smb.conf`
- **Mount point**: `/mnt/timecapsule` on pi4

## Data Sources

### Reliable Data (ALWAYS USE THESE)

#### 1. SnapshotHistory.plist - Backup History
**Location**: `/mnt/timecapsule/MBP16diRiccardo.sparsebundle/com.apple.TimeMachine.SnapshotHistory.plist`

**Format**:
```xml
<dict>
    <key>Snapshots</key>
    <array>
        <dict>
            <key>com.apple.backupd.SnapshotCompletionDate</key>
            <date>2026-02-05T01:16:36Z</date>  ← UTC timestamp
            <key>com.apple.backupd.SnapshotName</key>
            <string>2026-02-05-011636.backup</string>
        </dict>
        <!-- More snapshots... -->
    </array>
</dict>
```

**Data to extract**:
- Last completed backup timestamp
- Previous backup timestamps (for history)
- Number of total snapshots

**Python parsing example**:
```python
import plistlib

with open('/mnt/timecapsule/MBP16diRiccardo.sparsebundle/com.apple.TimeMachine.SnapshotHistory.plist', 'rb') as f:
    data = plistlib.load(f)

snapshots = data['Snapshots']
last_snapshot = snapshots[-1]['com.apple.backupd.SnapshotCompletionDate']
```

#### 2. df Command - Disk Space
**Command**: `df -h /mnt/timecapsule`

**Output**:
```
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1       916G  273G  597G  32% /mnt/timecapsule
```

**Data to extract**:
- Total size: 916 GB
- Used space: 273 GB
- Available space: 597 GB
- Usage percentage: 32%

**Python parsing example**:
```python
import subprocess

result = subprocess.run(['df', '-h', '/mnt/timecapsule'], capture_output=True, text=True)
lines = result.stdout.split('\n')
size_line = lines[1].split()

total_gb = size_line[1]  # "916G"
used_gb = size_line[2]      # "273G"
avail_gb = size_line[3]     # "597G"
percent = size_line[4]      # "32%"
```

### Unreliable Data (NEVER USE)

#### Results.plist - Backup Status
**Location**: `/mnt/timecapsule/MBP16diRiccardo.sparsebundle/com.apple.TimeMachine.Results.plist`

**Status**: ❌ **INAFFIDABILE - Flag remains `true` even after backup completion**

**Why unreliable**:
- Running flag: Always `true` after backup completes (zombie state)
- Lock files: Not updated during backup
- Progress data: Only accurate during active backup, not after completion

**DO NOT USE**:
- `Running` flag (always true, meaningless)
- Progress percentage (stale after completion)
- Time remaining (stale after completion)

## Implementation Guide

### Screen Layout (264x176 pixel e-paper)

```
┌─────────────────────────────┐
│ 🗄 Time Machine            │
├─────────────────────────────┤
│                             │
│ Ultimo backup:             │
│ Oggi 02:16 (15 min fa)   │
│                             │
│ 💾 Spazio:                  │
│ 273GB / 916GB (32%)       │
│ ▓▓▓░░░░░░░░░░░░░░░░░    │
│                             │
│ Storico (ultimi 3):         │
│ • Oggi 02:16               │
│ • Oggi 01:27               │
│ • 4 feb 23:33              │
└─────────────────────────────┘
```

### Screen Implementation Steps

#### 1. Create Screen File
**File**: `core/screens/timemachine.py`

```python
import logging
import plistlib
import subprocess
from datetime import datetime, timezone, timedelta
from screens import AbstractScreen

class Screen(AbstractScreen):
    reload_interval = 300  # 5 minutes
    logger = logging.getLogger('screens.timemachine')

    def __init__(self):
        super().__init__()
        self.bundle_path = "/mnt/timecapsule/MBP16diRiccardo.sparsebundle"

    def reload(self):
        self.blank()

        # Title
        self.text("Time Machine", font_size=20, position=(10, 5))

        # Load backup data
        backup_data = self._load_snapshot_history()
        disk_data = self._load_disk_space()

        # Display last backup
        if backup_data['last_backup']:
            self._display_last_backup(backup_data['last_backup'])

        # Display disk space
        self._display_disk_space(disk_data)

        # Display history (last 3)
        self._display_backup_history(backup_data['history'][:3])

    def _load_snapshot_history(self):
        """Load and parse SnapshotHistory.plist"""
        try:
            plist_path = f"{self.bundle_path}/com.apple.TimeMachine.SnapshotHistory.plist"
            with open(plist_path, 'rb') as f:
                data = plistlib.load(f)

            snapshots = data.get('Snapshots', [])
            if not snapshots:
                self.logger.warning("No snapshots found in SnapshotHistory.plist")
                return {'last_backup': None, 'history': []}

            # Parse all snapshots
            history = []
            for snap in snapshots:
                timestamp = snap.get('com.apple.backupd.SnapshotCompletionDate')
                name = snap.get('com.apple.backupd.SnapshotName', '')
                history.append({
                    'timestamp': timestamp,
                    'name': name
                })

            # Sort by timestamp (newest first)
            history.sort(key=lambda x: x['timestamp'], reverse=True)

            return {
                'last_backup': history[0] if history else None,
                'history': history
            }
        except FileNotFoundError:
            self.logger.error("SnapshotHistory.plist not found")
            return {'last_backup': None, 'history': []}
        except Exception as e:
            self.logger.error(f"Error loading SnapshotHistory: {e}")
            return {'last_backup': None, 'history': []}

    def _load_disk_space(self):
        """Load disk space using df command"""
        try:
            result = subprocess.run(
                ['df', '-h', '/mnt/timecapsule'],
                capture_output=True,
                text=True
            )

            lines = result.stdout.split('\n')
            if len(lines) < 2:
                return {'total': 'N/A', 'used': 'N/A', 'available': 'N/A', 'percent': 'N/A'}

            size_line = lines[1].split()
            if len(size_line) < 5:
                return {'total': 'N/A', 'used': 'N/A', 'available': 'N/A', 'percent': 'N/A'}

            return {
                'total': size_line[1],    # "916G"
                'used': size_line[2],       # "273G"
                'available': size_line[3],  # "597G"
                'percent': size_line[4]     # "32%"
            }
        except Exception as e:
            self.logger.error(f"Error loading disk space: {e}")
            return {'total': 'N/A', 'used': 'N/A', 'available': 'N/A', 'percent': 'N/A'}

    def _display_last_backup(self, last_backup):
        """Display last completed backup with humanized time"""
        timestamp = last_backup['timestamp']
        now = datetime.now(timezone.utc)

        # Convert to local time
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        local_time = timestamp.astimezone()

        # Calculate time difference
        time_diff = now - timestamp
        if time_diff < timedelta(minutes=60):
            time_str = f"{int(time_diff.total_seconds() / 60)} min fa"
        elif time_diff < timedelta(hours=24):
            time_str = f"{int(time_diff.total_seconds() / 3600)} ore fa"
        else:
            days = int(time_diff.total_seconds() / 86400)
            time_str = f"{days} giorni fa"

        # Format: "Oggi 02:16" or "4 feb 23:33"
        date_str = local_time.strftime("%d %b %H:%M") if time_diff > timedelta(hours=24) else f"Oggi {local_time.strftime('%H:%M')}"

        # Display
        self.text(f"Ultimo backup:", font_size=12, position=(10, 30))
        self.text(f"{date_str} ({time_str})", font_size=10, position=(10, 45))

    def _display_disk_space(self, disk_data):
        """Display disk usage with progress bar"""
        y_pos = 70

        # Header
        self.text("Spazio:", font_size=12, position=(10, y_pos))

        # Usage text
        total = disk_data['total']
        used = disk_data['used']
        percent = disk_data['percent']

        self.text(f"{used} / {total} ({percent})", font_size=10, position=(10, y_pos + 15))

        # Progress bar
        try:
            # Extract percentage number
            percent_num = int(percent.replace('%', ''))
            bar_width = 244  # Full width minus margins
            filled_width = int(bar_width * percent_num / 100)
            empty_width = bar_width - filled_width

            # Draw progress bar
            bar_y = y_pos + 30
            bar_x = 10

            # Filled portion
            self.line((bar_x, bar_y, bar_x + filled_width, bar_y), width=3)
            # Empty portion (dots or spaces)
            # Simple text-based bar is easier on e-paper
            self.centered_text(f"{percent_num}% di {total}", font_size=10, y=bar_y + 5)
        except (ValueError, AttributeError):
            self.text(f"Uso: {percent}", font_size=10, position=(10, y_pos + 30))

    def _display_backup_history(self, history):
        """Display last 3 backups in history"""
        y_start = 130
        line_height = 15

        for i, backup in enumerate(history[:3]):
            y_pos = y_start + (i * line_height)
            timestamp = backup['timestamp']

            # Convert to local time
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            local_time = timestamp.astimezone()

            # Format
            date_str = local_time.strftime("%d %b %H:%M")
            if timestamp.date() == datetime.now().date():
                date_str = f"Oggi {local_time.strftime('%H:%M')}"

            # Display with bullet
            self.text(f"• {date_str}", font_size=9, position=(10, y_pos))
```

#### 2. Add Screen to Configuration
**File**: `local_settings.py`

```python
SCREENS = [
    'system',
    'tailscale',
    'system_dashboard',
    'weather',
    'calendar',
    'timemachine',  # Add this line
    'webview',
]
```

## Testing

### Manual Testing on pi4

```bash
# Test plist reading
python3 -c "
import plistlib
with open('/mnt/timecapsule/MBP16diRiccardo.sparsebundle/com.apple.TimeMachine.SnapshotHistory.plist', 'rb') as f:
    data = plistlib.load(f)
    print('Snapshots:', len(data['Snapshots']))
    print('Last:', data['Snapshots'][-1]['com.apple.backupd.SnapshotCompletionDate'])
"

# Test df command
df -h /mnt/timecapsule
```

### Test Screen on paperGate

```bash
# Switch to timemachine screen
cd ~/paperGate/core
./cli.py screen timemachine

# View logs
pg-log
```

## Troubleshooting

### Issue: Cannot read SnapshotHistory.plist

**Symptoms**: "SnapshotHistory.plist not found" error in logs

**Solutions**:
1. Verify mount point: `ls -la /mnt/timecapsule/`
2. Check sparsebundle name: `ls /mnt/timecapsule/`
3. Verify permissions: `sudo ls -la /mnt/timecapsule/MBP16diRiccardo.sparsebundle/`

### Issue: df command fails

**Symptoms**: Disk space shows "N/A" or error in logs

**Solutions**:
1. Check mount is active: `mount | grep timecapsule`
2. Remount if necessary: `sudo umount /mnt/timecapsule && sudo mount /mnt/timecapsule`
3. Check disk is connected: `lsblk | grep sda`

### Issue: Screen shows no data

**Symptoms**: Screen is blank or shows default values

**Solutions**:
1. Check Time Machine is accessible from Mac
2. Verify recent backup completed on Mac
3. Check Samba services are running: `sudo systemctl status smbd nmbd`
4. Verify plist file contains data: `plutil -p /mnt/timecapsule/MBP16diRiccardo.sparsebundle/com.apple.TimeMachine.SnapshotHistory.plist`

### Issue: Date/time display incorrect

**Symptoms**: Timestamps show wrong time or timezone

**Solutions**:
1. Verify pi4 timezone: `timedatectl`
2. Set timezone if needed: `sudo timedatectl set-timezone Europe/Rome`
3. Verify macOS and pi4 are using NTP for time synchronization

## Known Limitations

1. **No real-time backup progress**: Cannot show active backup progress because `Results.plist` Running flag is unreliable
2. **No backup failure detection**: Cannot detect failed backups from plist files alone
3. **Read-only access**: System only reads backup metadata, cannot control or initiate backups
4. **Bundle-specific**: Currently hardcodes `MBP16diRiccardo.sparsebundle` - should be made configurable

## Future Enhancements

1. **Multiple Mac support**: Auto-detect all sparsebundle directories
2. **Alert system**: Show alerts if last backup > 7 days old
3. **Storage threshold**: Alert if disk space < 100 GB remaining
4. **Backup estimation**: Calculate backup frequency and estimate next backup time
5. **Interactive controls**: Add button to view full backup history via web interface

## References

- **TimeCapsule-Pi**: https://github.com/rizal72/TimeCapsule-Pi
- **paperGate**: https://github.com/rizal72/papergate
- **Samba vfs_fruit**: https://www.samba.org/samba/docs/current/man-html/vfs_fruit.8.html
- **macOS Time Machine**: https://support.apple.com/guide/mac-help/use-time-machine-to-back-up-or-restore-your-mac-mh26981382/mac
