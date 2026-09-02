from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from flask import Blueprint, jsonify

logger = logging.getLogger(__name__)

documents_bp = Blueprint(
    "documents",
    __name__,
    url_prefix="/api/documents",
)

# =============================================================
# CONFIGURATION
# =============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

UPLOAD_DIR = BASE_DIR / "uploads"
RESULT_DIR = BASE_DIR / "results"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
RESULT_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================
# UTILITAIRES
# =============================================================

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff",
    ".bmp",
}


def get_document_type(path: Path) -> str:
    """Retourne le type du document."""

    extension = path.suffix.lower()

    if extension == ".pdf":
        return "pdf"

    if extension in {
        ".png",
        ".jpg",
        ".jpeg",
        ".tif",
        ".tiff",
        ".bmp",
    }:
        return "image"

    return "unknown"


def find_result_file(filename: str) -> Path | None:
    """
    Recherche le fichier JSON correspondant
    au document.
    """

    source = Path(filename)

    result_path = RESULT_DIR / f"{source.stem}.json"

    if result_path.exists():
        return result_path

    return None


def load_result(result_path: Path) -> dict[str, Any]:
    """Charge un résultat JSON."""

    try:
        with result_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        if isinstance(data, dict):
            return data

    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:
        logger.warning(
            "Impossible de lire %s : %s",
            result_path,
            exc,
        )

    return {}


# =============================================================
# GET /api/documents
# =============================================================

@documents_bp.get("")
def list_documents():
    """
    Retourne la liste des documents disponibles.

    Exemple :

    GET /api/documents
    """

    documents = []

    for path in sorted(
        UPLOAD_DIR.iterdir(),
        key=lambda item: item.name.lower(),
    ):
        if not path.is_file():
            continue

        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            continue

        result_path = find_result_file(
            path.name
        )

        result_exists = (
            result_path is not None
        )

        result_data = {}

        if result_path is not None:
            result_data = load_result(
                result_path
            )

        document_data = result_data.get(
            "document",
            {},
        )

        if not isinstance(
            document_data,
            dict,
        ):
            document_data = {}

        documents.append(
            {
                "filename": path.name,
                "type": document_data.get(
                    "type",
                    get_document_type(path),
                ),
                "size": path.stat().st_size,
                "result_available": result_exists,
                "result_file": (
                    result_path.name
                    if result_path
                    else None
                ),
                "confidence": result_data.get(
                    "confidence",
                    0.0,
                ),
            }
        )

    return jsonify(
        {
            "success": True,
            "count": len(documents),
            "documents": documents,
        }
    )


# =============================================================
# GET /api/documents/<filename>
# =============================================================

@documents_bp.get("/<path:filename>")
def get_document(filename: str):
    """
    Retourne les informations et le résultat
    OCR d'un document.

    Exemple :

    GET /api/documents/test.pdf
    """

    source_path = UPLOAD_DIR / filename

    # ---------------------------------------------------------
    # Sécurité : empêcher les chemins ../../
    # ---------------------------------------------------------

    try:
        source_path = source_path.resolve()
        upload_root = UPLOAD_DIR.resolve()

        source_path.relative_to(
            upload_root
        )

    except ValueError:
        return jsonify(
            {
                "success": False,
                "error": "Chemin de fichier invalide.",
            }
        ), 400

    # ---------------------------------------------------------
    # Vérification fichier
    # ---------------------------------------------------------

    if not source_path.exists():
        return jsonify(
            {
                "success": False,
                "error": "Document introuvable.",
            }
        ), 404

    if not source_path.is_file():
        return jsonify(
            {
                "success": False,
                "error": "Le chemin indiqué n'est pas un fichier.",
            }
        ), 400

    # ---------------------------------------------------------
    # Résultat OCR
    # ---------------------------------------------------------

    result_path = find_result_file(
        source_path.name
    )

    result = {}

    if result_path is not None:
        result = load_result(
            result_path
        )

    document_data = result.get(
        "document",
        {},
    )

    if not isinstance(
        document_data,
        dict,
    ):
        document_data = {}

    response = {
        "success": True,

        "document": {
            "filename": source_path.name,
            "type": document_data.get(
                "type",
                get_document_type(
                    source_path
                ),
            ),
            "size": source_path.stat().st_size,
            "path": str(source_path),
        },

        "result_available": (
            result_path is not None
        ),

        "result": result if result else None,
    }

    return jsonify(response)


# =============================================================
# GET /api/documents/<filename>/result
# =============================================================

@documents_bp.get("/<path:filename>/result")
def get_document_result(filename: str):
    """
    Retourne uniquement le résultat OCR.

    Exemple :

    GET /api/documents/test.pdf/result
    """

    source_path = UPLOAD_DIR / filename

    try:
        source_path = source_path.resolve()
        upload_root = UPLOAD_DIR.resolve()

        source_path.relative_to(
            upload_root
        )

    except ValueError:
        return jsonify(
            {
                "success": False,
                "error": "Chemin de fichier invalide.",
            }
        ), 400

    if not source_path.exists():
        return jsonify(
            {
                "success": False,
                "error": "Document introuvable.",
            }
        ), 404

    result_path = find_result_file(
        source_path.name
    )

    if result_path is None:
        return jsonify(
            {
                "success": False,
                "error": "Aucun résultat OCR disponible.",
            }
        ), 404

    result = load_result(
        result_path
    )

    if not result:
        return jsonify(
            {
                "success": False,
                "error": "Le résultat OCR est vide ou invalide.",
            }
        ), 500

    return jsonify(result)


# =============================================================
# DELETE /api/documents/<filename>
# =============================================================

@documents_bp.delete("/<path:filename>")
def delete_document(filename: str):
    """
    Supprime un document et son résultat OCR.

    Exemple :

    DELETE /api/documents/test.pdf
    """

    source_path = UPLOAD_DIR / filename

    try:
        source_path = source_path.resolve()
        upload_root = UPLOAD_DIR.resolve()

        source_path.relative_to(
            upload_root
        )

    except ValueError:
        return jsonify(
            {
                "success": False,
                "error": "Chemin de fichier invalide.",
            }
        ), 400

    if not source_path.exists():
        return jsonify(
            {
                "success": False,
                "error": "Document introuvable.",
            }
        ), 404

    result_path = find_result_file(
        source_path.name
    )

    deleted_files = []

    # ---------------------------------------------------------
    # Suppression document
    # ---------------------------------------------------------

    try:
        source_path.unlink()
        deleted_files.append(
            source_path.name
        )

    except OSError as exc:
        logger.exception(
            "Erreur suppression document"
        )

        return jsonify(
            {
                "success": False,
                "error": str(exc),
            }
        ), 500

    # ---------------------------------------------------------
    # Suppression résultat JSON
    # ---------------------------------------------------------

    if result_path is not None:
        try:
            result_path.unlink()
            deleted_files.append(
                result_path.name
            )

        except OSError as exc:
            logger.warning(
                "Impossible de supprimer le résultat : %s",
                exc,
            )

    return jsonify(
        {
            "success": True,
            "message": "Document supprimé.",
            "deleted_files": deleted_files,
        }
    )


# =============================================================
# TEST
# =============================================================

def run_test() -> None:

    print("=" * 70)
    print("TEST DOCUMENT ROUTES - OCR SANS IA")
    print("=" * 70)

    print()

    print("Dossier uploads :")
    print(f"  {UPLOAD_DIR}")

    print()

    print("Dossier results :")
    print(f"  {RESULT_DIR}")

    print()

    print("Routes disponibles :")
    print("  GET    /api/documents")
    print("  GET    /api/documents/<filename>")
    print("  GET    /api/documents/<filename>/result")
    print("  DELETE /api/documents/<filename>")

    print()

    print("IA activée : NON")
    print("LLM activé : NON")

    print()
    print("=" * 70)
    print("TEST DOCUMENT ROUTES TERMINE")
    print("=" * 70)


# =============================================================
# POINT D'ENTREE
# =============================================================

if __name__ == "__main__":
    run_test()