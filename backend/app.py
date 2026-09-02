
from __future__ import annotations

import logging
from pathlib import Path

from flask import Flask, jsonify, send_from_directory

# =============================================================
# IMPORTS ROUTES
# =============================================================

from backend.routes.upload import upload_bp
from backend.routes.extraction import extraction_bp
from backend.routes.documents import documents_bp


# =============================================================
# CONFIGURATION
# =============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

UPLOAD_DIR = BASE_DIR / "uploads"
RESULT_DIR = BASE_DIR / "results"
FRONTEND_DIR = BASE_DIR / "frontend"

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

RESULT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =============================================================
# LOGGING
# =============================================================

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s"
    ),
)

logger = logging.getLogger(__name__)


# =============================================================
# CREATION APPLICATION
# =============================================================

def create_app() -> Flask:
    """
    Crée et configure l'application Flask.

    Architecture :

        frontend/
            index.html
            css/
                style.css
            js/
                app.js

        backend/
            app.py
            routes/
            services/
            models/

    OCR uniquement :
        IA  = NON
        LLM = NON
        DB  = NON
    """

    app = Flask(
        __name__,
    )

    # ---------------------------------------------------------
    # CONFIGURATION FLASK
    # ---------------------------------------------------------

    app.config["UPLOAD_FOLDER"] = str(
        UPLOAD_DIR
    )

    app.config["RESULT_FOLDER"] = str(
        RESULT_DIR
    )

    app.config["FRONTEND_FOLDER"] = str(
        FRONTEND_DIR
    )

    # Taille maximale : 50 MB
    app.config["MAX_CONTENT_LENGTH"] = (
        50 * 1024 * 1024
    )

    app.config["JSON_AS_ASCII"] = False

    # ---------------------------------------------------------
    # ENREGISTREMENT DES ROUTES API
    # ---------------------------------------------------------

    app.register_blueprint(
        upload_bp,
    )

    app.register_blueprint(
        extraction_bp,
    )

    app.register_blueprint(
        documents_bp,
    )

    # =========================================================
    # FRONTEND
    # =========================================================

    @app.get("/")
    def index():
        """
        Sert la page principale du frontend.
        """

        index_file = FRONTEND_DIR / "index.html"

        if not index_file.exists():

            logger.error(
                "Frontend introuvable : %s",
                index_file,
            )

            return jsonify(
                {
                    "success": False,
                    "error": (
                        "frontend/index.html "
                        "introuvable."
                    ),
                }
            ), 500

        return send_from_directory(
            FRONTEND_DIR,
            "index.html",
        )

    # ---------------------------------------------------------
    # CSS
    # ---------------------------------------------------------

    @app.get("/css/<path:filename>")
    def frontend_css(filename: str):
        """
        Sert les fichiers CSS du frontend.
        """

        css_dir = FRONTEND_DIR / "css"

        return send_from_directory(
            css_dir,
            filename,
        )

    # ---------------------------------------------------------
    # JAVASCRIPT
    # ---------------------------------------------------------

    @app.get("/js/<path:filename>")
    def frontend_js(filename: str):
        """
        Sert les fichiers JavaScript du frontend.
        """

        js_dir = FRONTEND_DIR / "js"

        return send_from_directory(
            js_dir,
            filename,
        )

    # ---------------------------------------------------------
    # FAVICON
    # ---------------------------------------------------------

    @app.get("/favicon.ico")
    def favicon():
        """
        Évite une erreur 404 si le navigateur demande
        automatiquement un favicon.
        """

        favicon_path = FRONTEND_DIR / "favicon.ico"

        if favicon_path.exists():

            return send_from_directory(
                FRONTEND_DIR,
                "favicon.ico",
            )

        return "", 204

    # =========================================================
    # HEALTH CHECK
    # =========================================================

    @app.get("/api/health")
    def health():

        return jsonify(
            {
                "success": True,
                "status": "healthy",
                "service": "OCR Platform",

                "ocr_enabled": True,

                "ai_enabled": False,
                "llm_enabled": False,

                "database_enabled": False,

                "frontend_enabled": True,
            }
        )

    # =========================================================
    # INFORMATIONS API
    # =========================================================

    @app.get("/api")
    def api_info():

        return jsonify(
            {
                "success": True,
                "name": "OCR Platform",
                "version": "1.0.0",

                "description": (
                    "Plateforme OCR industrielle "
                    "sans IA et sans LLM."
                ),

                "engine": {
                    "ocr": True,
                    "ai": False,
                    "llm": False,
                },

                "storage": {
                    "database": False,
                    "json": True,
                },

                "endpoints": {
                    "health": "/api/health",
                    "upload": "/api/upload",
                    "extraction": "/api/extraction",
                    "documents": "/api/documents",
                },
            }
        )

    # =========================================================
    # ERREUR 404
    # =========================================================

    @app.errorhandler(404)
    def not_found(error):

        return jsonify(
            {
                "success": False,
                "error": "Route introuvable.",
                "status_code": 404,
            }
        ), 404

    # =========================================================
    # ERREUR 413
    # =========================================================

    @app.errorhandler(413)
    def file_too_large(error):

        return jsonify(
            {
                "success": False,
                "error": (
                    "Fichier trop volumineux. "
                    "Taille maximale : 50 MB."
                ),
                "status_code": 413,
            }
        ), 413

    # =========================================================
    # ERREUR GENERALE
    # =========================================================

    @app.errorhandler(Exception)
    def handle_exception(error):

        logger.exception(
            "Erreur serveur : %s",
            error,
        )

        return jsonify(
            {
                "success": False,
                "error": "Erreur interne du serveur.",
                "status_code": 500,
            }
        ), 500

    # =========================================================
    # LOGS
    # =========================================================

    logger.info(
        "Application OCR initialisée."
    )

    logger.info(
        "Upload directory : %s",
        UPLOAD_DIR,
    )

    logger.info(
        "Result directory : %s",
        RESULT_DIR,
    )

    logger.info(
        "Frontend directory : %s",
        FRONTEND_DIR,
    )

    logger.info(
        "IA : désactivée"
    )

    logger.info(
        "LLM : désactivé"
    )

    logger.info(
        "Base de données : désactivée"
    )

    return app


# =============================================================
# APPLICATION
# =============================================================

app = create_app()


# =============================================================
# TEST CONFIGURATION
# =============================================================

def run_test() -> None:
    """
    Vérifie que Flask, le frontend et les routes
    sont correctement enregistrés.
    """

    print("=" * 70)
    print("TEST BACKEND OCR - SANS IA")
    print("=" * 70)

    print()

    print("Application : OCR Platform")

    print()

    print("Base directory :")
    print(f"  {BASE_DIR}")

    print()

    print("Upload directory :")
    print(f"  {UPLOAD_DIR}")

    print()

    print("Result directory :")
    print(f"  {RESULT_DIR}")

    print()

    print("Frontend directory :")
    print(f"  {FRONTEND_DIR}")

    print()

    print("Frontend index.html :")

    index_file = FRONTEND_DIR / "index.html"

    if index_file.exists():
        print("  OUI")
    else:
        print("  NON - FICHIER MANQUANT")

    print()

    print("Frontend CSS :")

    css_file = FRONTEND_DIR / "css" / "style.css"

    if css_file.exists():
        print("  OUI")
    else:
        print("  NON - FICHIER MANQUANT")

    print()

    print("Frontend JavaScript :")

    js_file = FRONTEND_DIR / "js" / "app.js"

    if js_file.exists():
        print("  OUI")
    else:
        print("  NON - FICHIER MANQUANT")

    print()

    print("Routes enregistrées :")

    for rule in app.url_map.iter_rules():

        print(
            f"  {sorted(rule.methods)} "
            f"{rule}"
        )

    print()

    print("Configuration :")

    print("  OCR       : OUI")
    print("  IA        : NON")
    print("  LLM       : NON")
    print("  PostgreSQL: NON")
    print("  JSON      : OUI")
    print("  Frontend  : OUI")

    print()

    print("=" * 70)
    print("TEST BACKEND TERMINE")
    print("=" * 70)


# =============================================================
# POINT D'ENTREE
# =============================================================

if __name__ == "__main__":

    run_test()

    print()

    print("=" * 70)
    print("DEMARRAGE SERVEUR OCR")
    print("=" * 70)

    print()

    print(
        "Interface : "
        "http://127.0.0.1:5000/"
    )

    print(
        "API Health : "
        "http://127.0.0.1:5000/api/health"
    )

    print()

    print(
        "Appuyez sur CTRL+C pour arrêter le serveur."
    )

    print()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
    )

