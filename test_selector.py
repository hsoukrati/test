from engine.selector import select_best_variant


EXPECTED_FIELDS = [
    "ref_sap",
    "ref_be",
    "indice_doc",
    "designation_piece",
    "ref_client",
    "designation_op",
    "numero_op",
    "atelier",
]


results = {
    "original": {
        "confidence": 0.821,
        "text": """
        Fiche de montage et de réglage
        Atelier: Emboutissage
        Ref. SAP M400026D01
        Ref. BE: REN21-507 D
        Indice doc: 1
        Désignation pièce: LONGERON ARD
        Ref. client: 755128396R
        Désignation OP: DECOUPE LASER
        N° OP: 10
        """,
        "fields": {
            "ref_sap": "M400026D01",
            "ref_be": "REN21-507 D",
            "indice_doc": "1",
            "designation_piece": "LONGERON ARD",
            "ref_client": "755128396R",
            "designation_op": "DECOUPE LASER",
            "numero_op": "10",
            "atelier": "Emboutissage",
        },
    },

    "grayscale": {
        "confidence": 0.741,
        "text": """
        Ref. SAP M400026D01
        Ref. BE REN21-507 D
        Désignation pièce LONGERON ARD
        Désignation OP DECOUPE LASER
        N° OP 10
        """,
        "fields": {
            "ref_sap": "M400026D01",
            "ref_be": "REN21-507 D",
            "designation_piece": "LONGERON ARD",
            "designation_op": "DECOUPE LASER",
            "numero_op": "10",
        },
    },

    "sharpened": {
        "confidence": 0.742,
        "text": """
        Ref. SAP M400026D01
        Ref. BE REN21-507 D
        Indice doc 1
        Désignation pièce LONGERON ARD
        Ref. client 755128396R
        Désignation OP DECOUPE LASER
        N° OP 10
        """,
        "fields": {
            "ref_sap": "M400026D01",
            "ref_be": "REN21-507 D",
            "indice_doc": "1",
            "designation_piece": "LONGERON ARD",
            "ref_client": "755128396R",
            "designation_op": "DECOUPE LASER",
            "numero_op": "10",
        },
    },

    "binary": {
        "confidence": 0.667,
        "text": """
        Ref. SAP M400026D01
        Ref. BE REN21-507 D
        Désignation pièce LONGERON ARD
        Désignation OP DECOUPE LASER
        N° OP 10
        """,
        "fields": {
            "ref_sap": "M400026D01",
            "ref_be": "REN21-507 D",
            "designation_piece": "LONGERON ARD",
            "designation_op": "DECOUPE LASER",
            "numero_op": "10",
        },
    },

    "adaptive": {
        "confidence": 0.667,
        "text": """
        Fiche de montage et de réglage
        Atelier Emboutissage
        Désignation OP DECOUPE LASER
        N° OP 10
        """,
        "fields": {
            "designation_op": "DECOUPE LASER",
            "numero_op": "10",
            "atelier": "Emboutissage",
        },
    },

    "denoised": {
        "confidence": 0.741,
        "text": """
        Ref. SAP M400026D01
        Ref. BE REN21-507 D
        Désignation pièce LONGERON ARD
        Désignation OP DECOUPE LASER
        N° OP 10
        """,
        "fields": {
            "ref_sap": "M400026D01",
            "ref_be": "REN21-507 D",
            "designation_piece": "LONGERON ARD",
            "designation_op": "DECOUPE LASER",
            "numero_op": "10",
        },
    },
}


print("=" * 70)
print("TEST DU SELECTEUR OCR")
print("=" * 70)

selected = select_best_variant(
    results,
    EXPECTED_FIELDS,
)


print()
print("RESULTATS DES VARIANTES")
print("=" * 70)

for result in selected["all_results"]:
    print(
        f'{result["variant"]:12} '
        f'confiance={result["confidence"]:.3f} '
        f'champs={result["fields_found"]}/{result["total_fields"]} '
        f'qualite={result["text_quality"]:.3f} '
        f'score={result["score"]:.3f}'
    )


print()
print("=" * 70)
print("MEILLEURE VARIANTE")
print("=" * 70)

print("Variante :", selected["selected_variant"])
print("Score    :", selected["score"])
print("Confiance:", selected["confidence"])
print(
    "Champs   :",
    f'{selected["fields_found"]}/{selected["total_fields"]}'
)

print()
print("CHAMPS")
print("=" * 70)

for name, value in selected["fields"].items():
    print(f"{name:22} : {value}")