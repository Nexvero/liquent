"""Fixed OpenSSH proof and independent approval verification for key activation."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from liquent_platform.identity.release_authority import ReleaseActivationReviewerId


PROOF_NAMESPACE = "liquent-release-key-possession-v1"
APPROVAL_NAMESPACE = "liquent-release-key-activation-approval-v1"
_SSHSIG = re.compile(
    rb"-----BEGIN SSH SIGNATURE-----\n"
    rb"(?:[A-Za-z0-9+/=]+\n)+"
    rb"-----END SSH SIGNATURE-----\n"
)
_FINGERPRINT = re.compile(r"SHA256:[A-Za-z0-9+/]{43}")
_MAX_SIGNATURE_BYTES = 16_384


class ReleaseKeyActivationVerificationUnavailable(Exception):
    code = "release_key_activation_verification_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


@dataclass(frozen=True, slots=True)
class ReleaseActivationReviewerTrust:
    reviewer_id: ReleaseActivationReviewerId = field(repr=False)
    public_key: str = field(repr=False)
    fingerprint: str = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.reviewer_id) is not ReleaseActivationReviewerId:
            raise ValueError("release activation reviewer id is required")
        if (
            type(self.public_key) is not str
            or "\n" in self.public_key
            or len(self.public_key.split()) != 2
            or not self.public_key.startswith("ssh-ed25519 ")
        ):
            raise ValueError("release activation reviewer public key is invalid")
        if type(self.fingerprint) is not str or not _FINGERPRINT.fullmatch(
            self.fingerprint
        ):
            raise ValueError("release activation reviewer fingerprint is invalid")


def _signature(value: object) -> bytes | None:
    if (
        type(value) is not bytes
        or not value
        or len(value) > _MAX_SIGNATURE_BYTES
        or not _SSHSIG.fullmatch(value)
    ):
        return None
    return value


def _public_key(value: object) -> str | None:
    if (
        type(value) is not str
        or "\n" in value
        or len(value.split()) != 2
        or not value.startswith("ssh-ed25519 ")
    ):
        return None
    return value


def _verify(
    *,
    public_key: str,
    identity: str,
    namespace: str,
    challenge: bytes,
    signature: bytes,
    expected_fingerprint: str | None,
    ssh_keygen: str,
) -> bool:
    if (
        _public_key(public_key) is None
        or type(identity) is not str
        or not identity
        or "\n" in identity
        or type(challenge) is not bytes
        or not challenge
        or _signature(signature) is None
    ):
        return False
    try:
        with tempfile.TemporaryDirectory(
            prefix="liquent-release-key-verification-"
        ) as root:
            directory = Path(root)
            public = directory / "key.pub"
            allowed = directory / "allowed_signers"
            signed = directory / "challenge.sshsig"
            public.write_text(public_key + "\n", encoding="ascii")
            allowed.write_text(
                f'{identity} namespaces="{namespace}" {public_key}\n',
                encoding="ascii",
            )
            signed.write_bytes(signature)
            for path in (public, allowed, signed):
                os.chmod(path, 0o600)
            fingerprint = subprocess.run(
                [ssh_keygen, "-lf", str(public), "-E", "sha256"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.split()[1]
            if expected_fingerprint is not None and fingerprint != expected_fingerprint:
                return False
            result = subprocess.run(
                [
                    ssh_keygen,
                    "-Y",
                    "verify",
                    "-f",
                    str(allowed),
                    "-I",
                    identity,
                    "-n",
                    namespace,
                    "-s",
                    str(signed),
                ],
                input=challenge,
                capture_output=True,
            )
            return result.returncode == 0
    except (OSError, subprocess.CalledProcessError, IndexError, UnicodeError):
        raise ReleaseKeyActivationVerificationUnavailable from None


class OpenSshReleaseKeyProofVerifier:
    __slots__ = ("_ssh_keygen",)

    def __init__(self, ssh_keygen: str = "ssh-keygen") -> None:
        if type(ssh_keygen) is not str or not ssh_keygen:
            raise ValueError("ssh-keygen command is required")
        self._ssh_keygen = ssh_keygen

    def __repr__(self) -> str:
        return "OpenSshReleaseKeyProofVerifier()"

    def verify_proof(
        self, public_key: str, challenge: bytes, proof: bytes
    ) -> bool:
        return _verify(
            public_key=public_key,
            identity="release-key-possession",
            namespace=PROOF_NAMESPACE,
            challenge=challenge,
            signature=proof,
            expected_fingerprint=None,
            ssh_keygen=self._ssh_keygen,
        )


class OpenSshReleaseKeyActivationApprovalVerifier:
    __slots__ = ("_reviewers", "_ssh_keygen")

    def __init__(
        self,
        reviewers: tuple[ReleaseActivationReviewerTrust, ...],
        ssh_keygen: str = "ssh-keygen",
    ) -> None:
        if (
            type(reviewers) is not tuple
            or not reviewers
            or any(type(item) is not ReleaseActivationReviewerTrust for item in reviewers)
            or type(ssh_keygen) is not str
            or not ssh_keygen
        ):
            raise ValueError("fixed release activation reviewer trust is required")
        identities = [item.reviewer_id.value for item in reviewers]
        fingerprints = [item.fingerprint for item in reviewers]
        public_keys = [item.public_key for item in reviewers]
        if (
            len(set(identities)) != len(identities)
            or len(set(fingerprints)) != len(fingerprints)
            or len(set(public_keys)) != len(public_keys)
        ):
            raise ValueError("release activation reviewer trust must be unique")
        self._reviewers = reviewers
        self._ssh_keygen = ssh_keygen

    def __repr__(self) -> str:
        return "OpenSshReleaseKeyActivationApprovalVerifier()"

    def verify_approval(
        self, challenge: bytes, approval: bytes
    ) -> ReleaseActivationReviewerId | None:
        if _signature(approval) is None or type(challenge) is not bytes or not challenge:
            return None
        matches = [
            reviewer.reviewer_id
            for reviewer in self._reviewers
            if _verify(
                public_key=reviewer.public_key,
                identity=reviewer.reviewer_id.value,
                namespace=APPROVAL_NAMESPACE,
                challenge=challenge,
                signature=approval,
                expected_fingerprint=reviewer.fingerprint,
                ssh_keygen=self._ssh_keygen,
            )
        ]
        if len(matches) != 1:
            return None
        return matches[0]


@dataclass(frozen=True, slots=True)
class ReleaseKeyActivationVerificationComposition:
    proof_verifier: OpenSshReleaseKeyProofVerifier = field(repr=False)
    approval_verifier: OpenSshReleaseKeyActivationApprovalVerifier = field(
        repr=False
    )


def compose_release_key_activation_verification(
    *,
    reviewers: tuple[ReleaseActivationReviewerTrust, ...],
    ssh_keygen: str = "ssh-keygen",
) -> ReleaseKeyActivationVerificationComposition:
    """Bind fixed reviewer trust without reading requests, files, or persistence."""

    return ReleaseKeyActivationVerificationComposition(
        OpenSshReleaseKeyProofVerifier(ssh_keygen),
        OpenSshReleaseKeyActivationApprovalVerifier(reviewers, ssh_keygen),
    )
