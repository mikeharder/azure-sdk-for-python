# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------
import codecs
from datetime import datetime, timezone
import hashlib
from json import dumps
import os
import time
from datetime import datetime, timezone
from unittest import mock

from devtools_testutils import recorded_by_proxy, set_bodiless_matcher

from cryptography.hazmat.primitives.hashes import SHA1, SHA256
from cryptography.hazmat.primitives.asymmetric.padding import MGF1, OAEP, PKCS1v15
from cryptography.hazmat.primitives.asymmetric.rsa import (
    rsa_crt_dmp1,
    rsa_crt_dmq1,
    rsa_crt_iqmp,
    RSAPrivateNumbers,
    RSAPublicNumbers
)
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, PublicFormat
import pytest

from azure.core.exceptions import AzureError, HttpResponseError
from azure.core.pipeline.policies import SansIOHTTPPolicy
from azure.core.rest import HttpRequest
from azure.keyvault.keys import ApiVersion, JsonWebKey, KeyCurveName, KeyOperation, KeyVaultKey
from azure.keyvault.keys.crypto import (
    CryptographyClient,
    EncryptionAlgorithm,
    KeyWrapAlgorithm,
    SignatureAlgorithm,
)
from azure.keyvault.keys.crypto._providers import NoLocalCryptography, get_local_cryptography_provider
from azure.keyvault.keys._generated._serialization import Deserializer
from azure.keyvault.keys._generated.models import KeySignParameters
from azure.keyvault.keys._shared.client_base import DEFAULT_VERSION
from devtools_testutils import recorded_by_proxy, set_bodiless_matcher

from _shared.test_case import KeyVaultTestCase
from _test_case import KeysClientPreparer, get_decorator
from _keys_test_case import KeysTestCase


all_api_versions = get_decorator()
only_hsm = get_decorator(only_hsm=True)
only_vault_default = get_decorator(only_vault=True, api_versions=[DEFAULT_VERSION])
only_vault_7_4_plus = get_decorator(only_vault=True, api_versions=[ApiVersion.V7_4, ApiVersion.V7_5])


def _to_bytes(hex):
    if len(hex) % 2:
        hex = f"0{hex}"
    return codecs.decode(hex, "hex_codec")


# RSA key with private components so that the JWK can be used for private operations
TEST_JWK = {
    "kty":"RSA",
    "key_ops":["decrypt", "verify", "unwrapKey"],
    "n":_to_bytes(
        "00a0914d00234ac683b21b4c15d5bed887bdc959c2e57af54ae734e8f00720d775d275e455207e3784ceeb60a50a4655dd72a7a94d271e8ee8f7959a669ca6e775bf0e23badae991b4529d978528b4bd90521d32dd2656796ba82b6bbfc7668c8f5eeb5053747fd199319d29a8440d08f4412d527ff9311eda71825920b47b1c46b11ab3e91d7316407e89c7f340f7b85a34042ce51743b27d4718403d34c7b438af6181be05e4d11eb985d38253d7fe9bf53fc2f1b002d22d2d793fa79a504b6ab42d0492804d7071d727a06cf3a8893aa542b1503f832b296371b6707d4dc6e372f8fe67d8ded1c908fde45ce03bc086a71487fa75e43aa0e0679aa0d20efe35"
    ),
    "e":_to_bytes("10001"),
    "p":_to_bytes(
        "00d1deac8d68ddd2c1fd52d5999655b2cf1565260de5269e43fd2a85f39280e1708ffff0682166cb6106ee5ea5e9ffd9f98d0becc9ff2cda2febc97259215ad84b9051e563e14a051dce438bc6541a24ac4f014cf9732d36ebfc1e61a00d82cbe412090f7793cfbd4b7605be133dfc3991f7e1bed5786f337de5036fc1e2df4cf3"
    ),
    "q":_to_bytes(
        "00c3dc66b641a9b73cd833bc439cd34fc6574465ab5b7e8a92d32595a224d56d911e74624225b48c15a670282a51c40d1dad4bc2e9a3c8dab0c76f10052dfb053bc6ed42c65288a8e8bace7a8881184323f94d7db17ea6dfba651218f931a93b8f738f3d8fd3f6ba218d35b96861a0f584b0ab88ddcf446b9815f4d287d83a3237"
    ),
    "d":_to_bytes(
        "627c7d24668148fe2252c7fa649ea8a5a9ed44d75c766cda42b29b660e99404f0e862d4561a6c95af6a83d213e0a2244b03cd28576473215073785fb067f015da19084ade9f475e08b040a9a2c7ba00253bb8125508c9df140b75161d266be347a5e0f6900fe1d8bbf78ccc25eeb37e0c9d188d6e1fc15169ba4fe12276193d77790d2326928bd60d0d01d6ead8d6ac4861abadceec95358fd6689c50a1671a4a936d2376440a41445501da4e74bfb98f823bd19c45b94eb01d98fc0d2f284507f018ebd929b8180dbe6381fdd434bffb7800aaabdd973d55f9eaf9bb88a6ea7b28c2a80231e72de1ad244826d665582c2362761019de2e9f10cb8bcc2625649"
    )
}


class TestCryptoClient(KeyVaultTestCase, KeysTestCase):
    plaintext = b"5063e6aaa845f150200547944fd199679c98ed6f99da0a0b2dafeaf1f4684496fd532c1c229968cb9dee44957fcef7ccef59ceda0b362e56bcd78fd3faee5781c623c0bb22b35beabde0664fd30e0e824aba3dd1b0afffc4a3d955ede20cf6a854d52cfd"
    iv = codecs.decode("89b8adbfb07345e3598932a09c517441", "hex_codec")
    aad = b"test"

    def _create_rsa_key(self, client, key_name, **kwargs):
        key_ops = kwargs.get("key_operations") or ["encrypt", "decrypt", "sign", "verify", "wrapKey", "unwrapKey"]
        hsm = kwargs.get("hardware_protected") or False
        if self.is_live:
            time.sleep(2)  # to avoid throttling by the service
        created_key = client.create_rsa_key(key_name, **kwargs)
        kty = "RSA-HSM" if hsm else "RSA"
        self._validate_rsa_key_bundle(created_key, client.vault_url, key_name, kty, key_ops)
        return created_key

    def _create_ec_key(self, client, key_name, **kwargs):
        key_curve = kwargs.get("curve") or "P-256"
        hsm = kwargs.get("hardware_protected") or False
        if self.is_live:
            time.sleep(2)  # to avoid throttling by the service
        created_key = client.create_ec_key(key_name, **kwargs)
        key_type = "EC-HSM" if hsm else "EC"
        self._validate_ec_key_bundle(key_curve, created_key, client.vault_url, key_name, key_type)
        return created_key

    def _validate_rsa_key_bundle(self, key_attributes, vault, key_name, kty, key_ops):
        prefix = "/".join(s.strip("/") for s in [vault, "keys", key_name])
        key = key_attributes.key
        kid = key_attributes.id
        assert kid.index(prefix) == 0, f"Key Id should start with '{prefix}', but value is '{kid}'"
        assert key.kty == kty, f"kty should by '{key}', but is '{key.kty}'"
        assert key.n and key.e, "Bad RSA public material."
        assert sorted(key_ops) == sorted(key.key_ops), f"keyOps should be '{key_ops}', but is '{key.key_ops}'"
        
        assert key_attributes.properties.created_on and key_attributes.properties.updated_on, "Missing required date attributes."
        

    def _validate_ec_key_bundle(self, key_curve, key_attributes, vault, key_name, kty):
        prefix = "/".join(s.strip("/") for s in [vault, "keys", key_name])
        key = key_attributes.key
        kid = key_attributes.id
        assert key_curve == key.crv
        assert kid.index(prefix) == 0, f"Key Id should start with '{prefix}', but value is '{kid}'"
        assert key.kty == kty, f"kty should by '{key}', but is '{key.kty}'"
        assert key_attributes.properties.created_on and key_attributes.properties.updated_on,"Missing required date attributes."

    def _import_test_key(self, client, name, hardware_protected=False):
        key = JsonWebKey(
            kty="RSA-HSM" if hardware_protected else "RSA",
            key_ops=["encrypt", "decrypt", "sign", "verify", "wrapKey", "unwrapKey"],
            n=_to_bytes(
                "00a0914d00234ac683b21b4c15d5bed887bdc959c2e57af54ae734e8f00720d775d275e455207e3784ceeb60a50a4655dd72a7a94d271e8ee8f7959a669ca6e775bf0e23badae991b4529d978528b4bd90521d32dd2656796ba82b6bbfc7668c8f5eeb5053747fd199319d29a8440d08f4412d527ff9311eda71825920b47b1c46b11ab3e91d7316407e89c7f340f7b85a34042ce51743b27d4718403d34c7b438af6181be05e4d11eb985d38253d7fe9bf53fc2f1b002d22d2d793fa79a504b6ab42d0492804d7071d727a06cf3a8893aa542b1503f832b296371b6707d4dc6e372f8fe67d8ded1c908fde45ce03bc086a71487fa75e43aa0e0679aa0d20efe35"
            ),
            e=_to_bytes("10001"),
            d=_to_bytes(
                "627c7d24668148fe2252c7fa649ea8a5a9ed44d75c766cda42b29b660e99404f0e862d4561a6c95af6a83d213e0a2244b03cd28576473215073785fb067f015da19084ade9f475e08b040a9a2c7ba00253bb8125508c9df140b75161d266be347a5e0f6900fe1d8bbf78ccc25eeb37e0c9d188d6e1fc15169ba4fe12276193d77790d2326928bd60d0d01d6ead8d6ac4861abadceec95358fd6689c50a1671a4a936d2376440a41445501da4e74bfb98f823bd19c45b94eb01d98fc0d2f284507f018ebd929b8180dbe6381fdd434bffb7800aaabdd973d55f9eaf9bb88a6ea7b28c2a80231e72de1ad244826d665582c2362761019de2e9f10cb8bcc2625649"
            ),
            p=_to_bytes(
                "00d1deac8d68ddd2c1fd52d5999655b2cf1565260de5269e43fd2a85f39280e1708ffff0682166cb6106ee5ea5e9ffd9f98d0becc9ff2cda2febc97259215ad84b9051e563e14a051dce438bc6541a24ac4f014cf9732d36ebfc1e61a00d82cbe412090f7793cfbd4b7605be133dfc3991f7e1bed5786f337de5036fc1e2df4cf3"
            ),
            q=_to_bytes(
                "00c3dc66b641a9b73cd833bc439cd34fc6574465ab5b7e8a92d32595a224d56d911e74624225b48c15a670282a51c40d1dad4bc2e9a3c8dab0c76f10052dfb053bc6ed42c65288a8e8bace7a8881184323f94d7db17ea6dfba651218f931a93b8f738f3d8fd3f6ba218d35b96861a0f584b0ab88ddcf446b9815f4d287d83a3237"
            ),
            dp=_to_bytes(
                "00c9a159be7265cbbabc9afcc4967eb74fe58a4c4945431902d1142da599b760e03838f8cbd26b64324fea6bdc9338503f459793636e59b5361d1e6951e08ddb089e1b507be952a81fbeaf7e76890ea4f536e25505c3f648b1e88377dfc19b4c304e738dfca07211b792286a392a704d0f444c0a802539110b7f1f121c00cff0a9"
            ),
            dq=_to_bytes(
                "00a0bd4c0a3d9f64436a082374b5caf2488bac1568696153a6a5e4cd85d186db31e2f58f024c617d29f37b4e6b54c97a1e25efec59c4d1fd3061ac33509ce8cae5c11f4cd2e83f41a8264f785e78dc0996076ee23dfdfc43d67c463afaa0180c4a718357f9a6f270d542479a0f213870e661fb950abca4a14ca290570ba7983347"
            ),
            qi=_to_bytes(
                "009fe7ae42e92bc04fcd5780464bd21d0c8ac0c599f9af020fde6ab0a7e7d1d39902f5d8fb6c614184c4c1b103fb46e94cd10a6c8a40f9991a1f28269f326435b6c50276fda6493353c650a833f724d80c7d522ba16c79f0eb61f672736b68fb8be3243d10943c4ab7028d09e76cfb5892222e38bc4d35585bf35a88cd68c73b07"
            ),
        )
        imported_key = client.import_key(name, key)
        self._validate_rsa_key_bundle(imported_key, client.vault_url, name, key.kty, key.key_ops)
        return imported_key

    def _import_symmetric_test_key(self, client, name):
        key_material = codecs.decode("e27ed0c84512bbd55b6af434d237c11feba311870f80f2c2e3364260f31c82c8", "hex_codec")
        key = JsonWebKey(
            kty="oct-HSM",
            key_ops=["encrypt", "decrypt", "wrapKey", "unwrapKey"],
            k=key_material,
        )
        imported_key = client.import_key(name, key)  # the key material isn't returned by the service
        key.kid = imported_key.id
        key_vault_key = KeyVaultKey(key_id=imported_key.id, jwk=vars(key))  # create a key containing the material
        assert key_vault_key.key.k == key_material
        assert key_vault_key.key.kid == imported_key.id == key_vault_key.id
        return key_vault_key

    @pytest.mark.parametrize("api_version,is_hsm",all_api_versions)
    @KeysClientPreparer()
    @recorded_by_proxy
    def test_ec_key_id(self, key_client, is_hsm, **kwargs):
        """When initialized with a key ID, the client should retrieve the key and perform public operations locally"""
        key = self._create_ec_key(key_client, self.get_resource_name("eckey"), hardware_protected=is_hsm)

        crypto_client = self.create_crypto_client(key.id, api_version=key_client.api_version)
        crypto_client._initialize()
        assert crypto_client.key_id == key.id

        # ensure all remote crypto operations will fail
        crypto_client._client = None

        crypto_client.verify(SignatureAlgorithm.es256_k, hashlib.sha256(self.plaintext).digest(), self.plaintext)

    @pytest.mark.parametrize("api_version,is_hsm",all_api_versions)
    @KeysClientPreparer()
    @recorded_by_proxy
    def test_rsa_key_id(self, key_client, is_hsm, **kwargs):
        """When initialized with a key ID, the client should retrieve the key and perform public operations locally"""
        key = self._create_rsa_key(key_client, self.get_resource_name("rsakey"), hardware_protected=is_hsm)

        crypto_client = self.create_crypto_client(key.id, api_version=key_client.api_version)
        crypto_client._initialize()
        assert crypto_client.key_id == key.id

        # ensure all remote crypto operations will fail
        crypto_client._client = None

        crypto_client.encrypt(EncryptionAlgorithm.rsa_oaep, self.plaintext)
        crypto_client.verify(SignatureAlgorithm.rs256, hashlib.sha256(self.plaintext).digest(), self.plaintext)
        crypto_client.wrap_key(KeyWrapAlgorithm.rsa_oaep, self.plaintext)

    @pytest.mark.parametrize("api_version,is_hsm", all_api_versions)
    @KeysClientPreparer()
    @recorded_by_proxy
    def test_encrypt_and_decrypt(self, key_client, is_hsm, **kwargs):
        key_name = self.get_resource_name("keycrypt")

        imported_key = self._import_test_key(key_client, key_name, hardware_protected=is_hsm)
        crypto_client = self.create_crypto_client(imported_key.id, api_version=key_client.api_version)
        crypto_client._keys_get_forbidden = True  # Prevent caching key material locally, to force remote ops

        result = crypto_client.encrypt(EncryptionAlgorithm.rsa_oaep, self.plaintext)
        assert result.key_id == imported_key.id

        result = crypto_client.decrypt(result.algorithm, result.ciphertext)
        assert result.key_id == imported_key.id
        assert EncryptionAlgorithm.rsa_oaep == result.algorithm
        assert self.plaintext == result.plaintext

    @pytest.mark.parametrize("api_version,is_hsm", only_vault_7_4_plus)
    @KeysClientPreparer()
    @recorded_by_proxy
    def test_encrypt_and_decrypt_with_managed_key(self, key_client, **kwargs):
        key_name = self.get_resource_name("keycrypt")

        imported_key = self._import_test_key(key_client, key_name)
        # Use the key's ID to create the client, ensuring the material is fetched when the RSA key is created
        crypto_client = self.create_crypto_client(imported_key.id, api_version=key_client.api_version)

        # Create a KeyVaultRSAPublicKey that can perform encryption with `cryptography`'s interface
        public_key = crypto_client.create_rsa_public_key()
        algorithm = SHA1()
        mgf = MGF1(algorithm)
        padding = OAEP(mgf, algorithm, None)
        ciphertext = public_key.encrypt(self.plaintext, padding)

        # Create a KeyVaultRSAPrivateKey that can perform decryption with `cryptography`'s interface
        private_key = crypto_client.create_rsa_private_key()
        plaintext = private_key.decrypt(ciphertext=ciphertext, padding=padding)
        assert self.plaintext == plaintext

        # Use cryptography library's own implementation to validate ours (as well as our public/private numbers)
        crypto_public_key = public_key.public_numbers().public_key()
        crypto_ciphertext = crypto_public_key.encrypt(self.plaintext, padding)
        # Create a crypto client from private JWK since we can't get the private components from an imported key
        crypto_client = CryptographyClient.from_jwk(jwk=TEST_JWK)
        crypto_private_key = crypto_client.create_rsa_private_key().private_numbers().private_key()
        crypto_plaintext = crypto_private_key.decrypt(ciphertext=crypto_ciphertext, padding=padding)
        assert crypto_plaintext == plaintext

    @pytest.mark.parametrize("api_version,is_hsm", only_vault_default)
    @KeysClientPreparer()
    @recorded_by_proxy
    def test_encrypt_and_decrypt_with_managed_key_no_get(self, key_client, **kwargs):
        key_name = self.get_resource_name("keycrypt")

        imported_key = self._import_test_key(key_client, key_name)
        # Use the key's ID to create the client, ensuring the we don't have the material
        crypto_client = self.create_crypto_client(imported_key.id, api_version=key_client.api_version)
        crypto_client._keys_get_forbidden = True  # Prevent caching key material locally, to force remote ops

        # Create a KeyVaultRSAPublicKey that can perform encryption with `cryptography`'s interface
        public_key = crypto_client.create_rsa_public_key()
        algorithm = SHA1()
        mgf = MGF1(algorithm)
        padding = OAEP(mgf, algorithm, None)
        ciphertext = public_key.encrypt(self.plaintext, padding)

        # Create a KeyVaultRSAPrivateKey that can perform decryption with `cryptography`'s interface
        private_key = crypto_client.create_rsa_private_key()
        plaintext = private_key.decrypt(ciphertext=ciphertext, padding=padding)
        assert self.plaintext == plaintext

        # Ensure we raise for operations that can't be performed without local key material
        with pytest.raises(ValueError) as ex:
            public_key.public_numbers()
        assert "key material" in str(ex.value).lower()
        with pytest.raises(ValueError) as ex:
            public_key.public_bytes(None, None)
        assert "key material" in str(ex.value).lower()
        with pytest.raises(ValueError) as ex:
            public_key.key_size()
        assert "key material" in str(ex.value).lower()
        assert public_key != imported_key.key  # Even though the keys are equal, we can't compare without key material

        with pytest.raises(ValueError) as ex:
            private_key.private_numbers()
        assert "key material" in str(ex.value).lower()
        with pytest.raises(ValueError) as ex:
            private_key.private_bytes(None, None, None)
        assert "key material" in str(ex.value).lower()
        with pytest.raises(ValueError) as ex:
            private_key.key_size()
        assert "key material" in str(ex.value).lower()

    @pytest.mark.parametrize("api_version,is_hsm", all_api_versions)
    @KeysClientPreparer()
    @recorded_by_proxy
    def test_sign_and_verify(self, key_client, is_hsm, **kwargs):
        key_name = self.get_resource_name("keysign")

        md = hashlib.sha256()
        md.update(self.plaintext)
        digest = md.digest()

        imported_key = self._import_test_key(key_client, key_name, hardware_protected=is_hsm)
        crypto_client = self.create_crypto_client(imported_key.id, api_version=key_client.api_version)
        crypto_client._keys_get_forbidden = True  # Prevent caching key material locally, to force remote ops

        result = crypto_client.sign(SignatureAlgorithm.rs256, digest)
        assert result.key_id == imported_key.id

        verified = crypto_client.verify(result.algorithm, digest, result.signature)
        assert result.key_id == imported_key.id
        assert result.algorithm == SignatureAlgorithm.rs256
        assert verified.is_valid

    @pytest.mark.parametrize("api_version,is_hsm", only_vault_7_4_plus)
    @KeysClientPreparer()
    @recorded_by_proxy
    def test_sign_and_verify_with_managed_key(self, key_client, is_hsm, **kwargs):
        key_name = self.get_resource_name("keysign")

        imported_key = self._import_test_key(key_client, key_name, hardware_protected=is_hsm)
        crypto_client = self.create_crypto_client(imported_key.id, api_version=key_client.api_version)
        crypto_client._keys_get_forbidden = True  # Prevent caching key material locally, to force remote ops

        # Create a KeyVaultRSAPrivateKey that can perform signing with `cryptography`'s interface
        private_key = crypto_client.create_rsa_private_key()
        algorithm = SHA256()
        padding = PKCS1v15()
        signature = private_key.sign(self.plaintext, padding, algorithm)

        # Create a KeyVaultRSAPublicKey that can perform verifying with `cryptography`'s interface
        public_key = crypto_client.create_rsa_public_key()
        public_key.verify(signature, self.plaintext, padding, algorithm)

        # Use cryptography library's own implementation to validate ours (as well as our public/private numbers)
        # Create a crypto client from private JWK since we can't get the private components from an imported key
        crypto_client = CryptographyClient.from_jwk(jwk=TEST_JWK)
        private_numbers = crypto_client.create_rsa_private_key().private_numbers()
        crypto_private_key = private_numbers.private_key()
        crypto_signature = crypto_private_key.sign(self.plaintext, padding, algorithm)

        # PKCS#1 signing produces deterministic signatures, so we can compare the two signatures we generated
        # PSS padding is nondeterministic, by comparison
        assert signature == crypto_signature

        crypto_public_key = private_numbers.public_numbers.public_key()
        crypto_public_key.verify(crypto_signature, self.plaintext, padding, algorithm)
        crypto_public_key.verify(signature, self.plaintext, padding, algorithm)

    @pytest.mark.parametrize("api_version,is_hsm", all_api_versions)
    @KeysClientPreparer()
    @recorded_by_proxy
    def test_wrap_and_unwrap(self, key_client, is_hsm, **kwargs):
        key_name = self.get_resource_name("keywrap")

        created_key = self._create_rsa_key(key_client, key_name, hardware_protected=is_hsm)
        assert created_key is not None
        crypto_client = self.create_crypto_client(created_key.id, api_version=key_client.api_version)
        crypto_client._keys_get_forbidden = True  # Prevent caching key material locally, to force remote ops

        # Wrap a key with the created key, then unwrap it. The wrapped key's bytes should round-trip.
        key_bytes = self.plaintext
        result = crypto_client.wrap_key(KeyWrapAlgorithm.rsa_oaep, key_bytes)
        assert result.key_id == created_key.id

        result = crypto_client.unwrap_key(result.algorithm, result.encrypted_key)
        assert key_bytes, result.key

    @pytest.mark.parametrize("api_version,is_hsm", only_hsm)
    @KeysClientPreparer()
    @recorded_by_proxy
    def test_symmetric_encrypt_and_decrypt(self, key_client, **kwargs):
        """Encrypt and decrypt with the service"""
        key_name = self.get_resource_name("symmetric-encrypt")

        imported_key = self._import_symmetric_test_key(key_client, key_name)
        assert imported_key is not None
        crypto_client = self.create_crypto_client(imported_key, api_version=key_client.api_version)
        # Use 256-bit AES algorithms for the 256-bit key
        symmetric_algorithms = [algorithm for algorithm in EncryptionAlgorithm if algorithm.startswith("A256")]

        supports_nothing = mock.Mock(supports=mock.Mock(return_value=False))
        with mock.patch(crypto_client.__module__ + ".get_local_cryptography_provider", lambda *_: supports_nothing):
            for algorithm in symmetric_algorithms:
                if algorithm.endswith("GCM"):
                    encrypt_result = crypto_client.encrypt(
                        algorithm, self.plaintext, additional_authenticated_data=self.aad
                    )
                    assert encrypt_result.key_id == imported_key.id
                    decrypt_result = crypto_client.decrypt(
                        encrypt_result.algorithm,
                        encrypt_result.ciphertext,
                        iv=encrypt_result.iv,
                        authentication_tag=encrypt_result.tag,
                        additional_authenticated_data=self.aad
                    )
                else:
                    encrypt_result = crypto_client.encrypt(
                        algorithm, self.plaintext, iv=self.iv, additional_authenticated_data=self.aad
                    )
                    assert encrypt_result.key_id == imported_key.id
                    decrypt_result = crypto_client.decrypt(
                        encrypt_result.algorithm,
                        encrypt_result.ciphertext,
                        iv=encrypt_result.iv,
                        additional_authenticated_data=None if "CBC" in algorithm else self.aad
                    )

                assert decrypt_result.key_id == imported_key.id
                assert decrypt_result.algorithm == algorithm
                if algorithm.endswith("CBC"):
                    assert decrypt_result.plaintext.startswith(self.plaintext)  # AES-CBC returns a zero-padded plaintext
                else:
                    assert decrypt_result.plaintext == self.plaintext

    @pytest.mark.parametrize("api_version,is_hsm", only_hsm)
    @KeysClientPreparer()
    @recorded_by_proxy
    def test_symmetric_wrap_and_unwrap(self, key_client, **kwargs):
        key_name = self.get_resource_name("symmetric-kw")

        imported_key = self._import_symmetric_test_key(key_client, key_name)
        assert imported_key is not None
        crypto_client = self.create_crypto_client(imported_key.id, api_version=key_client.api_version)

        result = crypto_client.wrap_key(KeyWrapAlgorithm.aes_256, self.plaintext)
        assert result.key_id == imported_key.id

        result = crypto_client.unwrap_key(result.algorithm, result.encrypted_key)
        assert result.key == self.plaintext

    @pytest.mark.parametrize("api_version,is_hsm",all_api_versions)
    @KeysClientPreparer()
    @recorded_by_proxy
    def test_encrypt_local(self, key_client, is_hsm, **kwargs):
        """Encrypt locally, decrypt with Key Vault"""
        key_name = self.get_resource_name("encrypt-local")
        key = self._create_rsa_key(key_client, key_name, size=4096, hardware_protected=is_hsm)
        crypto_client = self.create_crypto_client(key, api_version=key_client.api_version)

        rsa_encrypt_algorithms = [algorithm for algorithm in EncryptionAlgorithm if algorithm.startswith("RSA")]
        for encrypt_algorithm in rsa_encrypt_algorithms:
            result = crypto_client.encrypt(encrypt_algorithm, self.plaintext)
            assert result.key_id == key.id

            result = crypto_client.decrypt(result.algorithm, result.ciphertext)
            assert result.plaintext == self.plaintext

    @pytest.mark.parametrize("api_version,is_hsm",all_api_versions)
    @KeysClientPreparer()
    @recorded_by_proxy
    def test_encrypt_local_from_jwk(self, key_client, is_hsm, **kwargs):
        """Encrypt locally, decrypt with Key Vault"""
        key_name = self.get_resource_name("encrypt-local")
        key = self._create_rsa_key(key_client, key_name, size=4096, hardware_protected=is_hsm)
        crypto_client = self.create_crypto_client(key, api_version=key_client.api_version)
        local_client = CryptographyClient.from_jwk(key.key)

        rsa_encrypt_algorithms = [algorithm for algorithm in EncryptionAlgorithm if algorithm.startswith("RSA")]
        for encrypt_algorithm in rsa_encrypt_algorithms:
            result = local_client.encrypt(encrypt_algorithm, self.plaintext)
            assert result.key_id == key.id

            result = crypto_client.decrypt(result.algorithm, result.ciphertext)
            assert result.plaintext == self.plaintext
    
    @pytest.mark.parametrize("api_version,is_hsm",only_hsm)
    @KeysClientPreparer()
    @recorded_by_proxy
    def test_symmetric_encrypt_local(self, key_client, **kwargs):
        """Encrypt locally, decrypt with the service"""
        key_name = self.get_resource_name("symmetric-encrypt")

        imported_key = self._import_symmetric_test_key(key_client, key_name)
        assert imported_key is not None
        crypto_client = self.create_crypto_client(imported_key, api_version=key_client.api_version)
        # Use 256-bit AES-CBCPAD for the 256-bit key (only AES-CBCPAD is implemented locally)
        algorithm = EncryptionAlgorithm.a256_cbcpad

        crypto_client._local_provider = get_local_cryptography_provider(imported_key.key)
        encrypt_result = crypto_client.encrypt(
            algorithm, self.plaintext, iv=self.iv, additional_authenticated_data=self.aad
        )
        assert encrypt_result.key_id == imported_key.id
        crypto_client._local_provider = NoLocalCryptography()
        decrypt_result = crypto_client.decrypt(
            encrypt_result.algorithm,
            encrypt_result.ciphertext,
            iv=encrypt_result.iv,
        )

        assert decrypt_result.key_id == imported_key.id
        assert decrypt_result.algorithm == algorithm
        assert decrypt_result.plaintext == self.plaintext
    
    @pytest.mark.parametrize("api_version,is_hsm", only_hsm)
    @KeysClientPreparer()
    @recorded_by_proxy
    def test_symmetric_decrypt_local(self, key_client, **kwargs):
        """Encrypt with the service, decrypt locally"""
        key_name = self.get_resource_name("symmetric-encrypt")

        imported_key = self._import_symmetric_test_key(key_client, key_name)
        assert imported_key is not None
        crypto_client = self.create_crypto_client(imported_key, api_version=key_client.api_version)
        # Use 256-bit AES-CBCPAD for the 256-bit key (only AES-CBCPAD is implemented locally)
        algorithm = EncryptionAlgorithm.a256_cbcpad

        crypto_client._initialized = True
        crypto_client._local_provider = NoLocalCryptography()
        encrypt_result = crypto_client.encrypt(
            algorithm, self.plaintext, iv=self.iv, additional_authenticated_data=self.aad
        )
        assert encrypt_result.key_id == imported_key.id
        crypto_client._local_provider = get_local_cryptography_provider(imported_key.key)
        decrypt_result = crypto_client.decrypt(
            encrypt_result.algorithm,
            encrypt_result.ciphertext,
            iv=encrypt_result.iv,
            additional_authenticated_data=self.aad
        )

        assert decrypt_result.key_id == imported_key.id
        assert decrypt_result.algorithm == algorithm
        assert decrypt_result.plaintext == self.plaintext

    @pytest.mark.parametrize("api_version,is_hsm",all_api_versions)
    @KeysClientPreparer()
    @recorded_by_proxy
    def test_wrap_local(self, key_client, is_hsm, **kwargs):
        """Wrap locally, unwrap with Key Vault"""
        key_name = self.get_resource_name("wrap-local")
        key = self._create_rsa_key(key_client, key_name, size=4096, hardware_protected=is_hsm)
        crypto_client = self.create_crypto_client(key, api_version=key_client.api_version)

        for wrap_algorithm in (algorithm for algorithm in KeyWrapAlgorithm if algorithm.startswith("RSA")):
            result = crypto_client.wrap_key(wrap_algorithm, self.plaintext)
            assert result.key_id == key.id

            result = crypto_client.unwrap_key(result.algorithm, result.encrypted_key)
            assert result.key == self.plaintext

    @pytest.mark.parametrize("api_version,is_hsm",all_api_versions)
    @KeysClientPreparer()
    @recorded_by_proxy
    def test_wrap_local_from_jwk(self, key_client, is_hsm, **kwargs):
        """Wrap locally, unwrap with Key Vault"""
        key_name = self.get_resource_name("wrap-local")
        key = self._create_rsa_key(key_client, key_name, size=4096, hardware_protected=is_hsm)
        crypto_client = self.create_crypto_client(key, api_version=key_client.api_version)
        local_client = CryptographyClient.from_jwk(key.key)

        for wrap_algorithm in (algorithm for algorithm in KeyWrapAlgorithm if algorithm.startswith("RSA")):
            result = local_client.wrap_key(wrap_algorithm, self.plaintext)
            assert result.key_id == key.id

            result = crypto_client.unwrap_key(result.algorithm, result.encrypted_key)
            assert result.key == self.plaintext

    @pytest.mark.parametrize("api_version,is_hsm",all_api_versions)
    @KeysClientPreparer()
    @recorded_by_proxy
    def test_rsa_verify_local(self, key_client, is_hsm, **kwargs):
        """Sign with Key Vault, verify locally"""
        for size in (2048, 3072, 4096):
            key_name = self.get_resource_name(f"rsa-verify-{size}")
            key = self._create_rsa_key(key_client, key_name, size=size, hardware_protected=is_hsm)
            crypto_client = self.create_crypto_client(key, api_version=key_client.api_version)
            for signature_algorithm, hash_function in (
                (SignatureAlgorithm.ps256, hashlib.sha256),
                (SignatureAlgorithm.ps384, hashlib.sha384),
                (SignatureAlgorithm.ps512, hashlib.sha512),
                (SignatureAlgorithm.rs256, hashlib.sha256),
                (SignatureAlgorithm.rs384, hashlib.sha384),
                (SignatureAlgorithm.rs512, hashlib.sha512),
            ):
                digest = hash_function(self.plaintext).digest()

                result = crypto_client.sign(signature_algorithm, digest)
                assert result.key_id == key.id

                result = crypto_client.verify(result.algorithm, digest, result.signature)
                assert result.is_valid

    @pytest.mark.parametrize("api_version,is_hsm",all_api_versions)
    @KeysClientPreparer()
    @recorded_by_proxy
    def test_rsa_verify_local_from_jwk(self, key_client, is_hsm, **kwargs):
        """Sign with Key Vault, verify locally"""
        for size in (2048, 3072, 4096):
            key_name = self.get_resource_name(f"rsa-verify-{size}")
            key = self._create_rsa_key(key_client, key_name, size=size, hardware_protected=is_hsm)
            crypto_client = self.create_crypto_client(key, api_version=key_client.api_version)
            local_client = CryptographyClient.from_jwk(key.key)
            for signature_algorithm, hash_function in (
                    (SignatureAlgorithm.ps256, hashlib.sha256),
                    (SignatureAlgorithm.ps384, hashlib.sha384),
                    (SignatureAlgorithm.ps512, hashlib.sha512),
                    (SignatureAlgorithm.rs256, hashlib.sha256),
                    (SignatureAlgorithm.rs384, hashlib.sha384),
                    (SignatureAlgorithm.rs512, hashlib.sha512),
            ):
                digest = hash_function(self.plaintext).digest()

                result = crypto_client.sign(signature_algorithm, digest)
                assert result.key_id, key.id

                result = local_client.verify(result.algorithm, digest, result.signature)
                assert result.is_valid

    @pytest.mark.parametrize("api_version,is_hsm",all_api_versions)
    @KeysClientPreparer()
    @recorded_by_proxy
    def test_ec_verify_local(self, key_client, is_hsm, **kwargs):
        """Sign with Key Vault, verify locally"""
        matrix = {
            KeyCurveName.p_256: (SignatureAlgorithm.es256, hashlib.sha256),
            KeyCurveName.p_256_k: (SignatureAlgorithm.es256_k, hashlib.sha256),
            KeyCurveName.p_384: (SignatureAlgorithm.es384, hashlib.sha384),
            KeyCurveName.p_521: (SignatureAlgorithm.es512, hashlib.sha512),
        }

        for curve, (signature_algorithm, hash_function) in sorted(matrix.items()):
            key_name = self.get_resource_name(f"ec-verify-{curve.value}")
            key = self._create_ec_key(key_client, key_name, curve=curve, hardware_protected=is_hsm)
            crypto_client = self.create_crypto_client(key, api_version=key_client.api_version)

            digest = hash_function(self.plaintext).digest()

            result = crypto_client.sign(signature_algorithm, digest)
            assert result.key_id, key.id

            result = crypto_client.verify(result.algorithm, digest, result.signature)
            assert result.is_valid

    @pytest.mark.parametrize("api_version,is_hsm",all_api_versions)
    @KeysClientPreparer()
    @recorded_by_proxy
    def test_ec_verify_local_from_jwk(self, key_client, is_hsm, **kwargs):
        """Sign with Key Vault, verify locally"""
        matrix = {
            KeyCurveName.p_256: (SignatureAlgorithm.es256, hashlib.sha256),
            KeyCurveName.p_256_k: (SignatureAlgorithm.es256_k, hashlib.sha256),
            KeyCurveName.p_384: (SignatureAlgorithm.es384, hashlib.sha384),
            KeyCurveName.p_521: (SignatureAlgorithm.es512, hashlib.sha512),
        }

        for curve, (signature_algorithm, hash_function) in sorted(matrix.items()):
            key_name = self.get_resource_name(f"ec-verify-{curve.value}")
            key = self._create_ec_key(key_client, key_name, curve=curve, hardware_protected=is_hsm)
            crypto_client = self.create_crypto_client(key, api_version=key_client.api_version)
            local_client = CryptographyClient.from_jwk(key.key)

            digest = hash_function(self.plaintext).digest()

            result = crypto_client.sign(signature_algorithm, digest)
            assert result.key_id == key.id

            result = local_client.verify(result.algorithm, digest, result.signature)
            assert result.is_valid

    @pytest.mark.parametrize("api_version,is_hsm",all_api_versions)
    @KeysClientPreparer()
    @recorded_by_proxy
    def test_local_validity_period_enforcement(self, key_client, is_hsm, **kwargs):
        """Local crypto operations should respect a key's nbf and exp properties"""
        def test_operations(key, expected_error_substrings, encrypt_algorithms, wrap_algorithms):
            crypto_client = self.create_crypto_client(key, api_version=key_client.api_version)
            for algorithm in encrypt_algorithms:
                with pytest.raises(ValueError) as ex:
                    crypto_client.encrypt(algorithm, self.plaintext)
                for substring in expected_error_substrings:
                    assert substring in str(ex.value)
            for algorithm in wrap_algorithms:
                with pytest.raises(ValueError) as ex:
                    crypto_client.wrap_key(algorithm, self.plaintext)
                for substring in expected_error_substrings:
                    assert substring in str(ex.value)

        # operations should not succeed with a key whose nbf is in the future
        the_year_3000 = datetime(3000, 1, 1, tzinfo=timezone.utc)

        rsa_wrap_algorithms = [algorithm for algorithm in KeyWrapAlgorithm if algorithm.startswith("RSA")]
        rsa_encryption_algorithms = [algorithm for algorithm in EncryptionAlgorithm if algorithm.startswith("RSA")]
        key_name = self.get_resource_name("rsa-not-yet-valid")
        not_yet_valid_key = self._create_rsa_key(
            key_client, key_name, not_before=the_year_3000, hardware_protected=is_hsm
        )
        test_operations(not_yet_valid_key, [str(the_year_3000)], rsa_encryption_algorithms, rsa_wrap_algorithms)

        # nor should they succeed with a key whose exp has passed
        the_year_2000 = datetime(2000, 1, 1, tzinfo=timezone.utc)

        key_name = self.get_resource_name("rsa-expired")
        expired_key = self._create_rsa_key(key_client, key_name, expires_on=the_year_2000, hardware_protected=is_hsm)
        test_operations(expired_key, [str(the_year_2000)], rsa_encryption_algorithms, rsa_wrap_algorithms)

        # when exp and nbf are set, error messages should contain both
        the_year_3001 = datetime(3001, 1, 1, tzinfo=timezone.utc)

        key_name = self.get_resource_name("rsa-valid")
        valid_key = self._create_rsa_key(
            key_client, key_name, not_before=the_year_3000, expires_on=the_year_3001, hardware_protected=is_hsm
        )
        test_operations(
            valid_key, (str(the_year_3000), str(the_year_3001)), rsa_encryption_algorithms, rsa_wrap_algorithms
        )

    @pytest.mark.parametrize("api_version,is_hsm",only_vault_7_4_plus)
    @KeysClientPreparer()
    @recorded_by_proxy
    def test_send_request(self, key_client, is_hsm, **kwargs):
        key_name = self.get_resource_name("keysign")

        md = hashlib.sha256()
        md.update(self.plaintext)
        digest = md.digest()

        imported_key = self._import_test_key(key_client, key_name, hardware_protected=is_hsm)
        crypto_client = self.create_crypto_client(imported_key.id, api_version=key_client.api_version)

        parameters = KeySignParameters(algorithm=SignatureAlgorithm.rs256, value=digest)
        json = parameters.as_dict()

        # sign using a custom request
        request = HttpRequest(
            method="POST",
            url=f"keys/{key_name}/{imported_key.properties.version}/sign",
            headers={"Accept": "application/json"},
            json=json
        )
        response = crypto_client.send_request(request)
        response.raise_for_status()
        result = response.json()
        signature = Deserializer().deserialize_base64(result["value"])
        assert result["kid"] == imported_key.id

        # verify that the operation round-trips
        verified = crypto_client.verify(SignatureAlgorithm.rs256, digest, signature)
        assert verified.is_valid


def test_custom_hook_policy():
    class CustomHookPolicy(SansIOHTTPPolicy):
        pass

    client = CryptographyClient("https://localhost/fake/key/version", object(), custom_hook_policy=CustomHookPolicy())
    assert isinstance(client._client._config.custom_hook_policy, CustomHookPolicy)


def test_initialization_given_key():
    """If the client is given key material, it should not attempt to get this from the vault"""

    mock_client = mock.Mock()
    key = mock.Mock(spec=KeyVaultKey, id="https://localhost/fake/key/version")
    client = CryptographyClient(key, mock.Mock())
    client._client = mock_client

    with mock.patch(CryptographyClient.__module__ + ".get_local_cryptography_provider") as get_provider:
        client.verify(SignatureAlgorithm.rs256, b"...", b"...")
    get_provider.assert_called_once_with(key.key)
    assert mock_client.get_key.call_count == 0


def test_initialization_get_key_successful():
    """If the client is able to get key material, it shouldn't do so again"""

    key_id = "https://localhost/fake/key/version"
    mock_key = mock.Mock()
    mock_key.key.kid = key_id
    mock_client = mock.Mock()
    mock_client.get_key.return_value = mock_key

    client = CryptographyClient(key_id, mock.Mock())
    client._client = mock_client

    assert mock_client.get_key.call_count == 0
    with mock.patch(CryptographyClient.__module__ + ".get_local_cryptography_provider") as get_provider:
        client.verify(SignatureAlgorithm.rs256, b"...", b"...")

    args, _ = get_provider.call_args
    assert len(args) == 1 and isinstance(args[0], JsonWebKey) and args[0].kid == key_id

    for _ in range(3):
        assert mock_client.get_key.call_count == 1
        assert get_provider.call_count == 1
        client.verify(SignatureAlgorithm.rs256, b"...", b"...")


def test_initialization_forbidden_to_get_key():
    """If the client is forbidden to get key material, it should try to do so exactly once"""

    mock_client = mock.Mock()
    mock_client.get_key.side_effect = HttpResponseError(response=mock.Mock(status_code=403))
    client = CryptographyClient("https://localhost/fake/key/version", mock.Mock())
    client._client = mock_client

    assert mock_client.get_key.call_count == 0
    for _ in range(3):
        client.verify(SignatureAlgorithm.rs256, b"...", b"...")
        assert mock_client.get_key.call_count == 1


def test_initialization_transient_failure_getting_key():
    """If the client is not forbidden to get key material, it should retry after failing to do so"""

    mock_client = mock.Mock()
    mock_client.get_key.side_effect = HttpResponseError(response=mock.Mock(status_code=500))
    client = CryptographyClient("https://localhost/fake/key/version", mock.Mock())
    client._client = mock_client

    for i in range(3):
        assert mock_client.get_key.call_count == i
        client.verify(SignatureAlgorithm.rs256, b"...", b"...")


def test_calls_service_for_operations_unsupported_locally():
    """When an operation can't be performed locally, the client should request Key Vault perform it"""

    mock_client = mock.Mock()
    key = mock.Mock(spec=KeyVaultKey, id="https://localhost/fake/key/version")
    client = CryptographyClient(key, mock.Mock())
    client._client = mock_client

    supports_nothing = mock.Mock(supports=mock.Mock(return_value=False))
    with mock.patch(CryptographyClient.__module__ + ".get_local_cryptography_provider", lambda *_: supports_nothing):
        client.decrypt(EncryptionAlgorithm.rsa_oaep, b"...")
    assert mock_client.decrypt.call_count == 1
    assert supports_nothing.decrypt.call_count == 0

    client.encrypt(EncryptionAlgorithm.rsa_oaep, b"...")
    assert mock_client.encrypt.call_count == 1
    assert supports_nothing.encrypt.call_count == 0

    client.sign(SignatureAlgorithm.rs256, b"...")
    assert mock_client.sign.call_count == 1
    assert supports_nothing.sign.call_count == 0

    client.verify(SignatureAlgorithm.rs256, b"...", b"...")
    assert mock_client.verify.call_count == 1
    assert supports_nothing.verify.call_count == 0

    client.unwrap_key(KeyWrapAlgorithm.rsa_oaep, b"...")
    assert mock_client.unwrap_key.call_count == 1
    assert supports_nothing.unwrap_key.call_count == 0

    client.wrap_key(KeyWrapAlgorithm.rsa_oaep, b"...")
    assert mock_client.wrap_key.call_count == 1
    assert supports_nothing.wrap_key.call_count == 0


def test_local_only_mode_no_service_calls():
    """A local-only CryptographyClient shouldn't call the service if an operation can't be performed locally"""

    mock_client = mock.Mock()
    jwk = JsonWebKey(kty="RSA", key_ops=[], n=b"10011", e=b"10001")
    client = CryptographyClient.from_jwk(jwk=jwk)
    client._client = mock_client

    with pytest.raises(NotImplementedError):
        client.decrypt(EncryptionAlgorithm.rsa_oaep, b"...")
    assert mock_client.decrypt.call_count == 0

    with pytest.raises(NotImplementedError):
        client.encrypt(EncryptionAlgorithm.a256_gcm, b"...")
    assert mock_client.encrypt.call_count == 0

    with pytest.raises(NotImplementedError):
        client.sign(SignatureAlgorithm.rs256, b"...")
    assert mock_client.sign.call_count == 0

    with pytest.raises(NotImplementedError):
        client.verify(SignatureAlgorithm.es256, b"...", b"...")
    assert mock_client.verify.call_count == 0

    with pytest.raises(NotImplementedError):
        client.unwrap_key(KeyWrapAlgorithm.rsa_oaep, b"...")
    assert mock_client.unwrap_key.call_count == 0

    with pytest.raises(NotImplementedError):
        client.wrap_key(KeyWrapAlgorithm.aes_256, b"...")
    assert mock_client.wrap_key.call_count == 0


def test_local_only_mode_raise():
    """A local-only CryptographyClient should raise an exception if an operation can't be performed locally"""

    client = CryptographyClient.from_jwk(jwk=TEST_JWK)

    # Algorithm not supported locally
    with pytest.raises(NotImplementedError) as ex:
        client.decrypt(EncryptionAlgorithm.a256_gcm, b"...", iv=b"...", authentication_tag=b"...")
    # Look for f-string or .format-ed occurrence of enum value, to account for differences in 3.11+
    assert f"{EncryptionAlgorithm.a256_gcm}" in str(ex.value)
    assert f"{KeyOperation.decrypt}" in str(ex.value)

    # Operation not included in JWK permissions
    with pytest.raises(AzureError) as ex:
        client.encrypt(EncryptionAlgorithm.rsa_oaep, b"...")
    assert f"{KeyOperation.encrypt}" in str(ex.value)

    # Algorithm not supported locally
    with pytest.raises(NotImplementedError) as ex:
        client.verify(SignatureAlgorithm.es256, b"...", b"...")
    assert f"{SignatureAlgorithm.es256}" in str(ex.value)
    assert f"{KeyOperation.verify}" in str(ex.value)

    # Algorithm not supported locally, and operation not included in JWK permissions
    with pytest.raises(AzureError) as ex:
        client.sign(SignatureAlgorithm.rs256, b"...")
    assert f"{KeyOperation.sign}" in str(ex.value)

    # Algorithm not supported locally
    with pytest.raises(NotImplementedError) as ex:
        client.unwrap_key(KeyWrapAlgorithm.aes_256, b"...")
    assert f"{KeyWrapAlgorithm.aes_256}" in str(ex.value)
    assert f"{KeyOperation.unwrap_key}" in str(ex.value)

    # Operation not included in JWK permissions
    with pytest.raises(AzureError) as ex:
        client.wrap_key(KeyWrapAlgorithm.rsa_oaep, b"...")
    assert f"{KeyOperation.wrap_key}" in str(ex.value)


def test_prefers_local_provider():
    """The client should complete operations locally whenever possible"""

    mock_client = mock.Mock()
    key = mock.Mock(
        spec=KeyVaultKey,
        id="https://localhost/fake/key/version",
        properties=mock.Mock(
            not_before=datetime(2000, 1, 1, tzinfo=timezone.utc), expires_on=datetime(3000, 1, 1, tzinfo=timezone.utc)
        ),
    )
    client = CryptographyClient(key, mock.Mock())
    client._client = mock_client

    supports_everything = mock.Mock(supports=mock.Mock(return_value=True))
    with mock.patch(CryptographyClient.__module__ + ".get_local_cryptography_provider", lambda *_: supports_everything):
        client.decrypt(EncryptionAlgorithm.rsa_oaep, b"...")
    assert mock_client.decrypt.call_count == 0
    assert supports_everything.decrypt.call_count == 1

    client.encrypt(EncryptionAlgorithm.rsa_oaep, b"...")
    assert mock_client.encrypt.call_count == 0
    assert supports_everything.encrypt.call_count == 1

    client.sign(SignatureAlgorithm.rs256, b"...")
    assert mock_client.sign.call_count == 0
    assert supports_everything.sign.call_count == 1

    client.verify(SignatureAlgorithm.rs256, b"...", b"...")
    assert mock_client.verify.call_count == 0
    assert supports_everything.verify.call_count == 1

    client.unwrap_key(KeyWrapAlgorithm.rsa_oaep, b"...")
    assert mock_client.unwrap_key.call_count == 0
    assert supports_everything.unwrap_key.call_count == 1

    client.wrap_key(KeyWrapAlgorithm.rsa_oaep, b"...")
    assert mock_client.wrap_key.call_count == 0
    assert supports_everything.wrap_key.call_count == 1


def test_aes_cbc_key_size_validation():
    """The client should raise an error when the key is an inappropriate size for the specified algorithm"""

    jwk = JsonWebKey(kty="oct-HSM", key_ops=["encrypt", "decrypt"], k=os.urandom(64))
    iv = os.urandom(16)
    client = CryptographyClient.from_jwk(jwk=jwk)
    with pytest.raises(AzureError) as ex:
        client.encrypt(EncryptionAlgorithm.a128_cbcpad, b"...", iv=iv)  # requires 16-byte key
    assert "key size" in str(ex.value).lower()
    with pytest.raises(AzureError) as ex:
        client.encrypt(EncryptionAlgorithm.a192_cbcpad, b"...", iv=iv)  # requires 24-byte key
    assert "key size" in str(ex.value).lower()
    with pytest.raises(AzureError) as ex:
        client.encrypt(EncryptionAlgorithm.a256_cbcpad, b"...", iv=iv)  # requires 32-byte key
    assert "key size" in str(ex.value).lower()


def test_aes_cbc_iv_validation():
    """The client should raise an error when an iv is not provided"""

    jwk = JsonWebKey(kty="oct-HSM", key_ops=["encrypt", "decrypt"], k=os.urandom(32))
    client = CryptographyClient.from_jwk(jwk=jwk)
    with pytest.raises(ValueError) as ex:
        client.encrypt(EncryptionAlgorithm.a256_cbcpad, b"...")
    assert "iv" in str(ex.value).lower()


def test_encrypt_argument_validation():
    """The client should raise an error when arguments don't work with the specified algorithm"""

    mock_client = mock.Mock()
    key = mock.Mock(
        spec=KeyVaultKey,
        id="https://localhost/fake/key/version",
        properties=mock.Mock(
            not_before=datetime(2000, 1, 1, tzinfo=timezone.utc), expires_on=datetime(3000, 1, 1, tzinfo=timezone.utc)
        ),
    )
    client = CryptographyClient(key, mock.Mock())
    client._client = mock_client

    with pytest.raises(ValueError) as ex:
        client.encrypt(EncryptionAlgorithm.rsa_oaep, b"...", iv=b"...")
    assert "iv" in str(ex.value)
    with pytest.raises(ValueError) as ex:
        client.encrypt(EncryptionAlgorithm.rsa_oaep, b"...", additional_authenticated_data=b"...")
    assert "additional_authenticated_data" in str(ex.value)
    with pytest.raises(ValueError) as ex:
        client.encrypt(EncryptionAlgorithm.a256_cbc, b"...")
    assert "iv" in str(ex.value) and "required" in str(ex.value)


def test_decrypt_argument_validation():
    mock_client = mock.Mock()
    key = mock.Mock(
        spec=KeyVaultKey,
        id="https://localhost/fake/key/version",
        properties=mock.Mock(
            not_before=datetime(2000, 1, 1, tzinfo=timezone.utc), expires_on=datetime(3000, 1, 1, tzinfo=timezone.utc)
        ),
    )
    client = CryptographyClient(key, mock.Mock())
    client._client = mock_client

    with pytest.raises(ValueError) as ex:
        client.decrypt(EncryptionAlgorithm.rsa_oaep, b"...", iv=b"...")
    assert "iv" in str(ex.value)
    with pytest.raises(ValueError) as ex:
        client.decrypt(EncryptionAlgorithm.rsa_oaep, b"...", additional_authenticated_data=b"...")
    assert "additional_authenticated_data" in str(ex.value)
    with pytest.raises(ValueError) as ex:
        client.decrypt(EncryptionAlgorithm.rsa_oaep, b"...", authentication_tag=b"...")
    assert "authentication_tag" in str(ex.value)
    with pytest.raises(ValueError) as ex:
        client.decrypt(EncryptionAlgorithm.a128_gcm, b"...", iv=b"...")
    assert "authentication_tag" in str(ex.value) and "required" in str(ex.value)
    with pytest.raises(ValueError) as ex:
        client.decrypt(EncryptionAlgorithm.a192_cbcpad, b"...")
    assert "iv" in str(ex.value) and "required" in str(ex.value)


def test_rsa_public_key_public_numbers():
    """Verify behavior of KeyVaultRSAPublicKey.public_numbers"""

    client = CryptographyClient.from_jwk(jwk=TEST_JWK)
    public_key = client.create_rsa_public_key()
    public_numbers = public_key.public_numbers()
    assert public_numbers.e == int.from_bytes(TEST_JWK["e"], "big")
    assert public_numbers.n == int.from_bytes(TEST_JWK["n"], "big")


def test_rsa_public_key_equals():
    """Verify behavior of KeyVaultRSAPublicKey.__eq__ against a JWK and KeyVaultRSAPublicKey instance"""

    client = CryptographyClient.from_jwk(jwk=TEST_JWK)
    public_key = client.create_rsa_public_key()
    assert public_key == JsonWebKey(**TEST_JWK)
    key_dupe = client.create_rsa_public_key()
    assert public_key == key_dupe


def test_rsa_public_key_public_bytes():
    """Verify behavior of KeyVaultRSAPublicKey.public_bytes"""

    client = CryptographyClient.from_jwk(jwk=TEST_JWK)
    public_key = client.create_rsa_public_key()
    public_bytes = public_key.public_bytes(Encoding.PEM, PublicFormat.PKCS1)

    public_numbers = public_key.public_numbers()
    crypto_public_numbers = RSAPublicNumbers(e=public_numbers.e, n=public_numbers.n)
    crypto_public_bytes = crypto_public_numbers.public_key().public_bytes(Encoding.PEM, PublicFormat.PKCS1)
    assert public_bytes ==  crypto_public_bytes


def test_rsa_public_key_private_key_size():
    """Verify that KeyVaultRSAPublicKey.key_size and KeyVaultRSAPrivateKey.key_size are equal for the same key"""

    client = CryptographyClient.from_jwk(jwk=TEST_JWK)
    public_key = client.create_rsa_public_key()
    private_key = client.create_rsa_private_key()
    assert public_key.key_size == private_key.key_size == 2048


def test_rsa_private_key_public_key():
    """Verify behavior of KeyVaultRSAPrivateKey.public_key against a JWK and KeyVaultRSAPublicKey instance"""

    client = CryptographyClient.from_jwk(jwk=TEST_JWK)
    public_key = client.create_rsa_public_key()
    private_key = client.create_rsa_private_key()
    assert private_key.public_key() == public_key


def test_rsa_private_key_private_numbers():
    """Verify behavior of KeyVaultRSAPrivateKey.private_numbers"""

    client = CryptographyClient.from_jwk(jwk=TEST_JWK)
    private_key = client.create_rsa_private_key()
    private_numbers = private_key.private_numbers()
    assert private_numbers.d == int.from_bytes(TEST_JWK["d"], "big")
    assert private_numbers.p == int.from_bytes(TEST_JWK["p"], "big")
    assert private_numbers.q == int.from_bytes(TEST_JWK["q"], "big")
    assert private_numbers.dmp1 == rsa_crt_dmp1(private_numbers.d, private_numbers.p)
    assert private_numbers.dmq1 == rsa_crt_dmq1(private_numbers.d, private_numbers.q)
    assert private_numbers.iqmp == rsa_crt_iqmp(private_numbers.p, private_numbers.q)


def test_rsa_private_key_private_bytes():
    """Verify behavior of KeyVaultRSAPrivateKey.private_bytes"""

    client = CryptographyClient.from_jwk(jwk=TEST_JWK)
    private_key = client.create_rsa_private_key()
    private_bytes = private_key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())

    private_numbers = private_key.private_numbers()
    crypto_private_numbers = RSAPrivateNumbers(
        p=private_numbers.p,
        q=private_numbers.q,
        d=private_numbers.d,
        dmp1=private_numbers.dmp1,
        dmq1=private_numbers.dmq1,
        iqmp=private_numbers.iqmp,
        public_numbers=private_numbers.public_numbers,
    )
    crypto_private_bytes = crypto_private_numbers.private_key().private_bytes(
        Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption()
    )
    assert private_bytes == crypto_private_bytes


def test_retain_url_port():
    """Regression test for https://github.com/Azure/azure-sdk-for-python/issues/24446"""

    key = mock.Mock(spec=KeyVaultKey, id="https://localhost:8443/keys/rsa-2048/2d93f37afada4679b00b528f7238ad5c")
    client = CryptographyClient(key, mock.Mock())
    # Client's vault_url is also set as generated client's base URL as-is (with port)
    assert client.vault_url == "https://localhost:8443"
