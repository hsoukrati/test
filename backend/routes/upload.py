
from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from backend.services.ocr_service import (
    OCRServiceError,
    process_document,
)


# =============================================================
# LOGGING
# =============================================================

logger = logging.getLogger(__name__)


# =============================================================
# BLUEPRINT
# =============================================================

upload_bp = Blueprint(
    "upload",
    __name__,
    url_prefix="/api/upload",
)


# =============================================================
# CONFIGURATION
# =============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

UPLOAD_DIR = BASE_DIR / "uploads"

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


ALLOWED_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff",
    ".bmp",
}


# =============================================================
# UTILITAIRES
# =============================================================

def is_allowed_file(filename: str) -> bool:
    """
    Vérifie si l'extension du fichier est autorisée.
    """

    if not filename:
        return False

    extension = Path(filename).suffix.lower()

    return extension in ALLOWED_EXTENSIONS


def generate_filename(original_filename: str) -> str:
    """
    Génère un nom de fichier sécurisé et unique.

    Exemple :

        test.pdf

    devient :

        8f3c2a1b_test.pdf
    """

    safe_name = secure_filename(
        original_filename
    )

    if not safe_name:
        safe_name = "document"

    unique_id = uuid.uuid4().hex[:8]

    return f"{unique_id}_{safe_name}"


# =============================================================
# ROUTE TEST
# =============================================================

@upload_bp.get("/health")
def upload_health():
    """
    Vérifie que le module upload fonctionne.
    """

    return jsonify(
        {
            "success": True,
            "service": "upload",
            "status": "ok",
            "ai_enabled": False,
            "llm_enabled": False,
        }
    )


# =============================================================
# ROUTE UPLOAD + OCR
# =============================================================

@upload_bp.post("/")
def upload_document():
    """
    Reçoit un document et lance automatiquement
    le pipeline OCR.

    Form-data attendu :

        file = document.pdf

    Exemple :

        POST /api/upload/
    """

    # ---------------------------------------------------------
    # Vérification de la présence du fichier
    # ---------------------------------------------------------

    if "file" not in request.files:

        return jsonify(
            {
                "success": False,
                "error": "Aucun fichier envoyé.",
                "code": "FILE_MISSING",
            }
        ), 400

    uploaded_file = request.files["file"]

    # ---------------------------------------------------------
    # Vérification du nom
    # ---------------------------------------------------------

    if not uploaded_file.filename:

        return jsonify(
            {
                "success": False,
                "error": "Le fichier n'a pas de nom.",
                "code": "FILENAME_MISSING",
            }
        ), 400

    original_filename = uploaded_file.filename

    # ---------------------------------------------------------
    # Vérification extension
    # ---------------------------------------------------------

    if not is_allowed_file(
        original_filename
    ):

        return jsonify(
            {
                "success": False,
                "error": (
                    "Format de fichier non supporté."
                ),
                "code": "UNSUPPORTED_FORMAT",
                "allowed_extensions": sorted(
                    ALLOWED_EXTENSIONS
                ),
            }
        ), 400

    # ---------------------------------------------------------
    # Génération nom sécurisé
    # ---------------------------------------------------------

    filename = generate_filename(
        original_filename
    )

    file_path = UPLOAD_DIR / filename

    # ---------------------------------------------------------
    # Sauvegarde fichier
    # ---------------------------------------------------------

    try:

        uploaded_file.save(
            str(file_path)
        )

    except OSError as exc:

        logger.exception(
            "Erreur sauvegarde fichier"
        )

        return jsonify(
            {
                "success": False,
                "error": (
                    "Impossible de sauvegarder "
                    "le fichier."
                ),
                "code": "SAVE_ERROR",
                "details": str(exc),
            }
        ), 500

    logger.info(
        "Fichier reçu : %s",
        file_path,
    )

    # ---------------------------------------------------------
    # LANCEMENT OCR
    # ---------------------------------------------------------

    try:

        result = process_document(
            file_path,
            save_json=True,
        )

    except OCRServiceError as exc:

        logger.exception(
            "Erreur service OCR"
        )

        # -----------------------------------------------------
        # Suppression du fichier si OCR échoue
        # -----------------------------------------------------

        try:

            if file_path.exists():
                file_path.unlink()

        except OSError:
            logger.warning(
                "Impossible de supprimer : %s",
                file_path,
            )

        return jsonify(
            {
                "success": False,
                "error": str(exc),
                "code": "OCR_ERROR",
                "filename": original_filename,
            }
        ), 500

    except Exception as exc:

        logger.exception(
            "Erreur inattendue pendant OCR"
        )

        return jsonify(
            {
                "success": False,
                "error": (
                    "Erreur inattendue "
                    "pendant le traitement OCR."
                ),
                "code": "INTERNAL_ERROR",
                "details": str(exc),
            }
        ), 500

    # ---------------------------------------------------------
    # REPONSE
    # ---------------------------------------------------------

    return jsonify(
        {
            "success": True,

            "message": (
                "Document envoyé et analysé "
                "avec succès."
            ),

            "filename": original_filename,

            "stored_filename": filename,

            "file_path": str(
                file_path
            ),

            "result": result,

            "engine": {
                "name": "OCR Engine",
                "ai_enabled": False,
                "llm_enabled": False,
            },
        }
    ), 200


# =============================================================
# ROUTE UPLOAD SANS OCR
# =============================================================

@upload_bp.post("/file")
def upload_file_only():
    """
    Upload uniquement le fichier.

    Cette route ne lance PAS l'OCR.

    Utile si l'on souhaite séparer :

        1. Upload
        2. Extraction

    """

    if "file" not in request.files:

        return jsonify(
            {
                "success": False,
                "error": "Aucun fichier envoyé.",
                "code": "FILE_MISSING",
            }
        ), 400

    uploaded_file = request.files["file"]

    if not uploaded_file.filename:

        return jsonify(
            {
                "success": False,
                "error": "Nom du fichier manquant.",
                "code": "FILENAME_MISSING",
            }
        ), 400

    original_filename = uploaded_file.filename

    if not is_allowed_file(
        original_filename
    ):

        return jsonify(
            {
                "success": False,
                "error": "Format non supporté.",
                "code": "UNSUPPORTED_FORMAT",
                "allowed_extensions": sorted(
                    ALLOWED_EXTENSIONS
                ),
            }
        ), 400

    filename = generate_filename(
        original_filename
    )

    file_path = UPLOAD_DIR / filename

    try:

        uploaded_file.save(
            str(file_path)
        )

    except OSError as exc:

        logger.exception(
            "Erreur upload"
        )

        return jsonify(
            {
                "success": False,
                "error": (
                    "Impossible de sauvegarder "
                    "le fichier."
                ),
                "code": "SAVE_ERROR",
                "details": str(exc),
            }
        ), 500

    return jsonify(
        {
            "success": True,
            "message": "Fichier uploadé avec succès.",
            "filename": original_filename,
            "stored_filename": filename,
            "file_path": str(file_path),
        }
    ), 201


# =============================================================
# FONCTION POUR TEST LOCAL
# =============================================================

def test_configuration() -> dict[str, Any]:
    """
    Retourne la configuration actuelle du module.
    """

    return {
        "upload_directory": str(
            UPLOAD_DIR
        ),
        "allowed_extensions": sorted(
            ALLOWED_EXTENSIONS
        ),
        "ai_enabled": False,
        "llm_enabled": False,
    }


# =============================================================
# TEST
# =============================================================

if __name__ == "__main__":

    print("=" * 70)

    print(
        "TEST UPLOAD ROUTE OCR - SANS IA"
    )

    print("=" * 70)

    print()

    configuration = test_configuration()

    print(
        "Dossier upload :"
    )

    print(
        f"  {configuration['upload_directory']}"
    )

    print()

    print(
        "Formats acceptés :"
    )

    for extension in configuration[
        "allowed_extensions"
    ]:
        print(
            f"  {extension}"
        )

    print()

    print(
        "IA activée : NON"
    )

    print(
        "LLM activé : NON"
    )

    print()

    print("=" * 70)

    print(
        "TEST UPLOAD ROUTE TERMINE"
    )

    print("=" * 70)

