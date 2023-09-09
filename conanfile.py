from conan import ConanFile
import shutil

class LibwebpRecipe(ConanFile):
    def requirements(self):
        self.requires("libwebp/1.0.3")

    def build_requirements(self):
        # if self.settings.arch in ("x86_64", "armv8"):
        if not shutil.which('cmake'):
            self.tool_requires("cmake/[>=3.5]")