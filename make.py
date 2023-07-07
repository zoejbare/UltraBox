#!/usr/bin/env python3
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

from __future__ import unicode_literals, division, print_function

import csbuild
import os
import platform
import sys

from csbuild.tools import AsmCompileChecker, CppCompileChecker
from csbuild.tools.project_generators import visual_studio

###################################################################################################

_REPO_ROOT_PATH = os.path.abspath(os.path.dirname(__file__))
_POST_BUILD_HOOK = "onBuildFinishedHook"
_HOST_PLATFORM = platform.system().lower()

###################################################################################################

# Add the build support path so we have access to the N64 tools.
sys.path.insert(0, os.path.normpath(f"{_REPO_ROOT_PATH}/build"))

###################################################################################################

# Disabling file type folders will put all source files under the the same respective directories in
# the generated project files, so for instance, there will be no separation between .cpp and .hpp files.
# This is useful for development that touches many files, but it can make the filters in each project
# look somewhat less organized.
visual_studio.SetEnableFileTypeFolders(False)

from n64_assembler import N64Assembler
from n64_cpp_compiler import N64CppCompiler
from n64_linker import N64Linker
from n64_rom_builder import N64RomBuilder

def _createCheckers(mappings):
	checkers = {}

	for checkerType, toolType in mappings.items():
		for ext in toolType.inputFiles:
			checkers[ext] = checkerType(toolType)

	return checkers

checkers = _createCheckers({
	CppCompileChecker: N64CppCompiler,
	AsmCompileChecker: N64Assembler,
})

# Register the N64 toolchain so we can make builds that target the platform.
csbuild.RegisterToolchain(
	"n64",
	"mips",
	N64CppCompiler,
	N64Linker,
	N64Assembler,
	N64RomBuilder,
	checkers=checkers
)

###################################################################################################

with csbuild.Target("debug"):
	csbuild.AddDefines("_DEBUG", "DEBUG")
	csbuild.SetDebugLevel(csbuild.DebugLevel.ExternalSymbolsPlus)
	csbuild.SetOptimizationLevel(csbuild.OptimizationLevel.Disabled)

with csbuild.Target("fastdebug"):
	csbuild.AddDefines("_DEBUG", "DEBUG")
	csbuild.SetDebugLevel(csbuild.DebugLevel.ExternalSymbolsPlus)
	csbuild.SetOptimizationLevel(csbuild.OptimizationLevel.Size)

with csbuild.Target("release"):
	csbuild.AddDefines("NDEBUG", "_FINALROM")
	csbuild.SetDebugLevel(csbuild.DebugLevel.Disabled)
	csbuild.SetOptimizationLevel(csbuild.OptimizationLevel.Max)

###################################################################################################

# Set the default output directories; these will be used for all builds that do not use the 'n64' toolchain.
csbuild.SetOutputDirectory("output/tool/{targetName}")
csbuild.SetIntermediateDirectory("_int/tool/{targetName}")

csbuild.SetCcLanguageStandard("c11")
csbuild.SetCxxLanguageStandard("c++11")

with csbuild.Toolchain("n64", "gcc"):
	csbuild.AddCompilerFlags(
		# Enabled warnings.
		"-Wall",
		"-Wextra",

		# Disabled warnings.
		"-Wno-address",
		"-Wno-deprecated-declarations",
		"-Wno-ignored-qualifiers",
		"-Wno-implicit-fallthrough",
		"-Wno-missing-field-initializers",
		"-Wno-nonnull-compare",
	)

with csbuild.Toolchain("n64"):
	csbuild.SetOutputDirectory("output/game/{targetName}")
	csbuild.SetIntermediateDirectory("_int/game/{targetName}")

	csbuild.AddCompilerFlags(
		# Disabled warnings.
		"-Wno-incompatible-pointer-types",
	)

with csbuild.Toolchain("clang"):
	csbuild.AddCompilerFlags(
		# Enabled warnings.
		"-Wall",
		"-Wextra",
		"-Wpedantic",

		# Disabled warnings.
		"-Wno-extra-semi",
		"-Wno-dollar-in-identifier-extension",
		"-Wno-format-pedantic",
		"-Wno-gnu-anonymous-struct",
		"-Wno-gnu-zero-variadic-macro-arguments",
		"-Wno-nested-anon-types",
		"-Wno-undefined-var-template",

		# Test warnings - only use when tracking down specific issues!
		#"-Weverything",
		#"-Wno-c++98-compat",
		#"-Wno-c++98-compat-pedantic",
		#"-Wno-float-equal",
		#"-Wno-old-style-cast",
		#"-Wno-padded",
		#"-Wno-sign-conversion",
		#"-Wno-weak-vtables",
	)

with csbuild.Toolchain("gcc", "clang"):
	csbuild.AddCompilerFlags(
		"-fexceptions",
		"-fPIC",
	)

with csbuild.Toolchain("msvc"):
	if csbuild.GetRunMode() == csbuild.RunMode.GenerateSolution:
		csbuild.AddDefines(
			"__cplusplus=201703L",
			"_HAS_CXX17=1",
		)
	csbuild.SetVisualStudioVersion("17") # Visual Studio 2022
	csbuild.AddDefines(
		"_CRT_SECURE_NO_WARNINGS",
		"_CRT_NONSTDC_NO_WARNINGS",
	)
	csbuild.AddCompilerCxxFlags(
		"/bigobj",
		"/permissive-",
		"/Zc:__cplusplus",
		"/EHsc",
		"/W4",
	)

with csbuild.Toolchain("msvc", "gcc", "clang"):
	csbuild.SetCxxLanguageStandard("c++17")

########################################################################################################################

@csbuild.OnBuildFinished
def onGlobalPostBuild(projects):
	if csbuild.GetRunMode() == csbuild.RunMode.Normal:
		for project in projects:
			if _POST_BUILD_HOOK in project.userData:
				project.userData.onBuildFinishedHook(project)

###################################################################################################

class UltraBoxEngine(object):
	projectName = "UltraBoxEngine"
	outputName = "libultrabox"
	path = f"{_REPO_ROOT_PATH}/engine"

with csbuild.Project(UltraBoxEngine.projectName, UltraBoxEngine.path):
	csbuild.SetOutput(UltraBoxEngine.outputName, csbuild.ProjectType.StaticLibrary)
	csbuild.SetSupportedToolchains("n64")

	csbuild.AddSourceFiles(
		f"{_REPO_ROOT_PATH}/toolchain/{_HOST_PLATFORM}/sdk/ultra/usr/lib/PR/rspboot.o",
		f"{_REPO_ROOT_PATH}/toolchain/{_HOST_PLATFORM}/sdk/ultra/usr/lib/PR/gspF3DEX2.xbus.o"
	)

	with csbuild.Scope(csbuild.ScopeDef.Final):
		ultraSdkPath = f"{_REPO_ROOT_PATH}/toolchain/{_HOST_PLATFORM}/sdk/ultra/usr"

		csbuild.AddLibraryDirectories(
			f"{ultraSdkPath}/lib",
		)
		csbuild.AddLibraries(
			"gultra_rom",
			"leo",
			"c",
			"gcc",
		)

	with csbuild.Scope(csbuild.ScopeDef.All):
		csbuild.AddIncludeDirectories(
			UltraBoxEngine.path,
			f"{ultraSdkPath}/include",
			f"{ultraSdkPath}/include/PR",
		)
		csbuild.AddDefines(
			"F3DEX_GBI_2",
		)

###################################################################################################

class External(object):
	rootPath = f"{_REPO_ROOT_PATH}/external"

###################################################################################################

class ExtLibCxxOpts(object):
	projectName = "ExtStub_cxxopts"
	path = f"{External.rootPath}/cxxopts"

with csbuild.Project(ExtLibCxxOpts.projectName, ExtLibCxxOpts.path, autoDiscoverSourceFiles=False):
	csbuild.SetOutput("{name}", csbuild.ProjectType.Stub)
	csbuild.SetSupportedToolchains("msvc", "gcc", "clang")

	if csbuild.GetRunMode() == csbuild.RunMode.GenerateSolution:
		csbuild.AddSourceFiles(f"{ExtLibCxxOpts.path}/include/*.hpp")

	with csbuild.Scope(csbuild.ScopeDef.Children):
		csbuild.AddIncludeDirectories(f"{ExtLibCxxOpts.path}/include")

###################################################################################################

class Tool(object):
	rootPath = f"{_REPO_ROOT_PATH}/tools"

	@staticmethod
	def commonSetup(outputName):
		csbuild.SetOutput(outputName, csbuild.ProjectType.Application)
		csbuild.SetSupportedToolchains("msvc", "gcc", "clang")

		with csbuild.Toolchain("msvc"):
			csbuild.SetMsvcSubsystem("CONSOLE")

###################################################################################################

class LibToolCommon(object):
	projectName = "LibToolCommon"
	outputName = "libtoolcommon"
	path = f"{Tool.rootPath}/common"

with csbuild.Project(LibToolCommon.projectName, LibToolCommon.path):
	csbuild.SetOutput(LibToolCommon.outputName, csbuild.ProjectType.StaticLibrary)
	csbuild.SetSupportedToolchains("msvc", "gcc", "clang")

###################################################################################################

class MaskRom64(object):
	projectName = "MaskRom64"
	outputName = "maskrom64"
	path = f"{Tool.rootPath}/maskrom64"
	dependencies = [
		ExtLibCxxOpts.projectName,
		LibToolCommon.projectName,
	]

with csbuild.Project(MaskRom64.projectName, MaskRom64.path, MaskRom64.dependencies):
	Tool.commonSetup(MaskRom64.outputName)

###################################################################################################

class Game(object):
	rootPath = f"{_REPO_ROOT_PATH}/games"

	@staticmethod
	def commonSetup(outputName, gameTitle, gameCode, romVersion):
		csbuild.SetOutput(outputName, csbuild.ProjectType.Application)
		csbuild.SetSupportedToolchains("n64")

		csbuild.SetN64GameTitle(gameTitle)
		csbuild.SetN64GameCode(gameCode)
		csbuild.SetN64RomVersion(romVersion)

###################################################################################################

class UltraBoxTemplate(object):
	projectName = "UltraBoxTemplate"
	outputName = "template"
	gameTitle = "UltraBox Template"
	gameCode = "NT0A"
	romVersion = 0
	path = f"{Game.rootPath}/template"
	dependencies = [
		UltraBoxEngine.projectName,
	]

with csbuild.Project(UltraBoxTemplate.projectName, UltraBoxTemplate.path, UltraBoxTemplate.dependencies):
	Game.commonSetup(
		UltraBoxTemplate.outputName,
		UltraBoxTemplate.gameTitle,
		UltraBoxTemplate.gameCode,
		UltraBoxTemplate.romVersion)

	csbuild.AddDefines(
		#"_DISPLAY_HIRES",
		#"_DISPLAY_PAL",
	)

###################################################################################################
