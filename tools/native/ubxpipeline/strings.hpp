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
#pragma once

//----------------------------------------------------------------------------------------------------------------------

enum JSON_KEY
{
	JSON_KEY_FILE,
	JSON_KEY_FORMAT,
	JSON_KEY_TYPE,

	JSON_KEY__COUNT,
};

enum ASSET_TYPE
{
	ASSET_TYPE_ANIMATION,
	ASSET_TYPE_MODEL,
	ASSET_TYPE_MUSIC,
	ASSET_TYPE_SFX,
	ASSET_TYPE_TEXTURE,

	ASSET_TYPE__COUNT,
};

//----------------------------------------------------------------------------------------------------------------------

constexpr const char* const gJsonKey[JSON_KEY__COUNT] =
{
	"file",   // JSON_KEY_FILE
	"format", // JSON_KEY_FORMAT
	"type",   // JSON_KEY_TYPE
};

constexpr const char* const gAssetType[ASSET_TYPE__COUNT] =
{
	"animation", // ASSET_TYPE_ANIMATION
	"model",     // ASSET_TYPE_MODEL
	"music",     // ASSET_TYPE_MUSIC
	"sfx",       // ASSET_TYPE_SFX
	"texture",   // ASSET_TYPE_TEXTURE
};

constexpr const char* const gOutputSubDirName[ASSET_TYPE__COUNT] =
{
	"anim",  // ASSET_TYPE_ANIMATION
	"model", // ASSET_TYPE_MODEL
	"music", // ASSET_TYPE_MUSIC
	"sfx",   // ASSET_TYPE_SFX
	"tex",   // ASSET_TYPE_TEXTURE
};

//----------------------------------------------------------------------------------------------------------------------