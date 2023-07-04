/*
 * Copyright (c) 2023, Zoe J. Bare
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
 * documentation files (the "Software"), to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
 * and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all copies or substantial portions
 * of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED
 * TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
 * THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
 * CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
 * IN THE SOFTWARE.
 */
#include <ultra_box.h>

#include <math.h>
#include <string.h>

#include <ultra64.h>

/*--------------------------------------------------------------------------------------------------------------------*/

#ifdef _DISPLAY_HIRES
	#define DISPLAY_WIDTH  640
	#define DISPLAY_HEIGHT 480

	#ifdef _DISPLAY_PAL
		#define DISPLAY_VI_MODE_INDEX OS_VI_PAL_HPN1
	#else
		#define DISPLAY_VI_MODE_INDEX OS_VI_NTSC_HPN1
	#endif

#else
	#define DISPLAY_WIDTH  320
	#define DISPLAY_HEIGHT 240

	#ifdef _DISPLAY_PAL
		#define DISPLAY_VI_MODE_INDEX OS_VI_PAL_LPN1
	#else
		#define DISPLAY_VI_MODE_INDEX OS_VI_NTSC_LPN1
	#endif

#endif

#ifdef _DISPLAY_PAL
	#define DISPLAY_VSYNC_TIME_DELTA (1.0f / 50.0f)

#else
	#define DISPLAY_VSYNC_TIME_DELTA (1.0f / 60.0f)

#endif

#define DISPLAY_HALF_WIDTH  (DISPLAY_WIDTH / 2)
#define DISPLAY_HALF_HEIGHT (DISPLAY_HEIGHT / 2)

#define DISPLAY_BUFFER_COUNT 2

#define GFX_CLEAR_CMD_LENGTH 16
#define GFX_DRAW_CMD_LENGTH  2048

#define CFB_CLEAR_VALUE  GPACK_RGBA5551(0, 16, 16, 1)
#define ZBUF_CLEAR_VALUE GPACK_ZDZ(G_MAXFBZ, 0)

#define M_TAU (M_PI * 2.0f)

/* World coordinate system scale
 *
 * All vertices and transforms must be scaled by this value to be in the same coordinate system.
 * The larger this value is, the greater precision you'll have for fractional vertex positions,
 * but your maximum scene size will be smaller since you've made the trade for better precision.
 *
 * NOTE(1): Remember that vertices are ultimately stored as signed 16-bit integers, so your maximum
 *          and minimum final values (after transformation) are 0x7FFF and 0x8000 respectively with
 *          larger values having a greater likelihood of producting visual artifacts.
 *
 * NOTE(2): If certain objects need much higher precision than others, you could use a larger scale
 *          value for them and the world scale value for objects which are fine with lower precision,
 *          then use a scale matrix to bring the larger objects back down the normal world scale.
 *          This is illustrated here by the use of two seperate world scales, one representing low
 *          precision for the world overall (where all coordinate scales must eventually end up),
 *          and the other representing high precision (split into two values). The 1st high precision
 *          value is applied to object vertex data, the 2nd high precision value would go into a
 *          scaling matrix to bring the object back down to the world scale.
 */
#define COORD_WORLD_SCALE 1.0f
#define COORD_HP1_SCALE   128.0f
#define COORD_HP2_SCALE   (COORD_WORLD_SCALE / COORD_HP1_SCALE)

/* Convert to the world coordinate scale, casting the result to a 16-bit integer (for use with vertex positions). */
#define COORD_AS_VTX(f) (s16)((f32)(f) * COORD_WORLD_SCALE)

/* Convert to the world coordinate scale, leaving the result as a floating point value. */
#define COORD_AS_FLT(f) ((f32)(f) * COORD_WORLD_SCALE)

/* Convert to the 1st stage of the high precision world scale (for use only with vertex positions). */
#define COORD_AS_HP1_VTX(f) (s16)((f32)(f) * COORD_HP1_SCALE)

/* Convert to the 1st stage of the high precision world scale (intended for use with translation matrices applied *before* the matrix). */
#define COORD_AS_HP1_FLT(f) ((f32)(f) * COORD_HP1_SCALE)

/* Convert to the 2nd stage of the high precision world scale (intended for use with scaling matrices). */
#define COORD_AS_HP2_FLT(f) ((f32)(f) * COORD_HP2_SCALE)

#define SET_VTX_POS_V(vtxptr, x, y, z) \
	(vtxptr)->v.ob[0] = (x); \
	(vtxptr)->v.ob[1] = (y); \
	(vtxptr)->v.ob[2] = (z)

#define SET_VTX_POS_N(vtxptr, x, y, z) \
	(vtxptr)->n.ob[0] = (x); \
	(vtxptr)->n.ob[1] = (y); \
	(vtxptr)->n.ob[2] = (z)

#define SET_VTX_TC_V(vtxptr, u, v) \
	(vtxptr)->v.tc[0] = (u); \
	(vtxptr)->v.tc[1] = (v)

#define SET_VTX_TC_N(vtxptr, u, v) \
	(vtxptr)->n.tc[0] = (u); \
	(vtxptr)->n.tc[1] = (v)

#define SET_VTX_COL_V(vtxptr, r, g, b, a) \
	(vtxptr)->v.cn[0] = (r); \
	(vtxptr)->v.cn[1] = (g); \
	(vtxptr)->v.cn[2] = (b); \
	(vtxptr)->v.cn[3] = (a)

#define SET_VTX_NORM_N(vtxptr, nx, ny, nz) \
	(vtxptr)->n.n[0] = (nx); \
	(vtxptr)->n.n[1] = (ny); \
	(vtxptr)->n.n[2] = (nz)

#define SET_VTX_ALPHA_N(vtxptr, a) \
	(vtxptr)-> n.a = (a)

/*--------------------------------------------------------------------------------------------------------------------*/

typedef struct _Transform
{
	Mtx modelView;
	Mtx projection;
} Transform;

typedef struct _GfxState
{
	Gfx clearCmd[GFX_CLEAR_CMD_LENGTH];
	Gfx drawCmd[GFX_DRAW_CMD_LENGTH];

	OSTask clearTask;
	OSTask drawTask;
} GfxState;

typedef struct _FrameState
{
	Transform transform;
} FrameState;

typedef struct _GameState
{
	float movAmt;
	float rotAngle;
	float morphAmt;

	u16 perspNorm;
} GameState;

/*--------------------------------------------------------------------------------------------------------------------*/

u16 gFrameBuffer[DISPLAY_BUFFER_COUNT][DISPLAY_WIDTH * DISPLAY_HEIGHT] __attribute__((aligned(0x10)));
u16 gDepthBuffer[DISPLAY_WIDTH * DISPLAY_HEIGHT] __attribute__((aligned(0x10)));
u64 gDramStack[SP_DRAM_STACK_SIZE64] __attribute__((aligned(0x10)));

size_t gDrawBufferIndex = 0;

GfxState gGfxState[DISPLAY_BUFFER_COUNT];
FrameState gFrameState[DISPLAY_BUFFER_COUNT];

GameState gGameState;

/*--------------------------------------------------------------------------------------------------------------------*/

static const Vp gDisplayViewport =
{
	.vp =
	{
		{ DISPLAY_WIDTH << 1, DISPLAY_HEIGHT << 1, G_MAXZ >> 1, 0 },
		{ DISPLAY_WIDTH << 1, DISPLAY_HEIGHT << 1, G_MAXZ >> 1, 0 },
	},
};

static const Gfx rcpInitDlist[] =
{
	/* Setup the segments. */
	gsSPSegment(0, 0),

	/* Initialize the RSP. */
	gsSPClearGeometryMode(G_ZBUFFER
		| G_SHADE
		| G_SHADING_SMOOTH
		| G_CULL_BOTH
		| G_FOG
		| G_LIGHTING
		| G_TEXTURE_GEN
		| G_TEXTURE_GEN_LINEAR
		| G_LOD
		| G_CLIPPING),
	gsSPSetGeometryMode(G_ZBUFFER | G_CLIPPING),
	gsSPTexture(0, 0, 0, 0, G_OFF),
	gsSPViewport(&gDisplayViewport),

	/* Initialize the RDP. */
	gsDPPipelineMode(G_PM_NPRIMITIVE),
	gsDPSetScissor(G_SC_NON_INTERLACE, 0, 0, DISPLAY_WIDTH - 1, DISPLAY_HEIGHT - 1),
	gsDPSetTextureLOD(G_TL_TILE),
	gsDPSetTextureLUT(G_TT_NONE),
	gsDPSetTextureDetail(G_TD_CLAMP),
	gsDPSetTexturePersp(G_TP_PERSP),
	gsDPSetTextureFilter(G_TF_BILERP),
	gsDPSetTextureConvert(G_TC_FILT),
	gsDPSetCombineKey(G_CK_NONE),
	gsDPSetAlphaCompare(G_AC_NONE),
	gsDPSetColorDither(G_CD_DISABLE),
	gsDPSetPrimColor(0, 0, 0, 0, 64, 255),

	/* Wait for the RDP state setup to complete. */
	gsDPPipeSync(),

	/* Signal the end of this display list. */
	gsSPEndDisplayList(),
};

static Vtx gQuadVtx[DISPLAY_BUFFER_COUNT][4];

/*--------------------------------------------------------------------------------------------------------------------*/

void OnGameBoot()
{
	// Set the VI mode index to the value determined by our build settings.
	gUbxVideo.viModeIndex = DISPLAY_VI_MODE_INDEX;

	const OSTask defaultGfxTask =
	{
		.t =
		{
			.type = M_GFXTASK,
			.flags = OS_TASK_DP_WAIT,
			.ucode_boot = NULL,
			.ucode_boot_size = 0,
			.ucode = NULL,
			.ucode_size = 0,
			.ucode_data = NULL,
			.ucode_data_size = 0,
			.dram_stack = gDramStack,
			.dram_stack_size = SP_DRAM_STACK_SIZE8,
			.output_buff = NULL,
			.output_buff_size = 0,
			.data_ptr = NULL,
			.data_size = 0,
			.yield_data_ptr = NULL,
			.yield_data_size = 0,
		},
	};

	for(size_t i = 0; i < DISPLAY_BUFFER_COUNT; ++i)
	{
		gGfxState[i].clearTask = defaultGfxTask;
		gGfxState[i].drawTask = defaultGfxTask;

		/* Set the static micro-code for the gfx clear task. */
		UBX_TASK_SET_BOOT_UCODE(&gGfxState[i].clearTask, (u64*) rspbootTextStart, (u64*) rspbootTextEnd);
		UBX_TASK_SET_RSP_UCODE(&gGfxState[i].clearTask, (u64*) gspF3DEX2_xbusTextStart, (u64*) gspF3DEX2_xbusTextEnd);
		UBX_TASK_SET_RSP_UCODE_DATA(&gGfxState[i].clearTask, (u64*) gspF3DEX2_xbusDataStart, (u64*) gspF3DEX2_xbusDataEnd);

		/* Set the static micro-code for the gfx draw task. */
		UBX_TASK_SET_BOOT_UCODE(&gGfxState[i].drawTask, (u64*) rspbootTextStart, (u64*) rspbootTextEnd);
		UBX_TASK_SET_RSP_UCODE(&gGfxState[i].drawTask, (u64*) gspF3DEX2_xbusTextStart, (u64*) gspF3DEX2_xbusTextEnd);
		UBX_TASK_SET_RSP_UCODE_DATA(&gGfxState[i].drawTask, (u64*) gspF3DEX2_xbusDataStart, (u64*) gspF3DEX2_xbusDataEnd);
	}
}

/*--------------------------------------------------------------------------------------------------------------------*/

void OnGameInitialize()
{
	const Vtx defaultQuadVtx[4] =
	{
		{ .v = { { 0, 0, 0 }, 0,  {       (0),        (0) },  { 0xFF, 0x00, 0x00, 0xFF } } },
		{ .v = { { 0, 0, 0 }, 0,  { (31 << 6),        (0) },  { 0x00, 0xFF, 0x00, 0xFF } } },
		{ .v = { { 0, 0, 0 }, 0,  {       (0), (127 << 6) },  { 0x00, 0x00, 0xFF, 0xFF } } },
		{ .v = { { 0, 0, 0 }, 0,  { (31 << 6), (127 << 6) },  { 0xFF, 0xFF, 0x00, 0xFF } } },
	};

	for(size_t i = 0; i < DISPLAY_BUFFER_COUNT; ++i)
	{
		/* Initialize the quad vertex data. */
		memcpy(gQuadVtx[i], defaultQuadVtx, sizeof(defaultQuadVtx));
	}

	/* Initialize the game state. */
	memset(&gGameState, 0, sizeof(GameState));

	/* Do an initial buffer swap so there is a vertical retrace to wait on when we get to the main loop. */
	osViSwapBuffer(gFrameBuffer[1]);
}

/*--------------------------------------------------------------------------------------------------------------------*/

/* Forward declare the game main loop functions. */
void _OnGameNewFrame();
void _OnGameUpdate();
void _OnGameRender();

__attribute__((noreturn)) void OnGameMainLoop(void*)
{
	/* Main loop */
	for(;;)
	{
		_OnGameNewFrame();
		_OnGameUpdate();
		_OnGameRender();
	}

	__builtin_unreachable();
}

/*--------------------------------------------------------------------------------------------------------------------*/

void _OnGameNewFrame()
{
	GfxState* pGfxState = &gGfxState[gDrawBufferIndex];

	/* Setup the gfx display list for clearing the display buffers; start this as early in the frame as possible
	 * to give the RCP time to work on it while we update the game and prepare the 'draw scene' display list. */
	{
		UBX_GFX_CMD_USE(pGfxState->clearCmd);

		/* Initialize the RDP to its default state. */
		gSPDisplayList(UBX_GFX_CMD_NEXT, rcpInitDlist);

		/* Clear the active frame buffer and the depth buffer. */
		{
			gDPSetCycleType(UBX_GFX_CMD_NEXT, G_CYC_FILL);

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Warray-bounds"
			/* Depth buffer */
			gDPSetColorImage(UBX_GFX_CMD_NEXT, G_IM_FMT_RGBA, G_IM_SIZ_16b, DISPLAY_WIDTH, OS_K0_TO_PHYSICAL(gDepthBuffer));
			gDPSetFillColor(UBX_GFX_CMD_NEXT, ZBUF_CLEAR_VALUE | (ZBUF_CLEAR_VALUE << 16));
			gDPFillRectangle(UBX_GFX_CMD_NEXT, 0, 0, DISPLAY_WIDTH, DISPLAY_HEIGHT - 1);
#pragma GCC diagnostic pop

			/* Frame buffer (this is only an example; in a real game, you should be drawing to the entire frame buffer, making this unnessary) */
			gDPSetColorImage(UBX_GFX_CMD_NEXT, G_IM_FMT_RGBA, G_IM_SIZ_16b, DISPLAY_WIDTH, OS_K0_TO_PHYSICAL(gFrameBuffer[gDrawBufferIndex]));
			gDPSetFillColor(UBX_GFX_CMD_NEXT, CFB_CLEAR_VALUE | (CFB_CLEAR_VALUE << 16));
			gDPFillRectangle(UBX_GFX_CMD_NEXT, 0, 0, DISPLAY_WIDTH - 1, DISPLAY_HEIGHT - 1);

			/* Set the depth buffer */
			gDPSetDepthImage(UBX_GFX_CMD_NEXT, OS_K0_TO_PHYSICAL(gDepthBuffer));
		}

		/* Finalize the clear command list for this frame. */
		gDPFullSync(UBX_GFX_CMD_NEXT);
		gSPEndDisplayList(UBX_GFX_CMD_NEXT);

		/* Bind the current gfx command list to the gfx clear task. */
		UBX_TASK_SET_DATA(&pGfxState->clearTask, UBX_GFX_CMD_LIST_HEAD, UBX_GFX_CMD_LIST_TAIL);

		/* Write back the updated command buffer to physical memory. */
		osWritebackDCache(pGfxState->clearTask.t.data_ptr, pGfxState->clearTask.t.data_size);

		/* Launch the gfx clear task. */
		osSpTaskStart(&pGfxState->clearTask);
	}
}

/*--------------------------------------------------------------------------------------------------------------------*/

void _OnGameUpdate()
{
	FrameState* pFrameState = &gFrameState[gDrawBufferIndex];
	Vtx* pQuadVtx = gQuadVtx[gDrawBufferIndex];

	/* Update the object movement value. */
	gGameState.movAmt += 0.2185f * DISPLAY_VSYNC_TIME_DELTA;
	if(gGameState.movAmt > M_TAU)
	{
		gGameState.movAmt -= M_TAU;
	}

	/* Update the object rotation. */
	gGameState.rotAngle += 0.7316f * DISPLAY_VSYNC_TIME_DELTA;
	if(gGameState.rotAngle > M_TAU)
	{
		gGameState.rotAngle -= M_TAU;
	}

	/* Update the object morph value. */
	gGameState.morphAmt -= 1.4823f * DISPLAY_VSYNC_TIME_DELTA;
	if(gGameState.morphAmt < 0.0f)
	{
		gGameState.morphAmt += M_TAU;
	}

#if 0
	const s16 ulx = COORD_AS_HP1_VTX(-1.0f);
	const s16 uly = COORD_AS_HP1_VTX(1.0);
	const s16 lrx = COORD_AS_HP1_VTX(1.0f);
	const s16 lry = COORD_AS_HP1_VTX(-1.0f);
#else
	const f32 verticalMorph = sinf(gGameState.morphAmt) * 0.7f;
	const f32 horizontalMorph = cosf(gGameState.morphAmt) * 0.5f;

	const s16 ulx = COORD_AS_HP1_VTX(-1.0f + horizontalMorph);
	const s16 uly = COORD_AS_HP1_VTX(1.0f + verticalMorph);
	const s16 lrx = COORD_AS_HP1_VTX(1.0f + -horizontalMorph);
	const s16 lry = COORD_AS_HP1_VTX(-1.0f);
#endif

	/* Update the vertex positions. */
	SET_VTX_POS_V(&pQuadVtx[0], ulx, uly, 0);
	SET_VTX_POS_V(&pQuadVtx[1], lrx, uly, 0);
	SET_VTX_POS_V(&pQuadVtx[2], ulx, lry, 0);
	SET_VTX_POS_V(&pQuadVtx[3], lrx, lry, 0);

	/* Write back the vertex data from the cache to physical memory. */
	osWritebackDCache(pQuadVtx, sizeof(Vtx) * 4);

	Mtx transMtx;
	Mtx rotMtx;
	Mtx scaleMtx;
	Mtx viewMtx;

	/* Calculate world transform matrices. */
	guTranslateF(&transMtx, COORD_AS_FLT(sinf(gGameState.rotAngle)), 0.0f, 0.0f);
	guRotateF(&rotMtx, gGameState.rotAngle / M_TAU * 360.0f, 0.0f, 1.0f, 0.0f);
	guScaleF(&scaleMtx, COORD_AS_HP2_FLT(1.0f), COORD_AS_HP2_FLT(1.0f), COORD_AS_HP2_FLT(1.0f));

	/* Calculate the view matrix. */
	guLookAtF(
		&viewMtx,
		0.0f, 0.0f, COORD_AS_FLT(2.5f),
		0.0f, 0.0f, 0.0f,
		0.0f, 1.0f, 0.0f);

	/* Calculate the final model-view matrix. */
	guMtxCatF(&scaleMtx, &rotMtx, &rotMtx);
	guMtxCatF(&rotMtx, &transMtx, &transMtx);
	guMtxCatF(&transMtx, &viewMtx, &viewMtx);
	guMtxF2L(&viewMtx, &pFrameState->transform.modelView);

	/* Create the projection matrix. */
	guPerspective(
		&pFrameState->transform.projection,
		&gGameState.perspNorm,
		80.0f,
		(f32) DISPLAY_WIDTH / (f32) DISPLAY_HEIGHT,
		COORD_AS_FLT(0.01f), COORD_AS_FLT(10.0f),
		1.0f);

	/* Write back the frame transform data from the cache to physical memory. */
	osWritebackDCache(&pFrameState->transform, sizeof(Transform));
}

/*--------------------------------------------------------------------------------------------------------------------*/

void _OnGameRender()
{
	GfxState* pGfxState = &gGfxState[gDrawBufferIndex];
	FrameState* pFrameState = &gFrameState[gDrawBufferIndex];
	Vtx* pQuadVtx = gQuadVtx[gDrawBufferIndex];

	/* Setup the gfx display list for drawing the scene. */
	{
		UBX_GFX_CMD_USE(pGfxState->drawCmd);

		/* Initialize the RDP to its default state. */
		gSPDisplayList(UBX_GFX_CMD_NEXT, rcpInitDlist);


		/* Set the frame transforms. */
		gSPPerspNormalize(UBX_GFX_CMD_NEXT, gGameState.perspNorm);
		gSPMatrix(UBX_GFX_CMD_NEXT, OS_K0_TO_PHYSICAL(&pFrameState->transform.projection), G_MTX_PROJECTION | G_MTX_LOAD | G_MTX_NOPUSH);
		gSPMatrix(UBX_GFX_CMD_NEXT, OS_K0_TO_PHYSICAL(&pFrameState->transform.modelView), G_MTX_MODELVIEW | G_MTX_LOAD | G_MTX_NOPUSH);

		/* Set the default texture state. */
		gDPSetTextureFilter(UBX_GFX_CMD_NEXT, G_TF_BILERP);
		gDPSetTexturePersp(UBX_GFX_CMD_NEXT, G_TP_PERSP);
		gDPSetTextureDetail(UBX_GFX_CMD_NEXT, G_TD_CLAMP);
		gDPSetTextureLOD(UBX_GFX_CMD_NEXT, G_TL_TILE);
		gDPSetTextureLUT(UBX_GFX_CMD_NEXT, G_TT_NONE);

		/* Set the geometry rasterizer state. */
		gSPSetGeometryMode(UBX_GFX_CMD_NEXT, G_SHADE | G_SHADING_SMOOTH /*| G_CULL_BACK*/);
		gDPSetCycleType(UBX_GFX_CMD_NEXT, G_CYC_1CYCLE);
		gDPSetRenderMode(UBX_GFX_CMD_NEXT, G_RM_ZB_XLU_SURF, G_RM_ZB_XLU_SURF2);
		gDPSetCombineMode(UBX_GFX_CMD_NEXT, G_CC_SHADE, G_CC_SHADE);
		gDPPipeSync(UBX_GFX_CMD_NEXT);

		/* Draw the quad (triangle front faces are counter-clockwise). */
		gSPVertex(UBX_GFX_CMD_NEXT, pQuadVtx, 4, 0);
		gSP1Triangle(UBX_GFX_CMD_NEXT, 0, 2, 1, 0);
		gSP1Triangle(UBX_GFX_CMD_NEXT, 1, 2, 3, 0);

		/* Finalize the display list. */
		gDPFullSync(UBX_GFX_CMD_NEXT);
		gSPEndDisplayList(UBX_GFX_CMD_NEXT);

		/* Bind the current gfx command list to the gfx draw task. */
		UBX_TASK_SET_DATA(&pGfxState->drawTask, UBX_GFX_CMD_LIST_HEAD, UBX_GFX_CMD_LIST_TAIL);

		/* Write back the updated command buffer to physical memory. */
		osWritebackDCache(pGfxState->drawTask.t.data_ptr, pGfxState->drawTask.t.data_size);

		/* Wait for RDP to finish the 'clear buffers' task before launching the 'draw scene' task. */
		osRecvMesg(&gUbxSystem.rdpMsgQueue, NULL, OS_MESG_BLOCK);

		/* Launch the gfx draw task. */
		osSpTaskStart(&pGfxState->drawTask);
	}

	/* Wait for RDP to complete its current workload. */
	osRecvMesg(&gUbxSystem.rdpMsgQueue, NULL, OS_MESG_BLOCK);

	/* Flip the frame buffer */
	osViSwapBuffer(gFrameBuffer[gDrawBufferIndex]);

	/* Wait for the vertical retrace to complete (this is effectively waiting on vsync). */
	osRecvMesg(&gUbxVideo.retraceMsgQueue, NULL, OS_MESG_BLOCK);

	gDrawBufferIndex ^= 1;
}

/*--------------------------------------------------------------------------------------------------------------------*/
