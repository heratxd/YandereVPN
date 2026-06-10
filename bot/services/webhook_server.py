import hmac
import hashlib
import logging
import json
import re
from typing import Dict, Any, Optional
from aiohttp import web
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.requests import (
    find_order_by_order_id,
    find_order_by_cryptobot_id,
    find_order_by_xrocket_id,
    find_order_by_crystalpay_id,
    is_order_already_paid,
    get_user_by_id,
    get_tariff_by_id,
    get_active_servers,
    get_setting,
    get_cryptobot_token,
    get_xrocket_token,
    get_crystalpay_credentials
)
from bot.services.billing import process_payment_order, process_referral_reward
from bot.utils.groups import get_servers_for_key

logger = logging.getLogger(__name__)


async def handle_cryptobot_webhook(request: web.Request) -> web.Response:
    """Обработчик вебхуков от CryptoBot."""
    token = get_cryptobot_token()
    if not token:
        logger.error("CryptoBot webhook: api_token не настроен")
        return web.Response(status=500, text="API token not configured")

    signature = request.headers.get("Crypto-Pay-API-Signature")
    if not signature:
        logger.warning("CryptoBot webhook: отсутствует заголовок Crypto-Pay-API-Signature")
        return web.Response(status=400, text="Missing signature header")

    body_bytes = await request.read()
    
    # Верификация подписи
    secret = hashlib.sha256(token.encode('utf-8')).digest()
    expected_signature = hmac.new(secret, body_bytes, hashlib.sha256).hexdigest()
    
    if not hmac.compare_digest(expected_signature, signature):
        logger.warning(f"CryptoBot webhook: неверная подпись. Получено: {signature}")
        return web.Response(status=401, text="Invalid signature")

    try:
        data = json.loads(body_bytes.decode('utf-8'))
    except Exception as e:
        logger.error(f"CryptoBot webhook: ошибка декодирования JSON: {e}")
        return web.Response(status=400, text="Invalid JSON body")

    update_type = data.get("update_type")
    if update_type != "invoice_paid":
        logger.debug(f"CryptoBot webhook: пропуск события {update_type}")
        return web.Response(status=200, text="Ignored update type")

    payload_data = data.get("payload", {})
    invoice_id = str(payload_data.get("invoice_id"))
    status = payload_data.get("status")

    if status != "paid":
        return web.Response(status=200, text="Invoice not paid")

    order = find_order_by_cryptobot_id(invoice_id)
    if not order:
        logger.warning(f"CryptoBot webhook: ордер не найден для invoice_id={invoice_id}")
        return web.Response(status=200, text="Order not found")

    await process_successful_payment(request.app["bot"], order, "cryptobot")
    return web.Response(status=200, text="OK")


async def handle_xrocket_webhook(request: web.Request) -> web.Response:
    """Обработчик вебхуков от xRocket."""
    api_key = get_xrocket_token()
    if not api_key:
        logger.error("xRocket webhook: api_key не настроен")
        return web.Response(status=500, text="API key not configured")

    signature = request.headers.get("Rocket-Sign")
    if not signature:
        logger.warning("xRocket webhook: отсутствует заголовок Rocket-Sign")
        return web.Response(status=400, text="Missing signature header")

    body_bytes = await request.read()
    
    # Верификация подписи
    expected_signature = hmac.new(api_key.encode('utf-8'), body_bytes, hashlib.sha256).hexdigest()
    
    if not hmac.compare_digest(expected_signature, signature):
        logger.warning(f"xRocket webhook: неверная подпись. Получено: {signature}")
        return web.Response(status=401, text="Invalid signature")

    try:
        data = json.loads(body_bytes.decode('utf-8'))
    except Exception as e:
        logger.error(f"xRocket webhook: ошибка декодирования JSON: {e}")
        return web.Response(status=400, text="Invalid JSON body")

    # В xRocket Pay webhook может иметь вложенные данные в "data"
    event_data = data.get("data", data)
    invoice_id = str(event_data.get("id"))
    status = event_data.get("status")

    if status != "PAID":
        return web.Response(status=200, text="Invoice not paid")

    order = find_order_by_xrocket_id(invoice_id)
    if not order:
        logger.warning(f"xRocket webhook: ордер не найден для invoice_id={invoice_id}")
        return web.Response(status=200, text="Order not found")

    await process_successful_payment(request.app["bot"], order, "xrocket")
    return web.Response(status=200, text="OK")


async def handle_crystalpay_webhook(request: web.Request) -> web.Response:
    """Обработчик вебхуков от CrystalPay."""
    _, secret = get_crystalpay_credentials()
    if not secret:
        logger.error("CrystalPay webhook: secret не настроен")
        return web.Response(status=500, text="Secret not configured")

    # Чтение данных формы или JSON
    if request.content_type == 'application/x-www-form-urlencoded':
        data = await request.post()
    else:
        try:
            data = await request.json()
        except Exception:
            data = await request.post()

    signature = data.get("signature")
    invoice_id = data.get("id")
    state = data.get("state")

    if not signature or not invoice_id:
        logger.warning("CrystalPay webhook: отсутствуют обязательные параметры")
        return web.Response(status=400, text="Missing signature or id")

    # Верификация подписи: md5(id + ":" + secret)
    expected_signature = hashlib.md5(f"{invoice_id}:{secret}".encode()).hexdigest().lower()
    
    if signature.lower() != expected_signature:
        logger.warning(f"CrystalPay webhook: неверная подпись. Получено: {signature}, ожидалось: {expected_signature}")
        return web.Response(status=401, text="Invalid signature")

    if state != "pay":
        return web.Response(status=200, text="State not pay")

    order = find_order_by_crystalpay_id(str(invoice_id))
    if not order:
        logger.warning(f"CrystalPay webhook: ордер не найден для invoice_id={invoice_id}")
        return web.Response(status=200, text="Order not found")

    await process_successful_payment(request.app["bot"], order, "crystalpay")
    return web.Response(status=200, text="OK")


async def process_successful_payment(bot: Bot, order: Dict[str, Any], payment_type: str) -> None:
    """Обрабатывает успешный платёж и отправляет уведомление пользователю."""
    order_id = order['order_id']
    
    if is_order_already_paid(order_id):
        logger.info(f"Ордер {order_id} уже был обработан ранее — пропускаем.")
        return

    user_internal_id = order['user_id']
    user = get_user_by_id(user_internal_id)
    if not user:
        logger.error(f"Не удалось найти пользователя ID {user_internal_id} для ордера {order_id}")
        return
        
    telegram_id = user['telegram_id']

    # 1. Вызываем стандартный обработчик логики БД и API панели
    success, text, updated_order = await process_payment_order(order_id)
    if not success or not updated_order:
        logger.error(f"Ошибка процесса обработки платежа для ордера {order_id}: {text}")
        return

    # 2. Начисление реферального вознаграждения
    days = updated_order.get('period_days') or updated_order.get('duration_days') or 30
    _tariff = get_tariff_by_id(updated_order.get('tariff_id'))
    
    if payment_type in ('cryptobot', 'xrocket'):
        referral_amount = _tariff.get('price_cents', 0) if _tariff else 0
    else:
        referral_amount = int((_tariff.get('price_rub', 0) or 0) * 100) if _tariff else 0

    try:
        await process_referral_reward(user_internal_id, days, referral_amount, payment_type)
    except Exception as e:
        logger.error(f"Ошибка реферального начисления: {e}")

    # 3. Уведомление пользователя
    vpn_key_id = updated_order.get('vpn_key_id')
    
    try:
        if vpn_key_id and order.get('vpn_key_id'):  # Продление существующего ключа
            # Загружаем название ключа для отображения
            from database.requests import get_key_details_for_user
            key_details = get_key_details_for_user(vpn_key_id, telegram_id)
            key_name = key_details['display_name'] if key_details else f"#{vpn_key_id}"
            
            notification_text = (
                f"🎉 <b>Оплата успешно получена!</b>\n\n"
                f"Ваш VPN-ключ <b>{key_name}</b> успешно продлён на <b>{days}</b> дней.\n\n"
                f"Спасибо за покупку! ❤️"
            )
            await bot.send_message(chat_id=telegram_id, text=notification_text, parse_mode="HTML")
            
        else:  # Покупка нового ключа (черновик)
            # Отправляем список серверов в виде клавиатуры
            tariff_id = updated_order.get('tariff_id')
            if tariff_id:
                servers = get_servers_for_key(tariff_id)
            else:
                servers = get_active_servers()

            if not servers:
                error_text = (
                    f"🎉 <b>Оплата успешно получена!</b>\n\n"
                    f"⚠️ К сожалению, сейчас нет доступных серверов.\n"
                    f"Пожалуйста, обратитесь в поддержку для настройки ключа."
                )
                await bot.send_message(chat_id=telegram_id, text=error_text, parse_mode="HTML")
                return

            notification_text = (
                f"🎉 <b>Оплата успешно получена!</b>\n\n"
                f"Для настройки вашего нового VPN-подключения, пожалуйста, выберите сервер:"
            )
            
            builder = InlineKeyboardBuilder()
            for srv in servers:
                builder.row(InlineKeyboardButton(
                    text=srv['name'], 
                    callback_data=f"wh_server:{order_id}:{srv['id']}"
                ))
            
            await bot.send_message(
                chat_id=telegram_id,
                text=notification_text,
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )
            
    except Exception as err:
        logger.error(f"Не удалось отправить уведомление о платеже пользователю {telegram_id}: {err}")


async def start_webhook_server(bot: Bot) -> web.AppRunner:
    """Запускает вебхук HTTP сервер на указанном порту."""
    app = web.Application()
    app["bot"] = bot

    # Регистрируем маршруты
    app.router.add_post("/webhook/cryptobot", handle_cryptobot_webhook)
    app.router.add_post("/webhook/xrocket", handle_xrocket_webhook)
    app.router.add_post("/webhook/crystalpay", handle_crystalpay_webhook)

    try:
        import config
        port = getattr(config, "WEBHOOK_PORT", 8080)
        host = getattr(config, "WEBHOOK_HOST", "0.0.0.0")
    except ImportError:
        port = 8080
        host = "0.0.0.0"

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    
    logger.info(f"🌐 Webhook-сервер запущен на http://{host}:{port}")
    return runner
