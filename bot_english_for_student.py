import discord
from discord.ext import commands
import logging
import asyncio
import os
from flask import Flask
from threading import Thread
from google import genai

# ==============================================================================
# 1. CẤU HÌNH WEB SERVER ẨN (Để Render/Koyeb không cho Bot ngủ)
# ==============================================================================
app = Flask('')

@app.route('/')
def home():
    return "Bot đang chạy ổn định 24/7!"

def run_server():
    # Render/Koyeb sẽ tự cấp PORT thông qua biến môi trường, mặc định là 8080
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_server)
    t.start()


# ==============================================================================
# 2. CẤU HÌNH LOGGING & DISCORD BOT
# ==============================================================================
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w') 
logging.basicConfig(level=logging.INFO, handlers=[handler])

intents = discord.Intents.default()
intents.message_content = True

client = commands.Bot(command_prefix='!', intents=intents)


# ==============================================================================
# 3. LỚP XỬ LÝ GEMINI API (google-genai SDK)
# ==============================================================================
class GeminiAPI:
    def __init__(self, api_key):
        # Khởi tạo client chính thức
        self.client = genai.Client(api_key=api_key)
        self.model_name = 'gemini-2.5-flash'

    def translate(self, word):
        prompt = f"Dịch từ tiếng Anh này sang tiếng Việt, chỉ trả về kết quả dịch ngắn gọn: {word}"
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt
        )
        return response.text.strip()

    def find_stress(self, word):
        prompt = f"Xác định trọng âm của từ tiếng Anh '{word}'. Chỉ ra trọng âm rơi vào âm tiết thứ mấy và viết phiên âm có đánh dấu trọng âm rõ ràng."
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt
        )
        return response.text.strip()

    def close(self):
        # SDK mới tự quản lý connection pool, không cần đóng thủ công
        pass


# ==============================================================================
# 4. SỰ KIỆN & LỆNH CỦA DISCORD BOT
# ==============================================================================
@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

@client.command() 
async def learn(ctx):
    await ctx.send('Hello, I am a bot for student to learn english!')
    await ctx.send('I can help you to learn english by using the command !learn') 
    await ctx.send('Please input the word you want to learn:')
    
    # Kiểm tra tin nhắn phản hồi phải trùng khớp tác giả và kênh chat
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        # Chờ phản hồi trong 30 giây, quá giờ sẽ tự hủy lệnh
        word_msg = await client.wait_for('message', check=check, timeout=30.0)
    except asyncio.TimeoutError:
        return await ctx.send('Quá thời gian phản hồi (30s). Vui lòng gõ lại `!learn`.')

    word = word_msg.content.strip()
    await ctx.send(f'You input the word: {word}')
    await ctx.send(f'The word is: {word}')
    
    # Lấy API Key từ biến môi trường của hệ thống/hệ điều hành
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        return await ctx.send("Lỗi: Chưa cấu hình biến môi trường GEMINI_API_KEY!")

    # Khởi tạo và gọi API dịch thuật + tìm trọng âm
    gemini_api = GeminiAPI(api_key=gemini_key)
    
    try:
        translation = gemini_api.translate(word)
        await ctx.send('The translation is:\n' + translation)
        
        stress = gemini_api.find_stress(word)
        await ctx.send('The stress of the word is:\n' + stress)
    except Exception as e:
        logging.error(f"Lỗi API Gemini: {e}")
        await ctx.send("Có lỗi xảy ra khi xử lý dữ liệu từ Gemini API.")
    finally:
        gemini_api.close()


# ==============================================================================
# 5. KÍCH HOẠT BOT VÀ SERVER
# ==============================================================================
if __name__ == "__main__":
    # Lấy Discord Token từ biến môi trường
    discord_token = os.environ.get("DISCORD_TOKEN")
    
    if not discord_token:
        print("Lỗi: Chưa cấu hình biến môi trường DISCORD_TOKEN!")
    else:
        # Chạy Web Server ẩn trước để giữ môi trường Live
        keep_alive()
        # Khởi chạy Discord Bot
        client.run(discord_token, log_handler=handler)