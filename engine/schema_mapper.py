
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, asdict
from typing import Any


# =============================================================
# SCHEMA MAPPER OCR - SANS IA
# =============================================================
#
# Rôle :
#   Transformer les champs OCR bruts en champs standardisés.
#
# Exemple :
#
#   "Ref"              -> "ref_sap"
#   "Réf SAP"          -> "ref_sap"
#   "Reference SAP"    -> "ref_sap"
#   "Client"           -> "client"
#   "Atelier"          -> "atelier"
#
# Le mapper fonctionne uniquement avec des règles.
# Aucune IA / aucun LLM.
# =============================================================


# =============================================================
# CONFIGURATION
# =============================================================

MIN_LABEL_LENGTH = 2
MAX_LABEL_LENGTH = 100
MAX_VALUE_LENGTH = 500

MIN_CONFIDENCE = 20.0


# =============================================================
# ALIASES DES CHAMPS INDUSTRIELS
# =============================================================
#
# La clé = nom standard
# La liste = variantes possibles dans les documents OCR
# =============================================================

FIELD_ALIASES: dict[str, list[str]] = {

    # ---------------------------------------------------------
    # REFERENCES
    # ---------------------------------------------------------

    "ref_sap": [
        "ref sap",
        "ref. sap",
        "reference sap",
        "référence sap",
        "ref sap piece",
        "ref sap pièce",
        "reference piece",
        "référence pièce",
        "ref piece",
        "réf pièce",
        "code sap",
        "sap",
    ],

    "ref_be": [
        "ref be",
        "ref. be",
        "reference be",
        "référence be",
        "ref bureau etude",
        "ref bureau d'etude",
        "référence bureau etude",
        "reference bureau etude",
        "be",
    ],

    "ref_client": [
        "ref client",
        "ref. client",
        "reference client",
        "référence client",
        "code client",
        "référence constructeur",
        "ref constructeur",
    ],

    # ---------------------------------------------------------
    # DESIGNATION
    # ---------------------------------------------------------

    "designation_piece": [
        "designation",
        "désignation",
        "designation piece",
        "désignation pièce",
        "designation produit",
        "désignation article",
        "produit",
        "article",
        "piece",
        "pièce",
        "nom piece",
        "nom pièce",
    ],

    "designation_op": [
        "designation op",
        "désignation op",
        "designation operation",
        "désignation opération",
        "operation",
        "opération",
        "libelle operation",
        "libellé opération",
    ],

    # ---------------------------------------------------------
    # CLIENT
    # ---------------------------------------------------------

    "client": [
        "client",
        "nom client",
        "client final",
        "constructeur",
        "donneur ordre",
        "donneur d'ordre",
    ],

    # ---------------------------------------------------------
    # ATELIER
    # ---------------------------------------------------------

    "atelier": [
        "atelier",
        "atelier de production",
        "atelier production",
        "secteur",
        "service",
        "unité",
        "unite",
    ],

    # ---------------------------------------------------------
    # OPERATION
    # ---------------------------------------------------------

    "numero_op": [
        "n op",
        "n° op",
        "no op",
        "numero op",
        "num op",
        "numéro op",
        "n operation",
        "n° operation",
        "numero operation",
        "numéro opération",
        "operation n",
        "op n",
    ],

    # ---------------------------------------------------------
    # DATE
    # ---------------------------------------------------------

    "date": [
        "date",
        "date creation",
        "date création",
        "date emission",
        "date émission",
        "date document",
        "date de creation",
        "date de création",
        "date de modification",
        "date modification",
        "établi le",
        "etabli le",
    ],

    # ---------------------------------------------------------
    # INDICE
    # ---------------------------------------------------------

    "indice": [
        "indice",
        "indice document",
        "indice piece",
        "indice pièce",
        "version",
        "revision",
        "révision",
        "rev",
        "rév",
    ],

    # ---------------------------------------------------------
    # EMETTEUR
    # ---------------------------------------------------------

    "emetteur": [
        "emetteur",
        "émetteur",
        "emetteur document",
        "émetteur document",
        "auteur",
        "rédacteur",
        "redacteur",
    ],

    # ---------------------------------------------------------
    # GSP / DOSSIER
    # ---------------------------------------------------------

    "gsp": [
        "gsp",
        "code gsp",
        "numero gsp",
        "numéro gsp",
        "n gsp",
        "n° gsp",
    ],

    # ---------------------------------------------------------
    # PROJET
    # ---------------------------------------------------------

    "projet": [
        "projet",
        "nom projet",
        "programme",
        "programme projet",
    ],

    # ---------------------------------------------------------
    # MOYEN
    # ---------------------------------------------------------

    "moyen": [
        "moyen",
        "moyen production",
        "moyen de production",
        "machine",
        "poste",
        "poste de travail",
        "equipement",
        "équipement",
    ],

    # ---------------------------------------------------------
    # QUANTITE
    # ---------------------------------------------------------

    "quantite": [
        "quantite",
        "quantité",
        "qte",
        "qté",
        "nombre",
        "nb",
    ],

    # ---------------------------------------------------------
    # PRIX
    # ---------------------------------------------------------

    "prix": [
        "prix",
        "prix unitaire",
        "prix unité",
        "prix unitaire ht",
        "cout",
        "coût",
    ],

    # ---------------------------------------------------------
    # STATUT
    # ---------------------------------------------------------

    "statut": [
        "statut",
        "état",
        "etat",
        "status",
    ],
}


# =============================================================
# LABELS A REJETER
# =============================================================
#
# Ces mots sont généralement des morceaux de phrases OCR
# et ne doivent PAS devenir des champs.
# =============================================================

REJECTED_LABELS = {
    "de",
    "du",
    "des",
    "la",
    "le",
    "les",
    "et",
    "en",
    "a",
    "à",
    "au",
    "aux",
    "un",
    "une",
    "pour",
    "par",
    "sur",
    "avec",
    "dans",
    "fiche",
    "technique",
    "montage",
    "réglage",
    "reglage",
    "document",
    "page",
    "coupe",
    "laser",
}


# =============================================================
# LABELS PARTIELS DANGEREUX
# =============================================================
#
# On ne fait pas de correspondance partielle agressive.
# Cela évite :
#
#   "DE"       -> designation_op
#   "et"       -> ...
#   "Fiche"    -> ...
#
# =============================================================

DANGEROUS_SHORT_LABELS = {
    "de",
    "du",
    "et",
    "op",
    "be",
    "sap",
    "n",
    "no",
}


# =============================================================
# DATACLASS
# =============================================================

@dataclass
class MappedField:
    original_label: str
    standard_label: str
    value: str

    page_number: int | None = None

    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0

    confidence: float = 0.0

    source: str = "schema_mapper"


# =============================================================
# NETTOYAGE
# =============================================================

def clean_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value)

    text = text.replace("\r", " ")
    text = text.replace("\n", " ")

    text = re.sub(r"\s+", " ", text)

    return text.strip()


# =============================================================
# SUPPRESSION ACCENTS
# =============================================================

def remove_accents(text: str) -> str:
    text = clean_text(text)

    normalized = unicodedata.normalize(
        "NFD",
        text,
    )

    return "".join(
        char
        for char in normalized
        if unicodedata.category(char) != "Mn"
    )


# =============================================================
# NORMALISATION LABEL
# =============================================================

def normalize_label(label: str) -> str:
    label = clean_text(label)

    label = label.lower()

    label = remove_accents(label)

    label = label.replace("°", "")
    label = label.replace(".", " ")
    label = label.replace("_", " ")

    label = re.sub(
        r"[^a-z0-9\s'-]",
        " ",
        label,
    )

    label = re.sub(
        r"\s+",
        " ",
        label,
    )

    return label.strip()


# =============================================================
# NORMALISATION VALEUR
# =============================================================

def normalize_value(value: str) -> str:
    value = clean_text(value)

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


# =============================================================
# VALIDATION LABEL
# =============================================================

def is_valid_label(label: str) -> bool:
    original = clean_text(label)

    if not original:
        return False

    if len(original) < MIN_LABEL_LENGTH:
        return False

    if len(original) > MAX_LABEL_LENGTH:
        return False

    normalized = normalize_label(original)

    if not normalized:
        return False

    if normalized in REJECTED_LABELS:
        return False

    if normalized in DANGEROUS_SHORT_LABELS:
        return False

    # Un label doit contenir au moins une lettre.
    if not re.search(
        r"[A-Za-zÀ-ÖØ-öø-ÿ]",
        original,
    ):
        return False

    return True


# =============================================================
# VALIDATION VALEUR
# =============================================================

def is_valid_value(value: str) -> bool:
    value = normalize_value(value)

    if not value:
        return False

    if len(value) > MAX_VALUE_LENGTH:
        return False

    return True


# =============================================================
# CONSTRUCTION DE L'INDEX DES ALIASES
# =============================================================

def build_alias_index() -> dict[str, str]:
    index: dict[str, str] = {}

    for standard_label, aliases in FIELD_ALIASES.items():

        # Le nom standard lui-même est accepté.
        index[
            normalize_label(standard_label)
        ] = standard_label

        for alias in aliases:

            normalized = normalize_label(
                alias
            )

            if normalized:
                index[normalized] = standard_label

    return index


ALIAS_INDEX = build_alias_index()


# =============================================================
# CORRESPONDANCE EXACTE
# =============================================================

def map_label(
    label: str,
) -> str | None:

    if not is_valid_label(label):
        return None

    normalized = normalize_label(label)

    # ---------------------------------------------------------
    # Correspondance exacte
    # ---------------------------------------------------------

    if normalized in ALIAS_INDEX:
        return ALIAS_INDEX[normalized]

    return None


# =============================================================
# CORRECTIONS OCR DES LABELS
# =============================================================
#
# Quelques erreurs OCR fréquentes.
# =============================================================

OCR_LABEL_CORRECTIONS = {

    "ref": "ref",
    "rer": "ref",
    "re": "ref",

    "ateller": "atelier",
    "atellier": "atelier",
    "atelIer": "atelier",

    "cllent": "client",
    "c1ient": "client",

    "deslgnation": "designation",
    "deslgnatlon": "designation",

    "plece": "piece",
    "p1ece": "piece",

    "lndice": "indice",
    "indlce": "indice",

    "quantlte": "quantite",
    "quantlte": "quantite",

    "date": "date",

    "emetteur": "emetteur",
    "emetfeur": "emetteur",

    "projet": "projet",

    "statut": "statut",
}


def correct_ocr_label(
    label: str,
) -> str:

    cleaned = clean_text(label)

    normalized = normalize_label(
        cleaned
    )

    if normalized in OCR_LABEL_CORRECTIONS:

        return OCR_LABEL_CORRECTIONS[
            normalized
        ]

    return cleaned


# =============================================================
# EXTRACTION DES INFORMATIONS D'UN CHAMP
# =============================================================

def field_from_dict(
    field: dict[str, Any],
) -> MappedField | None:

    original_label = clean_text(
        field.get(
            "label",
            "",
        )
    )

    value = normalize_value(
        field.get(
            "value",
            "",
        )
    )

    if not original_label:
        return None

    if not is_valid_value(value):
        return None

    confidence_value = field.get(
        "confidence",
        field.get(
            "conf",
            0.0,
        ),
    )

    try:
        confidence = float(
            confidence_value or 0.0
        )
    except (
        TypeError,
        ValueError,
    ):
        confidence = 0.0

    if confidence < MIN_CONFIDENCE:
        return None

    corrected_label = correct_ocr_label(
        original_label
    )

    standard_label = map_label(
        corrected_label
    )

    if standard_label is None:
        return None

    return MappedField(
        original_label=original_label,
        standard_label=standard_label,
        value=value,

        page_number=field.get(
            "page_number"
        ),

        x=float(
            field.get(
                "x",
                0.0,
            )
            or 0.0
        ),

        y=float(
            field.get(
                "y",
                0.0,
            )
            or 0.0
        ),

        width=float(
            field.get(
                "width",
                0.0,
            )
            or 0.0
        ),

        height=float(
            field.get(
                "height",
                0.0,
            )
            or 0.0
        ),

        confidence=confidence,

        source=field.get(
            "source",
            "schema_mapper",
        ),
    )


# =============================================================
# MAPPING D'UNE LISTE DE CHAMPS
# =============================================================

def map_fields(
    fields: list[Any],
) -> list[MappedField]:

    mapped: list[MappedField] = []

    for field in fields:

        if isinstance(
            field,
            MappedField,
        ):
            mapped.append(field)
            continue

        if isinstance(
            field,
            dict,
        ):
            result = field_from_dict(
                field
            )

            if result is not None:
                mapped.append(result)

    return mapped


# =============================================================
# SUPPRESSION DES DOUBLONS
# =============================================================

def deduplicate_mapped_fields(
    fields: list[MappedField],
) -> list[MappedField]:

    grouped: dict[
        tuple[str, str],
        MappedField,
    ] = {}

    for field in fields:

        key = (
            field.standard_label,
            field.value.lower(),
        )

        current = grouped.get(key)

        if current is None:
            grouped[key] = field

        elif field.confidence > current.confidence:
            grouped[key] = field

    return list(
        grouped.values()
    )


# =============================================================
# DICTIONNAIRE STANDARD
# =============================================================

def mapped_fields_to_dict(
    fields: list[MappedField],
) -> dict[str, Any]:

    result: dict[str, Any] = {}

    for field in fields:

        label = field.standard_label
        value = field.value

        if label not in result:

            result[label] = value

            continue

        current = result[label]

        if isinstance(
            current,
            list,
        ):

            if value not in current:
                current.append(value)

        else:

            if current != value:

                result[label] = [
                    current,
                    value,
                ]

    return result


# =============================================================
# EXTRACTION DEPUIS LE RESULTAT DE field_extractor.py
# =============================================================

def map_extraction_result(
    extraction_result: dict[str, Any],
) -> dict[str, Any]:

    if not isinstance(
        extraction_result,
        dict,
    ):
        raise TypeError(
            "extraction_result doit être "
            "un dictionnaire."
        )

    field_list = extraction_result.get(
        "field_list",
        [],
    )

    mapped = map_fields(
        field_list
    )

    unique = deduplicate_mapped_fields(
        mapped
    )

    fields_dict = mapped_fields_to_dict(
        unique
    )

    detailed = [
        asdict(field)
        for field in unique
    ]

    return {
        "fields": fields_dict,

        "field_list": detailed,

        "count": len(unique),

        "mapped_count": len(mapped),

        "unknown_count": max(
            0,
            len(field_list) - len(mapped),
        ),
    }


# =============================================================
# MAPPING DIRECT D'UN DICTIONNAIRE
# =============================================================

def map_dictionary(
    fields: dict[str, Any],
) -> dict[str, Any]:

    if not isinstance(
        fields,
        dict,
    ):
        raise TypeError(
            "fields doit être un dictionnaire."
        )

    result: dict[str, Any] = {}

    for label, value in fields.items():

        corrected_label = correct_ocr_label(
            str(label)
        )

        standard_label = map_label(
            corrected_label
        )

        if standard_label is None:
            continue

        if isinstance(
            value,
            list,
        ):

            clean_values = []

            for item in value:

                item = normalize_value(
                    item
                )

                if item:
                    clean_values.append(
                        item
                    )

            if clean_values:
                result[
                    standard_label
                ] = clean_values

        else:

            value = normalize_value(
                value
            )

            if value:
                result[
                    standard_label
                ] = value

    return result


# =============================================================
# SCHEMA FINAL INDUSTRIEL
# =============================================================

def build_industrial_schema(
    fields: dict[str, Any],
) -> dict[str, Any]:

    schema = {

        "ref_sap": None,

        "ref_be": None,

        "ref_client": None,

        "designation_piece": None,

        "client": None,

        "projet": None,

        "atelier": None,

        "numero_op": None,

        "designation_op": None,

        "moyen": None,

        "gsp": None,

        "emetteur": None,

        "date": None,

        "indice": None,

        "statut": None,

        "quantite": None,

        "prix": None,
    }

    for key, value in fields.items():

        if key not in schema:
            continue

        schema[key] = value

    return schema


# =============================================================
# PIPELINE PRINCIPALE
# =============================================================

def process_extraction(
    extraction_result: dict[str, Any],
) -> dict[str, Any]:

    mapped_result = map_extraction_result(
        extraction_result
    )

    industrial_schema = build_industrial_schema(
        mapped_result["fields"]
    )

    return {

        "fields": mapped_result[
            "fields"
        ],

        "industrial_schema":
            industrial_schema,

        "field_list":
            mapped_result[
                "field_list"
            ],

        "count":
            mapped_result[
                "count"
            ],

        "mapped_count":
            mapped_result[
                "mapped_count"
            ],

        "unknown_count":
            mapped_result[
                "unknown_count"
            ],
    }


# =============================================================
# TESTS
# =============================================================

def run_test() -> None:

    print(
        "=" * 70
    )

    print(
        "TEST SCHEMA MAPPER OCR - SANS IA"
    )

    print(
        "=" * 70
    )

    # =========================================================
    # TEST 1
    # =========================================================

    print(
        "\n[1] Test mapping des labels"
    )

    test_labels = [

        "Ref SAP",

        "Réf. SAP",

        "Reference SAP",

        "Client",

        "Atelier",

        "Désignation pièce",

        "N° OP",

        "Date",

        "Indice",

        "Quantité",

        "Prix",
    ]

    for label in test_labels:

        result = map_label(
            label
        )

        print(
            f"  {label:<25} -> {result}"
        )

    # =========================================================
    # TEST 2
    # =========================================================

    print(
        "\n[2] Test correction OCR"
    )

    ocr_labels = [

        "cllent",

        "Ateller",

        "deslgnation",

        "plece",

        "lndice",

        "quantlte",
    ]

    for label in ocr_labels:

        corrected = correct_ocr_label(
            label
        )

        mapped = map_label(
            corrected
        )

        print(
            f"  {label:<20} -> "
            f"{corrected:<20} -> "
            f"{mapped}"
        )

    # =========================================================
    # TEST 3
    # =========================================================

    print(
        "\n[3] Test champs OCR"
    )

    extraction_result = {

        "field_list": [

            {
                "label": "Ref SAP",
                "value": "M400028D01",
                "confidence": 95,
                "source": "label_colon_value",
            },

            {
                "label": "Client",
                "value": "Renault",
                "confidence": 94,
                "source": "label_colon_value",
            },

            {
                "label": "Atelier",
                "value": "Emboutissage",
                "confidence": 93,
                "source": "label_colon_value",
            },

            {
                "label": "Désignation pièce",
                "value": "LONGERON AR D",
                "confidence": 92,
                "source": "label_colon_value",
            },

            {
                "label": "N° OP",
                "value": "125",
                "confidence": 90,
                "source": "label_colon_value",
            },

            {
                "label": "DE",
                "value": "COUPE",
                "confidence": 90,
                "source": "spatial_right",
            },

            {
                "label": "et",
                "value": "de",
                "confidence": 90,
                "source": "spatial_right",
            },

            {
                "label": "Fiche",
                "value": "de",
                "confidence": 90,
                "source": "spatial_right",
            },
        ]
    }

    result = process_extraction(
        extraction_result
    )

    print(
        "\nChamps standardisés :"
    )

    for label, value in result[
        "fields"
    ].items():

        print(
            f"  {label:<25} : {value}"
        )

    # =========================================================
    # TEST 4
    # =========================================================

    print(
        "\n[4] Schema industriel"
    )

    for label, value in result[
        "industrial_schema"
    ].items():

        if value is not None:

            print(
                f"  {label:<25} : {value}"
            )

    # =========================================================
    # TEST 5
    # =========================================================

    print(
        "\n[5] Faux champs rejetés"
    )

    bad_labels = [

        "DE",

        "et",

        "Fiche",

        "montage",

        "réglage",

        "de",

        "la",
    ]

    for label in bad_labels:

        result = map_label(
            label
        )

        status = (
            "REJETE"
            if result is None
            else result
        )

        print(
            f"  {label:<20} -> {status}"
        )

    # =========================================================
    # FIN
    # =========================================================

    print(
        "\n"
        + "=" * 70
    )

    print(
        "TEST SCHEMA MAPPER TERMINE"
    )

    print(
        "=" * 70
    )


# =============================================================
# POINT D'ENTREE
# =============================================================

if __name__ == "__main__":

    run_test()

