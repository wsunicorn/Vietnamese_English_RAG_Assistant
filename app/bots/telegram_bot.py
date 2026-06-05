import asyncio
import logging

from app.bots.common import format_chat_response, parse_ask_command
from app.core.config import Settings
from app.db.session import get_session_factory
from app.retrieval.embeddings import create_embedding_client
from app.retrieval.vector_store import QdrantHybridStore
from app.services.ask import AskService

logger = logging.getLogger(__name__)


async def run_telegram_bot(settings: Settings) -> None:
    from telegram import Update
    from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

    service = AskService(
        settings=settings,
        vector_store=QdrantHybridStore(settings),
        embedding_client=create_embedding_client(settings),
    )

    async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        question = parse_ask_command(" ".join(context.args), command="/ask")
        if not question:
            await update.effective_message.reply_text("Usage: /ask your question")
            return
        session_factory = get_session_factory()
        async with session_factory() as session:
            answer = await service.ask(
                question=question,
                session=session,
                channel="telegram",
                user_id=str(update.effective_user.id if update.effective_user else ""),
            )
        await update.effective_message.reply_text(format_chat_response(answer)[:3900])

    app = ApplicationBuilder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler("ask", ask))
    logger.info("Telegram bot polling started.")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    while True:
        await asyncio.sleep(3600)
