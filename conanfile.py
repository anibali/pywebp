from conan import ConanFile

class LibwebpRecipe(ConanFile):
    def requirements(self):
        self.requires("libwebp/1.0.3")

    def build_requirements(self):
        # if self.settings.arch in ("x86_64", "armv8"):
        self.tool_requires("cmake/3.22.6")