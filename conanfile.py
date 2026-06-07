"""Conan recipe for the bundled libwebp dependency."""

import shutil

from conan import ConanFile


class LibwebpRecipe(ConanFile):
    """Define the Conan recipe for libwebp."""

    def requirements(self) -> None:
        """Declare runtime Conan requirements."""
        assert self.requires is not None  # noqa: S101
        self.requires("libwebp/1.3.2")

    def build_requirements(self) -> None:
        """Declare build-time Conan requirements."""
        if not shutil.which("cmake"):
            assert self.tool_requires is not None  # noqa: S101
            self.tool_requires("cmake/[>=3.5]")
