import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.utils.text import escape_html, safe_edit_or_send
from bot.handlers.user.payments.base import (
    create_qr_payment_flow, check_qr_payment_flow
)

logger = logging.getLogger(__name__)

router = Router()

# Конфигурация провайдера CryptoBot
_CB_TITLE = '🤖 <b>Оплата CryptoBot (USDT)</b>'
_CB_TYPE = 'cryptobot'
_CB_ERROR = 'CryptoBot'
_CB_QR_FILE = 'cryptobot.png'
_CB_CHECK_PREFIX = 'check_cryptobot'
_CB_RESULT_KEY = 'cryptobot_invoice_id'
_CB_HINT = (
    'После оплаты нажмите «✅ Я оплатил» — или просто вернитесь '
    'в бот по ссылке после оплаты, проверка запустится автоматически.'
)


@router.callback_query(F.data == 'pay_cryptobot')
async def pay_cryptobot_select_tariff(callback: CallbackQuery):
    """Выбор тарифа для оплаты через CryptoBot (новый ключ)."""
    from database.requests import get_all_tariffs
    from bot.keyboards.user import tariff_select_kb
    from bot.keyboards.admin import home_only_kb

    tariffs = get_all_tariffs(include_hidden=False)
    crypto_tariffs = [t for t in tariffs if t.get('price_cents') and t['price_cents'] > 0]
    if not crypto_tariffs:
        await safe_edit_or_send(
            callback.message,
            f'{_CB_TITLE}\n\n😔 Нет тарифов с ценой в центах.\nОбратитесь к администратору.',
            reply_markup=home_only_kb()
        )
        await callback.answer()
        return
    await safe_edit_or_send(
        callback.message,
        '🤖 <b>Оплата CryptoBot (USDT)</b>\n\nВыберите тариф:\n\n'
        '<i>Оплата в USDT с помощью официального бота @CryptoBot.</i>',
        reply_markup=tariff_select_kb(crypto_tariffs, is_cryptobot=True)
    )
    await callback.answer()


@router.callback_query(F.data.startswith('cryptobot_pay:'))
async def cryptobot_pay_create(callback: CallbackQuery):
    """Создаёт счёт CryptoBot для нового ключа и отправляет QR-фото."""
    from database.requests import get_tariff_by_id, save_cryptobot_invoice_id, get_setting, get_cryptobot_token
    from bot.services.billing import create_cryptobot_payment

    tariff_id = int(callback.data.split(':')[1])
    tariff = get_tariff_by_id(tariff_id)
    if not tariff:
        await callback.answer('❌ Тариф не найден', show_alert=True)
        return
    price_usd = float(tariff.get('price_cents') or 0) / 100
    if price_usd <= 0:
        await callback.answer('❌ Некорректная цена тарифа', show_alert=True)
        return

    token = get_cryptobot_token()
    manual = get_setting('cryptobot_manual_address', '')
    if not token and manual:
        from bot.handlers.user.payments.base import create_manual_payment_flow
        await create_manual_payment_flow(
            callback=callback, tariff=tariff, price_usd=price_usd,
            payment_type=_CB_TYPE, manual_address=manual,
            back_callback='pay_cryptobot'
        )
        return

    await create_qr_payment_flow(
        callback=callback, tariff=tariff, price_rub=price_usd,
        payment_type=_CB_TYPE,
        create_func=create_cryptobot_payment,
        save_func=save_cryptobot_invoice_id,
        result_key=_CB_RESULT_KEY,
        title=_CB_TITLE,
        check_prefix=_CB_CHECK_PREFIX,
        error_name=_CB_ERROR,
        qr_filename=_CB_QR_FILE,
        back_callback='pay_cryptobot',
        hint_text=_CB_HINT,
    )


@router.callback_query(F.data.startswith('renew_cryptobot_tariff:'))
async def renew_cryptobot_select_tariff(callback: CallbackQuery):
    """Выбор тарифа для оплаты CryptoBot при продлении ключа."""
    from database.requests import get_key_details_for_user
    from bot.keyboards.user import renew_tariff_select_kb
    from bot.utils.groups import get_tariffs_for_renewal

    key_id = int(callback.data.split(':')[1])
    key = get_key_details_for_user(key_id, callback.from_user.id)
    if not key:
        await callback.answer('❌ Ключ не найден', show_alert=True)
        return
    tariffs = get_tariffs_for_renewal(key.get('tariff_id', 0))
    crypto_tariffs = [t for t in tariffs if t.get('price_cents') and t['price_cents'] > 0]
    if not crypto_tariffs:
        await callback.answer('😔 Нет доступных тарифов с ценой в центах', show_alert=True)
        return
    await safe_edit_or_send(
        callback.message,
        f"🤖 <b>Оплата CryptoBot (USDT)</b>\n\n🔑 Ключ: <b>{escape_html(key['display_name'])}</b>\n\nВыберите тариф для продления:",
        reply_markup=renew_tariff_select_kb(crypto_tariffs, key_id, is_cryptobot=True)
    )
    await callback.answer()


@router.callback_query(F.data.startswith('renew_pay_cryptobot:'))
async def renew_cryptobot_create(callback: CallbackQuery):
    """Создаёт счёт CryptoBot для продления ключа."""
    from database.requests import get_tariff_by_id, get_key_details_for_user, save_cryptobot_invoice_id, get_setting, get_cryptobot_token
    from bot.services.billing import create_cryptobot_payment

    parts = callback.data.split(':')
    key_id = int(parts[1])
    tariff_id = int(parts[2])
    tariff = get_tariff_by_id(tariff_id)
    key = get_key_details_for_user(key_id, callback.from_user.id)
    if not tariff or not key:
        await callback.answer('❌ Ошибка тарифа или ключа', show_alert=True)
        return
    price_usd = float(tariff.get('price_cents') or 0) / 100
    if price_usd <= 0:
        await callback.answer('❌ Некорректная цена тарифа', show_alert=True)
        return

    token = get_cryptobot_token()
    manual = get_setting('cryptobot_manual_address', '')
    if not token and manual:
        from bot.handlers.user.payments.base import create_manual_payment_flow
        await create_manual_payment_flow(
            callback=callback, tariff=tariff, price_usd=price_usd,
            payment_type=_CB_TYPE, manual_address=manual,
            back_callback=f'renew_cryptobot_tariff:{key_id}',
            key=key, vpn_key_id=key_id
        )
        return

    await create_qr_payment_flow(
        callback=callback, tariff=tariff, price_rub=price_usd,
        payment_type=_CB_TYPE,
        create_func=create_cryptobot_payment,
        save_func=save_cryptobot_invoice_id,
        result_key=_CB_RESULT_KEY,
        title=_CB_TITLE,
        check_prefix=_CB_CHECK_PREFIX,
        error_name=_CB_ERROR,
        qr_filename=_CB_QR_FILE,
        back_callback=f'renew_cryptobot_tariff:{key_id}',
        key=key, vpn_key_id=key_id,
        hint_text=_CB_HINT,
    )


@router.callback_query(F.data.startswith('check_cryptobot:'))
async def check_cryptobot_payment(callback: CallbackQuery, state: FSMContext):
    """Проверяет статус CryptoBot-платежа по нажатию «✅ Я оплатил»."""
    await _run_cryptobot_check(
        callback.message, state,
        order_id=callback.data.split(':', 1)[1],
        telegram_id=callback.from_user.id,
        callback=callback,
    )


async def _run_cryptobot_check(message, state, order_id: str,
                               telegram_id: int, callback=None) -> None:
    """Общая логика проверки CryptoBot-платежа."""
    from bot.services.billing import check_cryptobot_payment_status

    await check_qr_payment_flow(
        message=message,
        state=state,
        order_id=order_id,
        telegram_id=telegram_id,
        payment_type=_CB_TYPE,
        payment_id_field=_CB_RESULT_KEY,
        check_func=check_cryptobot_payment_status,
        rate_limit_seconds=10,
        rate_limit_prefix='cryptobot',
        callback=callback,
    )
