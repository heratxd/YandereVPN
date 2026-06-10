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

# Конфигурация провайдера CrystalPay
_CP_TITLE = '💎 <b>Оплата CrystalPay</b>'
_CP_TYPE = 'crystalpay'
_CP_ERROR = 'CrystalPay'
_CP_QR_FILE = 'crystalpay.png'
_CP_CHECK_PREFIX = 'check_crystalpay'
_CP_RESULT_KEY = 'crystalpay_invoice_id'
_CP_MIN_PRICE = 10
_CP_HINT = (
    'После оплаты нажмите «✅ Я оплатил» — или просто вернитесь '
    'в бот по ссылке после оплаты, проверка запустится автоматически.'
)


@router.callback_query(F.data == 'pay_crystalpay')
async def pay_crystalpay_select_tariff(callback: CallbackQuery):
    """Выбор тарифа для оплаты через CrystalPay (новый ключ)."""
    from database.requests import get_all_tariffs
    from bot.keyboards.user import tariff_select_kb
    from bot.keyboards.admin import home_only_kb

    tariffs = get_all_tariffs(include_hidden=False)
    rub_tariffs = [t for t in tariffs if t.get('price_rub') and t['price_rub'] >= _CP_MIN_PRICE]
    if not rub_tariffs:
        await safe_edit_or_send(
            callback.message,
            f'{_CP_TITLE}\n\n😔 Нет тарифов с ценой в рублях (от {_CP_MIN_PRICE} ₽).\nОбратитесь к администратору.',
            reply_markup=home_only_kb()
        )
        await callback.answer()
        return
    await safe_edit_or_send(
        callback.message,
        '💎 <b>Оплата CrystalPay</b>\n\nВыберите тариф:\n\n'
        '<i>Оплата банковской картой, СБП или криптовалютой через CrystalPay.</i>',
        reply_markup=tariff_select_kb(rub_tariffs, is_crystalpay=True)
    )
    await callback.answer()


@router.callback_query(F.data.startswith('crystalpay_pay:'))
async def crystalpay_pay_create(callback: CallbackQuery):
    """Создаёт счёт CrystalPay для нового ключа и отправляет QR-фото."""
    from database.requests import get_tariff_by_id, save_crystalpay_invoice_id
    from bot.services.billing import create_crystalpay_payment

    tariff_id = int(callback.data.split(':')[1])
    tariff = get_tariff_by_id(tariff_id)
    if not tariff:
        await callback.answer('❌ Тариф не найден', show_alert=True)
        return
    price_rub = float(tariff.get('price_rub') or 0)
    if price_rub < _CP_MIN_PRICE:
        await callback.answer(f'❌ Минимальная сумма для CrystalPay — {_CP_MIN_PRICE} ₽', show_alert=True)
        return

    await create_qr_payment_flow(
        callback=callback, tariff=tariff, price_rub=price_rub,
        payment_type=_CP_TYPE,
        create_func=create_crystalpay_payment,
        save_func=save_crystalpay_invoice_id,
        result_key=_CP_RESULT_KEY,
        title=_CP_TITLE,
        check_prefix=_CP_CHECK_PREFIX,
        error_name=_CP_ERROR,
        qr_filename=_CP_QR_FILE,
        back_callback='pay_crystalpay',
        hint_text=_CP_HINT,
    )


@router.callback_query(F.data.startswith('renew_crystalpay_tariff:'))
async def renew_crystalpay_select_tariff(callback: CallbackQuery):
    """Выбор тарифа для оплаты CrystalPay при продлении ключа."""
    from database.requests import get_key_details_for_user
    from bot.keyboards.user import renew_tariff_select_kb
    from bot.utils.groups import get_tariffs_for_renewal

    key_id = int(callback.data.split(':')[1])
    key = get_key_details_for_user(key_id, callback.from_user.id)
    if not key:
        await callback.answer('❌ Ключ не найден', show_alert=True)
        return
    tariffs = get_tariffs_for_renewal(key.get('tariff_id', 0))
    rub_tariffs = [t for t in tariffs if t.get('price_rub') and t['price_rub'] >= _CP_MIN_PRICE]
    if not rub_tariffs:
        await callback.answer(f'😔 Нет тарифов с ценой в рублях (от {_CP_MIN_PRICE} ₽)', show_alert=True)
        return
    await safe_edit_or_send(
        callback.message,
        f"💎 <b>Оплата CrystalPay</b>\n\n🔑 Ключ: <b>{escape_html(key['display_name'])}</b>\n\nВыберите тариф для продления:",
        reply_markup=renew_tariff_select_kb(rub_tariffs, key_id, is_crystalpay=True)
    )
    await callback.answer()


@router.callback_query(F.data.startswith('renew_pay_crystalpay:'))
async def renew_crystalpay_create(callback: CallbackQuery):
    """Создаёт счёт CrystalPay для продления ключа."""
    from database.requests import get_tariff_by_id, get_key_details_for_user, save_crystalpay_invoice_id
    from bot.services.billing import create_crystalpay_payment

    parts = callback.data.split(':')
    key_id = int(parts[1])
    tariff_id = int(parts[2])
    tariff = get_tariff_by_id(tariff_id)
    key = get_key_details_for_user(key_id, callback.from_user.id)
    if not tariff or not key:
        await callback.answer('❌ Ошибка тарифа или ключа', show_alert=True)
        return
    price_rub = float(tariff.get('price_rub') or 0)
    if price_rub < _CP_MIN_PRICE:
        await callback.answer(f'❌ Минимальная сумма для CrystalPay — {_CP_MIN_PRICE} ₽', show_alert=True)
        return

    await create_qr_payment_flow(
        callback=callback, tariff=tariff, price_rub=price_rub,
        payment_type=_CP_TYPE,
        create_func=create_crystalpay_payment,
        save_func=save_crystalpay_invoice_id,
        result_key=_CP_RESULT_KEY,
        title=_CP_TITLE,
        check_prefix=_CP_CHECK_PREFIX,
        error_name=_CP_ERROR,
        qr_filename=_CP_QR_FILE,
        back_callback=f'renew_crystalpay_tariff:{key_id}',
        key=key, vpn_key_id=key_id,
        hint_text=_CP_HINT,
    )


@router.callback_query(F.data.startswith('check_crystalpay:'))
async def check_crystalpay_payment(callback: CallbackQuery, state: FSMContext):
    """Проверяет статус CrystalPay-платежа по нажатию «✅ Я оплатил»."""
    await _run_crystalpay_check(
        callback.message, state,
        order_id=callback.data.split(':', 1)[1],
        telegram_id=callback.from_user.id,
        callback=callback,
    )


async def _run_crystalpay_check(message, state, order_id: str,
                                telegram_id: int, callback=None) -> None:
    """Общая логика проверки CrystalPay-платежа."""
    from bot.services.billing import check_crystalpay_payment_status

    await check_qr_payment_flow(
        message=message,
        state=state,
        order_id=order_id,
        telegram_id=telegram_id,
        payment_type=_CP_TYPE,
        payment_id_field=_CP_RESULT_KEY,
        check_func=check_crystalpay_payment_status,
        rate_limit_seconds=10,
        rate_limit_prefix='crystalpay',
        callback=callback,
    )
