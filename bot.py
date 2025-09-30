import discord
from discord.ext import commands
from huggingface_hub import InferenceClient
import json
import os
from dotenv import load_dotenv

# --- LOAD SECRETS ---
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

# --- HUGGING FACE CLIENT (Mistral-7B-Instruct) ---
hf_client = InferenceClient("mistralai/Mistral-7B-Instruct", token=HF_TOKEN)

# --- KNOWLEDGE BASE ---
if os.path.exists("knowledge.json"):
    with open("knowledge.json", "r") as f:
        knowledge = json.load(f)
else:
    knowledge = []

def save_knowledge():
    with open("knowledge.json", "w") as f:
        json.dump(knowledge, f, indent=2)

# --- DISCORD SETUP ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"🤖 Logged in as {bot.user}")

# --- STAFF COMMAND TO TEACH BOT ---
@bot.command()
async def learn(ctx, *, info):
    """Staff teaches the bot something"""
    # Only trigger if bot was pinged OR this message is a reply to the bot
    if not (bot.user.mentioned_in(ctx.message) or 
            (ctx.message.reference and ctx.message.reference.resolved and ctx.message.reference.resolved.author == bot.user)):
        return

    if ctx.author.guild_permissions.administrator:  # only admins can teach
        knowledge.append(info)
        save_knowledge()
        await ctx.send(f"✅ Learned: {info}")
    else:
        await ctx.send("❌ Only staff can teach me.")

# --- AUTO-REPLY (Pinged or Replied) ---
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    is_reply_to_bot = (
        message.reference
        and message.reference.resolved
        and message.reference.resolved.author == bot.user
    )

    if bot.user.mentioned_in(message) or is_reply_to_bot:
        user_question = message.content.replace(f"<@{bot.user.id}>", "").strip()

        if not user_question:
            await message.channel.send("👋 Hi! Ask me something about your Minecraft hosting.")
            return

        # Check saved knowledge first
        for fact in knowledge:
            if any(word.lower() in user_question.lower() for word in fact.split()):
                await message.channel.send(f"📘 {fact}")
                return

        # If nothing matches, ask Hugging Face
        try:
            knowledge_text = "\n".join(knowledge)
            prompt = f"""You are a helpful support bot for a Minecraft hosting company.
Here is what staff has taught you:
{knowledge_text}

Now answer this question from a customer:
{user_question}
"""
            response = hf_client.text_generation(
                prompt,
                max_new_tokens=200,
                do_sample=True,
                temperature=0.6,
            )
            await message.channel.send(response[:1900])  # Discord limit
        except Exception as e:
            await message.channel.send("⚠️ Something went wrong with the AI request.")
            print(e)

    await bot.process_commands(message)

# --- RUN BOT ---
bot.run(DISCORD_TOKEN)
