# COPPA posture for this demo

A demo where a child talks to Santa, says their name out loud and picks a
gift is, on its face, a service directed to children under 13. COPPA applies
to it. This file records what has been done, what has not, and what the
honest gap is.

## What is in place

**An age / parental-consent screen.** The microphone is not opened until the
visitor answers. Two paths: 13-or-older, or under-13 with a parent or
guardian present who agrees. Declining closes the dialog and touches
nothing. The answer is held in `sessionStorage`, so it is given by whoever
is at the machine this visit rather than inherited from last month's user.

**A privacy notice** at `/privacy.html`, in plain language, listing what is
collected, what is not, and an address for a parent to request deletion.

**Microphone only, verified.** The main page dials with `video: false`. This
was checked at the API level, not by reading the source: `getUserMedia` is
called exactly once per session with `{"audio":{},"video":false}`.

## What was found and fixed

**`/simple-client.html` was turning on the camera.** It dialled with
`video: true` and rendered the caller's own webcam in a "Local Video" panel.
It is served publicly next to the main page — `GET /simple-client.html`
returns 200 — so anyone who reached it was asked for camera permission by a
site built for children. Now `video: false`, the local preview is gone, and
the video toggle is permanently disabled.

> This fix is **not yet on the production host.** Until it ships,
> `santa.signalwire.me/simple-client.html` still asks for the camera.

## The honest gap

**An age screen is not verifiable parental consent.** COPPA requires a
verifiable method — a signed form, a card transaction, a phone or video
call with trained personnel, government-ID check. Clicking a button is none
of those. For a service *directed to children*, an age screen does not
shift the obligation either: a child-directed service is treated as
collecting from children regardless of what the visitor clicks. A neutral
age screen is the right control for a general-audience site; this is closer
to child-directed.

So the screen is a notice-and-acknowledgement step and a good-faith signal.
It is not, by itself, compliance.

**The biggest single exposure is call recording.** `app.py` sets
`record_call=True`, which retains a recording of a child's voice. The FTC's
audio-recording exception is narrow: it covers audio used *solely* as a
replacement for text input and deleted immediately after. A retained call
recording is outside it.

The one-line change that most reduces risk:

```python
# app.py
record_call=False
```

**Other open items**, in rough order of weight:

1. Decide and document a retention period for anything kept, and actually
   enforce it.
2. Name a contact who answers `privacy@signalwire.com` for deletion
   requests, and confirm that mailbox exists.
3. Have counsel confirm whether this is treated as child-directed. That
   answer changes what is required, and it is not an engineering call.
4. If it stays child-directed and keeps collecting voice, a real verifiable
   parental consent flow is needed before launch, not an age screen.

Nothing here is legal advice. It is an engineer's record of what the code
does, so whoever does give that advice is working from facts.
