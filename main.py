import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from scopa import ScopaGame
from io import BytesIO
from PIL import Image
import random

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Configurazione
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Variabili globali
game_sessions = {}
PERDENTE_ROLE_NAME = "Scopa Perdente"
CARD_WIDTH = 180  # Larghezza base per ogni carta
CARD_SPACING = 15  # Spazio nero tra le carte in pixel
MAX_CARDS_PER_ROW = 4  # Numero massimo di carte per riga
BG_COLOR = (0, 0, 0)  # Nero
CARD_CORNER_RADIUS = 15  # Arrotondamento angoli

async def add_corners(im, rad):
    """Aggiunge angoli arrotondati alle immagini delle carte"""
    circle = Image.new('L', (rad * 2, rad * 2), 0)
    alpha = Image.new('L', im.size, 255)
    w, h = im.size
    
    alpha.paste(circle.crop((0, 0, rad, rad)), (0, 0))
    alpha.paste(circle.crop((0, rad, rad, rad * 2)), (0, h - rad))
    alpha.paste(circle.crop((rad, 0, rad * 2, rad)), (w - rad, 0))
    alpha.paste(circle.crop((rad, rad, rad * 2, rad * 2)), (w - rad, h - rad))
    
    im.putalpha(alpha)
    return im

async def combine_cards_images(carte, is_table=True):
    """Combina le immagini delle carte con spaziatura e angoli arrotondati"""
    images = []
    for carta in carte:
        try:
            if os.path.exists(carta.image_url):
                img = Image.open(carta.image_url).convert("RGBA")
                
                # Ridimensionamento mantenendo proporzioni
                ratio = CARD_WIDTH / float(img.width)
                new_height = int(float(img.height) * float(ratio))
                img = img.resize((CARD_WIDTH, new_height), Image.LANCZOS)
                
                # Aggiungi angoli arrotondati
                img = await add_corners(img, CARD_CORNER_RADIUS)
                
                # Crea un bordo bianco
                border = Image.new("RGBA", (CARD_WIDTH + 2, new_height + 2), (255, 255, 255, 255))
                border.paste(img, (1, 1), img)
                images.append(border)
        except Exception as e:
            print(f"Errore nel processare {carta.image_url}: {e}")
    
    if not images:
        return None
    
    # Calcola layout
    cards_per_row = min(len(images), MAX_CARDS_PER_ROW)
    rows = (len(images) + MAX_CARDS_PER_ROW - 1) // MAX_CARDS_PER_ROW
    
    # Calcola dimensioni totali
    card_width_with_spacing = CARD_WIDTH + CARD_SPACING + 2  # +2 per il bordo
    total_width = (cards_per_row * card_width_with_spacing) - CARD_SPACING
    max_height = max(img.height for img in images)
    total_height = (rows * max_height) + ((rows - 1) * CARD_SPACING)
    
    # Crea immagine combinata
    combined = Image.new("RGBA", (total_width, total_height), (*BG_COLOR, 0))
    x_offset, y_offset = 0, 0
    
    for i, img in enumerate(images):
        combined.paste(img, (x_offset, y_offset), img)
        x_offset += card_width_with_spacing
        
        if (i + 1) % MAX_CARDS_PER_ROW == 0:
            x_offset = 0
            y_offset += max_height + CARD_SPACING
    
    # Converti in formato Discord
    buffer = BytesIO()
    combined.save(buffer, format="PNG", optimize=True, quality=90)
    buffer.seek(0)
    
    return buffer

async def invia_carte(ctx, carte, titolo=""):
    """Invia le carte formattate con immagini combinate"""
    if not carte:
        return await ctx.send("Nessuna carta presente")
    
    # Invia descrizione testuale
    carte_str = "  ⚫  ".join(str(c) for c in carte)
    embed = discord.Embed(description=f"**{titolo}**\n{carte_str}" if titolo else carte_str)
    await ctx.send(embed=embed)
    
    # Invia immagini combinate
    try:
        buffer = await combine_cards_images(carte)
        if buffer:
            await ctx.send(file=discord.File(buffer, filename="carte.png"))
    except Exception as e:
        print(f"Errore invio immagini: {e}")
        await ctx.send("🃏 Le carte non sono visualizzabili al momento")

async def mostra_mano(ctx, mano, is_ai=False):
    """Mostra la mano del giocatore o dell'AI"""
    if not mano:
        return await ctx.send("Nessuna carta nella mano")
    
    player = "AI" if is_ai else "Tu"
    embed = discord.Embed(title=f"🃏 Mano {player}", color=discord.Color.blurple())
    
    # Aggiungi descrizioni carte
    for i, carta in enumerate(mano):
        embed.add_field(
            name=f"{i+1}: {carta}",
            value="\u200b",
            inline=False
        )
    
    await ctx.send(embed=embed)
    
    # Invia immagini
    try:
        buffer = await combine_cards_images(mano, is_table=False)
        if buffer:
            await ctx.send(file=discord.File(buffer, filename=f"mano_{player.lower()}.png"))
    except Exception as e:
        print(f"Errore visualizzazione mano {player}: {e}")

@bot.command(name='scopa')
async def start_game(ctx):
    """Inizia una nuova partita di Scopa"""
    if ctx.author.id in game_sessions:
        return await ctx.send(f"{ctx.author.mention} Hai già una partita in corso! Usa `!stop` per terminarla.")
    
    try:
        game = ScopaGame()
        game_sessions[ctx.author.id] = game
        
        # Embed iniziale
        embed = discord.Embed(
            title="🎴 Nuova Partita di Scopa",
            description=f"{ctx.author.mention} contro il bot!",
            color=discord.Color.gold()
        )
        embed.add_field(name="Comandi", value="`!gioca <numero>` - Gioca una carta\n`!stop` - Termina la partita")
        await ctx.send(embed=embed)
        
        # Mostra stato iniziale
        await mostra_stato_gioco(ctx, game)
        
    except Exception as e:
        await ctx.send(f"❌ Errore nell'avviare la partita: {str(e)}")
        if ctx.author.id in game_sessions:
            del game_sessions[ctx.author.id]

async def mostra_stato_gioco(ctx, game):
    """Mostra lo stato completo del gioco"""
    # Tavolo
    if game.tavolo:
        await invia_carte(ctx, game.tavolo, "🎴 Tavolo")
    else:
        await ctx.send("🃏 Il tavolo è vuoto")
    
    # Mano giocatore
    await mostra_mano(ctx, game.mano_giocatore)
    
    # Istruzioni
    await ctx.send("✍️ **Gioca una carta con** `!gioca <numero>`")

@bot.command(name='gioca')
async def gioca_carta(ctx, indice: int):
    """Gioca una carta dalla tua mano"""
    if ctx.author.id not in game_sessions:
        return await ctx.send(f"{ctx.author.mention} Nessuna partita attiva. Usa `!scopa` per iniziare.")
    
    game = game_sessions[ctx.author.id]
    
    try:
        indice -= 1  # Converti in indice 0-based
        
        # Validazione
        if indice < 0 or indice >= len(game.mano_giocatore):
            return await ctx.send(f"❌ Numero non valido! Scegli tra 1 e {len(game.mano_giocatore)}")
        
        # Turno giocatore
        carta_giocata = game.mano_giocatore[indice]
        messaggi = game.gioca_carta_giocatore(indice)
        
        for msg in messaggi:
            await ctx.send(f"✅ {ctx.author.mention} {msg}")
        
        # Controlla fine partita
        if game.partita_finita():
            return await termina_partita(ctx, game)
        
        # Turno AI
        messaggi_ai = game.gioca_turno_ai()
        for msg in messaggi_ai:
            await ctx.send(f"🤖 {msg}")
        
        # Controlla fine partita dopo AI
        if game.partita_finita():
            return await termina_partita(ctx, game)
        
        # Pesca nuove carte se necessario
        if len(game.mano_giocatore) == 0 and len(game.mano_ai) == 0:
            if len(game.mazzo) >= 6:
                game.pesca_carte()
                await ctx.send("🃏 **Nuove carte distribuite!**")
            else:
                return await termina_partita(ctx, game)
        
        # Mostra nuovo stato
        await mostra_stato_gioco(ctx, game)
        
    except Exception as e:
        await ctx.send(f"❌ Errore durante il turno: {str(e)}")
        print(f"Errore in gioca_carta: {e}")

async def termina_partita(ctx, game):
    """Gestisce la fine della partita"""
    game.assegna_carte_finali()
    punti_giocatore, punti_ai = game.calcola_punti()
    
    # Crea embed dei risultati
    embed = discord.Embed(
        title="🏁 Partita Terminata",
        color=discord.Color.dark_gold()
    )
    
    # Aggiungi risultati
    embed.add_field(name="Tu", value=str(punti_giocatore), inline=True)
    embed.add_field(name="Totti", value=str(punti_ai), inline=True)
    
    # Determina vincitore
    if punti_giocatore > punti_ai:
        risultato = "🎉 **HAI VINTO!** 🎉"
        embed.color = discord.Color.green()
    elif punti_ai > punti_giocatore:
        risultato = "💀 **HAI PERSO!** 💀"
        embed.color = discord.Color.red()
        
        # Assegna ruolo perdente
        try:
            role = discord.utils.get(ctx.guild.roles, name=PERDENTE_ROLE_NAME)
            if not role:
                role = await ctx.guild.create_role(
                    name=PERDENTE_ROLE_NAME,
                    color=discord.Color.dark_red(),
                    reason="Ruolo per perdenti a Scopa"
                )
            await ctx.author.add_roles(role)
            risultato += f"\n🏷 Ti è stato assegnato il ruolo **{PERDENTE_ROLE_NAME}**!"
        except Exception as e:
            print(f"Errore nell'assegnare il ruolo: {e}")
    else:
        risultato = "⚖ **PAREGGIO!** ⚖"
        embed.color = discord.Color.blue()
    
    embed.add_field(
        name="Risultato",
        value=risultato,
        inline=False
    )
    
    # Dettagli aggiuntivi
    dettagli = [
        f"• Scope: Tu {game.scope_giocatore} - Totti {game.scope_ai}",
        f"• Carte totali: Tu {len(game.prese_giocatore)} - Totti {len(game.prese_ai)}"
    ]
    embed.add_field(
        name="Statistiche",
        value="\n".join(dettagli),
        inline=False
    )
    
    await ctx.send(embed=embed)
    del game_sessions[ctx.author.id]

@bot.command(name='stop')
async def stop_game(ctx):
    """Termina la partita corrente"""
    if ctx.author.id in game_sessions:
        del game_sessions[ctx.author.id]
        await ctx.send(f"⏹ {ctx.author.mention} Partita terminata.")
    else:
        await ctx.send(f"{ctx.author.mention} Nessuna partita attiva.")

@bot.event
async def on_command_error(ctx, error):
    """Gestisce gli errori dei comandi"""
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ {ctx.author.mention} Specifica un numero di carta! Es: `!gioca 1`")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ {ctx.author.mention} Devi inserire un numero valido!")
    else:
        await ctx.send(f"❌ Errore sconosciuto: {str(error)}")
        print(f"Errore non gestito: {error}")

#____________________________________________________________


import asyncio

spam_tasks = {}  # Dizionario per tenere traccia degli spam attivi per autore

@bot.command(name='spamloop')
async def spamloop(ctx, *, messaggio: str):
    if ctx.author.id in spam_tasks:
        return await ctx.send("🚫 Hai già uno spam attivo! Usa `!stopspam` per fermarlo.")

    await ctx.send(f"♾ Inizio spam infinito: `{messaggio}` (usa `!stopspam` per fermarlo)")

    async def spam_forever():
        try:
            while True:
                await ctx.send(messaggio)
                await asyncio.sleep(1)  # Pausa per evitare rate limit
        except asyncio.CancelledError:
            await ctx.send("🛑 Spam interrotto.")
            pass

    task = asyncio.create_task(spam_forever())
    spam_tasks[ctx.author.id] = task

@bot.command(name='stopspam')
async def stopspam(ctx):
    task = spam_tasks.get(ctx.author.id)
    if task:
        task.cancel()
        del spam_tasks[ctx.author.id]
    else:
        await ctx.send("ℹ️ Nessuno spam attivo da fermare.")

if __name__ == "__main__":
    bot.run(TOKEN)