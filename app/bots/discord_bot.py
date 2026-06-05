import logging

from app.bots.common import format_chat_response
from app.core.config import Settings
from app.db.session import get_session_factory
from app.retrieval.embeddings import create_embedding_client
from app.retrieval.vector_store import QdrantHybridStore
from app.services.ask import AskService

logger = logging.getLogger(__name__)


async def run_discord_bot(settings: Settings) -> None:
    import discord
    from discord import app_commands

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    tree = app_commands.CommandTree(client)

    @client.event
    async def on_ready():
        await tree.sync()
        logger.info("Discord bot ready as %s.", client.user)

    @tree.command(name="ask", description="Ask the indexed knowledge base")
    async def ask(interaction: discord.Interaction, question: str):
        await interaction.response.defer(thinking=True)
        service = AskService(
            settings=settings,
            vector_store=QdrantHybridStore(settings),
            embedding_client=create_embedding_client(settings),
        )
        session_factory = get_session_factory()
        async with session_factory() as session:
            answer = await service.ask(
                question=question,
                session=session,
                channel="discord",
                user_id=str(interaction.user.id),
            )
        await interaction.followup.send(format_chat_response(answer)[:1900])

    await client.start(settings.discord_bot_token)
