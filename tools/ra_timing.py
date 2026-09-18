"""Correct mapping from RetailAction labels to video playback time.

Each clip is encoded as 32 frames at 6 fps (5.33 s) no matter how long the real
segment was (0.9 s to 49.8 s). The 32 frames are picked by motion scoring, so they
are NOT evenly spaced in real time — 86% of clips are non-uniform. Action `start`
and `end` are fractions of the SEGMENT, not of the video, so mapping them straight
onto the video timeline puts the action in the wrong place.

The frame timestamps are the bridge: frame i of the video happened at real time
frame_timestamps[i] within the segment.
"""
from datetime import datetime

FPS = 6.0


def seg_duration(content):
    s = content.get('segment_info') or {}
    try:
        return (datetime.fromisoformat(s['sampled_at_end'])
                - datetime.fromisoformat(s['sampled_at_start'])).total_seconds()
    except Exception:
        return None


def frame_times(content, rank='rank0'):
    """Seconds into the segment for each encoded video frame."""
    cam = (content.get('action_cam') or {}).get(rank) or {}
    ts = cam.get('frame_timestamps')
    if not ts:
        return None
    t0 = datetime.fromisoformat(ts[0])
    return [(datetime.fromisoformat(t) - t0).total_seconds() for t in ts]


def action_window(content, action, rank='rank0'):
    """(start, end) in VIDEO seconds for an action, plus whether it is exact.

    Falls back to a linear mapping when frame timestamps are missing (319 of the
    2,501 samples), in which case `exact` is False.
    """
    sd = seg_duration(content)
    ts = frame_times(content, rank)
    nframes = len(ts) if ts else 32
    if sd is None or not ts:
        return action['start'] * (nframes / FPS), action['end'] * (nframes / FPS), False

    s, e = action['start'] * sd, action['end'] * sd
    idx = [i for i, t in enumerate(ts) if s <= t <= e]
    if not idx:                                   # action falls between sampled frames
        mid = (s + e) / 2
        idx = [min(range(len(ts)), key=lambda i: abs(ts[i] - mid))]
    return idx[0] / FPS, (idx[-1] + 1) / FPS, True


def action_mid(content, action, rank='rank0'):
    a, b, _ = action_window(content, action, rank)
    return (a + b) / 2
