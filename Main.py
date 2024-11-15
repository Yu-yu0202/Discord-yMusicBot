import discord
from discord.ext import commands
import yt_dlp
import asyncio
import random
from pydub import AudioSegment
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = '!'

bot = commands.Bot(command_prefix=PREFIX)

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl_format_options = {
    'format': 'bestaudio/best',
    'noplaylist': False,
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class MusicQueue:
    def __init__(self):
        self.queue = []
        self.loop = False
        self.shuffle_mode = False

    def add(self, track):
        self.queue.append(track)

    def get_next(self):
        if self.shuffle_mode:
            return random.choice(self.queue)
        return self.queue.pop(0) if self.queue else None

    def get_previous(self):
        if len(self.queue) > 1:
            return self.queue[-2]
        return None

    def toggle_loop(self):
        self.loop = not self.loop

    def toggle_shuffle(self):
        self.shuffle_mode = not self.shuffle_mode

    def is_empty(self):
        return len(self.queue) == 0

music_queue = MusicQueue()

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            songs = data['entries']
            for song in songs:
                music_queue.add(song)
            return cls(discord.FFmpegPCMAudio(songs[0]['url'], **ffmpeg_options), data=songs[0])
        
        return cls(discord.FFmpegPCMAudio(data['url'], **ffmpeg_options), data=data)

def check_queue(ctx):
    if music_queue.loop and not music_queue.is_empty():
        next_song = music_queue.get_next()
        player = discord.FFmpegPCMAudio(next_song['url'], **ffmpeg_options)
        ctx.voice_client.play(player, after=lambda e: check_queue(ctx))
    elif not music_queue.is_empty():
        next_song = music_queue.get_next()
        player = discord.FFmpegPCMAudio(next_song['url'], **ffmpeg_options)
        ctx.voice_client.play(player, after=lambda e: check_queue(ctx))

@bot.command(name='play', help='URLまたはプレイリストから音楽を再生します')
async def play(ctx, url):
    async with ctx.typing():
        player = await YTDLSource.from_url(url, loop=bot.loop)
        
        if not ctx.voice_client.is_playing():
            ctx.voice_client.play(player, after=lambda e: check_queue(ctx))
            await ctx.send(f'Now playing: {player.title}')
        else:
            await ctx.send(f'Added to queue: {player.title}')

@bot.command(name='skip', help='次の曲にスキップします')
async def skip(ctx):
    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()

@bot.command(name='previous', help='前の曲に戻ります')
async def previous(ctx):
    prev_song = music_queue.get_previous()
    if prev_song:
        player = discord.FFmpegPCMAudio(prev_song['url'], **ffmpeg_options)
        ctx.voice_client.play(player, after=lambda e: check_queue(ctx))
        await ctx.send(f'Now playing previous song: {prev_song["title"]}')
    else:
        await ctx.send("No previous song in the queue.")

@bot.command(name='volume', help='音量を調整します (0-100)')
async def volume(ctx, volume: int):
    if ctx.voice_client.source:
        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f'Volume set to {volume}%')

@bot.command(name='bassboost', help='ベースブースト（低音強調）を適用します')
async def bassboost(ctx):
    if ctx.voice_client.is_playing():
        audio_segment = AudioSegment.from_file("current_audio_file.mp3")
        
        bass_boosted_audio = audio_segment.low_pass_filter(100).apply_gain(10)

@bot.command(name='equalizer', help='イコライザー設定 (例: !equalizer bass mid treble)')
async def equalizer(ctx, bass: int, mid: int, treble: int):
    if ctx.voice_client.is_playing():
        audio_segment = AudioSegment.from_file("current_audio_file.mp3")
        
        eq_audio = audio_segment.low_pass_filter(100).apply_gain(bass) \
                    .band_pass_filter(500).apply_gain(mid) \
                    .high_pass_filter(5000).apply_gain(treble)

@bot.command(name='join', help='ボイスチャンネルに参加します')
async def join(ctx):
    if not ctx.author.voice:
        await ctx.send("ボイスチャンネルに接続してください")
        return
    channel = ctx.author.voice.channel
    await channel.connect()

@bot.command(name='leave', help='ボイスチャンネルから退出します')
async def leave(ctx):
    await ctx.voice_client.disconnect()

@bot.command(name='queue', help='現在の再生キューを表示します')
async def show_queue(ctx):
    if music_queue.is_empty():
        await ctx.send("Queue is empty!")
    else:
        queue_list = '\n'.join([f"{i+1}. {track['title']}" for i, track in enumerate(music_queue.queue)])
        await ctx.send(f"Current Queue:\n{queue_list}")

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

bot.run(TOKEN)