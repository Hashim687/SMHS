# Put SMHS online for free (Render + Neon)

Website: Render (free web service). Database: Neon (free Postgres, no card needed).
Free limits: the site sleeps after ~15 min without visitors and takes about a minute to wake up.
Use FAKE data only. This is a demo, not a place for real patient records.

## 1. Put the project on GitHub
1. Make a free account at github.com, then click New repository (name it smhs, Private is fine).
2. Click "uploading an existing file". Unzip this project first, then drag in EVERYTHING
   inside the folder (backend, frontend, deploy, Dockerfile, render.yaml, etc.).
   Do NOT upload the folders `venv` or `node_modules` (setup.bat made them).
3. Click Commit changes.

## 2. Create the free database (Neon)
1. Sign up at neon.com, create a project (any name, nearest region).
2. On the dashboard click Connect, copy the connection string
   (it starts with postgresql://). Keep it secret.

## 3. Create the website (Render)
1. Sign up at render.com with your GitHub account.
2. New + > Blueprint > pick your smhs repository > Apply.
   (Or New + > Web Service > Docker, plan Free.)
3. When asked for DATABASE_URL, paste the Neon connection string.
4. Wait for the first deploy to finish (several minutes). Your link looks like
   https://smhs-hospital.onrender.com

## 4. Create your admin (from your own PC)
Double-click `online-admin.bat`, paste the same Neon connection string, choose a username
and a strong password (10+ characters).

## 5. First login
Open your link, then add `#/staff` to the end, sign in, and scan the QR code with
Google Authenticator. Then add doctors, departments, prices in the admin portal.

## Notes
- Payments run in test mode until Razorpay keys are added in Render > Environment.
- SMS/OTP is not delivered (console mode). Patient OTP login needs a real SMS provider.
- The background notification worker is not run on the free plan.
- Never change DJANGO_SECRET_KEY after the first login (it protects 2FA secrets).
