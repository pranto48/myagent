# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 3.0.0
import os
import base64
import hashlib
import logging
from typing import Optional, Union
from config import settings

logger = logging.getLogger(__name__)

# Attempt to load cryptography library; provide standard fallback if not present
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False
    logger.warning("cryptography package not found. Using fallback standard encryption.")

class DataCrypto:
    """
    Enterprise Data Encryption at Rest Engine (AES-256-GCM).
    Provides transparent data encryption for sensitive files, memory chunks, and secrets.
    """
    _instance: Optional['DataCrypto'] = None
    _derived_key: bytes = b""

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DataCrypto, cls).__new__(cls)
            cls._instance._init_engine()
        return cls._instance

    def _init_engine(self):
        master_secret = settings.SECURITY_ENCRYPTION_KEY or "it-support-bd-secure-aes256-master-key-2026"
        salt = b"itsupport-bd-salt-2026-secure"
        
        if HAS_CRYPTOGRAPHY:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32, # 256 bits
                salt=salt,
                iterations=100000,
            )
            self._derived_key = kdf.derive(master_secret.encode('utf-8'))
        else:
            # Fallback 256-bit key from SHA-256
            self._derived_key = hashlib.sha256(master_secret.encode('utf-8') + salt).digest()

    def encrypt_bytes(self, data: bytes) -> bytes:
        """Encrypts arbitrary bytes using AES-256-GCM."""
        if not data:
            return b""
        
        if HAS_CRYPTOGRAPHY:
            aesgcm = AESGCM(self._derived_key)
            nonce = os.urandom(12) # 96-bit standard nonce for GCM
            encrypted = aesgcm.encrypt(nonce, data, None)
            # Format: nonce (12 bytes) + encrypted ciphertext with 16-byte auth tag
            return nonce + encrypted
        else:
            # Reversible XOR stream fallback with SHA256 keystream and HMAC
            nonce = os.urandom(12)
            keystream = hashlib.sha256(self._derived_key + nonce).digest()
            while len(keystream) < len(data):
                keystream += hashlib.sha256(keystream + self._derived_key).digest()
            xor_data = bytes([b ^ keystream[i] for i, b in enumerate(data)])
            tag = hashlib.sha256(self._derived_key + nonce + xor_data).digest()[:16]
            return nonce + tag + xor_data

    def decrypt_bytes(self, encrypted_payload: bytes) -> bytes:
        """Decrypts bytes previously encrypted by encrypt_bytes."""
        if not encrypted_payload or len(encrypted_payload) < 28:
            return encrypted_payload
        
        if HAS_CRYPTOGRAPHY:
            try:
                nonce = encrypted_payload[:12]
                ciphertext = encrypted_payload[12:]
                aesgcm = AESGCM(self._derived_key)
                return aesgcm.decrypt(nonce, ciphertext, None)
            except Exception as e:
                logger.error(f"AES-256 decryption error: {e}")
                raise ValueError("Decryption failed: corrupted data or wrong encryption key.")
        else:
            try:
                nonce = encrypted_payload[:12]
                tag = encrypted_payload[12:28]
                xor_data = encrypted_payload[28:]
                expected_tag = hashlib.sha256(self._derived_key + nonce + xor_data).digest()[:16]
                if tag != expected_tag:
                    raise ValueError("Integrity check failed: invalid HMAC tag.")
                keystream = hashlib.sha256(self._derived_key + nonce).digest()
                while len(keystream) < len(xor_data):
                    keystream += hashlib.sha256(keystream + self._derived_key).digest()
                return bytes([b ^ keystream[i] for i, b in enumerate(xor_data)])
            except Exception as e:
                logger.error(f"Decryption fallback error: {e}")
                raise ValueError("Decryption failed.")

    def encrypt_text(self, text: str) -> str:
        """Encrypts UTF-8 text and returns a base64-encoded string prefixed with 'enc:aes256:'."""
        if not text:
            return ""
        enc_bytes = self.encrypt_bytes(text.encode('utf-8'))
        b64 = base64.b64encode(enc_bytes).decode('ascii')
        return f"enc:aes256:{b64}"

    def decrypt_text(self, ciphertext: str) -> str:
        """Decrypts a base64 encrypted string (prefixed with 'enc:aes256:') or returns original if not encrypted."""
        if not ciphertext or not isinstance(ciphertext, str):
            return ciphertext
        
        if not ciphertext.startswith("enc:aes256:"):
            return ciphertext
        
        raw_b64 = ciphertext[len("enc:aes256:"):]
        try:
            enc_bytes = base64.b64decode(raw_b64)
            dec_bytes = self.decrypt_bytes(enc_bytes)
            return dec_bytes.decode('utf-8')
        except Exception as e:
            logger.warning(f"Failed to decrypt text payload: {e}")
            return "[ENCRYPTED_DATA_ACCESS_DENIED]"

    def encrypt_file(self, file_path: str, output_path: Optional[str] = None) -> str:
        """Encrypts an entire file on disk in place or to a designated target path."""
        target = output_path or f"{file_path}.enc"
        with open(file_path, "rb") as f:
            raw_data = f.read()
        encrypted = self.encrypt_bytes(raw_data)
        with open(target, "wb") as f:
            f.write(encrypted)
        return target

    def decrypt_file(self, enc_file_path: str, output_path: Optional[str] = None) -> str:
        """Decrypts an encrypted file on disk."""
        target = output_path or (enc_file_path[:-4] if enc_file_path.endswith(".enc") else f"{enc_file_path}.dec")
        with open(enc_file_path, "rb") as f:
            enc_data = f.read()
        decrypted = self.decrypt_bytes(enc_data)
        with open(target, "wb") as f:
            f.write(decrypted)
        return target

    def hash_id(self, val: str) -> str:
        """Computes a salted SHA-256 hash for anonymized tracking."""
        return hashlib.sha256((val + "itsupport-salt").encode('utf-8')).hexdigest()[:16]
