"""Repository unittest entrypoint for the post-platform R2-INT-010 adapter."""

from tests.m2.probes.r2_int_010_post_platform.adapter_contract import (
    PostPlatformAcceptanceTests,
    PostPlatformDeterminismAndIsolationTests,
    PostPlatformIdentityTests,
    PostPlatformSchemaTests,
    PostPlatformSourceConfinementTests,
)


__all__ = [
    "PostPlatformIdentityTests",
    "PostPlatformSourceConfinementTests",
    "PostPlatformSchemaTests",
    "PostPlatformAcceptanceTests",
    "PostPlatformDeterminismAndIsolationTests",
]
