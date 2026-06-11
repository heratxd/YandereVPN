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

_TITLE = '⚡ <b>Оплата Payok</b>'
_TYPE = 'payok'
_ERROR = 'Payok'
_QR_FILE = 'payok.png'
_CHECK_PREFIX = 'check_payok'
_RESULT_KEY = 'payok_invoice_id'
_MIN_PRICE = 10
_HINT = (
    'После оплаты нажмите «✅ Я оплатил» — или просто вернитесь '
    'в бот по ссылке после оплаты, проверка запустится автоматически.'
)


@router.callback_query(F.data == 'pay_payok')
async def pay_payok_select_tariff(callback: CallbackQuery):
    """Выбор тарифа для оплаты через Payok (новый ключ)."""
    from database.requests import get_all_tariffs
    from bot.keyboards.user import tariff_select_kb
    from bot.keyboards.admin import home_only_kb

    tariffs = get_all_tariffs(include_hidden=False)
    rub_tariffs = [t for t in tariffs if t.get('price_rub') and t['price_rub'] >= _MIN_PRICE]
    if not rub_tariffs:
        await safe_edit_or_send(
            callback.message,
            f'{_TITLE}\n\n😔 Нет тарифов с ценой в рублях (от {_MIN_PRICE} ₽).\nОбратитесь к администратору.',
            reply_markup=home_only_kb()
        )
        await callback.answer()
        return
    await safe_edit_or_send(
        callback.message,
        '⚡ <b>Оплата Payok</b>\n\nВыберите тариф:\n\n'
        '<i>Оплата банковскими картами и СБП через агрегатор Payok.</i>',
        reply_markup=tariff_select_kb(rub_tariffs, is_payok=True)
    )
    await callback.answer()


@router.callback_query(F.data.startswith('payok_pay:'))
async def payok_pay_create(callback: CallbackQuery):
    """Создаёт счёт Payok для нового ключа и отправляет QR-фото."""
    from database.requests import get_tariff_by_id, save_payok_invoice_id
    from bot.services.billing import create_payok_payment

    tariff_id = int(callback.data.split(':')[1])
    tariff = get_tariff_by_id(tariff_id)
    if not tariff:
        await callback.answer('❌ Тариф не найден', show_alert=True)
        return
    price_rub = float(tariff.get('price_rub') or 0)
    if price_rub < _MIN_PRICE:
        await callback.answer(f'❌ Минимальная сумма для Payok — {_MIN_PRICE} ₽', show_alert=True)
        return

    await create_qr_payment_flow(
        callback=callback, tariff=tariff, price_rub=price_rub,
        payment_type=_TYPE,
        create_func=create_payok_payment,
        save_func=save_payok_invoice_id,
        result_key=_RESULT_KEY,
        title=_TITLE,
        check_prefix=_CHECK_PREFIX,
        error_name=_ERROR,
        qr_filename=_QR_FILE,
        back_callback='pay_payok',
        hint_text=_HINT,
    )


@router.callback_query(F.data.startswith('renew_payok_tariff:'))
async def renew_payok_select_tariff(callback: CallbackQuery):
    """Выбор тарифа для оплаты Payok при продлении ключа."""
    from database.requests import get_key_details_for_user
    from bot.keyboards.user import renew_tariff_select_kb
    from bot.utils.groups import get_tariffs_for_renewal

    key_id = int(callback.data.split(':')[1])
    key = get_key_details_for_user(key_id, callback.from_user.id)
    if not key:
        await callback.answer('❌ Ключ не найден', show_alert=True)
        return
    tariffs = get_tariffs_for_renewal(key.get('tariff_id', 0))
    rub_tariffs = [t for t in tariffs if t.get('price_rub') and t['price_rub'] >= _MIN_PRICE]
    if not rub_tariffs:
        await callback.answer(f'😔 Нет тарифов с ценой в рублях (от {_MIN_PRICE} ₽)', show_alert=True)
        return
    await safe_edit_or_send(
        callback.message,
        f"⚡ <b>Оплата Payok</b>\n\n🔑 Ключ: <b>{escape_html(key['display_name'])}</b>\n\nВыберите тариф для продления:",
        reply_markup=renew_tariff_select_kb(rub_tariffs, key_id, is_payok=True)
    )
    await callback.answer()


@router.callback_query(F.data.startswith('renew_pay_payok:'))
async def renew_payok_create(callback: CallbackQuery):
    """Создаёт счёт Payok для продления ключа."""
    from database.requests import get_tariff_by_id, get_key_details_for_user, save_payok_invoice_id
    from bot.services.billing import create_payok_payment

    parts = callback.data.split(':')
    key_id = int(parts[1])
    tariff_id = int(parts[2])
    tariff = get_tariff_by_id(tariff_id)
    key = get_key_details_for_user(key_id, callback.from_user.id)
    if not tariff or not key:
        await callback.answer('❌ Ошибка тарифа или ключа', show_alert=True)
        return
    price_rub = float(tariff.get('price_rub') or 0)
    if price_rub < _MIN_PRICE:
        await callback.answer(f'❌ Минимальная сумма для Payok — {_MIN_PRICE} ₽', show_alert=True)
        return

    await create_qr_payment_flow(
        callback=callback, tariff=tariff, price_rub=price_rub,
        payment_type=_TYPE,
        create_func=create_payok_payment,
        save_func=save_payok_invoice_id,
        result_key=_RESULT_KEY,
        title=_TITLE,
        check_prefix=_CHECK_PREFIX,
        error_name=_ERROR,
        qr_filename=_QR_FILE,
        back_callback=f'renew_payok_tariff:{key_id}',
        key=key, vpn_key_id=key_id,
        hint_text=_HINT,
    )


@router.callback_query(F.data.startswith('check_payok:'))
async def check_payok_payment(callback: CallbackQuery, state: FSMContext):
    """Проверяет статус Payok-платежа по нажатию «✅ Я оплатил»."""
    await _run_payok_check(
        callback.message, state,
        order_id=callback.data.split(':', 1)[1],
        telegram_id=callback.from_user.id,
        callback=callback,
    )


async def _run_payok_check(message, state, order_id: str,
                           telegram_id: int, callback=None) -> None:
    """Общая логика проверки Payok-платежа."""
    from bot.services.billing import check_payok_payment_status

    await check_qr_payment_flow(
        message=message,
        state=state,
        order_id=order_id,
        telegram_id=telegram_id,
        payment_type=_TYPE,
        payment_id_field=_RESULT_KEY,
        check_func=check_payok_payment_status,
        rate_limit_seconds=10,
        rate_limit_prefix='payok',
        callback=callback,
    )
