# SMHS Srinagar Hospital: deployment on the hospital server

## Requirements
Linux server on the hospital network, Docker with the compose plugin, ports 80 and 443 open to the LAN (and to the internet only if the public site is meant to be reachable from outside), a DNS name, and a TLS certificate from the hospital's CA or a public CA.

## First install
1. Copy this folder to the server.
2. `cp .env.example .env` and edit it. Set a long random `DJANGO_SECRET_KEY` (never change it later: it protects stored 2FA secrets and Golden Card numbers), a strong `DB_PASSWORD`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, and the Razorpay keys.
3. Certificate: put `fullchain.pem` and `privkey.pem` in `./certs/`. For testing only: `sh deploy/make-selfsigned.sh your.hostname`.
4. `docker compose up -d --build`
5. Create the first administrator: `docker compose exec web python manage.py create_admin your-username`. Log in at `/#/staff`; you must set up an authenticator app before continuing.
6. In the admin portal: create departments' heads, doctors, nurses and staff; assign doctors and nurses to departments; set ticket and lab prices; add beds, locations and ambulances; review triage rules with the doctors.
7. Razorpay dashboard: add the webhook `https://your.hostname/api/payments/razorpay/webhook` for the `payment.captured` event, with the same secret as `RAZORPAY_WEBHOOK_SECRET`.
8. SMS: `SMS_BACKEND=http` posts JSON `{to, message, sender}` with a bearer key to `SMS_GATEWAY_URL`. Most Indian SMS providers need a small adapter or a different payload; edit `deliver()` in `backend/clinic/notify.py` for your provider and register the DLT templates. Until then OTP login and SMS will not be delivered.
9. Telemedicine: set `TELE_BASE_URL` to a self-hosted Jitsi Meet server. The public meet.jit.si is not suitable for patient consultations.

## Backups and restore
Add to cron: `0 2 * * * /path/to/smhs/deploy/backup.sh`. Copy `backups/` and `.env` off the server. Restore test: `gunzip -c backups/FILE.sql.gz | docker compose exec -T db psql -U $DB_USER $DB_NAME` on a spare machine. Rehearse this before go-live.

## Updating
`git pull` or copy the new folder, then `docker compose up -d --build`. Migrations run on start.

## Before go-live checklist
Admin portal, Review & audit tab: every line should be green. Then also:
- Doctors sign off the symptom severities, department rules and emergency criteria.
- The lab director signs off reference ranges and prices.
- Native speakers review Urdu and Kashmiri text (Translations tab fixes wording without a redeploy).
- Independent penetration test and a restore drill.
- Confirm consent notices and data retention against the DPDP Act and Ayushman Bharat rules with the hospital's legal officer.
- Keep the server patched; restrict SSH; put the database host on an isolated network; monitor `docker compose logs` and the audit log.
