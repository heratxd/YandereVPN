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
    find_order_by_lava_id,
    find_order_by_freekassa_id,
    find_order_by_rukassa_id,
    find_order_by_payok_id,
    find_order_by_nowpayments_id,
    find_order_by_robokassa_id,
    find_order_by_yoomoney_id,
    save_yoomoney_payment_id,
    is_order_already_paid,
    get_user_by_id,
    get_tariff_by_id,
    get_active_servers,
    get_setting,
    get_cryptobot_token,
    get_xrocket_token,
    get_crystalpay_credentials,
    get_lava_credentials,
    get_freekassa_credentials,
    get_rukassa_credentials,
    get_payok_credentials,
    get_nowpayments_api_key,
    get_robokassa_credentials
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


# ── Lava Webhook ──────────────────────────────────────────────────────────────

async def handle_lava_webhook(request: web.Request) -> web.Response:
    """Обработчик вебхуков от Lava."""
    _, api_key = get_lava_credentials()
    if not api_key:
        logger.error("Lava webhook: api_key не настроен")
        return web.Response(status=500, text="API key not configured")
        
    signature = request.headers.get("Signature")
    if not signature:
        logger.warning("Lava webhook: отсутствует заголовок Signature")
        return web.Response(status=400, text="Missing Signature header")
        
    body_bytes = await request.read()
    
    # Верификация подписи
    expected_signature = hmac.new(
        api_key.encode('utf-8'),
        body_bytes,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(expected_signature, signature.lower()):
        logger.warning(f"Lava webhook: неверная подпись. Получено: {signature}, ожидалось: {expected_signature}")
        return web.Response(status=401, text="Invalid signature")
        
    try:
        data = json.loads(body_bytes.decode('utf-8'))
    except Exception:
        logger.error("Lava webhook: невозможно разобрать JSON-тело")
        return web.Response(status=400, text="Invalid JSON body")
        
    invoice_id = data.get("invoice_id") or data.get("id")
    status = data.get("status")
    order_id = data.get("order_id") or data.get("orderId")
    
    if not invoice_id:
        logger.warning("Lava webhook: отсутствует invoice_id")
        return web.Response(status=400, text="Missing invoice_id")
        
    # Проверяем успешность платежа (success или paid)
    if str(status).lower() not in ('success', 'paid'):
        return web.Response(status=200, text="Status not paid")
        
    order = find_order_by_lava_id(str(invoice_id))
    if not order and order_id:
        order = find_order_by_order_id(str(order_id))
        
    if not order:
        logger.warning(f"Lava webhook: ордер не найден для invoice_id={invoice_id}")
        return web.Response(status=200, text="Order not found")
        
    await process_successful_payment(request.app["bot"], order, "lava")
    return web.Response(status=200, text="OK")


# ── Freekassa Webhook ─────────────────────────────────────────────────────────

async def handle_freekassa_webhook(request: web.Request) -> web.Response:
    """Обработчик вебхуков от Freekassa."""
    # Freekassa отправляет POST с application/x-www-form-urlencoded
    data = await request.post()
    
    merchant_id = data.get("MERCHANT_ID")
    amount = data.get("AMOUNT")
    merchant_order_id = data.get("MERCHANT_ORDER_ID")
    sign = data.get("SIGN")
    
    if not merchant_id or not amount or not merchant_order_id or not sign:
        logger.warning("Freekassa webhook: отсутствуют обязательные параметры")
        return web.Response(status=400, text="Missing parameters")
        
    secret_2 = get_setting('freekassa_secret_2', '')
    if not secret_2:
        logger.error("Freekassa webhook: secret_2 не настроен")
        return web.Response(status=500, text="Secret 2 not configured")
        
    # Подпись: md5(MERCHANT_ID:AMOUNT:secret_2:MERCHANT_ORDER_ID)
    sign_str = f"{merchant_id}:{amount}:{secret_2}:{merchant_order_id}"
    expected_sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest().lower()
    
    if sign.lower() != expected_sign:
        logger.warning(f"Freekassa webhook: неверная подпись. Получено: {sign}, ожидалось: {expected_sign}")
        return web.Response(status=401, text="Invalid signature")
        
    order = find_order_by_order_id(str(merchant_order_id))
    if not order:
        logger.warning(f"Freekassa webhook: ордер не найден для merchant_order_id={merchant_order_id}")
        return web.Response(status=200, text="YES") # возвращаем YES, чтобы остановить повторы
        
    await process_successful_payment(request.app["bot"], order, "freekassa")
    return web.Response(status=200, text="YES") # Freekassa требует возвращать именно YES


# ── Rukassa Webhook ───────────────────────────────────────────────────────────

async def handle_rukassa_webhook(request: web.Request) -> web.Response:
    """Обработчик вебхуков от Rukassa."""
    if request.content_type == 'application/x-www-form-urlencoded':
        data = await request.post()
    else:
        try:
            data = await request.json()
        except Exception:
            data = await request.post()
            
    shop_id = data.get("shop_id")
    order_id = data.get("order_id")
    amount = data.get("amount")
    sign = data.get("sign")
    status = data.get("status")
    invoice_id = data.get("id")
    
    if not shop_id or not order_id or not sign or not status:
        logger.warning("Rukassa webhook: отсутствуют обязательные параметры")
        return web.Response(status=400, text="Missing parameters")
        
    _, token = get_rukassa_credentials()
    if not token:
        logger.error("Rukassa webhook: token не настроен")
        return web.Response(status=500, text="Token not configured")
        
    # Подпись: sha256(shop_id + order_id + token)
    sign_str = f"{shop_id}{order_id}{token}"
    expected_sign = hashlib.sha256(sign_str.encode('utf-8')).hexdigest().lower()
    
    if sign.lower() != expected_sign:
        logger.warning(f"Rukassa webhook: неверная подпись. Получено: {sign}, ожидалось: {expected_sign}")
        return web.Response(status=401, text="Invalid signature")
        
    if str(status).upper() != 'PAID':
        return web.Response(status=200, text="Status not PAID")
        
    order = find_order_by_order_id(str(order_id))
    if not order and invoice_id:
        order = find_order_by_rukassa_id(str(invoice_id))
        
    if not order:
        logger.warning(f"Rukassa webhook: ордер не найден для order_id={order_id}")
        return web.Response(status=200, text="Order not found")
        
    await process_successful_payment(request.app["bot"], order, "rukassa")
    return web.Response(status=200, text="OK")


# ── Payok Webhook ─────────────────────────────────────────────────────────────

async def handle_payok_webhook(request: web.Request) -> web.Response:
    """Обработчик вебхуков от Payok."""
    if request.content_type == 'application/x-www-form-urlencoded':
        data = await request.post()
    else:
        try:
            data = await request.json()
        except Exception:
            data = await request.post()
            
    sign = data.get("sign")
    payment_id = data.get("payment_id")
    amount = data.get("amount")
    shop = data.get("shop")
    currency = data.get("currency")
    desc = data.get("desc")
    
    if not sign or not payment_id:
        logger.warning("Payok webhook: отсутствуют обязательные параметры")
        return web.Response(status=400, text="Missing sign or payment_id")
        
    _, _, secret_key = get_payok_credentials()
    if not secret_key:
        logger.error("Payok webhook: secret_key не настроен")
        return web.Response(status=500, text="Secret key not configured")
        
    # Подпись: md5(secret_key + desc + currency + shop + payment_id + amount) с разделителем |
    sign_str = f"{secret_key}|{desc}|{currency}|{shop}|{payment_id}|{amount}"
    expected_sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest().lower()
    
    if sign.lower() != expected_sign:
        logger.warning(f"Payok webhook: неверная подпись. Получено: {sign}, ожидалось: {expected_sign}")
        return web.Response(status=401, text="Invalid signature")
        
    order = find_order_by_order_id(str(payment_id))
    if not order:
        logger.warning(f"Payok webhook: ордер не найден для payment_id={payment_id}")
        return web.Response(status=200, text="Order not found")
        
    await process_successful_payment(request.app["bot"], order, "payok")
    return web.Response(status=200, text="OK")


# ── NowPayments Webhook ────────────────────────────────────────────────────────

async def handle_nowpayments_webhook(request: web.Request) -> web.Response:
    """Обработчик вебхуков от NowPayments."""
    signature = request.headers.get("x-nowpayments-sig")
    if not signature:
        logger.warning("NowPayments webhook: отсутствует заголовок x-nowpayments-sig")
        return web.Response(status=400, text="Missing signature header")
        
    ipn_secret = get_setting('nowpayments_ipn_secret', '')
    if not ipn_secret:
        logger.error("NowPayments webhook: ipn_secret не настроен в настройках")
        return web.Response(status=500, text="IPN Secret not configured")
        
    body_bytes = await request.read()
    
    try:
        payload_dict = json.loads(body_bytes.decode('utf-8'))
    except Exception:
        logger.error("NowPayments webhook: невозможно разобрать JSON-тело")
        return web.Response(status=400, text="Invalid JSON body")
        
    # Сортируем ключи и форматируем JSON без лишних пробелов для проверки подписи
    sorted_payload = json.dumps(payload_dict, sort_keys=True, separators=(',', ':'))
    expected_signature = hmac.new(
        ipn_secret.encode('utf-8'),
        sorted_payload.encode('utf-8'),
        hashlib.sha512
    ).hexdigest()
    
    if not hmac.compare_digest(expected_signature, signature.lower()):
        logger.warning(f"NowPayments webhook: неверная подпись. Получено: {signature}, ожидалось: {expected_signature}")
        return web.Response(status=401, text="Invalid signature")
        
    payment_status = payload_dict.get("payment_status")
    order_id = payload_dict.get("order_id")
    invoice_id = payload_dict.get("invoice_id")
    
    if not order_id:
        logger.warning("NowPayments webhook: отсутствует order_id")
        return web.Response(status=400, text="Missing order_id")
        
    # Проверяем успешность
    if payment_status not in ('finished', 'confirmed'):
        return web.Response(status=200, text="Payment not finished")
        
    order = find_order_by_order_id(str(order_id))
    if not order and invoice_id:
        order = find_order_by_nowpayments_id(str(invoice_id))
        
    if not order:
        logger.warning(f"NowPayments webhook: ордер не найден для order_id={order_id}")
        return web.Response(status=200, text="Order not found")
        
    await process_successful_payment(request.app["bot"], order, "nowpayments")
    return web.Response(status=200, text="OK")


# ── Robokassa Webhook ─────────────────────────────────────────────────────────

async def handle_robokassa_webhook(request: web.Request) -> web.Response:
    """Обработчик вебхуков от Robokassa."""
    # Robokassa ResultURL отправляет параметры в POST или GET (обычно POST)
    if request.method == 'POST':
        data = await request.post()
    else:
        data = request.query
        
    out_sum = data.get("OutSum")
    inv_id = data.get("InvId")
    signature = data.get("SignatureValue")
    shp_order_id = data.get("shp_order_id")
    
    if not out_sum or not inv_id or not signature or not shp_order_id:
        logger.warning("Robokassa webhook: отсутствуют обязательные параметры")
        return web.Response(status=400, text="Missing parameters")
        
    _, _, password_2 = get_robokassa_credentials()
    if not password_2:
        logger.error("Robokassa webhook: password_2 не настроен")
        return web.Response(status=500, text="Password 2 not configured")
        
    # Подпись для ResultURL: OutSum:InvId:Password2:shp_order_id=order_id
    sign_str = f"{out_sum}:{inv_id}:{password_2}:shp_order_id={shp_order_id}"
    expected_signature = hashlib.md5(sign_str.encode('utf-8')).hexdigest().lower()
    
    if signature.lower() != expected_signature:
        logger.warning(f"Robokassa webhook: неверная подпись. Получено: {signature}, ожидалось: {expected_signature}")
        return web.Response(status=401, text="Invalid signature")
        
    order = find_order_by_order_id(str(shp_order_id))
    if not order:
        logger.warning(f"Robokassa webhook: ордер не найден для shp_order_id={shp_order_id}")
        return web.Response(status=200, text=f"OK{inv_id}") # возвращаем OK{InvId}, чтобы остановить ретраи
        
    await process_successful_payment(request.app["bot"], order, "robokassa")
    return web.Response(status=200, text=f"OK{inv_id}")


async def handle_yoomoney_webhook(request: web.Request) -> web.Response:
    """Обработчик вебхуков (IPN) от ЮMoney."""
    import hashlib
    data = await request.post()
    
    notification_type = data.get("notification_type")
    operation_id = data.get("operation_id")
    amount = data.get("amount")
    currency = data.get("currency")
    datetime_str = data.get("datetime")
    sender = data.get("sender")
    codepro = data.get("codepro")
    label = data.get("label")  # В label мы передаем order_id
    sha1_hash = data.get("sha1_hash")
    
    if not operation_id or not label or not sha1_hash:
        logger.warning("YooMoney webhook: отсутствуют обязательные параметры")
        return web.Response(status=400, text="Missing parameters")
        
    secret = get_setting('yoomoney_secret', '')
    if not secret:
        logger.error("YooMoney webhook: Секретный ключ (IPN) не настроен")
        return web.Response(status=500, text="Secret not configured")
        
    # Строка подписи:
    sign_str = f"{notification_type}&{operation_id}&{amount}&{currency}&{datetime_str}&{sender}&{codepro}&{secret}&{label}"
    expected_hash = hashlib.sha1(sign_str.encode('utf-8')).hexdigest().lower()
    
    if sha1_hash.lower() != expected_hash:
        logger.warning(f"YooMoney webhook: неверная подпись. Получено: {sha1_hash}, ожидалось: {expected_hash}")
        return web.Response(status=401, text="Invalid signature")
        
    order = find_order_by_order_id(str(label))
    if not order:
        order = find_order_by_yoomoney_id(str(operation_id))
        
    if not order:
        logger.warning(f"YooMoney webhook: ордер не найден для label/operation_id={label}/{operation_id}")
        return web.Response(status=200, text="Order not found")
        
    save_yoomoney_payment_id(order['order_id'], operation_id)
    
    await process_successful_payment(request.app["bot"], order, "yoomoney")
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


async def start_webhook_server(bot: Bot, dp=None) -> web.AppRunner:
    """Запускает вебхук HTTP сервер на указанном порту."""
    app = web.Application()
    app["bot"] = bot

    # Регистрируем маршруты
    app.router.add_post("/webhook/cryptobot", handle_cryptobot_webhook)
    app.router.add_post("/webhook/xrocket", handle_xrocket_webhook)
    app.router.add_post("/webhook/crystalpay", handle_crystalpay_webhook)
    app.router.add_post("/webhook/lava", handle_lava_webhook)
    app.router.add_post("/webhook/freekassa", handle_freekassa_webhook)
    app.router.add_post("/webhook/rukassa", handle_rukassa_webhook)
    app.router.add_post("/webhook/payok", handle_payok_webhook)
    app.router.add_post("/webhook/nowpayments", handle_nowpayments_webhook)
    app.router.add_post("/webhook/robokassa", handle_robokassa_webhook)
    app.router.add_post("/webhook/yoomoney", handle_yoomoney_webhook)

    if dp is not None:
        from aiogram.webhook.aiohttp_impl import SimpleRequestHandler
        webhook_requests_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot
        )
        webhook_requests_handler.register(app, path="/webhook/bot")
        logger.info("🤖 Путь вебхука Telegram зарегистрирован: /webhook/bot")

    import ssl
    from database.requests import is_domain_enabled, get_domain_name, get_ssl_mode
    
    ssl_context = None
    domain_enabled = is_domain_enabled()
    domain_name = get_domain_name()
    ssl_mode = get_ssl_mode()
    
    if domain_enabled and domain_name and ssl_mode == "standalone":
        try:
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            cert_path = f"/etc/letsencrypt/live/{domain_name}/fullchain.pem"
            key_path = f"/etc/letsencrypt/live/{domain_name}/privkey.pem"
            ssl_context.load_cert_chain(certfile=cert_path, keyfile=key_path)
            logger.info(f"🔒 Standalone SSL Context создан для домена {domain_name}")
        except Exception as e:
            logger.error(f"❌ Ошибка при загрузке SSL сертификатов для {domain_name}: {e}")
            ssl_context = None

    runner = web.AppRunner(app)
    await runner.setup()
    
    if ssl_context:
        site = web.TCPSite(runner, "0.0.0.0", 443, ssl_context=ssl_context)
        logger.info(f"🌐 Webhook-сервер запущен на https://0.0.0.0:443 (Standalone SSL)")
    else:
        try:
            import config
            port = getattr(config, "WEBHOOK_PORT", 8080)
            host = getattr(config, "WEBHOOK_HOST", "0.0.0.0")
        except ImportError:
            port = 8080
            host = "0.0.0.0"
        site = web.TCPSite(runner, host, port)
        logger.info(f"🌐 Webhook-сервер запущен на http://{host}:{port}")
        
    await site.start()
    return runner

