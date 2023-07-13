//
// Copyright (c) 2023, Zoe J. Bare
//
// Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
// documentation files (the "Software"), to deal in the Software without restriction, including without limitation
// the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
// and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in all copies or substantial portions
// of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED
// TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
// THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
// CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
// IN THE SOFTWARE.
//

#include "../common/build.hpp"
#include "../common/file_buffer.hpp"
#include "../common/log.hpp"

#include <assert.h>
#include <locale.h>
#include <inttypes.h>
#include <memory.h>
#include <stdint.h>
#include <stdlib.h>

#include <functional>
#include <string>
#include <string_view>

#define CXXOPTS_NO_RTTI
#include <cxxopts.hpp>

//----------------------------------------------------------------------------------------------------------------------

#define APP_EXIT_SUCCESS 0
#define APP_EXIT_FAILURE 1

#define APP_VERSION_MAJOR 1
#define APP_VERSION_MINOR 0
#define APP_VERSION_PATCH 0

#define DEFAULT_ROM_VERSION 0
#define DEFAULT_GAME_CODE "N00A"

//----------------------------------------------------------------------------------------------------------------------

inline uint32_t LoadUint32(const uint8_t* const pData, const size_t offset)
{
#ifdef PLATFORM_LITTLE_ENDIAN
	const uint32_t b0 = uint32_t(pData[offset + 0]);
	const uint32_t b1 = uint32_t(pData[offset + 1]);
	const uint32_t b2 = uint32_t(pData[offset + 2]);
	const uint32_t b3 = uint32_t(pData[offset + 3]);

	return (b0 << 24) | (b1 << 16) | (b2 << 8) | b3;

#else
	return *((uint32_t*) &pData[offset]);

#endif
}

//----------------------------------------------------------------------------------------------------------------------

inline void StoreUint32(uint8_t* const pData, const size_t offset, const uint32_t value)
{
#ifdef PLATFORM_LITTLE_ENDIAN
	pData[offset + 3] = value & 0xFF;
	pData[offset + 2] = (value >> 8) & 0xFF;
	pData[offset + 1] = (value >> 16) & 0xFF;
	pData[offset + 0] = (value >> 24) & 0xFF;

#else
	*((uint32_t*) &pData[offset]) = value;

#endif
}

//----------------------------------------------------------------------------------------------------------------------

inline uint32_t RotateLeftUint32(const uint32_t value, const uint32_t bits)
{
	const uint32_t rightShiftMask = (1 << bits) - 1;
	const uint32_t leftShiftMask = ~rightShiftMask;

	return ((value << bits) & leftShiftMask) | ((value >> (32 - bits)) & rightShiftMask);
}

//----------------------------------------------------------------------------------------------------------------------

bool ProcessRom(
	const std::string_view& inputFilePath,
	const std::string_view& outputFilePath,
	const std::string_view& bootCodeFilePath,
	const uint32_t bootCodeId,
	const std::string_view& gameTitle,
	const std::string_view& gameCode,
	const uint8_t romVersion)
{
	constexpr size_t oneMbitInBytes = 1024 * 1024 / 8;
	constexpr uint8_t romFillByte = 0xFF;

	constexpr size_t checksumLength = 0x00100000;
	constexpr size_t checksumStart = 0x00001000;
	constexpr size_t checksumEnd = checksumStart + checksumLength;

	constexpr size_t checksumOffset = 0x10;
	constexpr size_t bootCodeOffset = 0x40;

	constexpr size_t gameTitleOffset = 0x20;
	constexpr size_t gameTitleMaxLength = 0x14;

	constexpr size_t gameCodeOffset = 0x3B;
	constexpr size_t gameCodeMaxLength = 0x04;

	constexpr size_t reservedOffset = 0x34;
	constexpr size_t reservedLength = 0x07;

	constexpr size_t romVersionOffset = 0x3F;

	constexpr uint32_t cic6102 = 0xF8CA4DDC;
	constexpr uint32_t cic6103 = 0xA3886759;
	constexpr uint32_t cic6105 = 0xDF26F436;
	constexpr uint32_t cic6106 = 0x1FEA617A;

	assert(inputFilePath.size() > 0);
	assert(outputFilePath.size() > 0);
	assert(bootCodeFilePath.size() > 0);
	assert(gameCode.size() > 0);

	FileBuffer bootCodeFile;
	FileBuffer romFile;

	// Read the contents of the bootcode file to a buffer.
	if(!FileBuffer::Read(bootCodeFile, bootCodeFilePath))
	{
		LOG_ERROR_FMT("Failed to load bootcode file: %s", bootCodeFilePath.data());
		return false;
	}

	// Read the contents of the input file to a padded buffer
	if(!FileBuffer::Read(romFile, inputFilePath, checksumEnd, oneMbitInBytes, romFillByte))
	{
		LOG_ERROR_FMT("Failed to load input file: %s", inputFilePath.data());
		return false;
	}

	// Verify the ROM file is large enough to contain the bootcode.
	if(bootCodeFile.length > romFile.length)
	{
		LOG_ERROR_FMT(
			"Length of bootcode file exceeds length of ROM file: %zu + 0x%02" PRIX32 " > %zu",
			bootCodeFile.length,
			uint32_t(bootCodeOffset),
			romFile.length);
		return false;
	}

	LOG_VERBOSE("Patching ROM header ...");

	// Clear the unused reserved data in the ROM header.
	memset(romFile.data.get() + reservedOffset, 0, reservedLength);

	// Clear the game title in the ROM header with the default padding value.
	memset(romFile.data.get() + gameTitleOffset, 0x20, gameTitleMaxLength);

	if(gameTitle.size() > 0)
	{
		// Copy the game title into the ROM header.
		const size_t copyLength = (gameTitle.size() < gameTitleMaxLength) ? gameTitle.size() : gameTitleMaxLength;
		memcpy(romFile.data.get() + gameTitleOffset, gameTitle.data(), copyLength);
	}

	if(gameCode.size() == gameCodeMaxLength)
	{
		// Fill the game code in the ROM header.
		memcpy(romFile.data.get() + gameCodeOffset, gameCode.data(), gameCodeMaxLength);
	}

	// Set the ROM version.
	romFile.data.get()[romVersionOffset] = romVersion;

	// Insert the bootcode into the ROM file.
	LOG_VERBOSE("Patching ROM bootcode ...");
	memcpy(romFile.data.get() + bootCodeOffset, bootCodeFile.data.get(), bootCodeFile.length);

	uint32_t cicSeed;

	switch(bootCodeId)
	{
		case 6101:
		case 6102:
			cicSeed = cic6102;
			break;

		case 6103: cicSeed = cic6103; break;
		case 6105: cicSeed = cic6105; break;
		case 6106: cicSeed = cic6106; break;

		default:
			LOG_ERROR_FMT("Unsupported bootcode ID: %" PRIu32, bootCodeId);
			return false;
	}

	uint32_t crc[2];

	uint32_t t1 = cicSeed;
	uint32_t t2 = cicSeed;
	uint32_t t3 = cicSeed;
	uint32_t t4 = cicSeed;
	uint32_t t5 = cicSeed;
	uint32_t t6 = cicSeed;

	uint32_t d;
	uint32_t r;

	uint32_t x;
	uint32_t u;

	LOG_VERBOSE("Generating checksum ...");

	const bool isBootCode6105 = (bootCodeId == 6105);

	// Calculate the ROM checksum parameters.
	for(uint32_t offset = checksumStart; offset < checksumEnd; offset += 4)
	{
		d = LoadUint32(romFile.data.get(), offset);
		x = t6 + d;

		if(x < t6)
		{
			++t4;
		}

		t6 = x;
		t3 ^= d;

		r = RotateLeftUint32(d, d & 0x1F);
		t5 += r;

		if(t2 > d)
		{
			t2 ^= r;
		}
		else
		{
			t2 ^= t6 ^ d;
		}

		if(isBootCode6105)
		{
			u = bootCodeOffset + 0x0710 + ((offset - checksumStart) & 0xFF);
			u = LoadUint32(romFile.data.get(), u);
			t1 += u ^ d;
		}
		else
		{
			t1 += t5 ^ d;
		}
	}

	// Complete the checksum calculation.
	switch(bootCodeId)
	{
		case 6103:
			crc[0] = (t6 ^ t4) + t3;
			crc[1] = (t5 ^ t2) + t1;
			break;

		case 6106:
			crc[0] = (t6 * t4) + t3;
			crc[1] = (t5 * t2) + t1;
			break;

		default:
			crc[0] = t6 ^ t4 ^ t3;
			crc[1] = t5 ^ t2 ^ t1;
			break;
	}

	LOG_INFO_FMT("ROM checksum: [0]=0x%08" PRIX32 ", [1]=0x%08" PRIX32, crc[0], crc[1]);

	// Store the checksum at the end of the ROM header.
	StoreUint32(romFile.data.get(), checksumOffset + 0, crc[0]);
	StoreUint32(romFile.data.get(), checksumOffset + 4, crc[1]);

	// Write the fully patched ROM file to disk.
	if(!FileBuffer::Write(outputFilePath, romFile))
	{
		LOG_ERROR_FMT("Failed to write output file: %s", outputFilePath.data());
		return false;
	}

	return true;
}

//----------------------------------------------------------------------------------------------------------------------

int main(int argc, char* argv[])
{
	// Set the program locale to the environment default.
	setlocale(LC_ALL, "");

#if defined(_WIN32)
	// This enables tracking of global heap allocations. If any are leaked,
	// they will show up in the Visual Studio output window on application exit.
	_CrtSetDbgFlag(_CRTDBG_ALLOC_MEM_DF | _CRTDBG_LEAK_CHECK_DF);
#endif

	cxxopts::Options options(
#if defined(_WIN32)
		"maskrom64.exe",
#else
		"maskrom64",
#endif
		"N64 ROM masking utility (functionally similar to MAKEMASK.EXE)"
	);

	options
		.custom_help("[options...]")
		.positional_help("<input_file>")
		.allow_unrecognised_options();

	// Add the options.
	options.add_options()
		("h,help", "Display this help text")
		("input_file", "File path of the unprocessed ROM", cxxopts::value<std::string>(), "<input_file>")
		("o,output", "File path where the final ROM file data will be written to (may be omitted to overwrite the input file)", cxxopts::value<std::string>(), "file")
		("b,bootcode", "File path of the CIC bootcode to insert into the ROM", cxxopts::value<std::string>(), "file")
		("i,id", "ID corresponding to the CIC bootcode file (e.g., 6102)", cxxopts::value<uint32_t>(), "value")
		("r,romversion", "ROM version to insert into ROM header (default = " + std::to_string(DEFAULT_ROM_VERSION) + ")", cxxopts::value<uint8_t>(), "value")
		("t,title", "Game title to insert into ROM header (may be omitted to leave game title blank in header)", cxxopts::value<std::string>(), "name")
		("g,gamecode", "4-character ASCII game code to insert into ROM header (default = \"" + std::string(DEFAULT_GAME_CODE) + "\")", cxxopts::value<std::string>(), "code")
		("q,quiet", "Disable all logging exception errors")
		("v,verbose", "Enable verbose logging (overrides -q/--quiet)");

	// Define which of the above arguments are positional.
	options.parse_positional({ "input_file" });

	// Parse the application's command line arguments.
	cxxopts::ParseResult args = options.parse(argc, argv);

	if(args.count("help"))
	{
		// Print the help text, then exit.
		printf("%s\n", options.help({ "" }).c_str());
		return APP_EXIT_SUCCESS;
	}

	// Get the logging options.
	const bool quietLogging = (args.count("quiet") > 0);
	const bool verboseLogging = (args.count("verbose") > 0);

	// Show a warning if "-q" and "-v" have been used together.
	if(quietLogging && verboseLogging)
	{
		LOG_WARN("Quiet logging and verbose logging are both enabled; verbose logging will be selected");
	}

	// Set the log level based on the selected logging options.
	gLogLevel = verboseLogging
		? LogLevel::Verbose
		: quietLogging
			? LogLevel::Quiet
			: LogLevel::Normal;

	// Check for the <input_file> argument.
	if(args.count("input_file") == 0)
	{
		LOG_ERROR("Missing required argument: <input_file>");
		return APP_EXIT_FAILURE;
	}

	// Get the input file path from the command line and make sure it's not empty.
	const std::string_view inputFilePath = args["input_file"].as<std::string>();
	if(inputFilePath.size() == 0)
	{
		LOG_ERROR("Input file path is empty");
		return APP_EXIT_FAILURE;
	}

	std::string_view outputFilePath;
	if(args.count("output"))
	{
		// Get the output file path from the command line and make sure it's not empty.
		outputFilePath = args["output"].as<std::string>();
		if(outputFilePath.size() == 0)
		{
			LOG_ERROR("Output file path is empty");
			return APP_EXIT_FAILURE;
		}
	}
	else
	{
		// When no output file is explicitly supplied, we assume the user wants to overwrite the input file.
		outputFilePath = inputFilePath;
	}

	// Check for the "--bootcode" argument.
	if(args.count("bootcode") == 0)
	{
		LOG_ERROR("Missing required argument: --bootcode");
		return APP_EXIT_FAILURE;
	}

	// Get the bootcode file path from the command line and make sure it's not empty.
	const std::string_view bootCodeFilePath = args["bootcode"].as<std::string>();
	if(inputFilePath.size() == 0)
	{
		LOG_ERROR("Bootcode file path is empty");
		return APP_EXIT_FAILURE;
	}

	// Check for the "--id" argument.
	if(args.count("id") == 0)
	{
		LOG_ERROR("Missing required argument: --id");
		return APP_EXIT_FAILURE;
	}

	const std::string defaultGameTitle = "";
	const std::string defaultGameCode = DEFAULT_GAME_CODE;

	const uint32_t bootCodeId = args["id"].as<uint32_t>();

	const std::string_view gameTitle = args.count("title") ? args["title"].as<std::string>() : defaultGameTitle;
	const std::string_view gameCode = args.count("gamecode") ? args["gamecode"].as<std::string>() : defaultGameCode;

	const uint8_t romVersion = args.count("romversion") ? args["romversion"].as<uint8_t>() : DEFAULT_ROM_VERSION;

	// Verify the game code is the correct length.
	if(gameCode.size() != 4)
	{
		LOG_ERROR_FMT("Specified game code is not exactly 4 characters long: \"%s\"", gameCode.data());
		return APP_EXIT_FAILURE;
	}

	LOG_INFO_FMT("MaskRom64 v%" PRIu32 ".%" PRIu32 ".%" PRIu32, APP_VERSION_MAJOR, APP_VERSION_MINOR, APP_VERSION_PATCH);

	// Attempt to generate a CRC hash for the input ROM and patch it, along with the supplied bootcode,
	// into the ROM data, saving the modified ROM data to the specified output file.
	if(!ProcessRom(inputFilePath, outputFilePath, bootCodeFilePath, bootCodeId, gameTitle, gameCode, romVersion))
	{
		return APP_EXIT_FAILURE;
	}

	return APP_EXIT_SUCCESS;
}

//----------------------------------------------------------------------------------------------------------------------