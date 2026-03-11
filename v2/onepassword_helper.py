import asyncio
from loguru import logger


async def _resolve(token, refs):
    from onepassword.client import Client

    client = await Client.authenticate(
        auth=token,
        integration_name="myGoogleCalendar",
        integration_version="1.0.0",
    )
    return [await client.secrets.resolve(ref) for ref in refs]


def load_credentials(token, refs):
    if not token:
        logger.error("OP_SERVICE_ACCOUNT_TOKEN is empty in config_file.py.")
        raise RuntimeError("OP_SERVICE_ACCOUNT_TOKEN not set")

    logger.info("Loading credentials from 1Password...")
    results = asyncio.run(_resolve(token, refs))
    logger.success("Credentials loaded from 1Password.")
    return results
