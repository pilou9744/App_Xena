import os
import threading
import time
import webbrowser

from app import app, demarrer_scheduler_discord
from database import initialiser_base


HOST = "127.0.0.1"
PORT = int(os.environ.get("GECKOCARE_PORT", "5000"))
URL = f"http://{HOST}:{PORT}/dashboard"


def ouvrir_application():
    time.sleep(1.2)
    webbrowser.open(URL)


if __name__ == "__main__":
    initialiser_base()
    demarrer_scheduler_discord()
    threading.Thread(target=ouvrir_application, daemon=True).start()
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)
