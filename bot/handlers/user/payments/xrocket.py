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

# Конфигурация провайдера xRocket
_XR_TITLE = '🚀 <b>Оплата xRocket (USDT)</b>'
_XR_TYPE = 'xrocket'
_XR_ERROR = 'xRocket'
_XR_QR_FILE = 'xrocket.png'
_XR_CHECK_PREFIX = 'check_xrocket'
_XR_RESULT_KEY = 'xrocket_invoice_id'
_XR_HINT = (
    'После оплаты нажмите «✅ Я оплатил» — или просто вернитесь '
    'в бот по ссылке после оплаты, проверка запустится автоматически.'
)


@router.callback_query(F.data == 'pay_xrocket')
async def pay_xrocket_select_tariff(callback: CallbackQuery):
    """Выбор тарифа для оплаты через xRocket (новый ключ)."""
    from database.requests import get_all_tariffs
    from bot.keyboards.user import tariff_select_kb
    from bot.keyboards.admin import home_only_kb

    tariffs = get_all_tariffs(include_hidden=False)
    crypto_tariffs = [t for t in tariffs if t.get('price_cents') and t['price_cents'] > 0]
    if not crypto_tariffs:
        await safe_edit_or_send(
            callback.message,
            f'{_XR_TITLE}\n\n😔 Нет тарифов с ценой в центах.\nОбратитесь к администратору.',
            reply_markup=home_only_kb()
        )
        await callback.answer()
        return
    await safe_edit_or_send(
        callback.message,
        '🚀 <b>Оплата xRocket (USDT)</b>\n\nВыберите тариф:\n\n'
        '<i>Оплата в USDT с помощью официального бота @xRocket.</i>',
        reply_markup=tariff_select_kb(crypto_tariffs, is_xrocket=True)
    )
    await callback.answer()


@router.callback_query(F.data.startswith('xrocket_pay:'))
async def xrocket_pay_create(callback: CallbackQuery):
    """Создаёт счёт xRocket для нового ключа и отправляет QR-фото."""
    from database.requests import get_tariff_by_id, save_xrocket_invoice_id, get_setting, get_xrocket_token
    from bot.services.billing import create_xrocket_payment

    tariff_id = int(callback.data.split(':')[1])
    tariff = get_tariff_by_id(tariff_id)
    if not tariff:
        await callback.answer('❌ Тариф не найден', show_alert=True)
        return
    price_usd = float(tariff.get('price_cents') or 0) / 100
    if price_usd <= 0:
        await callback.answer('❌ Некорректная цена тарифа', show_alert=True)
        return

    token = get_xrocket_token()
    manual = get_setting('xrocket_manual_address', '')
    if not token and manual:
        from bot.handlers.user.payments.base import create_manual_payment_flow
        await create_manual_payment_flow(
            callback=callback, tariff=tariff, price_usd=price_usd,
            payment_type=_XR_TYPE, manual_address=manual,
            back_callback='pay_xrocket'
        )
        return

    await create_qr_payment_flow(
        callback=callback, tariff=tariff, price_rub=price_usd,
        payment_type=_XR_TYPE,
        create_func=create_xrocket_payment,
        save_func=save_xrocket_invoice_id,
        result_key=_XR_RESULT_KEY,
        title=_XR_TITLE,
        check_prefix=_XR_CHECK_PREFIX,
        error_name=_XR_ERROR,
        qr_filename=_XR_QR_FILE,
        back_callback='pay_xrocket',
        hint_text=_XR_HINT,
    )


@router.callback_query(F.data.startswith('renew_xrocket_tariff:'))
async def renew_xrocket_select_tariff(callback: CallbackQuery):
    """Выбор тарифа для оплаты xRocket при продлении ключа."""
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
        f"🚀 <b>Оплата xRocket (USDT)</b>\n\n🔑 Ключ: <b>{escape_html(key['display_name'])}</b>\n\nВыберите тариф для продления:",
        reply_markup=renew_tariff_select_kb(crypto_tariffs, key_id, is_xrocket=True)
    )
    await callback.answer()


@router.callback_query(F.data.startswith('renew_pay_xrocket:'))
async def renew_xrocket_create(callback: CallbackQuery):
    """Создаёт счёт xRocket для продления ключа."""
    from database.requests import get_tariff_by_id, get_key_details_for_user, save_xrocket_invoice_id, get_setting, get_xrocket_token
    from bot.services.billing import create_xrocket_payment

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

    token = get_xrocket_token()
    manual = get_setting('xrocket_manual_address', '')
    if not token and manual:
        from bot.handlers.user.payments.base import create_manual_payment_flow
        await create_manual_payment_flow(
            callback=callback, tariff=tariff, price_usd=price_usd,
            payment_type=_XR_TYPE, manual_address=manual,
            back_callback=f'renew_xrocket_tariff:{key_id}',
            key=key, vpn_key_id=key_id
        )
        return

    await create_qr_payment_flow(
        callback=callback, tariff=tariff, price_rub=price_usd,
        payment_type=_XR_TYPE,
        create_func=create_xrocket_payment,
        save_func=save_xrocket_invoice_id,
        result_key=_XR_RESULT_KEY,
        title=_XR_TITLE,
        check_prefix=_XR_CHECK_PREFIX,
        error_name=_XR_ERROR,
        qr_filename=_XR_QR_FILE,
        back_callback=f'renew_xrocket_tariff:{key_id}',
        key=key, vpn_key_id=key_id,
        hint_text=_XR_HINT,
    )


@router.callback_query(F.data.startswith('check_xrocket:'))
async def check_xrocket_payment(callback: CallbackQuery, state: FSMContext):
    """Проверяет статус xRocket-платежа по нажатию «✅ Я оплатил»."""
    await _run_xrocket_check(
        callback.message, state,
        order_id=callback.data.split(':', 1)[1],
        telegram_id=callback.from_user.id,
        callback=callback,
    )


async def _run_xrocket_check(message, state, order_id: str,
                             telegram_id: int, callback=None) -> None:
    """Общая логика проверки xRocket-платежа."""
    from bot.services.billing import check_xrocket_payment_status

    await check_qr_payment_flow(
        message=message,
        state=state,
        order_id=order_id,
        telegram_id=telegram_id,
        payment_type=_XR_TYPE,
        payment_id_field=_XR_RESULT_KEY,
        check_func=check_xrocket_payment_status,
        rate_limit_seconds=10,
        rate_limit_prefix='xrocket',
        callback=callback,
    )
