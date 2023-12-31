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

#include "strings.hpp"

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
#include <memory>

#define CXXOPTS_NO_RTTI
#include <cxxopts.hpp>

#define LIGHTNINGJSON_STRICT 1
#include <LightningJSON/LightningJSON.hpp>

//----------------------------------------------------------------------------------------------------------------------

#define APP_EXIT_SUCCESS 0
#define APP_EXIT_FAILURE 1

#define APP_VERSION_MAJOR 0
#define APP_VERSION_MINOR 1
#define APP_VERSION_PATCH 0

//----------------------------------------------------------------------------------------------------------------------

#ifdef _WIN32
	#define PATH_SEP_CHR       '\\'
	#define WRONG_PATH_SEP_CHR '/'
#else
	#define PATH_SEP_CHR       '/'
	#define WRONG_PATH_SEP_CHR '\\'
#endif

//----------------------------------------------------------------------------------------------------------------------

bool ValidateAssetName(const std::string_view& name)
{
	if(name[0] == '\0' || name.length() == 0)
	{
		LOG_ERROR("Empty asset name string");
		return false;
	}

	auto isSymbol = [](const char c)
	{
		switch(c)
		{
			case '_':
			case '$':
				return true;

			default:
				return false;
		}
	};

	auto isNumber = [](const char c)
	{
		return (c >= '0' && c <= '9');
	};

	auto isAlpha = [](const char c)
	{
		return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z');
	};

	// Asset names will be used as variable names which cannot begin with a number.
	if(isNumber(name[0]))
	{
		LOG_ERROR_FMT("Asset name cannot start with a number: \"%s\"", name.data());
		return false;
	}

	// Continue the verification of the asset name's first character.
	if(!isAlpha(name[0]) && !isSymbol(name[0]))
	{
		LOG_ERROR_FMT("Asset name must start with an ASCII character or a valid symbol ('_', '$'): \"%s\"", name.data());
		return false;
	}

	// Validate the rest of the asset name using the default rules.
	for(size_t i = 1; i < name.length(); ++i)
	{
		if(!isNumber(name[i]) && !isAlpha(name[i]) && !isSymbol(name[i]))
		{
			LOG_ERROR_FMT("Asset name may only contain numbers, ASCII characters, and valid symbols ('_', '$'): \"%s\"", name.data());
			return false;
		}
	}

	return true;
};

//----------------------------------------------------------------------------------------------------------------------

std::string NormalizePath(const std::string_view& path)
{
	std::string output(path);

	for(size_t i = 0; i < output.length(); ++i)
	{
		if(output[i] == WRONG_PATH_SEP_CHR)
		{
			output[i] = PATH_SEP_CHR;
		}
	}

	return output;
}

//----------------------------------------------------------------------------------------------------------------------

int ResolveAssetType(const std::string_view& typeString)
{
	for(int i = 0; i < ASSET_TYPE__COUNT; ++i)
	{
		if(typeString == gAssetType[i])
		{
			return i;
		}
	}

	return ASSET_TYPE__COUNT;
}

//----------------------------------------------------------------------------------------------------------------------

std::string JoinPath(const std::string_view& left, const std::string_view& right)
{
	if(left.length() == 0 || right.length() == 0)
	{
		return std::string();
	}
	else if(left.length() == 0)
	{
		return std::string(right);
	}
	else if(right.length() == 0)
	{
		return std::string(left);
	}

	std::string output(left);
	output.append(1, PATH_SEP_CHR);
	output.append(right);

	return output;
}

//----------------------------------------------------------------------------------------------------------------------

bool ProcessManifest(const std::string_view& inputFilePath, const std::string_view& outputRootPath)
{
	using namespace LightningJSON;

	assert(inputFilePath.size() > 0);
	assert(outputRootPath.size() > 0);

	// Pre-calculate the asset output paths.
	std::string outputPath[ASSET_TYPE__COUNT];
	for(int i = 0; i < ASSET_TYPE__COUNT; ++i)
	{
		outputPath[i] = NormalizePath(JoinPath(outputRootPath, gOutputSubDirName[i]));
	}

	LOG_INFO_FMT("Loading asset manifest: \"%s\" ...", inputFilePath.data());

	FileBuffer manifestFile;
	if(!FileBuffer::Read(manifestFile, inputFilePath))
	{
		LOG_ERROR_FMT("Failed to load input file: %s", inputFilePath.data());
		return false;
	}

	bool success = true;

	try
	{
		const JSONObject jsonRoot = JSONObject::FromString(std::string_view(reinterpret_cast<char*>(manifestFile.data.get()), manifestFile.length));

		for(const auto childNode : jsonRoot)
		{
			// Only handle objects.
			if(childNode.IsObject())
			{
				const std::string_view nodeName = childNode.GetKey();
				if(!ValidateAssetName(nodeName))
				{
					// Invalid asset name.
					continue;
				}

				if(!childNode.HasKey(gJsonKey[JSON_KEY_TYPE]))
				{
					// Asset node does not specify its type.
					LOG_ERROR_FMT("Asset node missing '%s' field: \"%s\"", gJsonKey[JSON_KEY_TYPE], nodeName.data());
					success = false;
					continue;
				}

				JSONObject typeNode = childNode[gJsonKey[JSON_KEY_TYPE]];
				if(!typeNode.IsString())
				{
					// Asset node type is not a string.
					LOG_ERROR_FMT("Asset node has non-string '%s' field: \"%s\"", gJsonKey[JSON_KEY_TYPE], nodeName.data());
					success = false;
					continue;
				}

				const std::string typeString = typeNode.AsString();

				const int assetType = ResolveAssetType(typeString);
				if(assetType == ASSET_TYPE__COUNT)
				{
					// The asset type is not known.
					LOG_ERROR_FMT("Unknown asset type: \"%s\"", typeString.c_str());
					continue;
				}

				const std::string_view assetOutputPath = outputPath[assetType];

				// TODO: Use the type string to determine which type handler to use.
			}
		}
	}
	catch(const std::exception& e)
	{
		LOG_ERROR_FMT("%s", e.what());
		return false;
	}

	return success;
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
		"ubxpipeline.exe",
#else
		"ubxpipeline",
#endif
		"UltraBox asset pipeline"
	);

	options
		.custom_help("[options...]")
		.positional_help("<input_file>")
		.allow_unrecognised_options();

	// Add the options.
	options.add_options()
		("h,help", "Display this help text")
		("input_file", "File path of the asset manifest", cxxopts::value<std::string>(), "<input_file>")
		("o,output", "Root directory path where the output files will be written to", cxxopts::value<std::string>(), "path")
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

	// Check for the "--output" argument.
	if(args.count("output") == 0)
	{
		LOG_ERROR("Missing required argument: --output");
		return APP_EXIT_FAILURE;
	}

	// Get the output root path from the command line and make sure it's not empty.
	std::string_view outputRootPath = args["output"].as<std::string>();
	if(outputRootPath.size() == 0)
	{
		LOG_ERROR("Output root path is empty");
		return APP_EXIT_FAILURE;
	}

	LOG_INFO_FMT("UbxPipeline v%" PRIu32 ".%" PRIu32 ".%" PRIu32, APP_VERSION_MAJOR, APP_VERSION_MINOR, APP_VERSION_PATCH);

	// Attempt to parse the manifest and cook the assets it lists.
	if(!ProcessManifest(inputFilePath, outputRootPath))
	{
		return APP_EXIT_FAILURE;
	}

	return APP_EXIT_SUCCESS;
}

//----------------------------------------------------------------------------------------------------------------------