DEPLOY SU RENDER (SENZA GITHUB) — CRM SaaS Premium (Demo)

1) Crea account su Render
2) New +  -> Web Service
3) Scegli "Upload / Deploy from ZIP" e carica questo ZIP
4) Imposta:
   - Environment: Python 3
   - Build Command: pip install -r requirements.txt
   - Start Command: gunicorn -w 2 -b 0.0.0.0:$PORT app:app
5) Deploy

NOTE:
- Se vuoi una demo sempre "pulita", va benissimo SQLite.
- Se re-deployi, alcuni host possono resettare i dati: ok per demo Fiverr.
