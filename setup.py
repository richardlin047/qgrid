from __future__ import print_function
from setuptools import setup, find_packages, Command
from setuptools.command.sdist import sdist
from setuptools.command.build_py import build_py
from setuptools.command.egg_info import egg_info
from subprocess import check_call
import os
import sys
import platform
from os.path import join, dirname, abspath, exists
import versioneer

here = dirname(abspath(__file__))
node_root = join(here, "js")
is_repo = exists(join(here, ".git"))

npm_path = os.pathsep.join(
    [
        join(node_root, "node_modules", ".bin"),
        os.environ.get("PATH", os.defpath),
    ]
)

from distutils import log

log.set_verbosity(log.DEBUG)
log.info("setup.py entered")
log.info("$PATH=%s" % os.environ["PATH"])

LONG_DESCRIPTION = "An implementation for the Spreadsheet API of Modin"


def js_prerelease(command, strict=False):
    """decorator for building minified js/css prior to another command"""

    class DecoratedCommand(command):
        def run(self):
            jsdeps = self.distribution.get_command_obj("jsdeps")
            if not is_repo and all(exists(t) for t in jsdeps.targets):
                # sdist, nothing to do
                command.run(self)
                return

            try:
                self.distribution.run_command("jsdeps")
            except Exception as e:
                missing = [t for t in jsdeps.targets if not exists(t)]
                if strict or missing:
                    log.warn("rebuilding js and css failed")
                    if missing:
                        log.error("missing files: %s" % missing)
                    raise e
                else:
                    log.warn("rebuilding js and css failed (not a problem)")
                    log.warn(str(e))
            command.run(self)
            update_package_data(self.distribution)

    return DecoratedCommand


def update_package_data(distribution):
    """update package_data to catch changes during setup"""
    build_py = distribution.get_command_obj("build_py")
    # distribution.package_data = find_package_data()
    # re-init build_py options which load package_data
    build_py.finalize_options()


class NPM(Command):
    description = "install package.json dependencies using npm"

    user_options = []

    node_modules = join(node_root, "node_modules")

    targets = [
        join(here, "modin_spreadsheet", "static", "extension.js"),
        join(here, "modin_spreadsheet", "static", "index.js"),
    ]

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def has_npm(self):
        try:
            check_call(["npm", "--version"])
            return True
        except:
            return False

    def should_run_npm_install(self):
        package_json = join(node_root, "package.json")
        node_modules_exists = exists(self.node_modules)
        return self.has_npm()

    def run(self):
        has_npm = self.has_npm()
        if not has_npm:
            log.error(
                "`npm` unavailable.  If you're running this command using sudo, make sure `npm` is available to sudo"
            )

        env = os.environ.copy()
        env["PATH"] = npm_path

        if self.should_run_npm_install():
            log.info(
                "Installing build dependencies with npm.  This may take a while..."
            )
            check_call(
                ["npm", "install"], cwd=node_root, stdout=sys.stdout, stderr=sys.stderr
            )
            os.utime(self.node_modules, None)

        for t in self.targets:
            if not exists(t):
                msg = "Missing file: %s" % t
                if not has_npm:
                    msg += "\nnpm is required to build a development version of a widget extension"
                raise ValueError(msg)

        # update package data in case this created new files
        update_package_data(self.distribution)


def read_requirements(basename):
    reqs_file = join(dirname(abspath(__file__)), basename)
    with open(reqs_file) as f:
        return [req.strip() for req in f.readlines()]


reqs = read_requirements("requirements.txt")


def package_files(directory):
    paths = []
    for (path, directories, filenames) in os.walk(directory):
        for filename in filenames:
            paths.append(os.path.join(path, filename))
    return paths


data_files = package_files("modin_spreadsheet/static")


def extras_require():
    return {
        "test": ["pytest>=2.8.5", "flake8>=3.6.0"],
    }


setup_args = {
    "name": "modin-spreadsheet",
    "description": "An implementation for the Spreadsheet API of Modin",
    "long_description": LONG_DESCRIPTION,
    "include_package_data": True,
    "data_files": [
        ("share/jupyter/nbextensions/modin_spreadsheet", data_files),
    ],
    "install_requires": reqs,
    "extras_require": extras_require(),
    "python-requires": ">=3.6.1",
    "packages": find_packages(),
    "zip_safe": False,
    "author": "Modin Maintainers",
    "author_email": "dev@modin.org",
    "url": "https://github.com/modin-project/modin-spreadsheet",
    "license": "Apache-2.0",
    "keywords": [
        "ipython",
        "jupyter",
        "widgets",
    ],
}

setup(
    version=versioneer.get_version(), cmdclass=versioneer.get_cmdclass(), **setup_args
)
