from aiogram import Router
from .base import router as base_router
from .balance import router as balance_router
from .yookassa import router as yookassa_router
from .wata import router as wata_router
from .platega import router as platega_router
from .cardlink import router as cardlink_router
from .cryptobot import router as cryptobot_router
from .xrocket import router as xrocket_router
from .crystalpay import router as crystalpay_router
from .stars import router as stars_router
from .crypto import router as crypto_router
from .keys_config import router as keys_config_router
from .demo import router as demo_router
from .lava import router as lava_router
from .freekassa import router as freekassa_router
from .rukassa import router as rukassa_router
from .payok import router as payok_router
from .nowpayments import router as nowpayments_router
from .robokassa import router as robokassa_router
from .yoomoney import router as yoomoney_router

router = Router()
router.include_router(base_router)
router.include_router(balance_router)
router.include_router(yookassa_router)
router.include_router(wata_router)
router.include_router(platega_router)
router.include_router(cardlink_router)
router.include_router(cryptobot_router)
router.include_router(xrocket_router)
router.include_router(crystalpay_router)
router.include_router(stars_router)
router.include_router(crypto_router)
router.include_router(keys_config_router)
router.include_router(demo_router)
router.include_router(lava_router)
router.include_router(freekassa_router)
router.include_router(rukassa_router)
router.include_router(payok_router)
router.include_router(nowpayments_router)
router.include_router(robokassa_router)
router.include_router(yoomoney_router)


