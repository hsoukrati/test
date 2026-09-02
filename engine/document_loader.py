from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image


# =============================================================
# TYPES DE DOCUMENTS SUPPORTES
# =============================================================

SUPPORTED_IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff",
    ".webp",
}

SUPPORTED_EXTENSIONS = (
    SUPPORTED_IMAGE_EXTENSIONS
    | {
        ".pdf",
    }
)


# =============================================================
# STRUCTURE D'UNE PAGE
# =============================================================

@dataclass
class DocumentPage:
    """
    Représente une page d'un document.

    Pour une image :
        page_number = 1

    Pour un PDF multipage :
        page_number = numéro réel de la page.

    image :
        Image PIL utilisée ensuite par le preprocessing
        et le moteur OCR.
    """

    page_number: int
    image: Image.Image


# =============================================================
# STRUCTURE D'UN DOCUMENT
# =============================================================

@dataclass
class LoadedDocument:
    """
    Document chargé dans le pipeline OCR.

    Exemple :

        document.path
        document.document_type
        document.pages
        document.page_count
    """

    path: Path
    document_type: str
    pages: list[DocumentPage]

    @property
    def page_count(self) -> int:
        """
        Retourne le nombre de pages du document.
        """

        return len(self.pages)


# =============================================================
# VERIFICATION DU TYPE DE DOCUMENT
# =============================================================

def get_document_type(
    path: str | Path,
) -> str:
    """
    Détermine le type du document.

    Retourne :

        "image"
        "pdf"

    Exemples :

        test.png  -> image
        test.jpg  -> image
        test.tiff -> image
        test.pdf  -> pdf
    """

    document_path = Path(path)

    extension = (
        document_path
        .suffix
        .lower()
    )

    if extension in SUPPORTED_IMAGE_EXTENSIONS:

        return "image"

    if extension == ".pdf":

        return "pdf"

    raise ValueError(
        f"Format non supporté : "
        f"{extension or '[aucune extension]'}"
    )


# =============================================================
# VALIDATION DU FICHIER
# =============================================================

def validate_document_path(
    path: str | Path,
) -> Path:
    """
    Vérifie que :

    1. le chemin existe ;
    2. il s'agit bien d'un fichier ;
    3. son extension est supportée.

    Retourne le chemin sous forme de Path.
    """

    document_path = Path(path)

    # ---------------------------------------------------------
    # Vérification existence
    # ---------------------------------------------------------

    if not document_path.exists():

        raise FileNotFoundError(
            f"Document introuvable : "
            f"{document_path}"
        )

    # ---------------------------------------------------------
    # Vérification fichier
    # ---------------------------------------------------------

    if not document_path.is_file():

        raise ValueError(
            f"Le chemin n'est pas un fichier : "
            f"{document_path}"
        )

    # ---------------------------------------------------------
    # Vérification extension
    # ---------------------------------------------------------

    extension = (
        document_path
        .suffix
        .lower()
    )

    if extension not in SUPPORTED_EXTENSIONS:

        supported = ", ".join(
            sorted(
                SUPPORTED_EXTENSIONS
            )
        )

        raise ValueError(
            f"Format non supporté : "
            f"{extension or '[aucune extension]'}\n"
            f"Formats acceptés : "
            f"{supported}"
        )

    return document_path


# =============================================================
# CHARGEMENT D'UNE IMAGE
# =============================================================

def load_image(
    path: str | Path,
) -> Image.Image:
    """
    Charge une image avec Pillow.

    Formats supportés :

        PNG
        JPG
        JPEG
        TIFF
        WEBP

    L'image est convertie en RGB afin de garantir
    une compatibilité avec les étapes suivantes :

        preprocessing
        OCR
        coordonnées
        extraction
    """

    document_path = validate_document_path(
        path
    )

    document_type = get_document_type(
        document_path
    )

    if document_type != "image":

        raise ValueError(
            "load_image() accepte "
            "uniquement les fichiers image."
        )

    try:

        with Image.open(
            document_path
        ) as image:

            # -------------------------------------------------
            # Conversion uniforme en RGB
            # -------------------------------------------------

            loaded_image = image.convert(
                "RGB"
            )

            return loaded_image.copy()

    except Exception as exc:

        raise RuntimeError(
            f"Impossible de charger "
            f"l'image : {document_path}\n"
            f"Détail : {exc}"
        ) from exc


# =============================================================
# CHARGEMENT D'UNE IMAGE COMME DOCUMENT
# =============================================================

def load_image_document(
    path: str | Path,
) -> LoadedDocument:
    """
    Charge une image comme un document
    contenant une seule page.
    """

    document_path = validate_document_path(
        path
    )

    image = load_image(
        document_path
    )

    page = DocumentPage(
        page_number=1,
        image=image,
    )

    return LoadedDocument(
        path=document_path,
        document_type="image",
        pages=[
            page
        ],
    )


# =============================================================
# CHARGEMENT PDF
# =============================================================

def load_pdf_document(
    path: str | Path,
    dpi: int = 200,
) -> LoadedDocument:
    """
    Charge un PDF et transforme chaque page
    en image PIL.

    Supporte :

        PDF une page
        PDF multipage

    Paramètre :

        dpi :
            résolution utilisée pour convertir
            les pages PDF en images.

    Valeur recommandée :

        150 -> rapide
        200 -> bon compromis
        300 -> meilleure qualité OCR
    """

    document_path = validate_document_path(
        path
    )

    document_type = get_document_type(
        document_path
    )

    if document_type != "pdf":

        raise ValueError(
            "load_pdf_document() accepte "
            "uniquement les fichiers PDF."
        )

    # ---------------------------------------------------------
    # Validation DPI
    # ---------------------------------------------------------

    if dpi <= 0:

        raise ValueError(
            "Le DPI doit être supérieur à 0."
        )

    if dpi > 600:

        raise ValueError(
            "Le DPI est trop élevé. "
            "Utilisez une valeur comprise "
            "entre 1 et 600."
        )

    # ---------------------------------------------------------
    # Import PyMuPDF moderne
    # ---------------------------------------------------------

    try:

        import pymupdf

    except ImportError as exc:

        raise ImportError(
            "PyMuPDF n'est pas installé.\n\n"
            "Installez-le avec :\n"
            "python -m pip install pymupdf"
        ) from exc

    # =========================================================
    # OUVERTURE DU PDF
    # =========================================================

    try:

        pdf = pymupdf.open(
            document_path
        )

    except Exception as exc:

        raise RuntimeError(
            f"Impossible d'ouvrir le PDF : "
            f"{document_path}\n"
            f"Détail : {exc}"
        ) from exc

    pages: list[DocumentPage] = []

    try:

        # -----------------------------------------------------
        # PDF standard = 72 DPI
        # -----------------------------------------------------

        scale = dpi / 72.0

        matrix = pymupdf.Matrix(
            scale,
            scale,
        )

        # -----------------------------------------------------
        # Parcours de toutes les pages
        # -----------------------------------------------------

        for page_index in range(
            len(pdf)
        ):

            pdf_page = pdf[
                page_index
            ]

            # -------------------------------------------------
            # Conversion page PDF -> Pixmap
            # -------------------------------------------------

            pixmap = pdf_page.get_pixmap(
                matrix=matrix,
                alpha=False,
            )

            # -------------------------------------------------
            # Conversion Pixmap -> PIL
            # -------------------------------------------------

            image = Image.frombytes(
                "RGB",
                (
                    pixmap.width,
                    pixmap.height,
                ),
                pixmap.samples,
            )

            # -------------------------------------------------
            # Copie indépendante
            # -------------------------------------------------

            page_image = image.copy()

            image.close()

            # -------------------------------------------------
            # Ajout de la page
            # -------------------------------------------------

            pages.append(
                DocumentPage(
                    page_number=page_index + 1,
                    image=page_image,
                )
            )

    except Exception as exc:

        raise RuntimeError(
            f"Erreur pendant la conversion "
            f"du PDF en images : "
            f"{document_path}\n"
            f"Détail : {exc}"
        ) from exc

    finally:

        # -----------------------------------------------------
        # Fermeture obligatoire du PDF
        # -----------------------------------------------------

        pdf.close()

    # =========================================================
    # DOCUMENT FINAL
    # =========================================================

    return LoadedDocument(
        path=document_path,
        document_type="pdf",
        pages=pages,
    )


# =============================================================
# CHARGEUR PRINCIPAL
# =============================================================

def load_document(
    path: str | Path,
    pdf_dpi: int = 200,
) -> LoadedDocument:
    """
    Charge automatiquement un document.

    Images :

        PNG
        JPG
        JPEG
        TIFF
        WEBP

    PDF :

        PDF une page
        PDF multipage

    Exemple :

        document = load_document(
            "test.png"
        )

        document = load_document(
            "test.pdf"
        )

    Résultat :

        LoadedDocument(
            path=...,
            document_type=...,
            pages=[...]
        )
    """

    document_path = validate_document_path(
        path
    )

    document_type = get_document_type(
        document_path
    )

    # ---------------------------------------------------------
    # IMAGE
    # ---------------------------------------------------------

    if document_type == "image":

        return load_image_document(
            document_path
        )

    # ---------------------------------------------------------
    # PDF
    # ---------------------------------------------------------

    if document_type == "pdf":

        return load_pdf_document(
            document_path,
            dpi=pdf_dpi,
        )

    # ---------------------------------------------------------
    # Sécurité
    # ---------------------------------------------------------

    raise ValueError(
        f"Type de document inconnu : "
        f"{document_type}"
    )


# =============================================================
# INFORMATIONS RAPIDES
# =============================================================

def document_info(
    path: str | Path,
) -> dict:
    """
    Retourne les informations générales
    d'un document sans lancer l'OCR.

    Exemple :

        {
            "path": "test.pdf",
            "name": "test.pdf",
            "extension": ".pdf",
            "type": "pdf"
        }
    """

    document_path = validate_document_path(
        path
    )

    return {
        "path": str(
            document_path
        ),
        "name": document_path.name,
        "extension": (
            document_path
            .suffix
            .lower()
        ),
        "type": get_document_type(
            document_path
        ),
    }


# =============================================================
# TEST DIRECT DU MODULE
# =============================================================

if __name__ == "__main__":

    print("=" * 70)

    print(
        "TEST DOCUMENT LOADER"
    )

    print("=" * 70)

    # ---------------------------------------------------------
    # Fichiers à tester
    # ---------------------------------------------------------

    test_files = [
        "test.png",
        "test.jpg",
        "test.jpeg",
        "test.tif",
        "test.tiff",
        "test.webp",
        "test.pdf",
    ]

    # ---------------------------------------------------------
    # Test de chaque document
    # ---------------------------------------------------------

    for filename in test_files:

        path = Path(
            filename
        )

        # -----------------------------------------------------
        # Fichier absent
        # -----------------------------------------------------

        if not path.exists():

            print(
                f"\n[IGNORE] "
                f"{filename} "
                f"-> fichier absent"
            )

            continue

        print(
            f"\n[TEST] {filename}"
        )

        try:

            # -------------------------------------------------
            # Informations
            # -------------------------------------------------

            info = document_info(
                path
            )

            print(
                f"  Type      : "
                f"{info['type']}"
            )

            print(
                f"  Extension : "
                f"{info['extension']}"
            )

            # -------------------------------------------------
            # Chargement
            # -------------------------------------------------

            document = load_document(
                path
            )

            print(
                f"  Pages     : "
                f"{document.page_count}"
            )

            # -------------------------------------------------
            # Informations pages
            # -------------------------------------------------

            for page in document.pages:

                print(
                    f"    Page "
                    f"{page.page_number}: "
                    f"{page.image.width} x "
                    f"{page.image.height}"
                )

                print(
                    f"    Mode    : "
                    f"{page.image.mode}"
                )

        except Exception as exc:

            print(
                f"  ERREUR : "
                f"{exc}"
            )

    # =========================================================
    # FIN TEST
    # =========================================================

    print("\n")

    print(
        "=" * 70
    )

    print(
        "TEST TERMINE"
    )

    print(
        "=" * 70
    )