import discord
import requests
import asyncio
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from keep_alive import keep_alive

# Ładowanie zmiennych środowiskowych z pliku .env
load_dotenv()

# Token bota Discorda zmienna środowiskowa
TOKEN = os.getenv("DISCORD_TOKEN")

# Adres URL API z danymi o halvingu Bitcoin zmienna środowiskowa
API_URL = os.getenv("API_URL")

# ID kanału głosowego, którego nazwa będzie aktualizowana
VOICE_CHANNEL_ID = int(os.getenv("DISCORD_VOICE_CHANNEL_ID"))

# ID kanału, na którym bot będzie wysyłał wiadomość przy 10 minutach pozostałych
ALERT_CHANNEL_ID = int(os.getenv("DISCORD_ALERT_CHANNEL_ID"))

# Flaga kontrolująca, czy wiadomość alertowa została już wysłana
alert_sent = False


# Funkcja do pobierania daty następnego halvingu Bitcoin z API, uwzględniająca GMT+2
async def get_halving_date():
    response = requests.get(API_URL)
    data = response.json()
    bitcoin_data = data['data']['bitcoin']
    halving_date_utc = datetime.strptime(bitcoin_data['halvening_time'], '%Y-%m-%d %H:%M:%S')
    
    # Dodajemy dwie godziny do daty UTC, aby przekształcić ją do GMT+2
    halving_date_gmt2 = halving_date_utc + timedelta(hours=0)
    
    return halving_date_gmt2



# Funkcja zmieniająca status bota na niestandardowy
async def ustaw_status(client, status):
  await client.change_presence(activity=discord.CustomActivity(
      type=discord.ActivityType.custom, name=status))


# Funkcja do aktualizowania statusu bota
async def update_status(client):
  global alert_sent  # Użyj zmiennej globalnej do śledzenia, czy alert został wysłany
  while True:
    halving_date = await get_halving_date()
    now = datetime.utcnow()
    time_remaining = halving_date - now

    days = time_remaining.days
    hours, remainder = divmod(time_remaining.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    status_message = f"{minutes} minut"
    await ustaw_status(client, status_message)

    # Sprawdzamy, czy pozostało dokładnie 10 minut
    if time_remaining <= timedelta(minutes=10) and not alert_sent:
      # Pobieramy kanał alertowy
      alert_channel = client.get_channel(ALERT_CHANNEL_ID)
      if alert_channel:
        await alert_channel.send("@here Pozostało około 10 minut do halvingu!")
        alert_sent = True  # Ustaw flagę, że alert został wysłany

    # Aktualizacja co 10 sekund
    await asyncio.sleep(10)


# Funkcja do aktualizowania nazwy kanału co 60 sekund
async def update_channel(client):
  voice_channel = client.get_channel(VOICE_CHANNEL_ID)
  while True:
    # Pobieramy aktualną liczbę bloków pozostałych do halvingu
    response = requests.get(API_URL)
    data = response.json()
    bitcoin_data = data['data']['bitcoin']
    blocks_remaining = bitcoin_data['blocks_left']

    # Edytujemy nazwę kanału głosowego, aby wyświetlała liczbę bloków
    await voice_channel.edit(name=f"Blocks Remaining: {blocks_remaining}")

    # Oczekujemy 60 sekund przed kolejną aktualizacją
    await asyncio.sleep(60)


# Funkcja do uruchomienia bota
async def start_bot():
  intents = discord.Intents.default()  # Inicjalizacja domyślnych intencji
  client = discord.Client(intents=intents)

  @client.event
  async def on_ready():
    print('Bot został uruchomiony.')
    # Po uruchomieniu bota, uruchamiamy pętle aktualizującą status
    asyncio.create_task(update_status(client))
    # Uruchamiamy pętlę aktualizującą nazwę kanału
    asyncio.create_task(update_channel(client))

  @client.event
  async def on_message(message):
    if message.author.bot:
      return

    if client.user in message.mentions:
      halving_date = await get_halving_date()
      now = datetime.utcnow()
      time_remaining = halving_date - now

      if time_remaining.total_seconds() < 0:
        await message.channel.send("Halving już nastąpił.")
      else:
        days = time_remaining.days
        hours, remainder = divmod(time_remaining.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        time_remaining_str = f"{minutes} minut"
        await message.channel.send(
            f"Bitcoin Halving Countdown: **{time_remaining_str}**")

  await client.start(TOKEN)


keep_alive()

# Uruchamiamy bota
asyncio.run(start_bot())

