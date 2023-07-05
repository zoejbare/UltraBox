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
# CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
#

import clint
import functools
import os
import platform
import shutil
import zipfile

from enum import Enum

from .config import Config

from ..util import (
	changeDirectory,
	copyFilesOnDisk,
	deletePathOnDisk,
	runProcess,

	log,
)

from ..util.downloadable_archive import DownloadableArchive

class _Archive(object):
	def __init__(self, downloadRootPath, tokenRootPath, unpackRootPath, url):
		self._unpackRootPath = unpackRootPath
		self._package = DownloadableArchive(downloadRootPath, tokenRootPath, url)

	def unpack(self):
		self._package.unpack(self._unpackRootPath)

	def download(self, force):
		self._package.download(force)

	@property
	def unpackRootPath(self):
		return self._unpackRootPath

class _GnuArchive(_Archive):
	def __init__(self, downloadRootPath, tokenRootPath, unpackRootPath, name, version, urlFormatter):
		_Archive.__init__(self, downloadRootPath, tokenRootPath, unpackRootPath, urlFormatter(name, version))

class _CachePath(object):
	Build = None
	Dependencies = None
	Download = None
	Log = None
	Staging = None
	UnpackArchive = None
	UnpackToken = None

class _BuildType(Enum):
	Host = 0
	Windows = 1

class _BuildInfo(object):
	def __init__(self, env, prefixPath, buildType):
		self.env = env
		self.prefixPath = prefixPath
		self.buildType = buildType

_THIS_PATH = os.path.abspath(os.path.dirname(__file__))
_META_DATA_FILENAME = ".build_data"
_BUILD_TARGET_NAME = "mips64-elf"
_BUILD_ARCH_NAME = "vr4300"
_BUILD_CPU_NAME = "mips64vr4300"
_MINGW32_MACHINE_SPEC = "x86_64-w64-mingw32"

_INVALID_ARCHIVE = None # type: _Archive
_INVALID_GNU_ARCHIVE = None # type: _GnuArchive

_SED_ARCHIVE = _INVALID_GNU_ARCHIVE # type: _GnuArchive
_TEXINFO_ARCHIVE = _INVALID_GNU_ARCHIVE # type: _GnuArchive
_BIN_UTILS_ARCHIVE = _INVALID_GNU_ARCHIVE # type: _GnuArchive
_GMP_ARCHIVE = _INVALID_GNU_ARCHIVE # type: _GnuArchive
_MPC_ARCHIVE = _INVALID_GNU_ARCHIVE # type: _GnuArchive
_MPFR_ARCHIVE = _INVALID_GNU_ARCHIVE # type: _GnuArchive
_GCC_ARCHIVE = _INVALID_GNU_ARCHIVE # type: _GnuArchive
_NEWLIB_ARCHIVE = _INVALID_GNU_ARCHIVE # type: _GnuArchive
_N64_SDK_ARCHIVE = _INVALID_ARCHIVE # type: _Archive

def buildToolchain():
	config = Config.getInstance()

	assert not config.isHostWindows, "Cannot build N64 toolchain on Windows host; see README.md for more information"
	assert not (config.isHostMacOs and config.windowsCrossCompile), "Cannot build N64 toolchain for Windows from macOS host; see README.md for more information"

	# The host machine spec is necessary for cross-compiling to Windows.
	if config.windowsCrossCompile and not config.hostMachineSpec:
		raise ChildProcessError("Failed call to get machine spec; gcc may not be installed or is inaccessible")

	hostPlatformName = {
		"Linux": "linux",
		"Darwin": "macos",
	}.get(platform.system(), None)
	assert hostPlatformName, f"Unsupported platform: {platform.system()}"

	unpackRootPath = os.path.join(config.cachePath, "unpack")

	# Build the cache paths.
	_CachePath.Build = os.path.join(config.cachePath, "build")
	_CachePath.Dependencies = os.path.join(config.cachePath, "deps")
	_CachePath.Download = os.path.join(config.cachePath, "dl")
	_CachePath.Log = os.path.join(config.cachePath, "log")
	_CachePath.Staging = os.path.join(config.cachePath, "stg")
	_CachePath.UnpackToken = os.path.join(unpackRootPath, "tok")
	_CachePath.UnpackArchive = os.path.join(unpackRootPath, "arc")

	# Construct the output filenames.
	outputFileNameBase = "n64-dev"
	hostOutputFileName = f"{outputFileNameBase}-{hostPlatformName}.zip"
	windowsOutputFileName = f"{outputFileNameBase}-windows.zip"

	stagingSysRootPath = os.path.join(_CachePath.Staging, "sysroot")
	installSysRootPath = os.path.join(config.installPath, "sysroot")

	outputFileName = windowsOutputFileName if config.windowsCrossCompile else hostOutputFileName
	hostSysRootPath = stagingSysRootPath if config.windowsCrossCompile else installSysRootPath
	n64SdkPath = os.path.join(config.installPath, "sdk")

	_warmUp()
	_download()
	_unpack()
	_buildDependencies(_CachePath.Dependencies)

	env = _getEnvWithDeps(_CachePath.Dependencies)
	env = _handleSysRootBuild(env, hostSysRootPath, _BuildType.Host, config.windowsCrossCompile)

	if config.windowsCrossCompile:
		# Create a new environment with both sysroot paths since the Windows build
		# will need to call into the binaries we built for the host platform.
		_handleSysRootBuild(env, installSysRootPath, _BuildType.Windows, False)

	_installSdk(n64SdkPath)
	_generateArchive(config.installPath, outputFileName)

def _getAllFilesInCurrentPath():
	allFilePaths = set()
	startDirPath = os.getcwd()

	# Walk the current path, keeping track of each file we come across.
	for root, _, files in os.walk(startDirPath):
		for filePath in files:
			if root == startDirPath and filePath.endswith(".token"):
				continue

			filePath = os.path.relpath(os.path.join(root, filePath), os.getcwd())
			allFilePaths.add(filePath)

	return sorted(allFilePaths)

def _writeZipFile(outputFilePath, allFilePaths):
	log.info(f"Writing archive: {outputFilePath}")

	fileCount = len(allFilePaths)

	# Create the zip file and add each of the input files to it.
	with zipfile.ZipFile(outputFilePath, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as f:
		for filePath in clint.textui.progress.bar(allFilePaths, expected_size=fileCount):
			f.write(filePath)

def _getEnvWithDeps(depInstallPath):
	env = dict(os.environ)

	# Split the environment path and add dependencies install path to the start.
	envPath = env.get("PATH", "").split(":")
	envPath.insert(0, os.path.join(depInstallPath, "bin"))

	# Reform the path in the environment.
	env["PATH"] = ":".join(envPath)

	return env

def _getEnvWithSysRoot(env, sysRootPath):
	env = dict(env if env else os.environ)

	# Split the environment path and add sysroot/bin to the start.
	envPath = env.get("PATH", "").split(":")
	envPath.insert(0, os.path.join(sysRootPath, "bin"))

	# Reform the path in the environment.
	env["PATH"] = ":".join(envPath)

	return env

def _cleanPath(path):
	deletePathOnDisk(path)
	os.makedirs(path)

def _getAppExt(buildType):
	return ".exe" if buildType == _BuildType.Windows else ""

def _getPackagePlatformName(packageName, buildType):
	return f"{packageName}{'-windows' if buildType == _BuildType.Windows else '-host'}"

def _printPackageBuildHeader(packageName, buildType):
	buildTypeString = "Windows" if buildType == _BuildType.Windows else "Host"
	log.info(f"--- Package: {packageName} ({buildTypeString}) ---")

def _addWindowsCrossCompileArgs(args, hostMachineSpec):
	args.extend([
		f"--build={hostMachineSpec}",
		f"--host={_MINGW32_MACHINE_SPEC}",
	])

def _getStreamWriter(stream):
	return functools.partial(print, file=stream, end="")

def _warmUp():
	global _SED_ARCHIVE
	global _TEXINFO_ARCHIVE
	global _BIN_UTILS_ARCHIVE
	global _GMP_ARCHIVE
	global _MPC_ARCHIVE
	global _MPFR_ARCHIVE
	global _GCC_ARCHIVE
	global _NEWLIB_ARCHIVE
	global _N64_SDK_ARCHIVE

	log.info("*** Warming up ***")

	_SED_ARCHIVE = _GnuArchive(
		_CachePath.Download,
		_CachePath.UnpackToken,
		os.path.join(_CachePath.UnpackArchive, "sed"),
		"sed",
		"4.9",
		lambda name, version: f"https://ftp.gnu.org/gnu/{name}/{name}-{version}.tar.xz"
	)

	_TEXINFO_ARCHIVE = _GnuArchive(
		_CachePath.Download,
		_CachePath.UnpackToken,
		os.path.join(_CachePath.UnpackArchive, "texinfo"),
		"texinfo",
		"7.0.3",
		lambda name, version: f"https://ftp.gnu.org/gnu/{name}/{name}-{version}.tar.xz"
	)

	_BIN_UTILS_ARCHIVE = _GnuArchive(
		_CachePath.Download,
		_CachePath.UnpackToken,
		os.path.join(_CachePath.UnpackArchive, "binutils"),
		"binutils",
		"2.40",
		lambda name, version: f"https://ftp.gnu.org/gnu/{name}/{name}-{version}.tar.xz"
	)

	_GMP_ARCHIVE = _GnuArchive(
		_CachePath.Download,
		_CachePath.UnpackToken,
		os.path.join(_CachePath.UnpackArchive, "gmp"),
		"gmp",
		"6.2.1",
		lambda name, version: f"https://ftp.gnu.org/gnu/{name}/{name}-{version}.tar.xz"
	)

	_MPC_ARCHIVE = _GnuArchive(
		_CachePath.Download,
		_CachePath.UnpackToken,
		os.path.join(_CachePath.UnpackArchive, "mpc"),
		"mpc",
		"1.3.1",
		lambda name, version: f"https://ftp.gnu.org/gnu/{name}/{name}-{version}.tar.gz"
	)

	_MPFR_ARCHIVE = _GnuArchive(
		_CachePath.Download,
		_CachePath.UnpackToken,
		os.path.join(_CachePath.UnpackArchive, "mpfr"),
		"mpfr",
		"4.2.0",
		lambda name, version: f"https://ftp.gnu.org/gnu/{name}/{name}-{version}.tar.xz"
	)

	_GCC_ARCHIVE = _GnuArchive(
		_CachePath.Download,
		_CachePath.UnpackToken,
		os.path.join(_CachePath.UnpackArchive, "gcc"),
		"gcc",
		"13.1.0",
		lambda name, version: f"https://ftp.gnu.org/gnu/{name}/{name}-{version}/{name}-{version}.tar.xz"
	)

	_NEWLIB_ARCHIVE = _GnuArchive(
		_CachePath.Download,
		_CachePath.UnpackToken,
		os.path.join(_CachePath.UnpackArchive, "newlib"),
		"newlib",
		"4.3.0.20230120",
		lambda name, version: f"https://sourceware.org/pub/{name}/{name}-{version}.tar.gz"
	)

	_N64_SDK_ARCHIVE = _Archive(
		_CachePath.Download,
		_CachePath.UnpackToken,
		os.path.join(_CachePath.UnpackArchive, "n64sdk"),
		"https://ultra64.ca/files/software/other/sdks/n64sdk.7z"
	)

	config = Config.getInstance()

	if not os.access(_CachePath.Download, os.F_OK):
		os.makedirs(_CachePath.Download)

	if not os.access(_CachePath.UnpackToken, os.F_OK):
		os.makedirs(_CachePath.UnpackToken)

	if not os.access(_CachePath.UnpackArchive, os.F_OK):
		os.makedirs(_CachePath.UnpackArchive)

	_cleanPath(_CachePath.Log)
	_cleanPath(_CachePath.Build)
	_cleanPath(_CachePath.Dependencies)
	_cleanPath(_CachePath.Staging)

	_cleanPath(config.installPath)

	# Create the output directory.
	if not os.access(config.installPath, os.F_OK):
		os.makedirs(config.installPath)

def _download():
	log.info("--- Downloading archives ---")

	config = Config.getInstance()

	_SED_ARCHIVE.download(config.forceDownload)
	_TEXINFO_ARCHIVE.download(config.forceDownload)
	_BIN_UTILS_ARCHIVE.download(config.forceDownload)
	_GMP_ARCHIVE.download(config.forceDownload)
	_MPC_ARCHIVE.download(config.forceDownload)
	_MPFR_ARCHIVE.download(config.forceDownload)
	_GCC_ARCHIVE.download(config.forceDownload)
	_NEWLIB_ARCHIVE.download(config.forceDownload)
	_N64_SDK_ARCHIVE.download(config.forceDownload)

def _unpack():
	log.info("--- Unpacking archives ---")

	_SED_ARCHIVE.unpack()
	_TEXINFO_ARCHIVE.unpack()
	_BIN_UTILS_ARCHIVE.unpack()
	_GMP_ARCHIVE.unpack()
	_MPC_ARCHIVE.unpack()
	_MPFR_ARCHIVE.unpack()
	_GCC_ARCHIVE.unpack()
	_NEWLIB_ARCHIVE.unpack()

	_N64_SDK_ARCHIVE.unpack()

def _buildDependencies(depInstallPath):
	log.info("*** Building dependencies ***")

	buildInfo = _BuildInfo(None, depInstallPath, _BuildType.Host)

	_buildSed(buildInfo)
	_buildTexInfo(buildInfo)

def _handleSysRootBuild(env, outputSysRootPath, buildType, minimalBuild):
	log.info("*** Performing {}{} build ***".format(
		"minimal " if minimalBuild else "",
		{
			_BuildType.Windows: "Windows",
		}.get(buildType, "host")
	))

	env = _getEnvWithSysRoot(env, outputSysRootPath)

	buildInfo = _BuildInfo(env, outputSysRootPath, buildType)

	_buildBinUtils(buildInfo)
	_buildGmp(buildInfo)
	_buildMpfr(buildInfo)
	_buildMpc(buildInfo)
	_buildGcc(buildInfo)

	if not minimalBuild:
		_buildLibGcc(buildInfo)
		_buildNewLib(buildInfo)

	return env

def _installSdk(sdkOutputPath):
	log.info("*** Installing N64 SDK ***")
	copyFilesOnDisk(_N64_SDK_ARCHIVE.unpackRootPath, sdkOutputPath)

	log.info("Fixing SDK files ...")

	with changeDirectory(sdkOutputPath):
		filePaths = _getAllFilesInCurrentPath()
		filePaths = [
			x for x in filePaths
			if os.path.splitext(x)[1].lower() in [".c", ".h", ".txt", ".htm", ".cmd", ".bat", ".ini", ".cfg"] \
				or os.path.basename(x).lower() in ["makefile", "spec", "arfile", "readme"]
		]

		# Scan each source file in the SDK to see if they need to be fixed.
		for filePath in clint.textui.progress.bar(filePaths):
			with open(filePath, "rb") as inputStream:
				fileData = inputStream.read()

			# Some of the files contain an invalid character at the end.
			# This needs to be removed to keep the tools from failing.
			if fileData.endswith(b"\x1A"):
				with open(filePath, "wb") as outputStream:
					outputStream.write(fileData[:-1])

def _generateArchive(stagingPath, outputFileName):
	config = Config.getInstance()

	log.info("*** Creating package ***")

	# Zip the contents of the input staging path.
	with changeDirectory(stagingPath):
		outputFilePath = os.path.join(config.installPath, outputFileName)
		allFilePaths = _getAllFilesInCurrentPath()

		_writeZipFile(outputFilePath, allFilePaths)

def _configurePackage(packageName, env, logPath, args):
	log.info("  Configuring ...")
	log.verbose("    $> {}".format(" ".join([f"\"{x}\"" if " " in x else x for x in args])))
	with open(os.path.join(logPath, "configure.out.log"), "w") as outStream:
		with open(os.path.join(logPath, "configure.err.log"), "w") as errStream:
			exitCode = runProcess(
				args,
				outputHandler=_getStreamWriter(outStream),
				errorHandler=_getStreamWriter(errStream),
				env=env
			)
			assert exitCode == 0, f"Failed to configure '{packageName}'"

def _buildPackage(packageName, env, logPath, makeTarget = None):
	config = Config.getInstance()

	log.info("  Building ...")
	with open(os.path.join(logPath, "build.out.log"), "w") as outStream:
		with open(os.path.join(logPath, "build.err.log"), "w") as errStream:
			cmd = ["make", "-j", str(config.cpuCoreCount), makeTarget]
			cmd = [x for x in cmd if x]
			exitCode = runProcess(
				cmd,
				outputHandler=_getStreamWriter(outStream),
				errorHandler=_getStreamWriter(errStream),
				env=env
			)
			assert exitCode == 0, f"Failed to build '{packageName}'"

def _installPackage(packageName, env, logPath, prefixPath, installTarget ="install"):
	log.info("  Installing ...")
	with open(os.path.join(logPath, "install.out.log"), "w") as outStream:
		with open(os.path.join(logPath, "install.err.log"), "w") as errStream:
			exitCode = runProcess(
				["make", installTarget],
				outputHandler=_getStreamWriter(outStream),
				errorHandler=_getStreamWriter(errStream),
				env=env
			)
			assert exitCode == 0, f"Failed to stage '{packageName}' to sysroot: {prefixPath}"

def _findConfigureFile(rootPath):
	configureFilePath = None

	for root, _, files in os.walk(rootPath, followlinks=False):
		for fileName in files:
			if fileName == "configure":
				tempFilePath = os.path.join(root, fileName)
				if configureFilePath is None or len(tempFilePath) < len(configureFilePath) and os.path.isfile(tempFilePath):
					configureFilePath = tempFilePath

	assert configureFilePath, f"Unable to find 'configure' file anywhere in root path: {rootPath}"
	return configureFilePath

def _buildSed(buildInfo):
	packageName = "sed"
	configurePath = _findConfigureFile(_SED_ARCHIVE.unpackRootPath)
	buildPath = os.path.join(_CachePath.Build, packageName)
	logPath = os.path.join(_CachePath.Log, packageName)

	# Create the output paths.
	os.makedirs(buildPath, exist_ok=True)
	os.makedirs(logPath, exist_ok=True)

	with changeDirectory(buildPath):
		args = [
			os.path.relpath(configurePath, buildPath),
			f"--prefix={buildInfo.prefixPath}"
		]

		_printPackageBuildHeader(packageName, buildInfo.buildType)

		_configurePackage(packageName, buildInfo.env, logPath, args)
		_buildPackage(packageName, buildInfo.env, logPath)
		_installPackage(packageName, buildInfo.env, logPath, buildInfo.prefixPath)

def _buildTexInfo(buildInfo):
	packageName = "texinfo"
	configurePath = _findConfigureFile(_TEXINFO_ARCHIVE.unpackRootPath)
	buildPath = os.path.join(_CachePath.Build, packageName)
	logPath = os.path.join(_CachePath.Log, packageName)

	# Create the output paths.
	os.makedirs(buildPath, exist_ok=True)
	os.makedirs(logPath, exist_ok=True)

	with changeDirectory(buildPath):
		args = [
			os.path.relpath(configurePath, buildPath),
			f"--prefix={buildInfo.prefixPath}"
		]

		_printPackageBuildHeader(packageName, buildInfo.buildType)

		_configurePackage(packageName, buildInfo.env, logPath, args)
		_buildPackage(packageName, buildInfo.env, logPath)
		_installPackage(packageName, buildInfo.env, logPath, buildInfo.prefixPath)

def _buildBinUtils(buildInfo):
	config = Config.getInstance()
	packageName = "binutils"
	platformPackageName = _getPackagePlatformName(packageName, buildInfo.buildType)
	prefixLibPath = os.path.join(buildInfo.prefixPath, "lib")
	configurePath = _findConfigureFile(_BIN_UTILS_ARCHIVE.unpackRootPath)
	buildPath = os.path.join(_CachePath.Build, platformPackageName)
	logPath = os.path.join(_CachePath.Log, platformPackageName)

	# Create the output paths.
	os.makedirs(buildPath, exist_ok=True)
	os.makedirs(logPath, exist_ok=True)

	with changeDirectory(buildPath):
		args = [
			os.path.relpath(configurePath, buildPath),
			f"--prefix={buildInfo.prefixPath}",
			f"--target={_BUILD_TARGET_NAME}",
			f"--with-lib-path={prefixLibPath}",
			f"--with-cpu={_BUILD_CPU_NAME}",
			"--with-abi=32",
			"--without-msgpack",
			"--enable-64-bit-bfd",
			"--enable-plugins",
			"--enable-deterministic-archives",
			"--enable-shared",
			"--disable-gold",
			"--disable-multilib",
			"--disable-nls",
			"--disable-rpath",
			"--disable-static",
			"--disable-werror",
		]

		if buildInfo.buildType == _BuildType.Windows:
			_addWindowsCrossCompileArgs(args, config.hostMachineSpec)

		_printPackageBuildHeader(packageName, buildInfo.buildType)

		_configurePackage(packageName, buildInfo.env, logPath, args)
		_buildPackage(packageName, buildInfo.env, logPath)
		_installPackage(packageName, buildInfo.env, logPath, buildInfo.prefixPath)

def _buildGmp(buildInfo):
	config = Config.getInstance()
	packageName = "gmp"
	platformPackageName = _getPackagePlatformName(packageName, buildInfo.buildType)
	configurePath = _findConfigureFile(_GMP_ARCHIVE.unpackRootPath)
	buildPath = os.path.join(_CachePath.Build, platformPackageName)
	logPath = os.path.join(_CachePath.Log, platformPackageName)

	# Create the output paths.
	os.makedirs(buildPath, exist_ok=True)
	os.makedirs(logPath, exist_ok=True)

	with changeDirectory(buildPath):
		args = [
			os.path.relpath(configurePath, buildPath),
			f"--prefix={buildInfo.prefixPath}",
			"--with-pic",
			"--enable-fft",
			"--enable-cxx",
			"--enable-static",
			"--disable-shared",
		]

		configEnv = dict(buildInfo.env)
		configEnv["CFLAGS"] = " ".join([
			"-fexceptions",
		])

		if buildInfo.buildType == _BuildType.Windows:
			_addWindowsCrossCompileArgs(args, config.hostMachineSpec)

			configEnv["CC_FOR_BUILD"] = f"{config.hostMachineSpec}-gcc"
			configEnv["CPP_FOR_BUILD"] = f"{config.hostMachineSpec}-cpp"
			configEnv["CC"] = f"{_MINGW32_MACHINE_SPEC}-gcc"

		_printPackageBuildHeader(packageName, buildInfo.buildType)

		_configurePackage(packageName, configEnv, logPath, args)
		_buildPackage(packageName, buildInfo.env, logPath)
		_installPackage(packageName, buildInfo.env, logPath, buildInfo.prefixPath)

def _buildMpfr(buildInfo):
	config = Config.getInstance()
	packageName = "mpfr"
	platformPackageName = _getPackagePlatformName(packageName, buildInfo.buildType)
	prefixIncPath = os.path.join(buildInfo.prefixPath, "include")
	prefixLibPath = os.path.join(buildInfo.prefixPath, "lib")
	configurePath = _findConfigureFile(_MPFR_ARCHIVE.unpackRootPath)
	buildPath = os.path.join(_CachePath.Build, platformPackageName)
	logPath = os.path.join(_CachePath.Log, platformPackageName)

	# Create the output paths.
	os.makedirs(buildPath, exist_ok=True)
	os.makedirs(logPath, exist_ok=True)

	with changeDirectory(buildPath):
		args = [
			os.path.relpath(configurePath, buildPath),
			f"--prefix={buildInfo.prefixPath}",
			f"--with-gmp-include={prefixIncPath}",
			f"--with-gmp-lib={prefixLibPath}",
			"--with-pic",
			"--enable-static",
			"--disable-shared",
			"--disable-thread-safe",
		]

		configEnv = dict(buildInfo.env)

		if buildInfo.buildType == _BuildType.Windows:
			_addWindowsCrossCompileArgs(args, config.hostMachineSpec)

			configEnv["CC"] = f"{_MINGW32_MACHINE_SPEC}-gcc"

		_printPackageBuildHeader(packageName, buildInfo.buildType)

		_configurePackage(packageName, configEnv, logPath, args)
		_buildPackage(packageName, buildInfo.env, logPath)
		_installPackage(packageName, buildInfo.env, logPath, buildInfo.prefixPath)

def _buildMpc(buildInfo):
	config = Config.getInstance()
	packageName = "mpc"
	platformPackageName = _getPackagePlatformName(packageName, buildInfo.buildType)
	prefixIncPath = os.path.join(buildInfo.prefixPath, "include")
	prefixLibPath = os.path.join(buildInfo.prefixPath, "lib")
	configurePath = _findConfigureFile(_MPC_ARCHIVE.unpackRootPath)
	buildPath = os.path.join(_CachePath.Build, platformPackageName)
	logPath = os.path.join(_CachePath.Log, platformPackageName)

	# Create the output paths.
	os.makedirs(buildPath, exist_ok=True)
	os.makedirs(logPath, exist_ok=True)

	with changeDirectory(buildPath):
		args = [
			os.path.relpath(configurePath, buildPath),
			f"--prefix={buildInfo.prefixPath}",
			f"--with-gmp-include={prefixIncPath}",
			f"--with-gmp-lib={prefixLibPath}",
			"--enable-static",
			"--disable-shared",
		]

		if buildInfo.buildType == _BuildType.Windows:
			_addWindowsCrossCompileArgs(args, config.hostMachineSpec)

		_printPackageBuildHeader(packageName, buildInfo.buildType)

		_configurePackage(packageName, buildInfo.env, logPath, args)
		_buildPackage(packageName, buildInfo.env, logPath)
		_installPackage(packageName, buildInfo.env, logPath, buildInfo.prefixPath)

def _buildGcc(buildInfo):
	config = Config.getInstance()
	packageName = "gcc"
	appExt = _getAppExt(buildInfo.buildType)
	platformPackageName = _getPackagePlatformName(packageName, buildInfo.buildType)
	prefixIncPath = os.path.join(buildInfo.prefixPath, "include")
	prefixLibPath = os.path.join(buildInfo.prefixPath, "lib")
	configurePath = _findConfigureFile(_GCC_ARCHIVE.unpackRootPath)
	buildPath = os.path.join(_CachePath.Build, platformPackageName)
	logPath = os.path.join(_CachePath.Log, platformPackageName)

	# Create the output paths.
	os.makedirs(buildPath, exist_ok=True)
	os.makedirs(logPath, exist_ok=True)

	with changeDirectory(buildPath):
		args = [
			os.path.relpath(configurePath, buildPath),
			f"--prefix={buildInfo.prefixPath}",
			f"--target={_BUILD_TARGET_NAME}",
			f"--with-arch={_BUILD_ARCH_NAME}",
			f"--with-tune={_BUILD_ARCH_NAME}",
			"--with-gnu-as={}".format(os.path.join(buildInfo.prefixPath, "bin", f"{_BUILD_TARGET_NAME}-as{appExt}")),
			"--with-gnu-ld={}".format(os.path.join(buildInfo.prefixPath, "bin", f"{_BUILD_TARGET_NAME}-ld{appExt}")),
			f"--with-gmp-include={prefixIncPath}",
			f"--with-gmp-lib={prefixLibPath}",
			f"--with-mpfr-include={prefixIncPath}",
			f"--with-mpfr-lib={prefixLibPath}",
			f"--with-mpc-include={prefixIncPath}",
			f"--with-mpc-lib={prefixLibPath}",
			"--with-abi=32",
			"--without-headers",
			"--with-gcc",
			"--with-newlib",
			"--enable-checking=release",
			"--enable-languages=c,c++",
			"--enable-lto",
			"--enable-plugin",
			"--enable-static",
			"--enable-static-libgcc",
			"--disable-shared",
			"--disable-decimal-float",
			"--disable-gold",
			"--disable-libatomic",
			"--disable-libgomp",
			"--disable-libitm",
			"--disable-libquadmath",
			"--disable-libquadmath-support",
			"--disable-libsanitizer",
			"--disable-libssp",
			"--disable-libunwind-exceptions",
			"--disable-libvtv",
			"--disable-multilib",
			"--disable-nls",
			"--disable-rpath",
			"--disable-threads",
			"--disable-win32-registry",
			"--without-included-gettext",
		]

		if buildInfo.buildType == _BuildType.Windows:
			_addWindowsCrossCompileArgs(args, config.hostMachineSpec)
			args.append("--disable-symvers")

		_printPackageBuildHeader(packageName, buildInfo.buildType)

		_configurePackage(packageName, buildInfo.env, logPath, args)
		_buildPackage(packageName, buildInfo.env, logPath, "all-gcc")
		_installPackage(packageName, buildInfo.env, logPath, buildInfo.prefixPath, "install-gcc")

	# Needed by the newlib build since it calls into 'cc' rather than 'gcc'.
	with changeDirectory(os.path.join(buildInfo.prefixPath, "bin")):
		srcExe = f"{_BUILD_TARGET_NAME}-gcc{appExt}"
		dstExe = f"{_BUILD_TARGET_NAME}-cc{appExt}"

		if buildInfo.buildType == _BuildType.Host:
			# Make a symlink to the gcc executable.
			os.link(srcExe, dstExe)

		else:
			# Make a copy of gcc when targeting Windows since we can't rely on symlinks there.
			shutil.copy2(srcExe, dstExe)

def _buildLibGcc(buildInfo):
	packageName = "libgcc"
	buildPackageName = _getPackagePlatformName("gcc", buildInfo.buildType)
	logPackageName = _getPackagePlatformName(packageName, buildInfo.buildType)
	buildPath = os.path.join(_CachePath.Build, buildPackageName)
	logPath = os.path.join(_CachePath.Log, logPackageName)

	# Create the output paths.
	os.makedirs(buildPath, exist_ok=True)
	os.makedirs(logPath, exist_ok=True)

	with changeDirectory(buildPath):
		_printPackageBuildHeader(packageName, buildInfo.buildType)

		_buildPackage(packageName, buildInfo.env, logPath, "all-target-libgcc")
		_installPackage(packageName, buildInfo.env, logPath, buildInfo.prefixPath, "install-target-libgcc")

def _buildNewLib(buildInfo):
	config = Config.getInstance()
	packageName = "newlib"
	platformPackageName = _getPackagePlatformName(packageName, buildInfo.buildType)
	configurePath = _findConfigureFile(_NEWLIB_ARCHIVE.unpackRootPath)
	buildPath = os.path.join(_CachePath.Build, platformPackageName)
	logPath = os.path.join(_CachePath.Log, platformPackageName)

	# Create the output paths.
	os.makedirs(buildPath, exist_ok=True)
	os.makedirs(logPath, exist_ok=True)

	with changeDirectory(buildPath):
		args = [
			os.path.relpath(configurePath, buildPath),
			f"--prefix={buildInfo.prefixPath}",
			f"--target={_BUILD_TARGET_NAME}",
			f"--with-cpu={_BUILD_CPU_NAME}"
			"--with-abi=32",
			"--disable-bootstrap",
			"--disable-build-poststage1-with-cxx",
			"--disable-build-with-cxx",
			"--disable-cloog-version-check",
			"--disable-dependency-tracking",
			"--disable-libada",
			"--disable-libquadmath",
			"--disable-libquadmath-support",
			"--disable-libssp",
			"--disable-maintainer-mode",
			"--disable-malloc-debugging",
			"--disable-multilib",
			"--disable-newlib-atexit-alloc",
			"--disable-newlib-hw-fp",
			"--disable-newlib-iconv",
			"--disable-newlib-io-float",
			"--disable-newlib-io-long-double",
			"--disable-newlib-io-long-long",
			"--disable-newlib-mb",
			"--disable-newlib-multithread",
			"--disable-newlib-register-fini",
			"--disable-newlib-supplied-syscalls",
			"--disable-objc-gc",
			"--enable-newlib-io-c99-formats",
			"--enable-newlib-io-pos-args",
			"--enable-newlib-reent-small",
			"--with-endian=big",
			"--without-cloog",
			"--without-gmp",
			"--without-mpc",
			"--without-mpfr",
		]

		if buildInfo.buildType == _BuildType.Windows:
			_addWindowsCrossCompileArgs(args, config.hostMachineSpec)

		_printPackageBuildHeader(packageName, buildInfo.buildType)

		configEnv = dict(buildInfo.env)
		configEnv["CFLAGS"] = " ".join([
			"-O2",
			"-fomit-frame-pointer",
			"-ffast-math",
			"-fstrict-aliasing",
		])

		_configurePackage(packageName, configEnv, logPath, args)
		_buildPackage(packageName, buildInfo.env, logPath)
		_installPackage(packageName, buildInfo.env, logPath, buildInfo.prefixPath)
