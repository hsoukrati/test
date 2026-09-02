from engine.validator import validate_fields


fields = {
    "ref_sap": "M400026D01",
    "ref_be": "REN21-507 D",
    "indice_doc": "1",
    "designation_piece": "LONGERON ARD",
    "ref_client": "755128396R",
    "designation_op": "DECOUPE LASER",
    "numero_op": "10",
    "atelier": "Emboutissage",
}


result = validate_fields(fields)


print("=" * 70)
print("TEST VALIDATION DES CHAMPS")
print("=" * 70)

print()

for name, data in result["fields"].items():
    status = "OK" if data["valid"] else "ERREUR"

    print(
        f"{name:25} : "
        f"{data['value']} "
        f"-> {status}"
    )

print()
print("=" * 70)
print(
    f"VALIDES : "
    f"{result['valid_fields']}/"
    f"{result['total_fields']}"
)

print(
    f"SCORE   : "
    f"{result['validation_score']}"
)
print("=" * 70)