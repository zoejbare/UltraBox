#
# Copyright (c) 2023, Zoe J. Bare
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions
# of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED
# TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
# CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#

"""
.. module:: n64_tool_base
	:synopsis: Base tools for the Xbox 360 tool implementations.

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

import csbuild
import os
import platform

from abc import ABCMeta

from csbuild import commands, log

from csbuild.tools.common.tool_traits import HasOptimizationLevel

from csbuild._utils.decorators import MetaClass
from csbuild.toolchain import Tool

OptimizationLevel = HasOptimizationLevel.OptimizationLevel

@MetaClass(ABCMeta)
class N64BaseTool(Tool):
	"""
	Parent class for all N64 tools.

	:param projectSettings: A read-only scoped view into the project settings dictionary
	:type projectSettings: toolchain.ReadOnlySettingsView
	"""
	def __init__(self, projectSettings):
		Tool.__init__(self, projectSettings)

		targetName = "mips64-elf"
		exeFileExt = ".exe" if platform.system() == "Windows" else ""
		toolchainPath = f"{os.path.dirname(__file__)}/../toolchain/{platform.system().lower()}"
		sysrootPath = f"{toolchainPath}/sysroot"

		sysrootTargetPath = f"{sysrootPath}/{targetName}"
		self._n64SysrootLibPath = os.path.abspath(f"{sysrootTargetPath}/lib")
		self._n64SysrootIncludePath = os.path.abspath(f"{sysrootTargetPath}/include")
		self._n64GccLibPath = os.path.abspath(f"{sysrootPath}/lib/gcc/{targetName}/13.1.0")

		sysrootBinPath = f"{toolchainPath}/sysroot/bin"
		self._n64GccExePath = os.path.abspath(f"{sysrootBinPath}/{targetName}-gcc{exeFileExt}")
		self._n64GppExePath = os.path.abspath(f"{sysrootBinPath}/{targetName}-g++{exeFileExt}")
		self._n64ArExePath = os.path.abspath(f"{sysrootBinPath}/{targetName}-ar{exeFileExt}")
		self._n64LdExePath = os.path.abspath(f"{sysrootBinPath}/{targetName}-ld{exeFileExt}")
		self._n64ObjCopyExePath = os.path.abspath(f"{sysrootBinPath}/{targetName}-objcopy{exeFileExt}")

		assert os.access(self._n64GccExePath, os.F_OK), f"Cannot find gcc executable at path: {self._n64GccExePath}"
		assert os.access(self._n64GppExePath, os.F_OK), f"Cannot find g++ executable at path: {self._n64GppExePath}"
		assert os.access(self._n64ArExePath, os.F_OK), f"Cannot find ar executable at path: {self._n64ArExePath}"
		assert os.access(self._n64LdExePath, os.F_OK), f"Cannot find ld executable at path: {self._n64LdExePath}"
		assert os.access(self._n64ObjCopyExePath, os.F_OK), f"Cannot find objcopy executable at path: {self._n64ObjCopyExePath}"

	####################################################################################################################
	### Methods implemented from base classes
	####################################################################################################################

	def SetupForProject(self, project):
		Tool.SetupForProject(self, project)
