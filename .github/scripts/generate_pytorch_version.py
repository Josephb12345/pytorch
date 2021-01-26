#!/usr/bin/env python3

import argparse
import os
import subprocess
import re

from datetime import datetime
from pathlib import Path

PYTORCH_ROOT = Path(__file__).parent.parent
LEADING_V_PATTERN = re.compile("^v")
LEGACY_BASE_VERSION_SUFFIX_PATTERN = re.compile("a0$")

class NoGitTagException(Exception):
    pass

def get_tag():
    # We're on a tag
    am_on_tag = (
        subprocess.run(
            ['git', 'describe', '--tags', '--exact'],
            cwd=PYTORCH_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        ).returncode == 0
    )
    tag = ""
    if am_on_tag:
        dirty_tag = subprocess.check_output(
            ['git', 'describe'],
            cwd=PYTORCH_ROOT
        ).decode('ascii').strip()
        # Strip leading v that we typically do when we tag branches
        # ie: v1.7.1 -> 1.7.1
        tag = re.sub(LEADING_V_PATTERN, "", dirty_tag)
    return tag

def get_base_version():
    PYTORCH_ROOT = Path(__file__).parent.parent
    dirty_version = open('version.txt', 'r').read().strip()
    # Strips trailing a0 from version.txt, not too sure why it's there in the
    # first place
    return re.sub(LEGACY_BASE_VERSION_SUFFIX_PATTERN, "", dirty_version)

class PytorchVersion:
    def __init__(self, gpu_arch_type, gpu_arch_version, with_build_suffix):
        self.gpu_arch_type = gpu_arch_type
        self.gpu_arch_version = gpu_arch_version
        self.with_build_suffix = with_build_suffix

    def get_post_build_suffix(self):
        # CUDA 10.2 is the version to be uploaded to PyPI so it doesn't have a
        # version suffix
        if ((self.gpu_arch_type == "cuda" and self.gpu_arch_version == "10.2")
                or not self.with_build_suffix):
            return ""
        return f"+{self.gpu_arch_type}{self.gpu_arch_version}"

    def get_release_version(self):
        if not get_tag():
            raise NoGitTagException(
                "Not on a git tag, are you sure you want a release version?"
            )
        return f"{get_tag()}{self.get_post_build_suffix()}"

    def get_nightly_version(self):
        date_str = datetime.today().strftime('+%Y%m%d')
        build_suffix = self.get_post_build_suffix()
        return f"{get_base_version()}.dev{date_str}{build_suffix}"

def main():
    parser = argparse.ArgumentParser(
        description="Generate pytorch version for binary builds"
    )
    parser.add_argument(
        "--no-build-suffix",
        type=bool,
        help="Whether or not to add a build suffix typically (+cpu)",
        default=False

    )
    parser.add_argument(
        "--gpu-arch-type",
        type=str,
        help="GPU arch you are building for, typically (cpu, cuda, rocm)",
        default=os.environ.get("GPU_ARCH_TYPE", "cpu")
    )
    parser.add_argument(
        "--gpu-arch-version",
        type=str,
        help="GPU arch version, typically (10.2, 4.0), leave blank for CPU",
        default=os.environ.get("GPU_ARCH_VERSION", "")
    )
    args = parser.parse_args()
    version_obj = PytorchVersion(
        args.gpu_arch_type,
        args.gpu_arch_version,
        args.no_build_suffix
    )
    try:
        print(version_obj.get_release_version())
    except NoGitTagException:
        print(version_obj.get_nightly_version())

if __name__ == "__main__":
    main()