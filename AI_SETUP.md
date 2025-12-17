# AI Processing Setup Guide (Temporarily Disabled)

**Status:** Legacy Gemini/Hugging Face OCR has been removed. Processing endpoints (`/api/process`, `/api/batch`) currently return HTTP 503 while we integrate a new Chinese-handwriting OCR backend.

## Interim Overview

- Planned replacement: self/hosted Chinese-handwriting OCR (e.g., PaddleOCR) behind a new inference service.
- Next.js frontend will call that service directly or via a thin proxy route.

## What to do now

- App still runs: auth, uploads, dashboards, exports, etc.
- OCR/translation are offline until the new backend is wired.
- No API keys are needed; Gemini/HF env vars are unused.

## Environment Variables

Create or update your `.env` file:

```env
# Required
DATABASE_URL="file:./prisma/db/dev.db"
NEXTAUTH_URL="http://localhost:3001"
NEXTAUTH_SECRET="your-secret-key-here"
```

## Coming soon

- FastAPI + PaddleOCR (Chinese handwriting) with a single `/process-image` endpoint.
- Frontend will display returned polygons/bboxes, per-segment text, and dictionary meanings.
- Optional local dictionary + rule-based translation.

