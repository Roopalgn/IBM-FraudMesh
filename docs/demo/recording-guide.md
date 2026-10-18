# Recording guide and artifact status

Current submission target: **180 seconds**. The narration, executable shot list
and SRT are synchronized drafts for rehearsal; no completed video/audio is included.

## Local preview

Project: C:/Users/Sidhesh/PycharmProjects/ibm2.0/IBM-FraudMesh
Delivery branch: frontend_finalized. The user has authorized the finalized frontend push; no main merge.

```powershell
.\.venv\Scripts\python.exe -B -m uvicorn app.main:app --host 127.0.0.1 --port 8018
```

Open http://127.0.0.1:8018/?preview=canvas-02. `frontend/START-PREVIEW.cmd` starts the same command.
The current preview is bound to loopback. Use the real API; a static-file preview alone cannot verify the journal or computed scenarios.

## Capture

Browser recording is not exposed by the available browser-control tools. **No video or narration audio was created.** This package provides an executable shot list, voiceover, storyboard and synchronized subtitle draft instead.

Use your existing screen recorder (for example Windows Snipping Tool screen recording) to capture a readable 16:9 browser area at 1920x1080 or 1440x810. Record 180 seconds following shotlist.md. Speak the voiceover or add narration afterward. Import captions.srt in a video editor if supported, and adjust timestamps to the actual takes. It is a draft script, not an automatic transcription.

No recording library is added to the application. Hide credential files, the console, notifications and unrelated windows. Preserve the synthetic provenance, scope-transition note and unverified LinuxONE status. Do not imply that the local Windows recording is LinuxONE evidence.

## Review checklist

Check the ring local/combined contrast, common-scenario payroll hard negative, evidence search/selection, export, live journal check and all four scenario controls. Verify zero page overflow at CSS widths 1440, 1280, 768 and 390. Screenshots and test logs live in ignored output/frontend-preview/.

The inline logo is original; public/brand contains standalone dark and monochrome SVG marks. IBM Plex Sans webfonts are bundled locally with their SIL OFL license; the code/data font retains a Consolas fallback. No external font request is required.
