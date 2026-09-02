from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Document:
    """
    Modèle simple d'un document OCR.

    Aucun PostgreSQL.
    Aucun LLM.
    Les résultats sont stockés en JSON.
    """

    filename: str

    file_path: str = ""

    document_type: str = "unknown"

    pages: int = 0

    text: str = ""

    fields: dict[str, Any] = field(
        default_factory=dict
    )

    tables: list[Any] = field(
        default_factory=list
    )

    statistics: dict[str, Any] = field(
        default_factory=dict
    )

    confidence: float = 0.0

    status: str = "uploaded"

    ai_enabled: bool = False

    llm_enabled: bool = False

    result_file: str | None = None


    def to_dict(self) -> dict[str, Any]:
        """Convertit le document en dictionnaire."""

        return {
            "filename": self.filename,
            "file_path": self.file_path,
            "document_type": self.document_type,
            "pages": self.pages,
            "text": self.text,
            "fields": self.fields,
            "tables": self.tables,
            "statistics": self.statistics,
            "confidence": self.confidence,
            "status": self.status,
            "ai_enabled": self.ai_enabled,
            "llm_enabled": self.llm_enabled,
            "result_file": self.result_file,
        }


    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> "Document":
        """Crée un Document depuis un dictionnaire."""

        return cls(
            filename=str(
                data.get(
                    "filename",
                    "",
                )
            ),

            file_path=str(
                data.get(
                    "file_path",
                    "",
                )
            ),

            document_type=str(
                data.get(
                    "document_type",
                    "unknown",
                )
            ),

            pages=int(
                data.get(
                    "pages",
                    0,
                )
                or 0
            ),

            text=str(
                data.get(
                    "text",
                    "",
                )
            ),

            fields=(
                data.get(
                    "fields",
                    {},
                )
                if isinstance(
                    data.get(
                        "fields",
                        {},
                    ),
                    dict,
                )
                else {}
            ),

            tables=(
                data.get(
                    "tables",
                    [],
                )
                if isinstance(
                    data.get(
                        "tables",
                        [],
                    ),
                    list,
                )
                else []
            ),

            statistics=(
                data.get(
                    "statistics",
                    {},
                )
                if isinstance(
                    data.get(
                        "statistics",
                        {},
                    ),
                    dict,
                )
                else {}
            ),

            confidence=float(
                data.get(
                    "confidence",
                    0.0,
                )
                or 0.0
            ),

            status=str(
                data.get(
                    "status",
                    "uploaded",
                )
            ),

            ai_enabled=bool(
                data.get(
                    "ai_enabled",
                    False,
                )
            ),

            llm_enabled=bool(
                data.get(
                    "llm_enabled",
                    False,
                )
            ),

            result_file=data.get(
                "result_file"
            ),
        )


    def is_processed(self) -> bool:
        """Indique si le document a été traité."""

        return self.status == "processed"


    def has_extraction(self) -> bool:
        """Indique si des champs ont été extraits."""

        return bool(self.fields)


    def has_tables(self) -> bool:
        """Indique si des tableaux ont été détectés."""

        return bool(self.tables)


# =============================================================
# TEST
# =============================================================

def run_test() -> None:

    print("=" * 70)
    print("TEST DOCUMENT MODEL - OCR SANS IA")
    print("=" * 70)

    document = Document(
        filename="test.pdf",
        file_path="uploads/test.pdf",
        document_type="pdf",
        pages=1,
        text="Ref: ABC123\nClient: Renault",
        fields={
            "ref_sap": "ABC123",
            "client": "Renault",
        },
        confidence=0.92,
        status="processed",
    )

    print()
    print("Document :")
    print(f"  filename    : {document.filename}")
    print(f"  type        : {document.document_type}")
    print(f"  pages       : {document.pages}")
    print(f"  confidence  : {document.confidence}")
    print(f"  status      : {document.status}")

    print()
    print("Extraction :")
    for key, value in document.fields.items():
        print(f"  {key:<15} : {value}")

    print()
    print(f"Traité       : {document.is_processed()}")
    print(f"Extraction   : {document.has_extraction()}")
    print(f"Tableaux     : {document.has_tables()}")

    print()
    print("IA activée   :", document.ai_enabled)
    print("LLM activé   :", document.llm_enabled)

    print()
    print("=" * 70)
    print("TEST DOCUMENT MODEL TERMINE")
    print("=" * 70)


if __name__ == "__main__":
    run_test()