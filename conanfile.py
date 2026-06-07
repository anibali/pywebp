import shutil

from conan import ConanFile


class LibwebpRecipe(ConanFile):
    def requirements(self):
        assert self.requires is not None
        self.requires("libwebp/1.3.2")

    def build_requirements(self):
        if not shutil.which("cmake"):
            assert self.tool_requires is not None
            self.tool_requires("cmake/[>=3.5]")
