# Another Beautiful Roof — site + lead database

A whosystems build. Static marketing site + a zero-dependency Python lead
database with an admin dashboard.

## Run locally
```bash
cd "another-beautiful-roof"
ABR_ADMIN_PW="pick-a-real-password" python3 server/app.py
```
- Site:  http://localhost:8000/
- Admin: http://localhost:8000/admin  (user: `admin`, pw: from `ABR_ADMIN_PW`, default `roof`)

The quote form on the site POSTs to `/api/leads`; rows land in `server/abr.db`
(SQLite) and appear instantly in the dashboard, where you can move each lead
through: new → contacted → quoted → won / lost.

## Data
`server/abr.db`, table `leads`: id, created_at, name, phone, email, address,
roof_type, message, source, status. Back it up by copying the file.

Export all leads as JSON (auth required):
```bash
curl -u admin:$ABR_ADMIN_PW http://localhost:8000/api/leads.json
```

## Before going live
- Set a strong `ABR_ADMIN_PW` and put the whole thing behind HTTPS (reverse
  proxy / platform TLS). The dashboard is HTTP Basic auth only.
- Point `www.anotherbeautifulroof.com` at the host; the server serves `site/`.
- Confirm the real phone, email, address, and VA license number in `site/index.html`.
