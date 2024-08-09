-- CreateTable
CREATE TABLE "ImageMonitor" (
    "id" SERIAL NOT NULL,
    "guild" BIGINT NOT NULL,
    "from_channel" BIGINT NOT NULL,
    "to_channel" BIGINT NOT NULL,
    "success_msg" TEXT DEFAULT 'Image moved successfully',
    "limit" INTEGER NOT NULL DEFAULT 1,

    CONSTRAINT "ImageMonitor_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "GuildConfig" (
    "id" SERIAL NOT NULL,
    "guild" BIGINT NOT NULL,
    "guild_log" BIGINT,
    "time_zone" TEXT DEFAULT 'UTC',

    CONSTRAINT "GuildConfig_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "ImageMonitor_from_channel_key" ON "ImageMonitor"("from_channel");

-- CreateIndex
CREATE INDEX "ImageMonitor_guild_idx" ON "ImageMonitor"("guild");

-- CreateIndex
CREATE UNIQUE INDEX "GuildConfig_guild_key" ON "GuildConfig"("guild");

-- CreateIndex
CREATE INDEX "GuildConfig_guild_idx" ON "GuildConfig"("guild");
