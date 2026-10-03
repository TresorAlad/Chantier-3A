from auth.password import hash_password, verify_password


def test_hash_and_verify_roundtrip():
    encoded = hash_password("TdevAdmin2026!")
    assert encoded.startswith("$argon2id$")
    assert verify_password(encoded, "TdevAdmin2026!")
    assert not verify_password(encoded, "wrong-password")
