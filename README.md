# Etsy Customizer Backend (Minimal Flask)

This tiny backend saves a user's design (SVG + optional state) and returns a short code. You can open a private viewer page by code to preview and download the SVG.

## Endpoints
- POST `/api/designs` → Save { productId, svg, state? } and return `{ code }`
- GET `/d/:code` → Viewer page (protect with Basic Auth) showing preview + download button
- GET `/healthz` → Health check

## Environment variables
- `DATABASE_URL` → Postgres URL (Render) or `sqlite:///designs.db` locally
- `ALLOWED_ORIGIN` → Your frontend origin (e.g., `https://yourname.github.io`)
- `ADMIN_USER`, `ADMIN_PASS` → Basic Auth for `/d/:code`

## Quick start (local)
1. Python 3.10+ and `pip install -r requirements.txt`
2. Run the app (it will create tables automatically): `gunicorn app:app` (or `flask run`)
3. Optional: copy `.env.example` to `.env` and export variables for local testing.

## Deploy to Render (recommended)
1. Push this folder as a GitHub repo
2. On Render: New → Web Service → connect repo
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Add environment variables:
   - `DATABASE_URL` (from Render Postgres)
   - `ALLOWED_ORIGIN` (your frontend origin)
   - `ADMIN_USER` / `ADMIN_PASS`
6. Create a Render Postgres instance → copy `DATABASE_URL` into the service env
7. Open `/healthz` to test, then POST to `/api/designs`

## POST example (via curl)
```bash
curl -X POST "https://YOUR_BACKEND.onrender.com/api/designs" \
  -H 'Content-Type: application/json' \
  -H 'Origin: https://YOUR_FRONTEND_HOST' \
  -d '{
    "productId": "mug",
    "svg": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 100 100\"><text x=\"50\" y=\"50\" text-anchor=\"middle\">Test</text></svg>",
    "state": {"note":"optional"}
  }'
```
Response: `{ "code": "AB7XQ9" }`

## Viewer
Open `https://YOUR_BACKEND.onrender.com/d/AB7XQ9` (use Basic Auth). Click Download SVG.

---
Notes:
- Keep SVG sizes small (editor export should be concise). The API enforces a 2MB max body.
- For security, keep `/d/:code` behind Basic Auth. You can add an `/admin` search later.
