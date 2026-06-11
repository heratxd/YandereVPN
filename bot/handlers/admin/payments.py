"""
Роутер раздела «Оплаты».

Обрабатывает:
- Главный экран оплат
- Toggle для Stars/Crypto
- Настройка крипто-платежей
- Редактирование крипто-настроек
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext

from config import ADMIN_IDS
from database.requests import (
    get_setting,
    set_setting,
    is_crypto_enabled,
    is_stars_enabled,
    is_cards_enabled,
    is_yookassa_qr_enabled,
    is_demo_payment_enabled,
    is_wata_enabled,
    is_platega_enabled,
    is_cardlink_enabled,
    is_cryptobot_enabled,
    is_xrocket_enabled,
    is_crystalpay_enabled,
    is_cryptobot_sandbox,
    is_xrocket_sandbox,
    is_lava_enabled,
    is_freekassa_enabled,
    is_rukassa_enabled,
    is_payok_enabled,
    is_nowpayments_enabled,
    is_robokassa_enabled,
    is_yoomoney_enabled,
    is_domain_enabled,
    get_domain_name,
    get_bot_connection_mode,
    get_ssl_mode,
)
from bot.states.admin_states import (
    AdminStates,
    CRYPTO_PARAMS,
    get_crypto_param_by_index,
    get_total_crypto_params
)
from bot.utils.admin import is_admin
from bot.keyboards.admin import (
    payments_menu_kb,
    domain_settings_kb,
    crypto_setup_kb,
    crypto_setup_confirm_kb,
    edit_crypto_kb,
    crypto_management_kb,
    cards_management_kb,
    wata_management_kb,
    platega_management_kb,
    cardlink_management_kb,
    cryptobot_management_kb,
    xrocket_management_kb,
    crystalpay_management_kb,
    lava_management_kb,
    freekassa_management_kb,
    rukassa_management_kb,
    payok_management_kb,
    nowpayments_management_kb,
    robokassa_management_kb,
    yoomoney_management_kb,
    back_and_home_kb
)
from bot.utils.text import escape_html, safe_edit_or_send

logger = logging.getLogger(__name__)


router = Router()


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================


def has_crypto_data() -> bool:
    """Проверяет, заполнены ли данные крипто-платежей в БД."""
    url = get_setting('crypto_item_url', '')
    secret = get_setting('crypto_secret_key', '')
    return bool(url and secret)


def parse_item_id_from_url(url: str) -> str:
    """
    Извлекает item_id из ссылки на товар Ya.Seller.
    
    Формат: https://t.me/Ya_SellerBot?start=item-{item_id}...
    """
    try:
        if '?start=item-' in url:
            start_part = url.split('?start=item-')[1]
            # item_id — это первая часть до следующего дефиса или конца строки
            item_id = start_part.split('-')[0]
            return item_id
        elif '?start=item0-' in url:
            # Тестовый режим
            start_part = url.split('?start=item0-')[1]
            item_id = start_part.split('-')[0]
            return item_id
    except Exception:
        pass
    return ""


# ============================================================================
# ГЛАВНЫЙ ЭКРАН ОПЛАТ
# ============================================================================

@router.callback_query(F.data == "admin_payments")
async def show_payments_menu(callback: CallbackQuery, state: FSMContext):
    """Показывает главный экран раздела оплат."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    await state.set_state(AdminStates.payments_menu)

    stars = is_stars_enabled()
    crypto = is_crypto_enabled()
    cards = is_cards_enabled()
    qr = is_yookassa_qr_enabled()
    demo = is_demo_payment_enabled()
    wata = is_wata_enabled()
    platega = is_platega_enabled()
    cardlink = is_cardlink_enabled()
    cryptobot = is_cryptobot_enabled()
    xrocket = is_xrocket_enabled()
    crystalpay = is_crystalpay_enabled()
    lava = is_lava_enabled()
    freekassa = is_freekassa_enabled()
    rukassa = is_rukassa_enabled()
    payok = is_payok_enabled()
    nowpayments = is_nowpayments_enabled()
    robokassa = is_robokassa_enabled()
    yoomoney = is_yoomoney_enabled()
    
    domain_enabled = is_domain_enabled()
    domain_name = get_domain_name()
    conn_mode = get_bot_connection_mode()
    ssl_mode = get_ssl_mode()

    text = (
        "💳 <b>Настройки оплаты</b>\n\n"
        "Здесь можно включить/выключить способы оплаты и настроить их.\n\n"
    )

    if stars:
        text += "🟢 <b>Telegram Stars</b>\n"
    else:
        text += "⚪ <b>Telegram Stars</b>\n"

    if crypto:
        item_url = get_setting('crypto_item_url', '')
        if item_url:
            text += f"🟢 <b>Крипто (@Ya_SellerBot)</b>\n<a href=\"{item_url}\">Ссылка на товар</a>\n"
        else:
            text += "🟢 <b>Крипто (@Ya_SellerBot)</b>\n"
    else:
        text += "⚪ <b>Крипто (@Ya_SellerBot)</b>\n"

    if cards:
        text += "🟢 <b>TG payments (ЮКасса Telegram Payments)</b>\n"
    else:
        text += "⚪ <b>TG payments (ЮКасса Telegram Payments)</b>\n"

    if qr:
        shop_id = get_setting('yookassa_shop_id', '')
        text += f"🟢 <b>ЮКасса (прямая/СБП)</b> | Shop ID: <code>{shop_id or '—'}</code>\n"
    else:
        text += "⚪ <b>ЮКасса (прямая/СБП)</b>\n"

    if wata:
        text += "🟢 <b>WATA (Карта/СБП)</b>\n"
    else:
        text += "⚪ <b>WATA (Карта/СБП)</b>\n"

    if platega:
        text += "🟢 <b>Platega (СБП)</b>\n"
    else:
        text += "⚪ <b>Platega (СБП)</b>\n"

    if cardlink:
        text += "🟢 <b>Cardlink (Карта/СБП)</b>\n"
    else:
        text += "⚪ <b>Cardlink (Карта/СБП)</b>\n"

    if cryptobot:
        text += f"🟢 <b>CryptoBot (USDT)</b>{' (Sandbox)' if is_cryptobot_sandbox() else ''}\n"
    else:
        text += "⚪ <b>CryptoBot (USDT)</b>\n"

    if xrocket:
        text += f"🟢 <b>xRocket (USDT)</b>{' (Sandbox)' if is_xrocket_sandbox() else ''}\n"
    else:
        text += "⚪ <b>xRocket (USDT)</b>\n"

    if crystalpay:
        text += "🟢 <b>CrystalPay (РФ/Крипта)</b>\n"
    else:
        text += "⚪ <b>CrystalPay (РФ/Крипта)</b>\n"

    if lava:
        text += "🟢 <b>Lava</b>\n"
    else:
        text += "⚪ <b>Lava</b>\n"

    if freekassa:
        text += "🟢 <b>Freekassa</b>\n"
    else:
        text += "⚪ <b>Freekassa</b>\n"

    if rukassa:
        text += "🟢 <b>RuKassa</b>\n"
    else:
        text += "⚪ <b>RuKassa</b>\n"

    if payok:
        text += "🟢 <b>Payok</b>\n"
    else:
        text += "⚪ <b>Payok</b>\n"

    if nowpayments:
        text += "🟢 <b>NowPayments</b>\n"
    else:
        text += "⚪ <b>NowPayments</b>\n"

    if robokassa:
        text += "🟢 <b>Robokassa</b>\n"
    else:
        text += "⚪ <b>Robokassa</b>\n"

    if yoomoney:
        text += "🟢 <b>ЮMoney (Кошелек)</b>\n"
    else:
        text += "⚪ <b>ЮMoney (Кошелек)</b>\n"

    if demo:
        text += "🟢 <b>Демо оплата (РФ)</b>\n"
    else:
        text += "⚪ <b>Демо оплата (РФ)</b>\n"
        
    text += f"\n🌐 <b>Домен и подключение:</b>\n"
    if domain_enabled and domain_name:
        text += f"🟢 Использование домена: <code>{domain_name}</code>\n"
    else:
        text += "🔴 Использование домена: Выключено\n"
    text += f"🔌 Режим подключения: <code>{conn_mode.upper()}</code>\n"
    text += f"🔒 Режим SSL: <code>{ssl_mode.upper()}</code>\n"

    monthly_reset = get_setting('monthly_traffic_reset_enabled', '0') == '1'

    await safe_edit_or_send(callback.message,
        text,
        reply_markup=payments_menu_kb(
            stars, crypto, cards, qr, monthly_reset, demo, wata, platega, cardlink,
            cryptobot_enabled=cryptobot, xrocket_enabled=xrocket, crystalpay_enabled=crystalpay,
            lava_enabled=lava, freekassa_enabled=freekassa, rukassa_enabled=rukassa,
            payok_enabled=payok, nowpayments_enabled=nowpayments, robokassa_enabled=robokassa,
            yoomoney_enabled=yoomoney
        )
    )
    await callback.answer()


# ============================================================================
# TOGGLE MONTHLY RESET
# ============================================================================

@router.callback_query(F.data == "admin_toggle_monthly_reset")
async def toggle_monthly_reset(callback: CallbackQuery, state: FSMContext):
    """Переключение автосброса трафика 1-го числа."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    current = get_setting('monthly_traffic_reset_enabled', '0')
    new_val = '0' if current == '1' else '1'
    set_setting('monthly_traffic_reset_enabled', new_val)
    
    # Перерисовываем меню оплат
    await show_payments_menu(callback, state)


# ============================================================================
# TOGGLE STARS
# ============================================================================

@router.callback_query(F.data == "admin_payments_toggle_stars")
async def toggle_stars(callback: CallbackQuery, state: FSMContext):
    """Переключает Telegram Stars."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    current = is_stars_enabled()
    new_value = '0' if current else '1'
    set_setting('stars_enabled', new_value)
    
    status = "включены ⭐" if new_value == '1' else "выключены"
    await callback.answer(f"Telegram Stars {status}")
    
    # Обновляем экран
    await show_payments_menu(callback, state)


# ============================================================================
# TOGGLE DEMO PAYMENT
# ============================================================================

@router.callback_query(F.data == "admin_payments_toggle_demo")
async def toggle_demo(callback: CallbackQuery, state: FSMContext):
    """Переключает демо оплату РФ картой."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    current = is_demo_payment_enabled()
    new_value = '0' if current else '1'
    set_setting('demo_payment_enabled', new_value)
    
    status = "включена" if new_value == '1' else "выключена"
    await callback.answer(f"Демо оплата {status}")
    
    # Обновляем экран
    await show_payments_menu(callback, state)


# ============================================================================
# TOGGLE CRYPTO
# ============================================================================

@router.callback_query(F.data == "admin_payments_toggle_crypto")
async def toggle_crypto(callback: CallbackQuery, state: FSMContext):
    """Открывает настройку или меню управления крипто-платежами."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    # Проверяем, есть ли данные в БД
    if has_crypto_data():
        # Если данные есть → меню управления
        await show_crypto_management_menu(callback, state)
    else:
        # Если данных нет → диалог настройки
        await start_crypto_setup(callback, state)


# ============================================================================
# НАСТРОЙКА КРИПТО-ПЛАТЕЖЕЙ
# ============================================================================

async def start_crypto_setup(callback: CallbackQuery, state: FSMContext):
    """Начинает диалог настройки крипто-платежей."""
    await state.set_state(AdminStates.crypto_setup_url)
    await state.update_data(crypto_data={}, crypto_step=1)
    
    # Получаем username бота для инструкции
    bot_username = callback.bot.my_username if hasattr(callback.bot, 'my_username') else "YOUR_BOT"
    callback_url = f"https://t.me/{bot_username}"
    
    instructions = (
        "1️⃣ В @Ya_SellerBot выберите «Управление» → «Товары» → «Добавить»\n"
        "2️⃣ Выберите тип позиции: <b>Счет</b>\n\n"
        "🎬 <b>Актуальная инструкция как добавлять:</b>\n"
        "<a href=\"https://youtu.be/cK0wX2LKxcs\">Смотреть видео</a>\n\n"
        "⚠️ <b>ВАЖНО:</b>\n"
        "• Тип позиции — именно <b>Счет</b>, а НЕ <b>Товар</b>!\n"
        "• Тарифы добавлять к позиции <b>НЕ нужно</b> — бот сам сформирует сумму оплаты.\n\n"
    )

    text = (
        "💰 <b>Настройка крипто-платежей</b>\n\n"
        "Для приёма криптовалюты мы используем @Ya_SellerBot.\n\n"
        f"{instructions}"
        "🔗 *Теперь скопируйте ссылку на позицию из бота и отправьте её мне:*"
    )
    
    await safe_edit_or_send(callback.message, 
        text,
        reply_markup=crypto_setup_kb(1)
    )


@router.message(AdminStates.crypto_setup_url)
async def process_crypto_url(message: Message, state: FSMContext):
    """Обрабатывает ввод ссылки на товар."""
    from bot.utils.text import get_message_text_for_storage
    
    url = get_message_text_for_storage(message, 'plain')
    
    # Валидация
    param = get_crypto_param_by_index(0)
    if not param['validate'](url):
        await safe_edit_or_send(message,
            f"❌ {param['error']}\n\nПопробуйте ещё раз:"
        )
        return
    
    # Удаляем сообщение
    try:
        await message.delete()
    except:
        pass
    
    # Проверяем режим
    data = await state.get_data()
    edit_mode = data.get('edit_mode', False)
    
    if edit_mode:
        # Режим редактирования - сохраняем и возвращаемся в меню
        set_setting('crypto_item_url', url)
        await state.update_data(edit_mode=False)
        
        await safe_edit_or_send(message,
            f"✅ Ссылка обновлена!\n<a href=\"{url}\">{escape_html(url)}</a>",
            force_new=True
        )
        
        # Создаём фейковый callback для показа меню
        class FakeCallback:
            def __init__(self, msg, user):
                self.message = msg
                self.from_user = user
                self.bot = msg.bot
            async def answer(self, *args, **kwargs):
                pass
        
        fake = FakeCallback(message, message.from_user)
        await show_crypto_management_menu(fake, state)
    else:
        # Режим настройки - сохраняем во временные данные
        crypto_data = data.get('crypto_data', {})
        crypto_data['crypto_item_url'] = url
        await state.update_data(crypto_data=crypto_data, crypto_step=2)
        
        # Переходим к вводу секретного ключа
        await state.set_state(AdminStates.crypto_setup_secret)
        
        bot_username = message.bot.my_username if hasattr(message.bot, 'my_username') else "YOUR_BOT"
        callback_url = f"https://t.me/{bot_username}"

        await safe_edit_or_send(message,
            f"✅ Ссылка принята!\n<a href=\"{url}\">{escape_html(url)}</a>\n\n"
            "🔔 <b>Настройка уведомлений:</b>\n"
            "В @Ya_SellerBot зайдите в настройки вашей созданной позиции → <code>Уведомления</code> → <code>Обратная ссылка</code> и укажите этот адрес:\n"
            f"<code>{callback_url}</code>\n\n"
            "🔑 <b>Ожидаю ввода секретного ключа:</b>\n"
            "Найти его можно в @Ya_SellerBot: <code>Профиль</code> → <code>Ключ подписи</code>.",
            reply_markup=crypto_setup_kb(2),
            force_new=True
        )


@router.message(AdminStates.crypto_setup_secret)
async def process_crypto_secret(message: Message, state: FSMContext):
    """Обрабатывает ввод секретного ключа."""
    from bot.utils.text import get_message_text_for_storage
    
    secret = get_message_text_for_storage(message, 'plain')
    
    # Валидация
    param = get_crypto_param_by_index(1)
    if not param['validate'](secret):
        await safe_edit_or_send(message,
            f"❌ {param['error']}\n\nПопробуйте ещё раз:"
        )
        return
    
    # Удаляем сообщение (там секретный ключ!)
    try:
        await message.delete()
    except:
        pass
    
    # Проверяем режим
    data = await state.get_data()
    edit_mode = data.get('edit_mode', False)
    
    if edit_mode:
        # Режим редактирования - сохраняем и возвращаемся в меню
        set_setting('crypto_secret_key', secret)
        await state.update_data(edit_mode=False)
        await safe_edit_or_send(message, "✅ Секретный ключ обновлён!", force_new=True)
        
        # Создаём фейковый callback для показа меню
        class FakeCallback:
            def __init__(self, msg, user):
                self.message = msg
                self.from_user = user
                self.bot = msg.bot
            async def answer(self, *args, **kwargs):
                pass
        
        fake = FakeCallback(message, message.from_user)
        await show_crypto_management_menu(fake, state)
    else:
        # Режим настройки - сохраняем во временные данные
        crypto_data = data.get('crypto_data', {})
        crypto_data['crypto_secret_key'] = secret
        await state.update_data(crypto_data=crypto_data)
        
        # Переходим к подтверждению
        await state.set_state(AdminStates.payments_menu)
        
        item_url = crypto_data.get('crypto_item_url', '')
        
        await safe_edit_or_send(message,
            "✅ <b>Все данные введены!</b>\n\n"
            f"📦 Товар: <a href=\"{item_url}\">{escape_html(item_url)}</a>\n"
            f"🔐 Ключ: <code>{'•' * 16}</code>\n\n"
            "Сохранить и включить крипто-платежи?",
            reply_markup=crypto_setup_confirm_kb(),
            force_new=True
        )


@router.callback_query(F.data == "admin_crypto_setup_back")
async def crypto_setup_back(callback: CallbackQuery, state: FSMContext):
    """Возврат на предыдущий шаг настройки крипто."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    data = await state.get_data()
    step = data.get('crypto_step', 1)
    
    if step <= 1:
        # Возврат к меню оплат
        await show_payments_menu(callback, state)
    else:
        # Возврат к вводу URL
        await state.set_state(AdminStates.crypto_setup_url)
        await state.update_data(crypto_step=1)
        await start_crypto_setup(callback, state)
    
    await callback.answer()


@router.callback_query(F.data == "admin_crypto_setup_save")
async def crypto_setup_save(callback: CallbackQuery, state: FSMContext):
    """Сохраняет настройки крипто и включает их."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    data = await state.get_data()
    crypto_data = data.get('crypto_data', {})
    
    if not crypto_data.get('crypto_item_url') or not crypto_data.get('crypto_secret_key'):
        await callback.answer("❌ Данные не полные", show_alert=True)
        return
    
    # Сохраняем
    set_setting('crypto_item_url', crypto_data['crypto_item_url'])
    set_setting('crypto_secret_key', crypto_data['crypto_secret_key'])
    set_setting('crypto_enabled', '1')
    
    await callback.answer("✅ Крипто-платежи включены!")
    
    await safe_edit_or_send(callback.message, 
        "✅ <b>Крипто-платежи настроены и включены!</b>\n\n"
        "Теперь пользователи смогут оплачивать криптовалютой."
    )
    
    # Показываем меню оплат
    await show_payments_menu(callback, state)


# ============================================================================
# МЕНЮ УПРАВЛЕНИЯ КРИПТО-ПЛАТЕЖАМИ
# ============================================================================

async def show_crypto_management_menu(callback: CallbackQuery, state: FSMContext):
    """Показывает меню управления крипто-платежами."""
    await state.set_state(AdminStates.payments_menu)
    
    is_enabled = is_crypto_enabled()
    item_url = get_setting('crypto_item_url', '')
    
    status_emoji = "🟢" if is_enabled else "⚪"
    status_text = "включены" if is_enabled else "выключены"
    
    info_text = (
        "ℹ️ Бот генерирует ссылку на оплату с указанием точной суммы в долларах (из настроек тарифа).\n\n"
        "⚠️ <b>ВАЖНО:</b> В Ya.Seller позиция обязательно должна иметь тип <b>«Счет»</b>. "
        "Тарифы к позиции добавлять не нужно — бот сам указывает сумму.\n\n"
    )
    
    if item_url:
        safe_url = escape_html(item_url)
        text = (
            "💰 <b>Управление крипто-платежами</b>\n\n"
            f"{status_emoji} Статус: <b>{status_text}</b>\n"
            f"📦 Ссылка: <a href=\"{item_url}\">{safe_url}</a>\n\n"
            f"{info_text}"
            "Выберите действие:"
        )
    else:
        text = (
            "💰 <b>Управление крипто-платежами</b>\n\n"
            f"{status_emoji} Статус: <b>{status_text}</b>\n"
            "📦 Ссылка: —\n\n"
            f"{info_text}"
            "Выберите действие:"
        )
    
    await safe_edit_or_send(callback.message, 
        text,
        reply_markup=crypto_management_kb(is_enabled)
    )
    await callback.answer()




@router.callback_query(F.data == "admin_crypto_mgmt_toggle")
async def crypto_mgmt_toggle(callback: CallbackQuery, state: FSMContext):
    """Включает/выключает крипто-платежи (без потери данных)."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    current = is_crypto_enabled()
    new_value = '0' if current else '1'
    set_setting('crypto_enabled', new_value)
    
    status = "включены ✅" if new_value == '1' else "выключены"
    await callback.answer(f"Крипто-платежи {status}")
    
    # Обновляем меню
    await show_crypto_management_menu(callback, state)


@router.callback_query(F.data == "admin_crypto_mgmt_edit_url")
async def crypto_mgmt_edit_url(callback: CallbackQuery, state: FSMContext):
    """Начинает редактирование ссылки на товар."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    await state.set_state(AdminStates.crypto_setup_url)
    await state.update_data(edit_mode=True)
    
    current_url = get_setting('crypto_item_url', '')
    
    bot_username = callback.bot.my_username if hasattr(callback.bot, 'my_username') else "YOUR_BOT"
    callback_url = f"https://t.me/{bot_username}"
    
    instructions = (
        "1️⃣ В @Ya_SellerBot выберите «Управление» → «Товары» → «Добавить»\n"
        "2️⃣ Выберите тип позиции: <b>Счет</b>\n\n"
        "🎬 <b>Актуальная инструкция как добавлять:</b>\n"
        "<a href=\"https://youtu.be/cK0wX2LKxcs\">Смотреть видео</a>\n\n"
        "⚠️ <b>ВАЖНО:</b>\n"
        "• Тип позиции — именно <b>Счет</b>, а НЕ <b>Товар</b>!\n"
        "• Тарифы добавлять к позиции <b>НЕ нужно</b> — бот сам сформирует сумму оплаты.\n\n"
    )
    
    if current_url:
        safe_url = escape_html(current_url)
        text = (
            "🔗 <b>Изменение ссылки</b>\n\n"
            f"{instructions}"
            f"Текущая ссылка: <a href=\"{current_url}\">{safe_url}</a>\n\n"
            "🔗 <b>Введите новую ссылку из @Ya_SellerBot:</b>"
        )
    else:
        text = (
            "🔗 <b>Изменение ссылки</b>\n\n"
            f"{instructions}"
            "Текущая ссылка: —\n\n"
            "🔗 <b>Введите новую ссылку из @Ya_SellerBot:</b>"
        )
    
    await safe_edit_or_send(callback.message, 
        text,
        reply_markup=back_and_home_kb("admin_crypto_management")
    )
    await callback.answer()


@router.callback_query(F.data == "admin_crypto_mgmt_edit_secret")
async def crypto_mgmt_edit_secret(callback: CallbackQuery, state: FSMContext):
    """Начинает редактирование секретного ключа."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    await state.set_state(AdminStates.crypto_setup_secret)
    await state.update_data(edit_mode=True)
    
    bot_username = callback.bot.my_username if hasattr(callback.bot, 'my_username') else "YOUR_BOT"
    callback_url = f"https://t.me/{bot_username}"

    text = (
        "🔐 <b>Изменение секретного ключа</b>\n\n"
        "🔔 <b>Настройка уведомлений:</b>\n"
        "В @Ya_SellerBot зайдите в настройки вашей созданной позиции → <code>Уведомления</code> → <code>Обратная ссылка</code> и укажите этот адрес:\n"
        f"<code>{callback_url}</code>\n\n"
        "🔑 <b>Ожидаю ввода нового секретного ключа:</b>\n"
        "Найти его можно в @Ya_SellerBot: <code>Профиль</code> → <code>Ключ подписи</code>."
    )
    
    await safe_edit_or_send(callback.message, 
        text,
        reply_markup=back_and_home_kb("admin_crypto_management")
    )
    await callback.answer()


@router.callback_query(F.data == "admin_crypto_management")
async def back_to_crypto_management(callback: CallbackQuery, state: FSMContext):
    """Возврат в меню управления крипто-платежами."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    await show_crypto_management_menu(callback, state)


# ============================================================================
# РЕДАКТИРОВАНИЕ КРИПТО-НАСТРОЕК
# ============================================================================

@router.callback_query(F.data == "admin_payments_crypto_settings")
async def start_edit_crypto(callback: CallbackQuery, state: FSMContext):
    """Начинает редактирование крипто-настроек."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    await state.set_state(AdminStates.edit_crypto)
    await state.update_data(edit_crypto_param=0)
    
    await show_crypto_edit_screen(callback, state, 0)


async def show_crypto_edit_screen(callback: CallbackQuery, state: FSMContext, param_index: int):
    """Показывает экран редактирования крипто-настройки."""
    param = get_crypto_param_by_index(param_index)
    total = get_total_crypto_params()
    
    current_value = get_setting(param['key'], '')
    
    # Маскируем секретный ключ
    if param['key'] == 'crypto_secret_key' and current_value:
        display_value = '•' * min(len(current_value), 16)
    else:
        display_value = current_value or '—'
    
    text = (
        f"⚙️ <b>Настройки крипто-платежей</b> ({param_index + 1}/{total})\n\n"
        f"📌 Параметр: <b>{param['label']}</b>\n"
        f"📝 Текущее значение: <code>{display_value}</code>\n\n"
        f"Введите новое значение или используйте кнопки навигации:\n"
        f"({param['hint']})"
    )
    
    await safe_edit_or_send(callback.message, 
        text,
        reply_markup=edit_crypto_kb(param_index, total)
    )


@router.callback_query(F.data == "admin_crypto_edit_prev")
async def crypto_edit_prev(callback: CallbackQuery, state: FSMContext):
    """Предыдущий параметр крипто-настроек."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    data = await state.get_data()
    current = data.get('edit_crypto_param', 0)
    new_param = max(0, current - 1)
    await state.update_data(edit_crypto_param=new_param)
    
    await show_crypto_edit_screen(callback, state, new_param)
    await callback.answer()


@router.callback_query(F.data == "admin_crypto_edit_next")
async def crypto_edit_next(callback: CallbackQuery, state: FSMContext):
    """Следующий параметр крипто-настроек."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    data = await state.get_data()
    current = data.get('edit_crypto_param', 0)
    total = get_total_crypto_params()
    new_param = min(total - 1, current + 1)
    await state.update_data(edit_crypto_param=new_param)
    
    await show_crypto_edit_screen(callback, state, new_param)
    await callback.answer()


@router.message(AdminStates.edit_crypto)
async def edit_crypto_value(message: Message, state: FSMContext):
    """Обрабатывает ввод нового значения крипто-настройки."""
    if not is_admin(message.from_user.id):
        return
    
    from bot.utils.text import get_message_text_for_storage
    
    data = await state.get_data()
    param_index = data.get('edit_crypto_param', 0)
    
    param = get_crypto_param_by_index(param_index)
    value = get_message_text_for_storage(message, 'plain')
    
    # Валидация
    if not param['validate'](value):
        await safe_edit_or_send(message,
            f"❌ {param['error']}"
        )
        return
    
    # Сохраняем в БД
    set_setting(param['key'], value)
    
    # Удаляем сообщение
    try:
        await message.delete()
    except:
        pass
    
    # Показываем обновлённый экран
    await safe_edit_or_send(message,
        f"✅ <b>{param['label']}</b> обновлено!",
        force_new=True
    )
    
    # Создаём фейковый callback для показа экрана
    # Это хак, но работает
    class FakeCallback:
        def __init__(self, msg, user):
            self.message = msg
            self.from_user = user
            self.bot = msg.bot
        
        async def answer(self, *args, **kwargs):
            pass
    
    fake = FakeCallback(message, message.from_user)
    await show_crypto_edit_screen(fake, state, param_index)


@router.callback_query(F.data == "admin_crypto_edit_done")
async def crypto_edit_done(callback: CallbackQuery, state: FSMContext):
    """Завершение редактирования крипто-настроек."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    await callback.answer("✅ Настройки сохранены")
    await show_payments_menu(callback, state)


# ============================================================================
# УПРАВЛЕНИЕ ОПЛАТОЙ КАРТАМИ
# ============================================================================

@router.callback_query(F.data == "admin_payments_cards")
async def show_cards_management_menu(callback: CallbackQuery, state: FSMContext):
    """Показывает меню управления оплатой картами (ЮКасса)."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.payments_menu)
    
    is_enabled = is_cards_enabled()
    token = get_setting('cards_provider_token', '')
    
    status_emoji = "🟢" if is_enabled else "⚪"
    status_text = "включено" if is_enabled else "выключено"
    
    if token:
        # Маскируем токен: первые 4 и последние 4 символа
        masked_token = f"{token[:4]}...{token[-4:]}"
        token_display = f"Установлен ✅ (<code>{masked_token}</code>)"
    else:
        token_display = "Не установлен ❌"
    
    text = (
        "💳 <b>Управление оплатой картами</b>\n\n"
        "Для работы этого способа необходимо настроить провайдера ЮКасса.\n\n"
        "❗️ <b>ШАГ 1: РЕГИСТРАЦИЯ</b>\n"
        "Обязательно <a href=\"https://yookassa.ru/joinups/?source=sva\">зарегистрируйте магазин в ЮКассе по этой ссылке</a>\n\n"
        "После проверки документов ЮКассой переходите к настройке токена.\n\n"
        f"{status_emoji} Статус: <b>{status_text}</b>\n"
        f"🔑 Provider Token: <b>{token_display}</b>\n\n"
        "Выберите действие:"
    )
    
    await safe_edit_or_send(callback.message, 
        text,
        reply_markup=cards_management_kb(is_enabled)
    )
    await callback.answer()


@router.callback_query(F.data == "admin_cards_mgmt_toggle")
async def cards_mgmt_toggle(callback: CallbackQuery, state: FSMContext):
    """Включает/выключает оплату картами."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    # Нельзя включить, если нет токена
    if not is_cards_enabled() and not get_setting('cards_provider_token', ''):
        await callback.answer("❌ Сначала укажите Provider Token!", show_alert=True)
        return

    current = is_cards_enabled()
    new_value = '0' if current else '1'
    set_setting('cards_enabled', new_value)
    
    status = "включена ✅" if new_value == '1' else "выключена"
    await callback.answer(f"Оплата картами {status}")
    
    # Обновляем меню
    await show_cards_management_menu(callback, state)


@router.callback_query(F.data == "admin_cards_mgmt_edit_token")
async def cards_mgmt_edit_token(callback: CallbackQuery, state: FSMContext):
    """Начинает редактирование токена ЮКасса."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    await state.set_state(AdminStates.cards_setup_token)
    # Сохраняем ID сообщения, чтобы потом его отредактировать
    await state.update_data(last_menu_msg_id=callback.message.message_id)
    
    text = (
        "🔗 <b>Установка Provider Token</b>\n\n"
        "❗️ <b>ШАГ 1: РЕГИСТРАЦИЯ В ЮКАССЕ</b>\n"
        "Обязательно <a href=\"https://yookassa.ru/joinups/?source=sva\">зарегистрируйтесь по этой ссылке</a>\n\n"
        "<b>ШАГ 2: ПОЛУЧЕНИЕ ТОКЕНА В @BotFather</b>\n"
        "1. Отправьте команду <code>/mybots</code> и выберите бота.\n"
        "2. Нажмите <code>Payments</code> → <code>YooKassa</code>.\n"
        "3. Подключите магазин в боте провайдера и **обязательно вернитесь в @BotFather**.\n"
        "4. В BotFather снова откройте <code>Payments</code>, там появится токен.\n\n"
        "Отправьте полученный токен ответом на это сообщение:"
    )
    
    await safe_edit_or_send(callback.message, 
        text,
        reply_markup=back_and_home_kb("admin_payments_cards")
    )
    await callback.answer()


@router.message(AdminStates.cards_setup_token)
async def cards_setup_token_value(message: Message, state: FSMContext):
    """Обрабатывает ввод токена ЮКасса."""
    from bot.utils.text import get_message_text_for_storage
    
    data = await state.get_data()
    last_menu_msg_id = data.get('last_menu_msg_id')

    token = get_message_text_for_storage(message, 'plain')
    
    if len(token) < 20 or ':' not in token:
        await safe_edit_or_send(message, "❌ Неверный формат токена. Попробуйте ещё раз:")
        return
    
    set_setting('cards_provider_token', token)
    
    try:
        await message.delete()
    except:
        pass
    
    # Если у нас есть ID сообщения меню, используем его для редактирования
    menu_message = message
    if last_menu_msg_id:
        try:
            # Создаем объект сообщения с нужным ID для редактирования
            menu_message = await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=last_menu_msg_id,
                text="⌛ Сохранение..."
            )
        except Exception:
            # Если не вышло (например, сообщение удалено), будем отвечать новым
            menu_message = await safe_edit_or_send(message, "⌛ Сохранение...", force_new=True)

    # Возвращаемся в меню через FakeCallback
    class FakeCallback:
        def __init__(self, msg, user, success_msg=None):
            self.message = msg
            self.from_user = user
            self.bot = msg.bot
            self.data = "admin_payments_cards"
            self.success_msg = success_msg
        
        async def answer(self, text=None, show_alert=False, *args, **kwargs):
            # Если передали текст для popup, запоминаем его (он будет показан при нажатии кнопок)
            # Но так как в AIOGram answerCallbackQuery работает только для реальных инстансов,
            # мы просто выведем информацию в консоль или пропустим.
            # Для пользователя мы добавим текст в само сообщение.
            pass

    fake = FakeCallback(menu_message, message.from_user)
    await show_cards_management_menu(fake, state)


# ============================================================================
# НАСТРОЙКА QR-ОПЛАТЫ ЮКАССА (прямой API)
# ============================================================================

def qr_management_kb(is_enabled: bool) -> "InlineKeyboardMarkup":
    """Клавиатура управления QR-оплатой ЮКасса."""
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    from bot.keyboards.admin import back_button, home_button

    builder = InlineKeyboardBuilder()

    toggle_text = "🔴 Выключить" if is_enabled else "🟢 Включить"
    builder.row(InlineKeyboardButton(text=toggle_text, callback_data="admin_qr_mgmt_toggle"))
    builder.row(InlineKeyboardButton(text="🏪 Изменить Shop ID", callback_data="admin_qr_edit_shop_id"))
    builder.row(InlineKeyboardButton(text="🔐 Изменить Secret Key", callback_data="admin_qr_edit_secret"))
    builder.row(back_button("admin_payments"), home_button())

    return builder.as_markup()


@router.callback_query(F.data == "admin_payments_qr")
async def show_qr_management_menu(callback: CallbackQuery, state: FSMContext):
    """Показывает меню управления QR-оплатой ЮКасса."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.payments_menu)

    from database.requests import is_yookassa_qr_enabled
    is_enabled = is_yookassa_qr_enabled()
    shop_id = get_setting('yookassa_shop_id', '')
    secret_key = get_setting('yookassa_secret_key', '')

    status_emoji = "🟢" if is_enabled else "⚪"
    status_text = "включено" if is_enabled else "выключено"

    shop_display = f"<code>{shop_id}</code>" if shop_id else "❌ Не задан"
    secret_display = f"Установлен ✅ (<code>{secret_key[:4]}...{secret_key[-4:]}</code>)" if len(secret_key) >= 8 else "❌ Не задан"

    text = (
        "📱 <b>QR-оплата ЮКасса (прямой API)</b>\n\n"
        "Позволяет принимать оплату картами и через СБП по QR-коду,\n"
        "без Telegram Payments.\n\n"
        "📋 <b>Как получить доступ:</b>\n"
        "1. Зарегистрируйте магазин: <a href=\"https://yookassa.ru/joinups/?source=sva\">yookassa.ru</a>\n"
        "2. Перейдите: Настройки → API-интеграция\n"
        "3. Скопируйте Shop ID и сгенерируйте новый Secret Key\n\n"
        f"{status_emoji} Статус: <b>{status_text}</b>\n"
        f"🏪 Shop ID: {shop_display}\n"
        f"🔑 Secret Key: {secret_display}\n\n"
        "Выберите действие:"
    )

    await safe_edit_or_send(callback.message, 
        text,
        reply_markup=qr_management_kb(is_enabled)
    )
    await callback.answer()


@router.callback_query(F.data == "admin_qr_mgmt_toggle")
async def qr_mgmt_toggle(callback: CallbackQuery, state: FSMContext):
    """Включает/выключает QR-оплату ЮКасса."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    from database.requests import is_yookassa_qr_enabled

    # Нельзя включить без реквизитов
    if not is_yookassa_qr_enabled():
        shop_id = get_setting('yookassa_shop_id', '')
        secret_key = get_setting('yookassa_secret_key', '')
        if not shop_id or not secret_key:
            await callback.answer("❌ Сначала укажите Shop ID и Secret Key!", show_alert=True)
            return

    current = is_yookassa_qr_enabled()
    new_value = '0' if current else '1'
    set_setting('yookassa_qr_enabled', new_value)

    status = "включена ✅" if new_value == '1' else "выключена"
    await callback.answer(f"QR-оплата {status}")
    await show_qr_management_menu(callback, state)


@router.callback_query(F.data == "admin_qr_edit_shop_id")
async def qr_edit_shop_id(callback: CallbackQuery, state: FSMContext):
    """Запрашивает Shop ID ЮКасса."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.qr_setup_shop_id)
    await state.update_data(last_menu_msg_id=callback.message.message_id)

    current = get_setting('yookassa_shop_id', '')
    current_display = f"\nТекущий: <code>{current}</code>" if current else ""

    await safe_edit_or_send(callback.message, 
        f"🏪 <b>Введите Shop ID ЮКасса</b>{current_display}\n\n"
        "Найдите в разделе: <b>Настройки → API-интеграция</b> вашего магазина.\n"
        "(Это числовой ID, например: <code>123456</code>)",
        reply_markup=back_and_home_kb("admin_payments_qr")
    )
    await callback.answer()


@router.message(AdminStates.qr_setup_shop_id)
async def qr_setup_shop_id_handler(message: Message, state: FSMContext):
    """Обрабатывает ввод Shop ID."""
    from bot.utils.text import get_message_text_for_storage
    
    shop_id = get_message_text_for_storage(message, 'plain')

    if not shop_id.isdigit() or len(shop_id) < 3:
        await safe_edit_or_send(message, "❌ Некорректный Shop ID. Должен быть числом (например, <code>123456</code>).")
        return

    try:
        await message.delete()
    except Exception:
        pass

    set_setting('yookassa_shop_id', shop_id)

    data = await state.get_data()
    last_menu_msg_id = data.get('last_menu_msg_id')

    class FakeCallback:
        def __init__(self, msg, user):
            self.message = msg
            self.from_user = user
            self.bot = msg.bot
        async def answer(self, *args, **kwargs):
            pass

    menu_message = message
    if last_menu_msg_id:
        try:
            menu_message = await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=last_menu_msg_id,
                text="⌛"
            )
        except Exception:
            menu_message = await safe_edit_or_send(message, "⌛", force_new=True)

    fake = FakeCallback(menu_message, message.from_user)
    await show_qr_management_menu(fake, state)



@router.callback_query(F.data == "admin_qr_edit_secret")
async def qr_edit_secret(callback: CallbackQuery, state: FSMContext):
    """Запрашивает Secret Key ЮКасса."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.qr_setup_secret_key)
    await state.update_data(last_menu_msg_id=callback.message.message_id)

    await safe_edit_or_send(callback.message, 
        "🔐 <b>Введите Secret Key ЮКасса</b>\n\n"
        "Найдите в разделе: <b>Настройки → API-интеграция</b> вашего магазина.\n"
        "_(Секретный ключ будет скрыт после сохранения)_",
        reply_markup=back_and_home_kb("admin_payments_qr")
    )
    await callback.answer()


@router.message(AdminStates.qr_setup_secret_key)
async def qr_setup_secret_key_handler(message: Message, state: FSMContext):
    """Обрабатывает ввод Secret Key."""
    from bot.utils.text import get_message_text_for_storage
    
    secret_key = get_message_text_for_storage(message, 'plain')

    if len(secret_key) < 16:
        await safe_edit_or_send(message, "❌ Слишком короткий ключ. Попробуйте ещё раз.")
        return

    try:
        await message.delete()
    except Exception:
        pass

    set_setting('yookassa_secret_key', secret_key)

    data = await state.get_data()
    last_menu_msg_id = data.get('last_menu_msg_id')

    class FakeCallback:
        def __init__(self, msg, user):
            self.message = msg
            self.from_user = user
            self.bot = msg.bot
        async def answer(self, *args, **kwargs):
            pass

    menu_message = message
    if last_menu_msg_id:
        try:
            menu_message = await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=last_menu_msg_id,
                text="⌛"
            )
        except Exception:
            menu_message = await safe_edit_or_send(message, "⌛", force_new=True)

    fake = FakeCallback(menu_message, message.from_user)
    await show_qr_management_menu(fake, state)


# ============================================================================
# НАСТРОЙКА WATA (карта/СБП через REST API)
# ============================================================================

@router.callback_query(F.data == "admin_payments_wata")
async def show_wata_management_menu(callback: CallbackQuery, state: FSMContext):
    """Показывает меню управления оплатой через WATA."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.payments_menu)

    is_enabled = is_wata_enabled()
    token = get_setting('wata_jwt_token', '') or ''

    status_emoji = "🟢" if is_enabled else "⚪"
    status_text = "включено" if is_enabled else "выключено"

    if len(token) >= 12:
        token_display = f"Установлен ✅ (<code>{escape_html(token[:6])}...{escape_html(token[-4:])}</code>)"
    elif token:
        token_display = "Установлен ✅"
    else:
        token_display = "❌ Не задан"

    text = (
        "🌊 <b>Оплата WATA (Карта/СБП)</b>\n\n"
        "Приём платежей через WATA — российский эквайринг (карты + СБП).\n"
        "Минимальная сумма платежа: <b>10 ₽</b>.\n\n"
        "📋 <b>Инструкция по подключению:</b>\n\n"
        "<b>1. Что добавить в бот перед подачей на проверку:</b>\n"
        "• <b>Документы:</b> Пользовательское соглашение и Политику конфиденциальности (ссылки доступны в руководстве пользователя ADMIN_GUIDE.md).\n"
        "• <b>Техподдержка:</b> Кнопка поддержки должна вести в личку (вашу или саппорта), а не в канал.\n"
        "• <b>Тарифы:</b> Прописать тарифы в рублях (можно просто текстом в описании бота).\n"
        "• <b>Новостной канал:</b> Укажите ссылку на свой новостной канал.\n\n"
        "<b>2. Верификационный платёж (разовый):</b>\n"
        "• Стандарт: 500$ (50.000₽)\n"
        "• <i>Платить только после одобрения проекта!</i>\n\n"
        "<b>3. Какие документы нужны:</b>\n"
        "• Никаких. Паспорта, ИП, самозанятость, банковские счета - не требуются.\n"
        "• Достаточно: Email и кошелёк TRC20 (USDT).\n\n"
        "<b>4. Подключение:</b>\n"
        "• Сайт: <a href=\"https://wata.pro/\">wata.pro</a>\n"
        "• Менеджер в Telegram: @Nikita_WATA.\n"
        "• В личном кабинете создайте JWT-токен (Профиль → API) и укажите его здесь.\n\n"
        f"{status_emoji} Статус: <b>{status_text}</b>\n"
        f"🔑 JWT-токен: {token_display}\n\n"
        "Выберите действие:"
    )

    await safe_edit_or_send(
        callback.message,
        text,
        reply_markup=wata_management_kb(is_enabled),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_wata_mgmt_toggle")
async def wata_mgmt_toggle(callback: CallbackQuery, state: FSMContext):
    """Включает/выключает оплату через WATA."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    current = is_wata_enabled()
    if not current:
        token = get_setting('wata_jwt_token', '')
        if not token or not token.strip():
            await callback.answer("❌ Сначала укажите JWT-токен!", show_alert=True)
            return

    new_value = '0' if current else '1'
    set_setting('wata_enabled', new_value)

    status = "включена ✅" if new_value == '1' else "выключена"
    await callback.answer(f"WATA-оплата {status}")
    await show_wata_management_menu(callback, state)


@router.callback_query(F.data == "admin_wata_mgmt_edit_token")
async def wata_edit_token(callback: CallbackQuery, state: FSMContext):
    """Запрашивает JWT-токен WATA."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.wata_setup_token)
    await state.update_data(last_menu_msg_id=callback.message.message_id)

    await safe_edit_or_send(
        callback.message,
        "🔑 <b>Введите JWT-токен WATA</b>\n\n"
        "Найдите в личном кабинете <a href=\"https://wata.pro\">wata.pro</a>: "
        "<b>Профиль → API</b>.\n\n"
        "<i>Токен будет частично скрыт после сохранения.</i>",
        reply_markup=back_and_home_kb("admin_payments_wata"),
    )
    await callback.answer()


@router.message(AdminStates.wata_setup_token)
async def wata_setup_token_handler(message: Message, state: FSMContext):
    """Обрабатывает ввод JWT-токена WATA."""
    from bot.utils.text import get_message_text_for_storage

    token = get_message_text_for_storage(message, 'plain').strip()

    if len(token) < 20:
        await safe_edit_or_send(message, "❌ Слишком короткий токен. Попробуйте ещё раз.")
        return

    try:
        await message.delete()
    except Exception:
        pass

    set_setting('wata_jwt_token', token)

    data = await state.get_data()
    last_menu_msg_id = data.get('last_menu_msg_id')

    class FakeCallback:
        def __init__(self, msg, user):
            self.message = msg
            self.from_user = user
            self.bot = msg.bot
        async def answer(self, *args, **kwargs):
            pass

    menu_message = message
    if last_menu_msg_id:
        try:
            menu_message = await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=last_menu_msg_id,
                text="⌛"
            )
        except Exception:
            menu_message = await safe_edit_or_send(message, "⌛", force_new=True)

    fake = FakeCallback(menu_message, message.from_user)
    await show_wata_management_menu(fake, state)


# ============================================================================
# НАСТРOЙКА PLATEGA (СБП через REST API)
# ============================================================================

@router.callback_query(F.data == "admin_payments_platega")
async def show_platega_management_menu(callback: CallbackQuery, state: FSMContext):
    """Показывает меню управления оплатой через Platega."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.payments_menu)

    is_enabled = is_platega_enabled()
    merchant_id = get_setting('platega_merchant_id', '') or ''
    secret = get_setting('platega_secret', '') or ''

    status_emoji = "🟢" if is_enabled else "⚪"
    status_text = "включено" if is_enabled else "выключено"

    if merchant_id:
        if len(merchant_id) >= 8:
            merchant_display = f"Установлен ✅ (<code>{escape_html(merchant_id[:4])}...{escape_html(merchant_id[-4:])}</code>)"
        else:
            merchant_display = "Установлен ✅"
    else:
        merchant_display = "❌ Не задан"

    if secret:
        if len(secret) >= 12:
            secret_display = f"Установлен ✅ (<code>{escape_html(secret[:4])}...{escape_html(secret[-4:])}</code>)"
        else:
            secret_display = "Установлен ✅"
    else:
        secret_display = "❌ Не задан"

    text = (
        "💸 <b>Оплата Platega (СБП)</b>\n\n"
        "Приём платежей по Системе Быстрых Платежей через Platega.\n"
        "Минимальная сумма платежа: <b>10 ₽</b>.\n\n"
        "📋 <b>Как получить доступ:</b>\n"
        "1. Напишите менеджеру <b>@platega_connect_manager</b>\n"
        "2. После подключения скопируйте <b>Merchant ID</b> и <b>Secret</b> из ЛК.\n"
        "3. Укажите их в кнопках ниже.\n\n"
        f"{status_emoji} Статус: <b>{status_text}</b>\n"
        f"🆔 Merchant ID: {merchant_display}\n"
        f"🔐 Secret: {secret_display}\n\n"
        "Выберите действие:"
    )

    await safe_edit_or_send(
        callback.message,
        text,
        reply_markup=platega_management_kb(is_enabled),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_platega_mgmt_toggle")
async def platega_mgmt_toggle(callback: CallbackQuery, state: FSMContext):
    """Включает/выключает оплату через Platega."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    current = is_platega_enabled()
    if not current:
        merchant_id = get_setting('platega_merchant_id', '')
        secret = get_setting('platega_secret', '')
        if not merchant_id or not merchant_id.strip() or not secret or not secret.strip():
            await callback.answer("❌ Сначала укажите Merchant ID и Secret!", show_alert=True)
            return

    new_value = '0' if current else '1'
    set_setting('platega_enabled', new_value)

    status = "включена ✅" if new_value == '1' else "выключена"
    await callback.answer(f"Platega-оплата {status}")
    await show_platega_management_menu(callback, state)


@router.callback_query(F.data == "admin_platega_mgmt_edit_merchant")
async def platega_edit_merchant(callback: CallbackQuery, state: FSMContext):
    """Запрашивает Merchant ID Platega."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.platega_setup_merchant)
    await state.update_data(last_menu_msg_id=callback.message.message_id)

    await safe_edit_or_send(
        callback.message,
        "🆔 <b>Введите Merchant ID Platega</b>\n\n"
        "Найдите его в личном кабинете Platega после подключения.\n\n"
        "<i>Значение будет частично скрыто после сохранения.</i>",
        reply_markup=back_and_home_kb("admin_payments_platega"),
    )
    await callback.answer()


@router.message(AdminStates.platega_setup_merchant)
async def platega_setup_merchant_handler(message: Message, state: FSMContext):
    """Обрабатывает ввод Merchant ID Platega."""
    from bot.utils.text import get_message_text_for_storage

    merchant_id = get_message_text_for_storage(message, 'plain').strip()

    if len(merchant_id) < 4:
        await safe_edit_or_send(message, "❌ Слишком короткий Merchant ID. Попробуйте ещё раз.")
        return

    try:
        await message.delete()
    except Exception:
        pass

    set_setting('platega_merchant_id', merchant_id)

    data = await state.get_data()
    last_menu_msg_id = data.get('last_menu_msg_id')

    class FakeCallback:
        def __init__(self, msg, user):
            self.message = msg
            self.from_user = user
            self.bot = msg.bot
        async def answer(self, *args, **kwargs):
            pass

    menu_message = message
    if last_menu_msg_id:
        try:
            menu_message = await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=last_menu_msg_id,
                text="⌛"
            )
        except Exception:
            menu_message = await safe_edit_or_send(message, "⌛", force_new=True)

    fake = FakeCallback(menu_message, message.from_user)
    await show_platega_management_menu(fake, state)


@router.callback_query(F.data == "admin_platega_mgmt_edit_secret")
async def platega_edit_secret(callback: CallbackQuery, state: FSMContext):
    """Запрашивает Secret Platega."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.platega_setup_secret)
    await state.update_data(last_menu_msg_id=callback.message.message_id)

    await safe_edit_or_send(
        callback.message,
        "🔐 <b>Введите Secret Platega</b>\n\n"
        "Найдите его в личном кабинете Platega после подключения.\n\n"
        "<i>Значение будет частично скрыто после сохранения.</i>",
        reply_markup=back_and_home_kb("admin_payments_platega"),
    )
    await callback.answer()


@router.message(AdminStates.platega_setup_secret)
async def platega_setup_secret_handler(message: Message, state: FSMContext):
    """Обрабатывает ввод Secret Platega."""
    from bot.utils.text import get_message_text_for_storage

    secret = get_message_text_for_storage(message, 'plain').strip()

    if len(secret) < 8:
        await safe_edit_or_send(message, "❌ Слишком короткий Secret. Попробуйте ещё раз.")
        return

    try:
        await message.delete()
    except Exception:
        pass

    set_setting('platega_secret', secret)

    data = await state.get_data()
    last_menu_msg_id = data.get('last_menu_msg_id')

    class FakeCallback:
        def __init__(self, msg, user):
            self.message = msg
            self.from_user = user
            self.bot = msg.bot
        async def answer(self, *args, **kwargs):
            pass

    menu_message = message
    if last_menu_msg_id:
        try:
            menu_message = await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=last_menu_msg_id,
                text="⌛"
            )
        except Exception:
            menu_message = await safe_edit_or_send(message, "⌛", force_new=True)

    fake = FakeCallback(menu_message, message.from_user)
    await show_platega_management_menu(fake, state)


# ============================================================================
# НАСТРOЙКА CARDLINK (Карта/СБП через REST API — cardlink.link)
# ============================================================================

@router.callback_query(F.data == "admin_payments_cardlink")
async def show_cardlink_management_menu(callback: CallbackQuery, state: FSMContext):
    """Показывает меню управления оплатой через Cardlink."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.payments_menu)

    is_enabled = is_cardlink_enabled()
    shop_id = get_setting('cardlink_shop_id', '') or ''
    api_token = get_setting('cardlink_api_token', '') or ''

    status_emoji = "🟢" if is_enabled else "⚪"
    status_text = "включено" if is_enabled else "выключено"

    if shop_id:
        if len(shop_id) >= 8:
            shop_display = f"Установлен ✅ (<code>{escape_html(shop_id[:4])}...{escape_html(shop_id[-4:])}</code>)"
        else:
            shop_display = "Установлен ✅"
    else:
        shop_display = "❌ Не задан"

    if api_token:
        if len(api_token) >= 12:
            token_display = f"Установлен ✅ (<code>{escape_html(api_token[:4])}...{escape_html(api_token[-4:])}</code>)"
        else:
            token_display = "Установлен ✅"
    else:
        token_display = "❌ Не задан"

    # bot_name для возвратных ссылок
    try:
        bot_info = await callback.bot.get_me()
        bot_username = bot_info.username or "your_bot"
    except Exception:
        bot_username = "your_bot"

    text = (
        "🔗 <b>Оплата Cardlink (Карта/СБП)</b>\n\n"
        "Приём платежей картой и через СБП по прямой интеграции с "
        "<a href=\"https://cardlink.link/\">cardlink.link</a> "
        "(без webhook — проверка по кнопке «Я оплатил» и через возвратные ссылки).\n"
        "Минимальная сумма платежа: <b>10 ₽</b>.\n\n"
        "👉 <b>Почему это рекомендуемый метод:</b> Ниже комиссии и максимально нативная интеграция "
        "с обратным переходом в бота после оплаты и автоматической проверкой платежа.\n\n"
        "📋 <b>Как получить доступ:</b>\n"
        "1. Зарегистрируйтесь на <a href=\"https://cardlink.link/\">cardlink.link</a>.\n"
        "2. После одобрения скопируйте <b>Shop ID</b> и <b>API-токен</b> из ЛК.\n"
        "3. Укажите их в кнопках ниже.\n\n"
        "🔁 <b>Возвратные ссылки</b> (указывайте в настройках магазина Cardlink):\n"
        f"• Успех — <code>https://t.me/{bot_username}?start=cl_Success</code>\n"
        f"• Ошибка — <code>https://t.me/{bot_username}?start=cl_Fail</code>\n"
        f"• Возврат — <code>https://t.me/{bot_username}?start=cl_Result</code>\n"
        "<i>Они же передаются в каждый запрос на создание платежа, поэтому "
        "настройка магазина не обязательна.</i>\n\n"
        f"{status_emoji} Статус: <b>{status_text}</b>\n"
        f"🆔 Shop ID: {shop_display}\n"
        f"🔐 API-токен: {token_display}\n\n"
        "Выберите действие:"
    )

    await safe_edit_or_send(
        callback.message,
        text,
        reply_markup=cardlink_management_kb(is_enabled),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_cardlink_mgmt_toggle")
async def cardlink_mgmt_toggle(callback: CallbackQuery, state: FSMContext):
    """Включает/выключает оплату через Cardlink."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    current = is_cardlink_enabled()
    if not current:
        shop_id = get_setting('cardlink_shop_id', '')
        api_token = get_setting('cardlink_api_token', '')
        if not shop_id or not shop_id.strip() or not api_token or not api_token.strip():
            await callback.answer("❌ Сначала укажите Shop ID и API-токен!", show_alert=True)
            return

    new_value = '0' if current else '1'
    set_setting('cardlink_enabled', new_value)

    status = "включена ✅" if new_value == '1' else "выключена"
    await callback.answer(f"Cardlink-оплата {status}")
    await show_cardlink_management_menu(callback, state)


@router.callback_query(F.data == "admin_cardlink_mgmt_edit_shop_id")
async def cardlink_edit_shop_id(callback: CallbackQuery, state: FSMContext):
    """Запрашивает Shop ID Cardlink."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.cardlink_setup_shop_id)
    await state.update_data(last_menu_msg_id=callback.message.message_id)

    await safe_edit_or_send(
        callback.message,
        "🆔 <b>Введите Shop ID Cardlink</b>\n\n"
        "Найдите его в личном кабинете на <a href=\"https://cardlink.link/\">cardlink.link</a>.\n\n"
        "<i>Значение будет частично скрыто после сохранения.</i>",
        reply_markup=back_and_home_kb("admin_payments_cardlink"),
    )
    await callback.answer()


@router.message(AdminStates.cardlink_setup_shop_id)
async def cardlink_setup_shop_id_handler(message: Message, state: FSMContext):
    """Обрабатывает ввод Shop ID Cardlink."""
    from bot.utils.text import get_message_text_for_storage

    shop_id = get_message_text_for_storage(message, 'plain').strip()

    if len(shop_id) < 4:
        await safe_edit_or_send(message, "❌ Слишком короткий Shop ID. Попробуйте ещё раз.")
        return

    try:
        await message.delete()
    except Exception:
        pass

    set_setting('cardlink_shop_id', shop_id)

    data = await state.get_data()
    last_menu_msg_id = data.get('last_menu_msg_id')

    class FakeCallback:
        def __init__(self, msg, user):
            self.message = msg
            self.from_user = user
            self.bot = msg.bot
        async def answer(self, *args, **kwargs):
            pass

    menu_message = message
    if last_menu_msg_id:
        try:
            menu_message = await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=last_menu_msg_id,
                text="⌛"
            )
        except Exception:
            menu_message = await safe_edit_or_send(message, "⌛", force_new=True)

    fake = FakeCallback(menu_message, message.from_user)
    await show_cardlink_management_menu(fake, state)


@router.callback_query(F.data == "admin_cardlink_mgmt_edit_api_token")
async def cardlink_edit_api_token(callback: CallbackQuery, state: FSMContext):
    """Запрашивает API-токен Cardlink."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.cardlink_setup_api_token)
    await state.update_data(last_menu_msg_id=callback.message.message_id)

    await safe_edit_or_send(
        callback.message,
        "🔐 <b>Введите API-токен Cardlink</b>\n\n"
        "Сгенерируйте токен в личном кабинете на <a href=\"https://cardlink.link/\">cardlink.link</a>.\n\n"
        "<i>Значение будет частично скрыто после сохранения.</i>",
        reply_markup=back_and_home_kb("admin_payments_cardlink"),
    )
    await callback.answer()


@router.message(AdminStates.cardlink_setup_api_token)
async def cardlink_setup_api_token_handler(message: Message, state: FSMContext):
    """Обрабатывает ввод API-токена Cardlink."""
    from bot.utils.text import get_message_text_for_storage

    api_token = get_message_text_for_storage(message, 'plain').strip()

    if len(api_token) < 8:
        await safe_edit_or_send(message, "❌ Слишком короткий токен. Попробуйте ещё раз.")
        return

    try:
        await message.delete()
    except Exception:
        pass

    set_setting('cardlink_api_token', api_token)

    data = await state.get_data()
    last_menu_msg_id = data.get('last_menu_msg_id')

    class FakeCallback:
        def __init__(self, msg, user):
            self.message = msg
            self.from_user = user
            self.bot = msg.bot
        async def answer(self, *args, **kwargs):
            pass

    menu_message = message
    if last_menu_msg_id:
        try:
            menu_message = await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=last_menu_msg_id,
                text="⌛"
            )
        except Exception:
            menu_message = await safe_edit_or_send(message, "⌛", force_new=True)

    fake = FakeCallback(menu_message, message.from_user)
    await show_cardlink_management_menu(fake, state)


# ============================================================================
# НАСТРОЙКА CRYPTOBOT
# ============================================================================

@router.callback_query(F.data == "admin_payments_cryptobot")
async def show_cryptobot_management_menu(callback: CallbackQuery, state: FSMContext):
    """Показывает меню управления CryptoBot."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.payments_menu)

    is_enabled = is_cryptobot_enabled()
    is_sandbox = is_cryptobot_sandbox()
    token = get_setting('cryptobot_api_token', '') or ''
    manual_addr = get_setting('cryptobot_manual_address', '') or '—'
    masked_token = f"{token[:6]}...{token[-4:]}" if len(token) > 10 else "—"

    text = (
        "🤖 <b>Управление оплатой через CryptoBot (USDT)</b>\n\n"
        f"Статус: {'🟢 Включено' if is_enabled else '⚪ Выключено'}\n"
        f"Режим: {'🧪 Sandbox (Testnet)' if is_sandbox else '🟢 Production (Mainnet)'}\n"
        f"API-токен: <code>{masked_token}</code>\n"
        f"Ручные реквизиты: <code>{manual_addr}</code>\n\n"
        "Инструкция по настройке:\n"
        "1. Перейдите в @CryptoBot (или @CryptoTestnetBot для Sandbox).\n"
        "2. Откройте Crypto Pay -> My Apps и создайте новое приложение.\n"
        "3. Скопируйте полученный API-токен и введите его здесь.\n"
        "<b>ИЛИ</b> укажите ручные реквизиты (никнейм/кошелёк) для оплаты переводом в ручном режиме."
    )

    domain_enabled = is_domain_enabled()
    domain_name = get_domain_name()
    if domain_enabled and domain_name:
        webhook_url = f"https://{domain_name}/webhook/cryptobot"
        text += f"\n\n🔗 <b>Адрес Webhook для настроек в CryptoBot:</b>\n<code>{webhook_url}</code>"
    else:
        text += "\n\n⚠️ <i>Для автоматического подтверждения оплат настройте домен в меню «Настройки домена и SSL».</i>"

    await safe_edit_or_send(
        callback.message,
        text,
        reply_markup=cryptobot_management_kb(is_enabled, is_sandbox),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_cryptobot_mgmt_toggle")
async def cryptobot_mgmt_toggle(callback: CallbackQuery, state: FSMContext):
    """Включение/выключение CryptoBot-оплаты."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    current = is_cryptobot_enabled()
    if not current:
        token = get_setting('cryptobot_api_token', '')
        manual = get_setting('cryptobot_manual_address', '')
        if not token and not manual:
            await callback.answer("⚠️ Сначала настройте API-токен или ручные реквизиты", show_alert=True)
            return

    new_value = '0' if current else '1'
    set_setting('cryptobot_enabled', new_value)
    await callback.answer("Статус CryptoBot изменён")
    await show_cryptobot_management_menu(callback, state)


@router.callback_query(F.data == "admin_cryptobot_mgmt_edit_manual")
async def cryptobot_edit_manual(callback: CallbackQuery, state: FSMContext):
    """Запрос ручных реквизитов CryptoBot."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.cryptobot_setup_manual_address)
    await state.update_data(last_menu_msg_id=callback.message.message_id)

    await safe_edit_or_send(
        callback.message,
        "📝 <b>Введите реквизиты для ручной оплаты через CryptoBot</b>\n\n"
        "Укажите ваш юзернейм (например, <code>@my_username</code>) или адрес кошелька USDT, "
        "куда пользователи должны отправлять средства.\n\n"
        "Для сброса настроек отправьте слово: <code>удалить</code>",
        reply_markup=back_and_home_kb("admin_payments_cryptobot"),
    )
    await callback.answer()


@router.message(AdminStates.cryptobot_setup_manual_address)
async def cryptobot_setup_manual_handler(message: Message, state: FSMContext):
    """Обработка ввода ручных реквизитов CryptoBot."""
    from bot.utils.text import get_message_text_for_storage
    val = get_message_text_for_storage(message, 'plain').strip()

    try:
        await message.delete()
    except Exception:
        pass

    if val.lower() == 'удалить':
        set_setting('cryptobot_manual_address', '')
    else:
        set_setting('cryptobot_manual_address', val)

    data = await state.get_data()
    last_menu_msg_id = data.get('last_menu_msg_id')

    class FakeCallback:
        def __init__(self, msg, user):
            self.message = msg
            self.from_user = user
            self.bot = msg.bot
        async def answer(self, *args, **kwargs):
            pass

    menu_message = message
    if last_menu_msg_id:
        try:
            menu_message = await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=last_menu_msg_id,
                text="⌛"
            )
        except Exception:
            menu_message = await safe_edit_or_send(message, "⌛", force_new=True)

    fake = FakeCallback(menu_message, message.from_user)
    await show_cryptobot_management_menu(fake, state)


@router.callback_query(F.data == "admin_cryptobot_mgmt_toggle_sandbox")
async def cryptobot_mgmt_toggle_sandbox(callback: CallbackQuery, state: FSMContext):
    """Переключение Sandbox (Testnet) режима для CryptoBot."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    current = is_cryptobot_sandbox()
    new_value = '0' if current else '1'
    set_setting('cryptobot_sandbox', new_value)
    await callback.answer("Режим Sandbox изменён")
    await show_cryptobot_management_menu(callback, state)


@router.callback_query(F.data == "admin_cryptobot_mgmt_edit_token")
async def cryptobot_edit_token(callback: CallbackQuery, state: FSMContext):
    """Запрос API-токена CryptoBot."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.cryptobot_setup_token)
    await state.update_data(last_menu_msg_id=callback.message.message_id)

    await safe_edit_or_send(
        callback.message,
        "🔑 <b>Введите API-токен CryptoBot</b>\n\n"
        "Отправьте токен вашего приложения из @CryptoBot или @CryptoTestnetBot.\n\n"
        "<i>Значение будет частично скрыто после сохранения.</i>",
        reply_markup=back_and_home_kb("admin_payments_cryptobot"),
    )
    await callback.answer()


@router.message(AdminStates.cryptobot_setup_token)
async def cryptobot_setup_token_handler(message: Message, state: FSMContext):
    """Обработка ввода API-токена CryptoBot."""
    from bot.utils.text import get_message_text_for_storage

    token = get_message_text_for_storage(message, 'plain').strip()

    if len(token) < 8:
        await safe_edit_or_send(message, "❌ Слишком короткий токен. Попробуйте ещё раз.")
        return

    try:
        await message.delete()
    except Exception:
        pass

    set_setting('cryptobot_api_token', token)

    data = await state.get_data()
    last_menu_msg_id = data.get('last_menu_msg_id')

    class FakeCallback:
        def __init__(self, msg, user):
            self.message = msg
            self.from_user = user
            self.bot = msg.bot
        async def answer(self, *args, **kwargs):
            pass

    menu_message = message
    if last_menu_msg_id:
        try:
            menu_message = await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=last_menu_msg_id,
                text="⌛"
            )
        except Exception:
            menu_message = await safe_edit_or_send(message, "⌛", force_new=True)

    fake = FakeCallback(menu_message, message.from_user)
    await show_cryptobot_management_menu(fake, state)


# ============================================================================
# НАСТРОЙКА XROCKET
# ============================================================================

@router.callback_query(F.data == "admin_payments_xrocket")
async def show_xrocket_management_menu(callback: CallbackQuery, state: FSMContext):
    """Показывает меню управления xRocket."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.payments_menu)

    is_enabled = is_xrocket_enabled()
    is_sandbox = is_xrocket_sandbox()
    token = get_setting('xrocket_api_key', '') or ''
    manual_addr = get_setting('xrocket_manual_address', '') or '—'
    masked_token = f"{token[:6]}...{token[-4:]}" if len(token) > 10 else "—"

    text = (
        "🚀 <b>Управление оплатой через xRocket (USDT)</b>\n\n"
        f"Статус: {'🟢 Включено' if is_enabled else '⚪ Выключено'}\n"
        f"Режим: {'🧪 Sandbox (Demo)' if is_sandbox else '🟢 Production (Mainnet)'}\n"
        f"API-ключ: <code>{masked_token}</code>\n"
        f"Ручные реквизиты: <code>{manual_addr}</code>\n\n"
        "Инструкция по настройке:\n"
        "1. Перейдите в @RocketBot (или @RocketBetaBot для Sandbox).\n"
        "2. Откройте Rocket Pay -> Web API -> Create App.\n"
        "3. Скопируйте API Key и отправьте его боту.\n"
        "<b>ИЛИ</b> укажите ручные реквизиты (никнейм/кошелёк) для оплаты переводом в ручном режиме."
    )

    domain_enabled = is_domain_enabled()
    domain_name = get_domain_name()
    if domain_enabled and domain_name:
        webhook_url = f"https://{domain_name}/webhook/xrocket"
        text += f"\n\n🔗 <b>Адрес Webhook для настроек в xRocket:</b>\n<code>{webhook_url}</code>"
    else:
        text += "\n\n⚠️ <i>Для автоматического подтверждения оплат настройте домен в меню «Настройки домена и SSL».</i>"

    await safe_edit_or_send(
        callback.message,
        text,
        reply_markup=xrocket_management_kb(is_enabled, is_sandbox),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_xrocket_mgmt_toggle")
async def xrocket_mgmt_toggle(callback: CallbackQuery, state: FSMContext):
    """Включение/выключение xRocket-оплаты."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    current = is_xrocket_enabled()
    if not current:
        token = get_setting('xrocket_api_key', '')
        manual = get_setting('xrocket_manual_address', '')
        if not token and not manual:
            await callback.answer("⚠️ Сначала настройте API-ключ или ручные реквизиты", show_alert=True)
            return

    new_value = '0' if current else '1'
    set_setting('xrocket_enabled', new_value)
    await callback.answer("Статус xRocket изменён")
    await show_xrocket_management_menu(callback, state)


@router.callback_query(F.data == "admin_xrocket_mgmt_edit_manual")
async def xrocket_edit_manual(callback: CallbackQuery, state: FSMContext):
    """Запрос ручных реквизитов xRocket."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.xrocket_setup_manual_address)
    await state.update_data(last_menu_msg_id=callback.message.message_id)

    await safe_edit_or_send(
        callback.message,
        "📝 <b>Введите реквизиты для ручной оплаты через xRocket</b>\n\n"
        "Укажите ваш юзернейм (например, <code>@my_username</code>) или адрес кошелька USDT, "
        "куда пользователи должны отправлять средства.\n\n"
        "Для сброса настроек отправьте слово: <code>удалить</code>",
        reply_markup=back_and_home_kb("admin_payments_xrocket"),
    )
    await callback.answer()


@router.message(AdminStates.xrocket_setup_manual_address)
async def xrocket_setup_manual_handler(message: Message, state: FSMContext):
    """Обработка ввода ручных реквизитов xRocket."""
    from bot.utils.text import get_message_text_for_storage
    val = get_message_text_for_storage(message, 'plain').strip()

    try:
        await message.delete()
    except Exception:
        pass

    if val.lower() == 'удалить':
        set_setting('xrocket_manual_address', '')
    else:
        set_setting('xrocket_manual_address', val)

    data = await state.get_data()
    last_menu_msg_id = data.get('last_menu_msg_id')

    class FakeCallback:
        def __init__(self, msg, user):
            self.message = msg
            self.from_user = user
            self.bot = msg.bot
        async def answer(self, *args, **kwargs):
            pass

    menu_message = message
    if last_menu_msg_id:
        try:
            menu_message = await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=last_menu_msg_id,
                text="⌛"
            )
        except Exception:
            menu_message = await safe_edit_or_send(message, "⌛", force_new=True)

    fake = FakeCallback(menu_message, message.from_user)
    await show_xrocket_management_menu(fake, state)


@router.callback_query(F.data == "admin_xrocket_mgmt_toggle_sandbox")
async def xrocket_mgmt_toggle_sandbox(callback: CallbackQuery, state: FSMContext):
    """Переключение Sandbox (Demo) режима для xRocket."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    current = is_xrocket_sandbox()
    new_value = '0' if current else '1'
    set_setting('xrocket_sandbox', new_value)
    await callback.answer("Режим Sandbox изменён")
    await show_xrocket_management_menu(callback, state)


@router.callback_query(F.data == "admin_xrocket_mgmt_edit_token")
async def xrocket_edit_token(callback: CallbackQuery, state: FSMContext):
    """Запрос API-ключа xRocket."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.xrocket_setup_token)
    await state.update_data(last_menu_msg_id=callback.message.message_id)

    await safe_edit_or_send(
        callback.message,
        "🔑 <b>Введите API-ключ xRocket</b>\n\n"
        "Отправьте ваш API-ключ (API Key) из @RocketBot или @RocketBetaBot.\n\n"
        "<i>Значение будет частично скрыто после сохранения.</i>",
        reply_markup=back_and_home_kb("admin_payments_xrocket"),
    )
    await callback.answer()


@router.message(AdminStates.xrocket_setup_token)
async def xrocket_setup_token_handler(message: Message, state: FSMContext):
    """Обработка ввода API-ключа xRocket."""
    from bot.utils.text import get_message_text_for_storage

    token = get_message_text_for_storage(message, 'plain').strip()

    if len(token) < 8:
        await safe_edit_or_send(message, "❌ Слишком короткий токен. Попробуйте ещё раз.")
        return

    try:
        await message.delete()
    except Exception:
        pass

    set_setting('xrocket_api_key', token)

    data = await state.get_data()
    last_menu_msg_id = data.get('last_menu_msg_id')

    class FakeCallback:
        def __init__(self, msg, user):
            self.message = msg
            self.from_user = user
            self.bot = msg.bot
        async def answer(self, *args, **kwargs):
            pass

    menu_message = message
    if last_menu_msg_id:
        try:
            menu_message = await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=last_menu_msg_id,
                text="⌛"
            )
        except Exception:
            menu_message = await safe_edit_or_send(message, "⌛", force_new=True)

    fake = FakeCallback(menu_message, message.from_user)
    await show_xrocket_management_menu(fake, state)


# ============================================================================
# НАСТРОЙКА CRYSTALPAY
# ============================================================================

@router.callback_query(F.data == "admin_payments_crystalpay")
async def show_crystalpay_management_menu(callback: CallbackQuery, state: FSMContext):
    """Показывает меню управления CrystalPay."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.payments_menu)

    is_enabled = is_crystalpay_enabled()
    login = get_setting('crystalpay_login', '') or ''
    secret = get_setting('crystalpay_secret', '') or ''
    masked_secret = f"{secret[:4]}...{secret[-4:]}" if len(secret) > 8 else "—"

    text = (
        "💎 <b>Управление оплатой через CrystalPay (РФ/Крипта)</b>\n\n"
        f"Статус: {'🟢 Включено' if is_enabled else '⚪ Выключено'}\n"
        f"Имя кассы (Login): <code>{login or '—'}</code>\n"
        f"Секретный ключ (Secret): <code>{masked_secret}</code>\n\n"
        "Инструкция по настройке:\n"
        "1. Перейдите на сайт crystalpay.io и создайте кассу.\n"
        "2. Скопируйте имя кассы (Login) и Секретный ключ (Secret API / Секретный ключ 1).\n"
        "3. Введите эти значения в соответствующих полях настройки."
    )

    domain_enabled = is_domain_enabled()
    domain_name = get_domain_name()
    if domain_enabled and domain_name:
        webhook_url = f"https://{domain_name}/webhook/crystalpay"
        text += f"\n\n🔗 <b>Адрес Webhook для настроек в CrystalPay:</b>\n<code>{webhook_url}</code>"
    else:
        text += "\n\n⚠️ <i>Для автоматического подтверждения оплат настройте домен в меню «Настройки домена и SSL».</i>"

    await safe_edit_or_send(
        callback.message,
        text,
        reply_markup=crystalpay_management_kb(is_enabled),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_crystalpay_mgmt_toggle")
async def crystalpay_mgmt_toggle(callback: CallbackQuery, state: FSMContext):
    """Включение/выключение CrystalPay-оплаты."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    current = is_crystalpay_enabled()
    if not current:
        login = get_setting('crystalpay_login', '')
        secret = get_setting('crystalpay_secret', '')
        if not login or not secret:
            await callback.answer("⚠️ Сначала настройте Login и Secret кассы", show_alert=True)
            return

    new_value = '0' if current else '1'
    set_setting('crystalpay_enabled', new_value)
    await callback.answer("Статус CrystalPay изменён")
    await show_crystalpay_management_menu(callback, state)


@router.callback_query(F.data == "admin_crystalpay_mgmt_edit_login")
async def crystalpay_edit_login(callback: CallbackQuery, state: FSMContext):
    """Запрос Login кассы CrystalPay."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.crystalpay_setup_login)
    await state.update_data(last_menu_msg_id=callback.message.message_id)

    await safe_edit_or_send(
        callback.message,
        "🆔 <b>Введите имя кассы (Login) CrystalPay</b>\n\n"
        "Скопируйте имя кассы (например: my_vpn_shop) из настроек CrystalPay.\n\n"
        "<i>Значение будет сохранено в базе данных.</i>",
        reply_markup=back_and_home_kb("admin_payments_crystalpay"),
    )
    await callback.answer()


@router.message(AdminStates.crystalpay_setup_login)
async def crystalpay_setup_login_handler(message: Message, state: FSMContext):
    """Обработка ввода Login CrystalPay."""
    from bot.utils.text import get_message_text_for_storage

    login = get_message_text_for_storage(message, 'plain').strip()

    if len(login) < 2:
        await safe_edit_or_send(message, "❌ Слишком короткое имя. Попробуйте ещё раз.")
        return

    try:
        await message.delete()
    except Exception:
        pass

    set_setting('crystalpay_login', login)

    data = await state.get_data()
    last_menu_msg_id = data.get('last_menu_msg_id')

    class FakeCallback:
        def __init__(self, msg, user):
            self.message = msg
            self.from_user = user
            self.bot = msg.bot
        async def answer(self, *args, **kwargs):
            pass

    menu_message = message
    if last_menu_msg_id:
        try:
            menu_message = await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=last_menu_msg_id,
                text="⌛"
            )
        except Exception:
            menu_message = await safe_edit_or_send(message, "⌛", force_new=True)

    fake = FakeCallback(menu_message, message.from_user)
    await show_crystalpay_management_menu(fake, state)


@router.callback_query(F.data == "admin_crystalpay_mgmt_edit_secret")
async def crystalpay_edit_secret(callback: CallbackQuery, state: FSMContext):
    """Запрос Secret кассы CrystalPay."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.crystalpay_setup_secret)
    await state.update_data(last_menu_msg_id=callback.message.message_id)

    await safe_edit_or_send(
        callback.message,
        "🔐 <b>Введите Секретный ключ (Secret) CrystalPay</b>\n\n"
        "Получите секретный API ключ в настройках вашей кассы на crystalpay.io.\n\n"
        "<i>Значение будет частично скрыто после сохранения.</i>",
        reply_markup=back_and_home_kb("admin_payments_crystalpay"),
    )
    await callback.answer()


@router.message(AdminStates.crystalpay_setup_secret)
async def crystalpay_setup_secret_handler(message: Message, state: FSMContext):
    """Обработка ввода Secret CrystalPay."""
    from bot.utils.text import get_message_text_for_storage

    secret = get_message_text_for_storage(message, 'plain').strip()

    if len(secret) < 8:
        await safe_edit_or_send(message, "❌ Слишком короткий секретный ключ. Попробуйте ещё раз.")
        return

    try:
        await message.delete()
    except Exception:
        pass

    set_setting('crystalpay_secret', secret)

    data = await state.get_data()
    last_menu_msg_id = data.get('last_menu_msg_id')

    class FakeCallback:
        def __init__(self, msg, user):
            self.message = msg
            self.from_user = user
            self.bot = msg.bot
        async def answer(self, *args, **kwargs):
            pass

    menu_message = message
    if last_menu_msg_id:
        try:
            menu_message = await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=last_menu_msg_id,
                text="⌛"
            )
        except Exception:
            menu_message = await safe_edit_or_send(message, "⌛", force_new=True)

    fake = FakeCallback(menu_message, message.from_user)
    await show_crystalpay_management_menu(fake, state)


# ============================================================================
# НАСТРОЙКА LAVA
# ============================================================================

@router.callback_query(F.data == "admin_payments_lava")
async def show_lava_management_menu(callback: CallbackQuery, state: FSMContext):
    """Показывает меню управления Lava."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.payments_menu)

    is_enabled = is_lava_enabled()
    shop_id = get_setting('lava_shop_id', '') or ''
    api_key = get_setting('lava_api_key', '') or ''
    masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "—"

    text = (
        "🌋 <b>Управление оплатой через Lava</b>\n\n"
        f"Статус: {'🟢 Включено' if is_enabled else '⚪ Выключено'}\n"
        f"Shop ID: <code>{shop_id or '—'}</code>\n"
        f"API-токен: <code>{masked_key}</code>\n\n"
        "Инструкция по настройке:\n"
        "1. Перейдите в личный кабинет Lava и создайте проект.\n"
        "2. Скопируйте Shop ID и API-токен.\n"
        "3. Введите эти значения в соответствующих полях настройки."
    )

    domain_enabled = is_domain_enabled()
    domain_name = get_domain_name()
    if domain_enabled and domain_name:
        webhook_url = f"https://{domain_name}/webhook/lava"
        text += f"\n\n🔗 <b>Адрес Webhook для настроек в Lava:</b>\n<code>{webhook_url}</code>"
    else:
        text += "\n\n⚠️ <i>Для автоматического подтверждения оплат настройте домен в меню «Настройки домена и SSL».</i>"

    await safe_edit_or_send(
        callback.message,
        text,
        reply_markup=lava_management_kb(is_enabled),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_lava_mgmt_toggle")
async def lava_mgmt_toggle(callback: CallbackQuery, state: FSMContext):
    """Включение/выключение Lava-оплаты."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    current = is_lava_enabled()
    if not current:
        shop_id = get_setting('lava_shop_id', '')
        api_key = get_setting('lava_api_key', '')
        if not shop_id or not api_key:
            await callback.answer("⚠️ Сначала настройте Shop ID и API-токен кассы", show_alert=True)
            return

    new_value = '0' if current else '1'
    set_setting('lava_enabled', new_value)
    await callback.answer("Статус Lava изменён")
    await show_lava_management_menu(callback, state)


@router.callback_query(F.data == "admin_lava_mgmt_edit_shop_id")
async def lava_edit_shop_id(callback: CallbackQuery, state: FSMContext):
    """Запрос Shop ID кассы Lava."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.lava_setup_shop_id)
    await state.update_data(last_menu_msg_id=callback.message.message_id)

    await safe_edit_or_send(
        callback.message,
        "🆔 <b>Введите Shop ID Lava</b>\n\n"
        "Скопируйте Shop ID из настроек Lava.\n\n"
        "<i>Значение будет сохранено в базе данных.</i>",
        reply_markup=back_and_home_kb("admin_payments_lava"),
    )
    await callback.answer()


@router.message(AdminStates.lava_setup_shop_id)
async def lava_setup_shop_id_handler(message: Message, state: FSMContext):
    """Обработка ввода Shop ID Lava."""
    from bot.utils.text import get_message_text_for_storage

    shop_id = get_message_text_for_storage(message, 'plain').strip()

    if len(shop_id) < 2:
        await safe_edit_or_send(message, "❌ Слишком короткое значение. Попробуйте ещё раз.")
        return

    try:
        await message.delete()
    except Exception:
        pass

    set_setting('lava_shop_id', shop_id)

    data = await state.get_data()
    last_menu_msg_id = data.get('last_menu_msg_id')

    class FakeCallback:
        def __init__(self, msg, user):
            self.message = msg
            self.from_user = user
            self.bot = msg.bot
        async def answer(self, *args, **kwargs):
            pass

    menu_message = message
    if last_menu_msg_id:
        try:
            menu_message = await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=last_menu_msg_id,
                text="⌛"
            )
        except Exception:
            menu_message = await safe_edit_or_send(message, "⌛", force_new=True)

    fake = FakeCallback(menu_message, message.from_user)
    await show_lava_management_menu(fake, state)


@router.callback_query(F.data == "admin_lava_mgmt_edit_api_key")
async def lava_edit_api_key(callback: CallbackQuery, state: FSMContext):
    """Запрос API-токена Lava."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.lava_setup_api_key)
    await state.update_data(last_menu_msg_id=callback.message.message_id)

    await safe_edit_or_send(
        callback.message,
        "🔑 <b>Введите API-токен Lava</b>\n\n"
        "Скопируйте API-токен из настроек Lava.\n\n"
        "<i>Значение будет частично скрыто после сохранения.</i>",
        reply_markup=back_and_home_kb("admin_payments_lava"),
    )
    await callback.answer()


@router.message(AdminStates.lava_setup_api_key)
async def lava_setup_api_key_handler(message: Message, state: FSMContext):
    """Обработка ввода API-токена Lava."""
    from bot.utils.text import get_message_text_for_storage

    api_key = get_message_text_for_storage(message, 'plain').strip()

    if len(api_key) < 4:
        await safe_edit_or_send(message, "❌ Слишком короткий ключ. Попробуйте ещё раз.")
        return

    try:
        await message.delete()
    except Exception:
        pass

    set_setting('lava_api_key', api_key)

    data = await state.get_data()
    last_menu_msg_id = data.get('last_menu_msg_id')

    class FakeCallback:
        def __init__(self, msg, user):
            self.message = msg
            self.from_user = user
            self.bot = msg.bot
        async def answer(self, *args, **kwargs):
            pass

    menu_message = message
    if last_menu_msg_id:
        try:
            menu_message = await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=last_menu_msg_id,
                text="⌛"
            )
        except Exception:
            menu_message = await safe_edit_or_send(message, "⌛", force_new=True)

    fake = FakeCallback(menu_message, message.from_user)
    await show_lava_management_menu(fake, state)


# ============================================================================
# НАСТРОЙКА FREEKASSA
# ============================================================================

@router.callback_query(F.data == "admin_payments_freekassa")
async def show_freekassa_management_menu(callback: CallbackQuery, state: FSMContext):
    """Показывает меню управления Freekassa."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.payments_menu)

    is_enabled = is_freekassa_enabled()
    shop_id = get_setting('freekassa_shop_id', '') or ''
    api_key = get_setting('freekassa_api_key', '') or ''
    secret_1 = get_setting('freekassa_secret_1', '') or ''
    secret_2 = get_setting('freekassa_secret_2', '') or ''
    
    masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "—"
    masked_sec1 = f"{secret_1[:2]}...{secret_1[-2:]}" if len(secret_1) > 4 else "—"
    masked_sec2 = f"{secret_2[:2]}...{secret_2[-2:]}" if len(secret_2) > 4 else "—"

    text = (
        "💸 <b>Управление оплатой через Freekassa</b>\n\n"
        f"Статус: {'🟢 Включено' if is_enabled else '⚪ Выключено'}\n"
        f"ID магазина (Shop ID): <code>{shop_id or '—'}</code>\n"
        f"API-ключ: <code>{masked_key}</code>\n"
        f"Секретное слово 1: <code>{masked_sec1}</code>\n"
        f"Секретное слово 2: <code>{masked_sec2}</code>\n\n"
        "Инструкция по настройке:\n"
        "1. Зарегистрируйтесь на freekassa.ru и добавьте магазин.\n"
        "2. Скопируйте ID магазина, API-ключ, Секретное слово 1 и Секретное слово 2.\n"
        "3. Введите эти значения в соответствующих полях настройки."
    )

    domain_enabled = is_domain_enabled()
    domain_name = get_domain_name()
    if domain_enabled and domain_name:
        webhook_url = f"https://{domain_name}/webhook/freekassa"
        text += f"\n\n🔗 <b>Адрес Webhook (Result URL) для настроек в Freekassa:</b>\n<code>{webhook_url}</code>"
    else:
        text += "\n\n⚠️ <i>Для автоматического подтверждения оплат настройте домен в меню «Настройки домена и SSL».</i>"

    await safe_edit_or_send(
        callback.message,
        text,
        reply_markup=freekassa_management_kb(is_enabled),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_freekassa_mgmt_toggle")
async def freekassa_mgmt_toggle(callback: CallbackQuery, state: FSMContext):
    """Включение/выключение Freekassa-оплаты."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    current = is_freekassa_enabled()
    if not current:
        shop_id = get_setting('freekassa_shop_id', '')
        api_key = get_setting('freekassa_api_key', '')
        sec1 = get_setting('freekassa_secret_1', '')
        sec2 = get_setting('freekassa_secret_2', '')
        if not shop_id or not api_key or not sec1 or not sec2:
            await callback.answer("⚠️ Сначала заполните все настройки Freekassa!", show_alert=True)
            return

    new_value = '0' if current else '1'
    set_setting('freekassa_enabled', new_value)
    await callback.answer("Статус Freekassa изменён")
    await show_freekassa_management_menu(callback, state)


@router.callback_query(F.data == "admin_freekassa_mgmt_edit_shop_id")
async def freekassa_edit_shop_id(callback: CallbackQuery, state: FSMContext):
    """Запрос Shop ID Freekassa."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.freekassa_setup_shop_id)
    await state.update_data(last_menu_msg_id=callback.message.message_id)

    await safe_edit_or_send(
        callback.message,
        "🆔 <b>Введите Shop ID Freekassa</b>\n\n"
        "Введите ID вашего магазина из личного кабинета Freekassa.",
        reply_markup=back_and_home_kb("admin_payments_freekassa"),
    )
    await callback.answer()


@router.message(AdminStates.freekassa_setup_shop_id)
async def freekassa_setup_shop_id_handler(message: Message, state: FSMContext):
    """Обработка ввода Shop ID Freekassa."""
    from bot.utils.text import get_message_text_for_storage
    val = get_message_text_for_storage(message, 'plain').strip()

    if len(val) < 1:
        await safe_edit_or_send(message, "❌ Недопустимое значение.")
        return

    try: message.delete()
    except: pass

    set_setting('freekassa_shop_id', val)
    data = await state.get_data()
    last_menu_msg_id = data.get('last_menu_msg_id')

    class FakeCallback:
        def __init__(self, msg, user):
            self.message, self.from_user, self.bot = msg, user, msg.bot
        async def answer(self, *args, **kwargs): pass

    menu_message = message
    if last_menu_msg_id:
        try: menu_message = await message.bot.edit_message_text(chat_id=message.chat.id, message_id=last_menu_msg_id, text="⌛")
        except: menu_message = await safe_edit_or_send(message, "⌛", force_new=True)

    fake = FakeCallback(menu_message, message.from_user)
    await show_freekassa_management_menu(fake, state)


@router.callback_query(F.data == "admin_freekassa_mgmt_edit_api_key")
async def freekassa_edit_api_key(callback: CallbackQuery, state: FSMContext):
    """Запрос API-ключа Freekassa."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.freekassa_setup_api_key)
    await state.update_data(last_menu_msg_id=callback.message.message_id)

    await safe_edit_or_send(
        callback.message,
        "🔑 <b>Введите API-ключ Freekassa</b>\n\n"
        "Введите API-ключ вашего аккаунта Freekassa.",
        reply_markup=back_and_home_kb("admin_payments_freekassa"),
    )
    await callback.answer()


@router.message(AdminStates.freekassa_setup_api_key)
async def freekassa_setup_api_key_handler(message: Message, state: FSMContext):
    """Обработка ввода API-ключа Freekassa."""
    from bot.utils.text import get_message_text_for_storage
    val = get_message_text_for_storage(message, 'plain').strip()

    if len(val) < 4:
        await safe_edit_or_send(message, "❌ Слишком короткий ключ.")
        return

    try: message.delete()
    except: pass

    set_setting('freekassa_api_key', val)
    data = await state.get_data()
    last_menu_msg_id = data.get('last_menu_msg_id')

    class FakeCallback:
        def __init__(self, msg, user):
            self.message, self.from_user, self.bot = msg, user, msg.bot
        async def answer(self, *args, **kwargs): pass

    menu_message = message
    if last_menu_msg_id:
        try: menu_message = await message.bot.edit_message_text(chat_id=message.chat.id, message_id=last_menu_msg_id, text="⌛")
        except: menu_message = await safe_edit_or_send(message, "⌛", force_new=True)

    fake = FakeCallback(menu_message, message.from_user)
    await show_freekassa_management_menu(fake, state)


@router.callback_query(F.data == "admin_freekassa_mgmt_edit_secret_1")
async def freekassa_edit_secret_1(callback: CallbackQuery, state: FSMContext):
    """Запрос Секретного слова 1 Freekassa."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.freekassa_setup_secret_1)
    await state.update_data(last_menu_msg_id=callback.message.message_id)

    await safe_edit_or_send(
        callback.message,
        "🔐 <b>Введите Секретное слово 1 Freekassa</b>\n\n"
        "Оно используется для инициализации платежей.",
        reply_markup=back_and_home_kb("admin_payments_freekassa"),
    )
    await callback.answer()


@router.message(AdminStates.freekassa_setup_secret_1)
async def freekassa_setup_secret_1_handler(message: Message, state: FSMContext):
    """Обработка ввода Секретного слова 1 Freekassa."""
    from bot.utils.text import get_message_text_for_storage
    val = get_message_text_for_storage(message, 'plain').strip()

    if len(val) < 2:
        await safe_edit_or_send(message, "❌ Слишком короткое значение.")
        return

    try: message.delete()
    except: pass

    set_setting('freekassa_secret_1', val)
    data = await state.get_data()
    last_menu_msg_id = data.get('last_menu_msg_id')

    class FakeCallback:
        def __init__(self, msg, user):
            self.message, self.from_user, self.bot = msg, user, msg.bot
        async def answer(self, *args, **kwargs): pass

    menu_message = message
    if last_menu_msg_id:
        try: menu_message = await message.bot.edit_message_text(chat_id=message.chat.id, message_id=last_menu_msg_id, text="⌛")
        except: menu_message = await safe_edit_or_send(message, "⌛", force_new=True)

    fake = FakeCallback(menu_message, message.from_user)
    await show_freekassa_management_menu(fake, state)


@router.callback_query(F.data == "admin_freekassa_mgmt_edit_secret_2")
async def freekassa_edit_secret_2(callback: CallbackQuery, state: FSMContext):
    """Запрос Секретного слова 2 Freekassa."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.freekassa_setup_secret_2)
    await state.update_data(last_menu_msg_id=callback.message.message_id)

    await safe_edit_or_send(
        callback.message,
        "🔐 <b>Введите Секретное слово 2 Freekassa</b>\n\n"
        "Оно используется для проверки оповещений (Result URL) от Freekassa.",
        reply_markup=back_and_home_kb("admin_payments_freekassa"),
    )
    await callback.answer()


@router.message(AdminStates.freekassa_setup_secret_2)
async def freekassa_setup_secret_2_handler(message: Message, state: FSMContext):
    """Обработка ввода Секретного слова 2 Freekassa."""
    from bot.utils.text import get_message_text_for_storage
    val = get_message_text_for_storage(message, 'plain').strip()

    if len(val) < 2:
        await safe_edit_or_send(message, "❌ Слишком короткое значение.")
        return

    try: message.delete()
    except: pass

    set_setting('freekassa_secret_2', val)
    data = await state.get_data()
    last_menu_msg_id = data.get('last_menu_msg_id')

    class FakeCallback:
        def __init__(self, msg, user):
            self.message, self.from_user, self.bot = msg, user, msg.bot
        async def answer(self, *args, **kwargs): pass

    menu_message = message
    if last_menu_msg_id:
        try: menu_message = await message.bot.edit_message_text(chat_id=message.chat.id, message_id=last_menu_msg_id, text="⌛")
        except: menu_message = await safe_edit_or_send(message, "⌛", force_new=True)

    fake = FakeCallback(menu_message, message.from_user)
    await show_freekassa_management_menu(fake, state)


# ============================================================================
# НАСТРОЙКА RUKASSA
# ============================================================================

@router.callback_query(F.data == "admin_payments_rukassa")
async def show_rukassa_management_menu(callback: CallbackQuery, state: FSMContext):
    """Показывает меню управления Rukassa."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.payments_menu)

    is_enabled = is_rukassa_enabled()
    shop_id = get_setting('rukassa_shop_id', '') or ''
    token = get_setting('rukassa_token', '') or ''
    masked_key = f"{token[:4]}...{token[-4:]}" if len(token) > 8 else "—"

    text = (
        "🇷🇺 <b>Управление оплатой через RuKassa</b>\n\n"
        f"Статус: {'🟢 Включено' if is_enabled else '⚪ Выключено'}\n"
        f"Shop ID: <code>{shop_id or '—'}</code>\n"
        f"Токен: <code>{masked_key}</code>\n\n"
        "Инструкция по настройке:\n"
        "1. Перейдите на сайт rukassa.is и создайте кассу.\n"
        "2. Скопируйте ID магазина (Shop ID) и API Токен.\n"
        "3. Укажите полученные значения здесь."
    )

    domain_enabled = is_domain_enabled()
    domain_name = get_domain_name()
    if domain_enabled and domain_name:
        webhook_url = f"https://{domain_name}/webhook/rukassa"
        text += f"\n\n🔗 <b>Адрес Webhook для настроек в RuKassa:</b>\n<code>{webhook_url}</code>"
    else:
        text += "\n\n⚠️ <i>Для автоматического подтверждения оплат настройте домен в меню «Настройки домена и SSL».</i>"

    await safe_edit_or_send(
        callback.message,
        text,
        reply_markup=rukassa_management_kb(is_enabled),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_rukassa_mgmt_toggle")
async def rukassa_mgmt_toggle(callback: CallbackQuery, state: FSMContext):
    """Включение/выключение Rukassa-оплаты."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    current = is_rukassa_enabled()
    if not current:
        shop_id = get_setting('rukassa_shop_id', '')
        token = get_setting('rukassa_token', '')
        if not shop_id or not token:
            await callback.answer("⚠️ Сначала укажите Shop ID и Токен кассы", show_alert=True)
            return

    new_value = '0' if current else '1'
    set_setting('rukassa_enabled', new_value)
    await callback.answer("Статус RuKassa изменён")
    await show_rukassa_management_menu(callback, state)


@router.callback_query(F.data == "admin_rukassa_mgmt_edit_shop_id")
async def rukassa_edit_shop_id(callback: CallbackQuery, state: FSMContext):
    """Запрос Shop ID RuKassa."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.rukassa_setup_shop_id)
    await state.update_data(last_menu_msg_id=callback.message.message_id)

    await safe_edit_or_send(
        callback.message,
        "🆔 <b>Введите Shop ID RuKassa</b>\n\n"
        "Скопируйте Shop ID вашей кассы из личного кабинета RuKassa.",
        reply_markup=back_and_home_kb("admin_payments_rukassa"),
    )
    await callback.answer()


@router.message(AdminStates.rukassa_setup_shop_id)
async def rukassa_setup_shop_id_handler(message: Message, state: FSMContext):
    """Обработка ввода Shop ID RuKassa."""
    from bot.utils.text import get_message_text_for_storage
    val = get_message_text_for_storage(message, 'plain').strip()

    if len(val) < 1:
        await safe_edit_or_send(message, "❌ Недопустимое значение.")
        return

    try: message.delete()
    except: pass

    set_setting('rukassa_shop_id', val)
    data = await state.get_data()
    last_menu_msg_id = data.get('last_menu_msg_id')

    class FakeCallback:
        def __init__(self, msg, user):
            self.message, self.from_user, self.bot = msg, user, msg.bot
        async def answer(self, *args, **kwargs): pass

    menu_message = message
    if last_menu_msg_id:
        try: menu_message = await message.bot.edit_message_text(chat_id=message.chat.id, message_id=last_menu_msg_id, text="⌛")
        except: menu_message = await safe_edit_or_send(message, "⌛", force_new=True)

    fake = FakeCallback(menu_message, message.from_user)
    await show_rukassa_management_menu(fake, state)


@router.callback_query(F.data == "admin_rukassa_mgmt_edit_token")
async def rukassa_edit_token(callback: CallbackQuery, state: FSMContext):
    """Запрос Токена RuKassa."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.rukassa_setup_token)
    await state.update_data(last_menu_msg_id=callback.message.message_id)

    await safe_edit_or_send(
        callback.message,
        "🔑 <b>Введите Токен RuKassa</b>\n\n"
        "Скопируйте API токен кассы из личного кабинета RuKassa.",
        reply_markup=back_and_home_kb("admin_payments_rukassa"),
    )
    await callback.answer()


@router.message(AdminStates.rukassa_setup_token)
async def rukassa_setup_token_handler(message: Message, state: FSMContext):
    """Обработка ввода Токена RuKassa."""
    from bot.utils.text import get_message_text_for_storage
    val = get_message_text_for_storage(message, 'plain').strip()

    if len(val) < 4:
        await safe_edit_or_send(message, "❌ Слишком короткий токен.")
        return

    try: message.delete()
    except: pass

    set_setting('rukassa_token', val)
    data = await state.get_data()
    last_menu_msg_id = data.get('last_menu_msg_id')

    class FakeCallback:
        def __init__(self, msg, user):
            self.message, self.from_user, self.bot = msg, user, msg.bot
        async def answer(self, *args, **kwargs): pass

    menu_message = message
    if last_menu_msg_id:
        try: menu_message = await message.bot.edit_message_text(chat_id=message.chat.id, message_id=last_menu_msg_id, text="⌛")
        except: menu_message = await safe_edit_or_send(message, "⌛", force_new=True)

    fake = FakeCallback(menu_message, message.from_user)
    await show_rukassa_management_menu(fake, state)


# ============================================================================
# НАСТРОЙКА PAYOK
# ============================================================================

@router.callback_query(F.data == "admin_payments_payok")
async def show_payok_management_menu(callback: CallbackQuery, state: FSMContext):
    """Показывает меню управления Payok."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.payments_menu)

    is_enabled = is_payok_enabled()
    shop_id = get_setting('payok_shop_id', '') or ''
    api_key = get_setting('payok_api_key', '') or ''
    secret_key = get_setting('payok_secret_key', '') or ''
    api_id = get_setting('payok_api_id', '') or ''

    masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "—"
    masked_sec = f"{secret_key[:4]}...{secret_key[-4:]}" if len(secret_key) > 8 else "—"

    text = (
        "⚡ <b>Управление оплатой через Payok</b>\n\n"
        f"Статус: {'🟢 Включено' if is_enabled else '⚪ Выключено'}\n"
        f"Shop ID: <code>{shop_id or '—'}</code>\n"
        f"API-ключ: <code>{masked_key}</code>\n"
        f"Секретный ключ (IPN): <code>{masked_sec}</code>\n"
        f"API ID: <code>{api_id or '—'}</code>\n\n"
        "Инструкция по настройке:\n"
        "1. Перейдите на payok.io и создайте проект.\n"
        "2. Скопируйте ID магазина, API-ключ, Секретный ключ и API ID.\n"
        "3. Введите эти значения в соответствующих полях настройки."
    )

    domain_enabled = is_domain_enabled()
    domain_name = get_domain_name()
    if domain_enabled and domain_name:
        webhook_url = f"https://{domain_name}/webhook/payok"
        text += f"\n\n🔗 <b>Адрес Webhook для настроек в Payok:</b>\n<code>{webhook_url}</code>"
    else:
        text += "\n\n⚠️ <i>Для автоматического подтверждения оплат настройте домен в меню «Настройки домена и SSL».</i>"

    await safe_edit_or_send(
        callback.message,
        text,
        reply_markup=payok_management_kb(is_enabled),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_payok_mgmt_toggle")
async def payok_mgmt_toggle(callback: CallbackQuery, state: FSMContext):
    """Включение/выключение Payok-оплаты."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    current = is_payok_enabled()
    if not current:
        shop_id = get_setting('payok_shop_id', '')
        api_key = get_setting('payok_api_key', '')
        sec = get_setting('payok_secret_key', '')
        if not shop_id or not api_key or not sec:
            await callback.answer("⚠️ Сначала настройте Shop ID, API-ключ и Секретный ключ!", show_alert=True)
            return

    new_value = '0' if current else '1'
    set_setting('payok_enabled', new_value)
    await callback.answer("Статус Payok изменён")
    await show_payok_management_menu(callback, state)


@router.callback_query(F.data == "admin_payok_mgmt_edit_shop_id")
async def payok_edit_shop_id(callback: CallbackQuery, state: FSMContext):
    """Запрос Shop ID Payok."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.payok_setup_shop_id)
    await state.update_data(last_menu_msg_id=callback.message.message_id)

    await safe_edit_or_send(
        callback.message,
        "🆔 <b>Введите Shop ID Payok</b>\n\n"
        "Введите ID проекта из настроек Payok.",
        reply_markup=back_and_home_kb("admin_payments_payok"),
    )
    await callback.answer()


@router.message(AdminStates.payok_setup_shop_id)
async def payok_setup_shop_id_handler(message: Message, state: FSMContext):
    """Обработка ввода Shop ID Payok."""
    from bot.utils.text import get_message_text_for_storage
    val = get_message_text_for_storage(message, 'plain').strip()

    if len(val) < 1:
        await safe_edit_or_send(message, "❌ Недопустимое значение.")
        return

    try: message.delete()
    except: pass

    set_setting('payok_shop_id', val)
    data = await state.get_data()
    last_menu_msg_id = data.get('last_menu_msg_id')

    class FakeCallback:
        def __init__(self, msg, user):
            self.message, self.from_user, self.bot = msg, user, msg.bot
        async def answer(self, *args, **kwargs): pass

    menu_message = message
    if last_menu_msg_id:
        try: menu_message = await message.bot.edit_message_text(chat_id=message.chat.id, message_id=last_menu_msg_id, text="⌛")
        except: menu_message = await safe_edit_or_send(message, "⌛", force_new=True)

    fake = FakeCallback(menu_message, message.from_user)
    await show_payok_management_menu(fake, state)


@router.callback_query(F.data == "admin_payok_mgmt_edit_api_key")
async def payok_edit_api_key(callback: CallbackQuery, state: FSMContext):
    """Запрос API-ключа Payok."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.payok_setup_api_key)
    await state.update_data(last_menu_msg_id=callback.message.message_id)

    await safe_edit_or_send(
        callback.message,
        "🔑 <b>Введите API-ключ Payok</b>\n\n"
        "Скопируйте API ключ из личного кабинета Payok.",
        reply_markup=back_and_home_kb("admin_payments_payok"),
    )
    await callback.answer()


@router.message(AdminStates.payok_setup_api_key)
async def payok_setup_api_key_handler(message: Message, state: FSMContext):
    """Обработка ввода API-ключа Payok."""
    from bot.utils.text import get_message_text_for_storage
    val = get_message_text_for_storage(message, 'plain').strip()

    if len(val) < 4:
        await safe_edit_or_send(message, "❌ Слишком короткий ключ.")
        return

    try: message.delete()
    except: pass

    set_setting('payok_api_key', val)
    data = await state.get_data()
    last_menu_msg_id = data.get('last_menu_msg_id')

    class FakeCallback:
        def __init__(self, msg, user):
            self.message, self.from_user, self.bot = msg, user, msg.bot
        async def answer(self, *args, **kwargs): pass

    menu_message = message
    if last_menu_msg_id:
        try: menu_message = await message.bot.edit_message_text(chat_id=message.chat.id, message_id=last_menu_msg_id, text="⌛")
        except: menu_message = await safe_edit_or_send(message, "⌛", force_new=True)

    fake = FakeCallback(menu_message, message.from_user)
    await show_payok_management_menu(fake, state)


@router.callback_query(F.data == "admin_payok_mgmt_edit_secret_key")
async def payok_edit_secret_key(callback: CallbackQuery, state: FSMContext):
    """Запрос Секретного ключа Payok."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.payok_setup_secret_key)
    await state.update_data(last_menu_msg_id=callback.message.message_id)

    await safe_edit_or_send(
        callback.message,
        "🔐 <b>Введите Секретный ключ Payok</b>\n\n"
        "Скопируйте Секретный ключ (для подписи вебхуков) из настроек проекта Payok.",
        reply_markup=back_and_home_kb("admin_payments_payok"),
    )
    await callback.answer()


@router.message(AdminStates.payok_setup_secret_key)
async def payok_setup_secret_key_handler(message: Message, state: FSMContext):
    """Обработка ввода Секретного ключа Payok."""
    from bot.utils.text import get_message_text_for_storage
    val = get_message_text_for_storage(message, 'plain').strip()

    if len(val) < 4:
        await safe_edit_or_send(message, "❌ Слишком короткий ключ.")
        return

    try: message.delete()
    except: pass

    set_setting('payok_secret_key', val)
    data = await state.get_data()
    last_menu_msg_id = data.get('last_menu_msg_id')

    class FakeCallback:
        def __init__(self, msg, user):
            self.message, self.from_user, self.bot = msg, user, msg.bot
        async def answer(self, *args, **kwargs): pass

    menu_message = message
    if last_menu_msg_id:
        try: menu_message = await message.bot.edit_message_text(chat_id=message.chat.id, message_id=last_menu_msg_id, text="⌛")
        except: menu_message = await safe_edit_or_send(message, "⌛", force_new=True)

    fake = FakeCallback(menu_message, message.from_user)
    await show_payok_management_menu(fake, state)


@router.callback_query(F.data == "admin_payok_mgmt_edit_api_id")
async def payok_edit_api_id(callback: CallbackQuery, state: FSMContext):
    """Запрос API ID Payok."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.payok_setup_api_id)
    await state.update_data(last_menu_msg_id=callback.message.message_id)

    await safe_edit_or_send(
        callback.message,
        "🆔 <b>Введите API ID Payok</b>\n\n"
        "Скопируйте API ID из личного кабинета Payok.",
        reply_markup=back_and_home_kb("admin_payments_payok"),
    )
    await callback.answer()


@router.message(AdminStates.payok_setup_api_id)
async def payok_setup_api_id_handler(message: Message, state: FSMContext):
    """Обработка ввода API ID Payok."""
    from bot.utils.text import get_message_text_for_storage
    val = get_message_text_for_storage(message, 'plain').strip()

    if len(val) < 1:
        await safe_edit_or_send(message, "❌ Недопустимое значение.")
        return

    try: message.delete()
    except: pass

    set_setting('payok_api_id', val)
    data = await state.get_data()
    last_menu_msg_id = data.get('last_menu_msg_id')

    class FakeCallback:
        def __init__(self, msg, user):
            self.message, self.from_user, self.bot = msg, user, msg.bot
        async def answer(self, *args, **kwargs): pass

    menu_message = message
    if last_menu_msg_id:
        try: menu_message = await message.bot.edit_message_text(chat_id=message.chat.id, message_id=last_menu_msg_id, text="⌛")
        except: menu_message = await safe_edit_or_send(message, "⌛", force_new=True)

    fake = FakeCallback(menu_message, message.from_user)
    await show_payok_management_menu(fake, state)


# ============================================================================
# НАСТРОЙКА NOWPAYMENTS
# ============================================================================

@router.callback_query(F.data == "admin_payments_nowpayments")
async def show_nowpayments_management_menu(callback: CallbackQuery, state: FSMContext):
    """Показывает меню управления NowPayments."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.payments_menu)

    is_enabled = is_nowpayments_enabled()
    api_key = get_setting('nowpayments_api_key', '') or ''
    ipn_secret = get_setting('nowpayments_ipn_secret', '') or ''

    masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "—"
    masked_sec = f"{ipn_secret[:4]}...{ipn_secret[-4:]}" if len(ipn_secret) > 8 else "—"

    text = (
        "🪙 <b>Управление оплатой через NowPayments (Крипта)</b>\n\n"
        f"Статус: {'🟢 Включено' if is_enabled else '⚪ Выключено'}\n"
        f"API-ключ: <code>{masked_key}</code>\n"
        f"IPN Secret: <code>{masked_sec}</code>\n\n"
        "Инструкция по настройке:\n"
        "1. Перейдите на nowpayments.io и создайте аккаунт.\n"
        "2. В настройках кабинета сгенерируйте API Key и IPN Secret.\n"
        "3. Введите полученные значения в полях ниже."
    )

    domain_enabled = is_domain_enabled()
    domain_name = get_domain_name()
    if domain_enabled and domain_name:
        webhook_url = f"https://{domain_name}/webhook/nowpayments"
        text += f"\n\n🔗 <b>Адрес Webhook (IPN URL) для настроек в NowPayments:</b>\n<code>{webhook_url}</code>"
    else:
        text += "\n\n⚠️ <i>Для автоматического подтверждения оплат настройте домен в меню «Настройки домена и SSL».</i>"

    await safe_edit_or_send(
        callback.message,
        text,
        reply_markup=nowpayments_management_kb(is_enabled),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_nowpayments_mgmt_toggle")
async def nowpayments_mgmt_toggle(callback: CallbackQuery, state: FSMContext):
    """Включение/выключение NowPayments-оплаты."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    current = is_nowpayments_enabled()
    if not current:
        api_key = get_setting('nowpayments_api_key', '')
        if not api_key:
            await callback.answer("⚠️ Сначала настройте API-ключ NowPayments", show_alert=True)
            return

    new_value = '0' if current else '1'
    set_setting('nowpayments_enabled', new_value)
    await callback.answer("Статус NowPayments изменён")
    await show_nowpayments_management_menu(callback, state)


@router.callback_query(F.data == "admin_nowpayments_mgmt_edit_api_key")
async def nowpayments_edit_api_key(callback: CallbackQuery, state: FSMContext):
    """Запрос API-ключа NowPayments."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.nowpayments_setup_api_key)
    await state.update_data(last_menu_msg_id=callback.message.message_id)

    await safe_edit_or_send(
        callback.message,
        "🔑 <b>Введите API-ключ NowPayments</b>\n\n"
        "Скопируйте API Key из вашего кабинета NowPayments.",
        reply_markup=back_and_home_kb("admin_payments_nowpayments"),
    )
    await callback.answer()


@router.message(AdminStates.nowpayments_setup_api_key)
async def nowpayments_setup_api_key_handler(message: Message, state: FSMContext):
    """Обработка ввода API-ключа NowPayments."""
    from bot.utils.text import get_message_text_for_storage
    val = get_message_text_for_storage(message, 'plain').strip()

    if len(val) < 4:
        await safe_edit_or_send(message, "❌ Слишком короткий ключ.")
        return

    try: message.delete()
    except: pass

    set_setting('nowpayments_api_key', val)
    data = await state.get_data()
    last_menu_msg_id = data.get('last_menu_msg_id')

    class FakeCallback:
        def __init__(self, msg, user):
            self.message, self.from_user, self.bot = msg, user, msg.bot
        async def answer(self, *args, **kwargs): pass

    menu_message = message
    if last_menu_msg_id:
        try: menu_message = await message.bot.edit_message_text(chat_id=message.chat.id, message_id=last_menu_msg_id, text="⌛")
        except: menu_message = await safe_edit_or_send(message, "⌛", force_new=True)

    fake = FakeCallback(menu_message, message.from_user)
    await show_nowpayments_management_menu(fake, state)


@router.callback_query(F.data == "admin_nowpayments_mgmt_edit_ipn_secret")
async def nowpayments_edit_ipn_secret(callback: CallbackQuery, state: FSMContext):
    """Запрос IPN Secret NowPayments."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.nowpayments_setup_ipn_secret)
    await state.update_data(last_menu_msg_id=callback.message.message_id)

    await safe_edit_or_send(
        callback.message,
        "🔐 <b>Введите IPN Secret NowPayments</b>\n\n"
        "Скопируйте Instant Payment Notifications (IPN) secret key из настроек кабинета NowPayments.",
        reply_markup=back_and_home_kb("admin_payments_nowpayments"),
    )
    await callback.answer()


@router.message(AdminStates.nowpayments_setup_ipn_secret)
async def nowpayments_setup_ipn_secret_handler(message: Message, state: FSMContext):
    """Обработка ввода IPN Secret NowPayments."""
    from bot.utils.text import get_message_text_for_storage
    val = get_message_text_for_storage(message, 'plain').strip()

    if len(val) < 4:
        await safe_edit_or_send(message, "❌ Слишком короткое значение.")
        return

    try: message.delete()
    except: pass

    set_setting('nowpayments_ipn_secret', val)
    data = await state.get_data()
    last_menu_msg_id = data.get('last_menu_msg_id')

    class FakeCallback:
        def __init__(self, msg, user):
            self.message, self.from_user, self.bot = msg, user, msg.bot
        async def answer(self, *args, **kwargs): pass

    menu_message = message
    if last_menu_msg_id:
        try: menu_message = await message.bot.edit_message_text(chat_id=message.chat.id, message_id=last_menu_msg_id, text="⌛")
        except: menu_message = await safe_edit_or_send(message, "⌛", force_new=True)

    fake = FakeCallback(menu_message, message.from_user)
    await show_nowpayments_management_menu(fake, state)


# ============================================================================
# НАСТРОЙКА ROBOKASSA
# ============================================================================

@router.callback_query(F.data == "admin_payments_robokassa")
async def show_robokassa_management_menu(callback: CallbackQuery, state: FSMContext):
    """Показывает меню управления Robokassa."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.payments_menu)

    is_enabled = is_robokassa_enabled()
    login = get_setting('robokassa_login', '') or ''
    pass1 = get_setting('robokassa_password_1', '') or ''
    pass2 = get_setting('robokassa_password_2', '') or ''

    masked_p1 = f"{pass1[:2]}...{pass1[-2:]}" if len(pass1) > 4 else "—"
    masked_p2 = f"{pass2[:2]}...{pass2[-2:]}" if len(pass2) > 4 else "—"

    text = (
        "🔴 <b>Управление оплатой через Robokassa</b>\n\n"
        f"Статус: {'🟢 Включено' if is_enabled else '⚪ Выключено'}\n"
        f"Идентификатор магазина (Login): <code>{login or '—'}</code>\n"
        f"Пароль 1: <code>{masked_p1}</code>\n"
        f"Пароль 2: <code>{masked_p2}</code>\n\n"
        "Инструкция по настройке:\n"
        "1. Перейдите на robokassa.com и зарегистрируйте магазин.\n"
        "2. В настройках магазина скопируйте Идентификатор, сгенерируйте Пароль 1 и Пароль 2.\n"
        "3. Введите полученные значения здесь."
    )

    domain_enabled = is_domain_enabled()
    domain_name = get_domain_name()
    if domain_enabled and domain_name:
        webhook_url = f"https://{domain_name}/webhook/robokassa"
        text += f"\n\n🔗 <b>Адрес Webhook (Result URL) для настроек в Robokassa:</b>\n<code>{webhook_url}</code>"
    else:
        text += "\n\n⚠️ <i>Для автоматического подтверждения оплат настройте домен в меню «Настройки домена и SSL».</i>"

    await safe_edit_or_send(
        callback.message,
        text,
        reply_markup=robokassa_management_kb(is_enabled),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_robokassa_mgmt_toggle")
async def robokassa_mgmt_toggle(callback: CallbackQuery, state: FSMContext):
    """Включение/выключение Robokassa-оплаты."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    current = is_robokassa_enabled()
    if not current:
        login = get_setting('robokassa_login', '')
        p1 = get_setting('robokassa_password_1', '')
        p2 = get_setting('robokassa_password_2', '')
        if not login or not p1 or not p2:
            await callback.answer("⚠️ Сначала настройте Login, Пароль 1 и Пароль 2!", show_alert=True)
            return

    new_value = '0' if current else '1'
    set_setting('robokassa_enabled', new_value)
    await callback.answer("Статус Robokassa изменён")
    await show_robokassa_management_menu(callback, state)


@router.callback_query(F.data == "admin_robokassa_mgmt_edit_login")
async def robokassa_edit_login(callback: CallbackQuery, state: FSMContext):
    """Запрос Login Robokassa."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.robokassa_setup_login)
    await state.update_data(last_menu_msg_id=callback.message.message_id)

    await safe_edit_or_send(
        callback.message,
        "🆔 <b>Введите Идентификатор магазина (Login) Robokassa</b>\n\n"
        "Скопируйте Идентификатор магазина из личного кабинета Robokassa.",
        reply_markup=back_and_home_kb("admin_payments_robokassa"),
    )
    await callback.answer()


@router.message(AdminStates.robokassa_setup_login)
async def robokassa_setup_login_handler(message: Message, state: FSMContext):
    """Обработка ввода Login Robokassa."""
    from bot.utils.text import get_message_text_for_storage
    val = get_message_text_for_storage(message, 'plain').strip()

    if len(val) < 1:
        await safe_edit_or_send(message, "❌ Недопустимое значение.")
        return

    try: message.delete()
    except: pass

    set_setting('robokassa_login', val)
    data = await state.get_data()
    last_menu_msg_id = data.get('last_menu_msg_id')

    class FakeCallback:
        def __init__(self, msg, user):
            self.message, self.from_user, self.bot = msg, user, msg.bot
        async def answer(self, *args, **kwargs): pass

    menu_message = message
    if last_menu_msg_id:
        try: menu_message = await message.bot.edit_message_text(chat_id=message.chat.id, message_id=last_menu_msg_id, text="⌛")
        except: menu_message = await safe_edit_or_send(message, "⌛", force_new=True)

    fake = FakeCallback(menu_message, message.from_user)
    await show_robokassa_management_menu(fake, state)


@router.callback_query(F.data == "admin_robokassa_mgmt_edit_password_1")
async def robokassa_edit_password_1(callback: CallbackQuery, state: FSMContext):
    """Запрос Пароля 1 Robokassa."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.robokassa_setup_password_1)
    await state.update_data(last_menu_msg_id=callback.message.message_id)

    await safe_edit_or_send(
        callback.message,
        "🔐 <b>Введите Пароль 1 Robokassa</b>\n\n"
        "Используется для подписи запросов на оплату (вводится в настройках Robokassa).",
        reply_markup=back_and_home_kb("admin_payments_robokassa"),
    )
    await callback.answer()


@router.message(AdminStates.robokassa_setup_password_1)
async def robokassa_setup_password_1_handler(message: Message, state: FSMContext):
    """Обработка ввода Пароля 1 Robokassa."""
    from bot.utils.text import get_message_text_for_storage
    val = get_message_text_for_storage(message, 'plain').strip()

    if len(val) < 4:
        await safe_edit_or_send(message, "❌ Слишком короткое значение.")
        return

    try: message.delete()
    except: pass

    set_setting('robokassa_password_1', val)
    data = await state.get_data()
    last_menu_msg_id = data.get('last_menu_msg_id')

    class FakeCallback:
        def __init__(self, msg, user):
            self.message, self.from_user, self.bot = msg, user, msg.bot
        async def answer(self, *args, **kwargs): pass

    menu_message = message
    if last_menu_msg_id:
        try: menu_message = await message.bot.edit_message_text(chat_id=message.chat.id, message_id=last_menu_msg_id, text="⌛")
        except: menu_message = await safe_edit_or_send(message, "⌛", force_new=True)

    fake = FakeCallback(menu_message, message.from_user)
    await show_robokassa_management_menu(fake, state)


@router.callback_query(F.data == "admin_robokassa_mgmt_edit_password_2")
async def robokassa_edit_password_2(callback: CallbackQuery, state: FSMContext):
    """Запрос Пароля 2 Robokassa."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.robokassa_setup_password_2)
    await state.update_data(last_menu_msg_id=callback.message.message_id)

    await safe_edit_or_send(
        callback.message,
        "🔐 <b>Введите Пароль 2 Robokassa</b>\n\n"
        "Используется для проверки входящих оповещений (Result URL) от Robokassa.",
        reply_markup=back_and_home_kb("admin_payments_robokassa"),
    )
    await callback.answer()


@router.message(AdminStates.robokassa_setup_password_2)
async def robokassa_setup_password_2_handler(message: Message, state: FSMContext):
    """Обработка ввода Пароля 2 Robokassa."""
    from bot.utils.text import get_message_text_for_storage
    val = get_message_text_for_storage(message, 'plain').strip()

    if len(val) < 4:
        await safe_edit_or_send(message, "❌ Слишком короткое значение.")
        return

    try: message.delete()
    except: pass

    set_setting('robokassa_password_2', val)
    data = await state.get_data()
    last_menu_msg_id = data.get('last_menu_msg_id')

    class FakeCallback:
        def __init__(self, msg, user):
            self.message, self.from_user, self.bot = msg, user, msg.bot
        async def answer(self, *args, **kwargs): pass

    menu_message = message
    if last_menu_msg_id:
        try: menu_message = await message.bot.edit_message_text(chat_id=message.chat.id, message_id=last_menu_msg_id, text="⌛")
        except: menu_message = await safe_edit_or_send(message, "⌛", force_new=True)

    fake = FakeCallback(menu_message, message.from_user)
    await show_robokassa_management_menu(fake, state)


# ============================================================================
# НАСТРОЙКА YOOMONEY
# ============================================================================

@router.callback_query(F.data == "admin_payments_yoomoney")
async def show_yoomoney_management_menu(callback: CallbackQuery, state: FSMContext):
    """Показывает меню управления YooMoney (ЮMoney)."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.payments_menu)

    is_enabled = is_yoomoney_enabled()
    wallet = get_setting('yoomoney_wallet', '') or ''
    secret = get_setting('yoomoney_secret', '') or ''
    masked_sec = f"{secret[:4]}...{secret[-4:]}" if len(secret) > 8 else "—"

    text = (
        "🟣 <b>Управление оплатой через ЮMoney (Кошелек)</b>\n\n"
        f"Статус: {'🟢 Включено' if is_enabled else '⚪ Выключено'}\n"
        f"Номер кошелька: <code>{wallet or '—'}</code>\n"
        f"Секретный ключ (IPN): <code>{masked_sec}</code>\n\n"
        "Инструкция по настройке:\n"
        "1. Перейдите на yoomoney.ru и войдите в свой кошелек.\n"
        "2. Скопируйте номер вашего кошелька.\n"
        "3. Перейдите в настройки уведомлений ЮMoney, вставьте адрес Webhook и скопируйте секрет оповещений.\n"
        "4. Введите полученные значения в кнопках ниже."
    )

    domain_enabled = is_domain_enabled()
    domain_name = get_domain_name()
    if domain_enabled and domain_name:
        webhook_url = f"https://{domain_name}/webhook/yoomoney"
        text += f"\n\n🔗 <b>Адрес Webhook (IPN) для настроек в ЮMoney:</b>\n<code>{webhook_url}</code>"
    else:
        text += "\n\n⚠️ <i>Для автоматического подтверждения оплат настройте домен в меню «Настройки домена и SSL».</i>"

    await safe_edit_or_send(
        callback.message,
        text,
        reply_markup=yoomoney_management_kb(is_enabled),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_yoomoney_mgmt_toggle")
async def yoomoney_mgmt_toggle(callback: CallbackQuery, state: FSMContext):
    """Включение/выключение ЮMoney-оплаты."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    current = is_yoomoney_enabled()
    if not current:
        wallet = get_setting('yoomoney_wallet', '')
        secret = get_setting('yoomoney_secret', '')
        if not wallet or not secret:
            await callback.answer("⚠️ Сначала настройте номер кошелька и секретный ключ (IPN)!", show_alert=True)
            return

    new_value = '0' if current else '1'
    set_setting('yoomoney_enabled', new_value)
    await callback.answer("Статус ЮMoney изменён")
    await show_yoomoney_management_menu(callback, state)


@router.callback_query(F.data == "admin_yoomoney_mgmt_edit_wallet")
async def yoomoney_edit_wallet(callback: CallbackQuery, state: FSMContext):
    """Запрос номера кошелька ЮMoney."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.yoomoney_setup_wallet)
    await state.update_data(last_menu_msg_id=callback.message.message_id)

    await safe_edit_or_send(
        callback.message,
        "🆔 <b>Введите номер кошелька ЮMoney</b>\n\n"
        "Например: <code>41001xxxxxxxxxx</code>",
        reply_markup=back_and_home_kb("admin_payments_yoomoney"),
    )
    await callback.answer()


@router.message(AdminStates.yoomoney_setup_wallet)
async def yoomoney_setup_wallet_handler(message: Message, state: FSMContext):
    """Обработка ввода кошелька ЮMoney."""
    from bot.utils.text import get_message_text_for_storage
    val = get_message_text_for_storage(message, 'plain').strip()

    if len(val) < 8:
        await safe_edit_or_send(message, "❌ Слишком короткое значение.")
        return

    try: message.delete()
    except: pass

    set_setting('yoomoney_wallet', val)
    data = await state.get_data()
    last_menu_msg_id = data.get('last_menu_msg_id')

    class FakeCallback:
        def __init__(self, msg, user):
            self.message, self.from_user, self.bot = msg, user, msg.bot
        async def answer(self, *args, **kwargs): pass

    menu_message = message
    if last_menu_msg_id:
        try: menu_message = await message.bot.edit_message_text(chat_id=message.chat.id, message_id=last_menu_msg_id, text="⌛")
        except: menu_message = await safe_edit_or_send(message, "⌛", force_new=True)

    fake = FakeCallback(menu_message, message.from_user)
    await show_yoomoney_management_menu(fake, state)


@router.callback_query(F.data == "admin_yoomoney_mgmt_edit_secret")
async def yoomoney_edit_secret(callback: CallbackQuery, state: FSMContext):
    """Запрос Секретного ключа (IPN) ЮMoney."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.set_state(AdminStates.yoomoney_setup_secret)
    await state.update_data(last_menu_msg_id=callback.message.message_id)

    await safe_edit_or_send(
        callback.message,
        "🔐 <b>Введите секрет оповещений ЮMoney (IPN Secret)</b>\n\n"
        "Скопируйте секрет из страницы настроек HTTP-уведомлений ЮMoney.",
        reply_markup=back_and_home_kb("admin_payments_yoomoney"),
    )
    await callback.answer()


@router.message(AdminStates.yoomoney_setup_secret)
async def yoomoney_setup_secret_handler(message: Message, state: FSMContext):
    """Обработка ввода Секретного ключа (IPN) ЮMoney."""
    from bot.utils.text import get_message_text_for_storage
    val = get_message_text_for_storage(message, 'plain').strip()

    if len(val) < 4:
        await safe_edit_or_send(message, "❌ Слишком короткое значение.")
        return

    try: message.delete()
    except: pass

    set_setting('yoomoney_secret', val)
    data = await state.get_data()
    last_menu_msg_id = data.get('last_menu_msg_id')

    class FakeCallback:
        def __init__(self, msg, user):
            self.message, self.from_user, self.bot = msg, user, msg.bot
        async def answer(self, *args, **kwargs): pass

    menu_message = message
    if last_menu_msg_id:
        try: menu_message = await message.bot.edit_message_text(chat_id=message.chat.id, message_id=last_menu_msg_id, text="⌛")
        except: menu_message = await safe_edit_or_send(message, "⌛", force_new=True)

    fake = FakeCallback(menu_message, message.from_user)
    await show_yoomoney_management_menu(fake, state)


# ============================================================================
# НАСТРОЙКИ ДОМЕНА И SSL
# ============================================================================

@router.callback_query(F.data == "admin_domain_settings")
async def show_domain_settings_menu(callback: CallbackQuery, state: FSMContext):
    """Показывает меню настроек домена и SSL."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    await state.set_state(AdminStates.payments_menu)  # возвращаемся в меню
    
    domain_enabled = is_domain_enabled()
    domain_name = get_domain_name()
    conn_mode = get_bot_connection_mode()
    ssl_mode = get_ssl_mode()
    
    status_domain = "🟢 Включено" if domain_enabled else "🔴 Выключено"
    status_mode = "📡 Webhook (Рекомендовано)" if conn_mode == "webhook" else "📥 Polling (Опрос)"
    status_ssl = "🛡️ Standalone (Бот сам слушает 443 порт)" if ssl_mode == "standalone" else "🎛️ Proxy (Nginx / Cloudflare)"
    
    text = (
        "🌐 <b>Настройки домена и SSL</b>\n\n"
        "Вы можете привязать домен к боту для автоматического прохождения Let's Encrypt проверок, "
        "генерации SSL-сертификатов и перевода бота в режим Webhook.\n\n"
        f"▪️ <b>Использование домена:</b> {status_domain}\n"
        f"▪️ <b>Доменное имя:</b> <code>{domain_name or 'не указано'}</code>\n"
        f"▪️ <b>Режим подключения:</b> {status_mode}\n"
        f"▪️ <b>Режим SSL:</b> {status_ssl}\n\n"
        "⚠️ <i>Для режима Standalone убедитесь, что порты 80 и 443 свободны на сервере и проброшены в контейнер бота.</i>\n"
        "⚠️ <i>При включенном домене все вебхуки платежных систем автоматически генерируются через указанный домен.</i>"
    )
    
    await safe_edit_or_send(
        callback.message,
        text,
        reply_markup=domain_settings_kb(domain_enabled, conn_mode, ssl_mode)
    )
    await callback.answer()


@router.callback_query(F.data == "admin_domain_toggle")
async def toggle_domain_setting(callback: CallbackQuery, state: FSMContext):
    """Включает/выключает использование домена."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
        
    current = is_domain_enabled()
    new_val = '0' if current else '1'
    
    domain_name = get_domain_name()
    if new_val == '1' and not domain_name:
        await callback.answer("⚠️ Сначала укажите доменное имя!", show_alert=True)
        return
        
    set_setting('domain_enabled', new_val)
    status = "включено 🟢" if new_val == '1' else "выключено 🔴"
    await callback.answer(f"Использование домена {status}", show_alert=True)
    await show_domain_settings_menu(callback, state)


@router.callback_query(F.data == "admin_domain_toggle_mode")
async def toggle_domain_connection_mode(callback: CallbackQuery, state: FSMContext):
    """Переключает режим подключения (polling / webhook)."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
        
    current = get_bot_connection_mode()
    new_val = 'polling' if current == 'webhook' else 'webhook'
    
    set_setting('bot_connection_mode', new_val)
    await callback.answer(f"Режим изменен на {new_val.upper()} 🔌\nПерезагрузите бота для применения изменений.", show_alert=True)
    await show_domain_settings_menu(callback, state)


@router.callback_query(F.data == "admin_domain_toggle_ssl")
async def toggle_domain_ssl_mode(callback: CallbackQuery, state: FSMContext):
    """Переключает режим SSL (proxy / standalone)."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
        
    current = get_ssl_mode()
    new_val = 'proxy' if current == 'standalone' else 'standalone'
    
    set_setting('ssl_mode', new_val)
    await callback.answer(f"SSL режим изменен на {new_val.upper()} 🔒\nПерезагрузите бота для применения изменений.", show_alert=True)
    await show_domain_settings_menu(callback, state)


@router.callback_query(F.data == "admin_domain_edit_name")
async def edit_domain_name_request(callback: CallbackQuery, state: FSMContext):
    """Запрашивает доменное имя."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
        
    await state.set_state(AdminStates.domain_setup_name)
    await state.update_data(last_menu_msg_id=callback.message.message_id)
    
    await safe_edit_or_send(
        callback.message,
        "📝 <b>Введите ваше доменное имя</b>\n\n"
        "Например: <code>myvpnbot.ru</code> или <code>sub.domain.com</code>\n\n"
        "⚠️ <i>Домен должен быть направлен A-записью (A record) на IP вашего сервера!</i>",
        reply_markup=back_and_home_kb("admin_domain_settings")
    )
    await callback.answer()


@router.message(AdminStates.domain_setup_name)
async def domain_setup_name_handler(message: Message, state: FSMContext):
    """Обрабатывает ввод доменного имени."""
    from bot.utils.text import get_message_text_for_storage
    import re
    
    domain = get_message_text_for_storage(message, 'plain').strip().lower()
    
    # Простая валидация домена
    domain_pattern = re.compile(r'^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$')
    if not domain_pattern.match(domain):
        await message.answer("❌ Некорректный формат домена. Попробуйте еще раз или нажмите Отмена.")
        return
        
    try:
        await message.delete()
    except Exception:
        pass
        
    set_setting('domain_name', domain)
    
    data = await state.get_data()
    last_menu_msg_id = data.get('last_menu_msg_id')
    
    class FakeCallback:
        def __init__(self, msg, user):
            self.message = msg
            self.from_user = user
            self.bot = msg.bot
        async def answer(self, *args, **kwargs):
            pass
            
    menu_message = message
    if last_menu_msg_id:
        try:
            menu_message = await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=last_menu_msg_id,
                text="⌛"
            )
        except Exception:
            menu_message = await safe_edit_or_send(message, "⌛", force_new=True)
            
    fake = FakeCallback(menu_message, message.from_user)
    await show_domain_settings_menu(fake, state)


@router.callback_query(F.data == "admin_domain_run_certbot")
async def run_certbot_ssl(callback: CallbackQuery, state: FSMContext):
    """Запускает процесс генерации/проверки SSL сертификата через Certbot."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
        
    domain = get_domain_name()
    if not domain:
        await callback.answer("⚠️ Сначала укажите доменное имя!", show_alert=True)
        return
        
    await callback.answer("⏳ Запуск процесса Certbot...", show_alert=False)
    
    # Отправляем сообщение о начале
    progress_msg = await callback.message.answer(
        f"⏳ <b>Запущен процесс получения SSL-сертификата для домена:</b> <code>{domain}</code>\n"
        f"Пожалуйста, подождите..."
    )
    
    import asyncio
    try:
        # Выполняем certbot в автономном (standalone) режиме.
        cmd = [
            "certbot", "certonly", 
            "--standalone", 
            "-d", domain, 
            "--non-interactive", 
            "--agree-tos", 
            "--register-unsafely-without-email"
        ]
        
        cmd.extend(["--expand", "--keep-until-expiring"])
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        stdout_str = stdout.decode('utf-8', errors='ignore')
        stderr_str = stderr.decode('utf-8', errors='ignore')
        
        if process.returncode == 0:
            text = (
                f"✅ <b>SSL-сертификат Let's Encrypt успешно получен/проверен!</b>\n\n"
                f"Сертификаты сохранены по пути:\n"
                f"<code>/etc/letsencrypt/live/{domain}/fullchain.pem</code>\n"
                f"<code>/etc/letsencrypt/live/{domain}/privkey.pem</code>\n\n"
                f"Бот теперь готов работать по протоколу HTTPS в режиме Standalone SSL."
            )
            logger.info(f"Certbot success for domain {domain}:\n{stdout_str}")
        else:
            text = (
                f"❌ <b>Ошибка при получении SSL-сертификата Certbot</b>\n\n"
                f"Код возврата: {process.returncode}\n"
                f"Вывод ошибок:\n<pre>{escape_html(stderr_str or stdout_str)}</pre>\n\n"
                f"💡 <i>Убедитесь, что порт 80 проброшен, свободен и домен {domain} направлен на этот IP-адрес.</i>"
            )
            logger.error(f"Certbot failed for domain {domain}:\nStdout: {stdout_str}\nStderr: {stderr_str}")
            
        await progress_msg.edit_text(text)
    except Exception as e:
        logger.exception("Error running certbot subprocess")
        await progress_msg.edit_text(f"❌ Системная ошибка при запуске Certbot:\n<code>{escape_html(str(e))}</code>")


