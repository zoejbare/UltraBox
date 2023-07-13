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

#include "file_buffer.hpp"

#include <assert.h>
#include <stdio.h>

//----------------------------------------------------------------------------------------------------------------------

bool FileBuffer::Read(
	FileBuffer& output,
	const std::string_view& filePath,
	const size_t minSize,
	const size_t padAlign,
	const uint8_t fillByte)
{
	// Open the file with binary read-only access.
	FILE* const pFile = fopen(filePath.data(), "rb");
	if(!pFile)
	{
		// The file could not be opened.
		return false;
	}

	// Get the total size of the file.
	fseek(pFile, 0, SEEK_END);
	const size_t fileSize = ftell(pFile);
	fseek(pFile, 0, SEEK_SET);

	if(fileSize == 0)
	{
		// The file is empty.
		return false;
	}

	// Determine the size of the file data buffer, padding it
	// up to the minimum size if the file itself is too small.
	size_t paddedFileSize = (fileSize < minSize) ? minSize : fileSize;

	if(padAlign > 0)
	{
		// Round the padded size up to the nearest megabit.
		paddedFileSize = (paddedFileSize + (padAlign - 1)) & ~(padAlign - 1);
	}

	// Instantiate the output file buffer.
	output.data = std::make_unique<uint8_t[]>(paddedFileSize);
	output.length = paddedFileSize;

	if(fileSize < paddedFileSize)
	{
		// Fill the padded section at the end of the file buffer with some known value;
		// what the value is doesn't matter, but the value itself will be needed for
		// computing a deterministic CRC hash of the ROM file later.
		memset(output.data.get() + fileSize, fillByte, paddedFileSize - fileSize);
	}

	// Read the contents of the file to the buffer.
	const size_t elementsRead = fread(output.data.get(), fileSize, 1, pFile);
	assert(elementsRead == 1); (void) elementsRead;

	// Close the file now that we have its data in memory.
	fclose(pFile);

	return true;
}

//----------------------------------------------------------------------------------------------------------------------

bool FileBuffer::Write(const std::string_view& filePath, const FileBuffer& buffer)
{
	// Open the file with binary write access.
	FILE* const pFile = fopen(filePath.data(), "wb");
	if(!pFile)
	{
		// The file could not be opened.
		return false;
	}

	// Write the buffer contents into the file.
	fwrite(buffer.data.get(), buffer.length, 1, pFile);
	fclose(pFile);

	return true;
}

//----------------------------------------------------------------------------------------------------------------------
