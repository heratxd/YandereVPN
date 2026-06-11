from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict, Any, Optional

from .admin_misc import back_button, home_button, cancel_button

def payments_menu_kb(stars_enabled: bool, crypto_enabled: bool, cards_enabled: bool, qr_enabled: bool=False, monthly_reset_enabled: bool=False, demo_enabled: bool=False, wata_enabled: bool=False, platega_enabled: bool=False, cardlink_enabled: bool=False, cryptobot_enabled: bool=False, xrocket_enabled: bool=False, crystalpay_enabled: bool=False, lava_enabled: bool=False, freekassa_enabled: bool=False, rukassa_enabled: bool=False, payok_enabled: bool=False, nowpayments_enabled: bool=False, robokassa_enabled: bool=False, yoomoney_enabled: bool=False) -> InlineKeyboardMarkup:
    """
    Главное меню раздела оплат.
    """
    builder = InlineKeyboardBuilder()
    stars_status = '✅' if stars_enabled else '❌'
    builder.row(InlineKeyboardButton(text=f'⭐ Telegram Stars: {stars_status}', callback_data='admin_payments_toggle_stars'))
    crypto_status = '✅' if crypto_enabled else '❌'
    builder.row(InlineKeyboardButton(text=f'💰 Крипто-платежи: {crypto_status}', callback_data='admin_payments_toggle_crypto'))
    cards_status = '✅' if cards_enabled else '❌'
    builder.row(InlineKeyboardButton(text=f'📱 TG payments (ЮКасса): {cards_status}', callback_data='admin_payments_cards'))
    qr_status = '✅' if qr_enabled else '❌'
    builder.row(InlineKeyboardButton(text=f'💳 ЮКасса (QR/СБП): {qr_status}', callback_data='admin_payments_qr'))
    wata_status = '✅' if wata_enabled else '❌'
    builder.row(InlineKeyboardButton(text=f'🌊 WATA (Карта/СБП): {wata_status}', callback_data='admin_payments_wata'))
    platega_status = '✅' if platega_enabled else '❌'
    builder.row(InlineKeyboardButton(text=f'💸 Platega (СБП): {platega_status}', callback_data='admin_payments_platega'))
    cardlink_status = '✅' if cardlink_enabled else '❌'
    builder.row(InlineKeyboardButton(text=f'🔗 Cardlink (Карта/СБП): {cardlink_status}', callback_data='admin_payments_cardlink'))
    cryptobot_status = '✅' if cryptobot_enabled else '❌'
    builder.row(InlineKeyboardButton(text=f'🤖 CryptoBot (USDT): {cryptobot_status}', callback_data='admin_payments_cryptobot'))
    xrocket_status = '✅' if xrocket_enabled else '❌'
    builder.row(InlineKeyboardButton(text=f'🚀 xRocket (USDT): {xrocket_status}', callback_data='admin_payments_xrocket'))
    crystalpay_status = '✅' if crystalpay_enabled else '❌'
    builder.row(InlineKeyboardButton(text=f'💎 CrystalPay (РФ/Крипта): {crystalpay_status}', callback_data='admin_payments_crystalpay'))
    lava_status = '✅' if lava_enabled else '❌'
    builder.row(InlineKeyboardButton(text=f'🌋 Lava: {lava_status}', callback_data='admin_payments_lava'))
    freekassa_status = '✅' if freekassa_enabled else '❌'
    builder.row(InlineKeyboardButton(text=f'💸 Freekassa: {freekassa_status}', callback_data='admin_payments_freekassa'))
    rukassa_status = '✅' if rukassa_enabled else '❌'
    builder.row(InlineKeyboardButton(text=f'🇷🇺 RuKassa: {rukassa_status}', callback_data='admin_payments_rukassa'))
    payok_status = '✅' if payok_enabled else '❌'
    builder.row(InlineKeyboardButton(text=f'⚡ Payok: {payok_status}', callback_data='admin_payments_payok'))
    nowpayments_status = '✅' if nowpayments_enabled else '❌'
    builder.row(InlineKeyboardButton(text=f'🪙 NowPayments: {nowpayments_status}', callback_data='admin_payments_nowpayments'))
    robokassa_status = '✅' if robokassa_enabled else '❌'
    builder.row(InlineKeyboardButton(text=f'🔴 Robokassa: {robokassa_status}', callback_data='admin_payments_robokassa'))
    yoomoney_status = '✅' if yoomoney_enabled else '❌'
    builder.row(InlineKeyboardButton(text=f'🟣 ЮMoney (Кошелек): {yoomoney_status}', callback_data='admin_payments_yoomoney'))
    demo_status = '✅' if demo_enabled else '❌'
    builder.row(InlineKeyboardButton(text=f'💳 Демо оплата (РФ): {demo_status}', callback_data='admin_payments_toggle_demo'))
    reset_status = '✅' if monthly_reset_enabled else '❌'
    builder.row(InlineKeyboardButton(text=f'🔄 Автосброс трафика 1-го числа: {reset_status}', callback_data='admin_toggle_monthly_reset'))
    builder.row(InlineKeyboardButton(text='📂 Группы тарифов', callback_data='admin_groups'))
    builder.row(InlineKeyboardButton(text='📋 Тарифы', callback_data='admin_tariffs'))
    builder.row(InlineKeyboardButton(text='🎁 Пробная подписка', callback_data='admin_trial'))
    builder.row(InlineKeyboardButton(text='🌐 Настройки домена и SSL', callback_data='admin_domain_settings'))
    builder.row(back_button('admin_panel'), home_button())
    return builder.as_markup()


def yoomoney_management_kb(is_enabled: bool) -> InlineKeyboardMarkup:
    """
    Меню управления оплатой через ЮMoney.
    """
    builder = InlineKeyboardBuilder()
    toggle_text = 'Выключить 🔴' if is_enabled else 'Включить 🟢'
    builder.row(InlineKeyboardButton(text=toggle_text, callback_data='admin_yoomoney_mgmt_toggle'))
    builder.row(InlineKeyboardButton(text='🆔 Изменить номер кошелька', callback_data='admin_yoomoney_mgmt_edit_wallet'))
    builder.row(InlineKeyboardButton(text='🔐 Изменить Секретный ключ (IPN)', callback_data='admin_yoomoney_mgmt_edit_secret'))
    builder.row(back_button('admin_payments'), home_button())
    return builder.as_markup()


def domain_settings_kb(is_domain_enabled: bool, connection_mode: str, ssl_mode: str) -> InlineKeyboardMarkup:
    """
    Клавиатура настроек домена и SSL.
    """
    builder = InlineKeyboardBuilder()
    
    domain_toggle_text = '🔴 Выключить домен' if is_domain_enabled else '🟢 Включить домен'
    builder.row(InlineKeyboardButton(text=domain_toggle_text, callback_data='admin_domain_toggle'))
    
    builder.row(InlineKeyboardButton(text='📝 Указать доменное имя', callback_data='admin_domain_edit_name'))
    
    mode_text = '🔌 Режим: Webhook 📡' if connection_mode == 'webhook' else '🔌 Режим: Polling 📥'
    builder.row(InlineKeyboardButton(text=mode_text, callback_data='admin_domain_toggle_mode'))
    
    ssl_text = '🔒 SSL: Standalone 🛡️' if ssl_mode == 'standalone' else '🔒 SSL: Proxy (Nginx/Cloudflare) 🎛️'
    builder.row(InlineKeyboardButton(text=ssl_text, callback_data='admin_domain_toggle_ssl'))
    
    builder.row(InlineKeyboardButton(text='🔑 Получить SSL-сертификат Let\'s Encrypt', callback_data='admin_domain_run_certbot'))
    
    builder.row(back_button('admin_payments'), home_button())
    return builder.as_markup()



def cryptobot_management_kb(is_enabled: bool, is_sandbox: bool) -> InlineKeyboardMarkup:
    """
    Меню управления оплатой через CryptoBot.
    """
    builder = InlineKeyboardBuilder()
    toggle_text = 'Выключить 🔴' if is_enabled else 'Включить 🟢'
    builder.row(InlineKeyboardButton(text=toggle_text, callback_data='admin_cryptobot_mgmt_toggle'))
    sandbox_text = 'Выйти из Sandbox ⚪' if is_sandbox else 'Войти в Sandbox 🧪'
    builder.row(InlineKeyboardButton(text=sandbox_text, callback_data='admin_cryptobot_mgmt_toggle_sandbox'))
    builder.row(InlineKeyboardButton(text='🔑 Изменить API-токен', callback_data='admin_cryptobot_mgmt_edit_token'))
    builder.row(InlineKeyboardButton(text='📝 Изменить реквизиты (Ручной режим)', callback_data='admin_cryptobot_mgmt_edit_manual'))
    builder.row(back_button('admin_payments'), home_button())
    return builder.as_markup()


def xrocket_management_kb(is_enabled: bool, is_sandbox: bool) -> InlineKeyboardMarkup:
    """
    Меню управления оплатой через xRocket.
    """
    builder = InlineKeyboardBuilder()
    toggle_text = 'Выключить 🔴' if is_enabled else 'Включить 🟢'
    builder.row(InlineKeyboardButton(text=toggle_text, callback_data='admin_xrocket_mgmt_toggle'))
    sandbox_text = 'Выйти из Sandbox ⚪' if is_sandbox else 'Войти in Sandbox 🧪'
    builder.row(sandbox_text_btn := InlineKeyboardButton(text=sandbox_text, callback_data='admin_xrocket_mgmt_toggle_sandbox'))
    builder.row(InlineKeyboardButton(text='🔑 Изменить API-токен', callback_data='admin_xrocket_mgmt_edit_token'))
    builder.row(InlineKeyboardButton(text='📝 Изменить реквизиты (Ручной режим)', callback_data='admin_xrocket_mgmt_edit_manual'))
    builder.row(back_button('admin_payments'), home_button())
    return builder.as_markup()


def crystalpay_management_kb(is_enabled: bool) -> InlineKeyboardMarkup:
    """
    Меню управления оплатой через CrystalPay.
    """
    builder = InlineKeyboardBuilder()
    toggle_text = 'Выключить 🔴' if is_enabled else 'Включить 🟢'
    builder.row(InlineKeyboardButton(text=toggle_text, callback_data='admin_crystalpay_mgmt_toggle'))
    builder.row(InlineKeyboardButton(text='🆔 Изменить Login', callback_data='admin_crystalpay_mgmt_edit_login'))
    builder.row(InlineKeyboardButton(text='🔐 Изменить Secret', callback_data='admin_crystalpay_mgmt_edit_secret'))
    builder.row(back_button('admin_payments'), home_button())
    return builder.as_markup()


def wata_management_kb(is_enabled: bool) -> InlineKeyboardMarkup:
    """
    Меню управления оплатой через WATA.

    Args:
        is_enabled: Включена ли WATA-оплата сейчас
    """
    builder = InlineKeyboardBuilder()
    toggle_text = 'Выключить 🔴' if is_enabled else 'Включить 🟢'
    builder.row(InlineKeyboardButton(text=toggle_text, callback_data='admin_wata_mgmt_toggle'))
    builder.row(InlineKeyboardButton(text='🔑 Изменить JWT-токен', callback_data='admin_wata_mgmt_edit_token'))
    builder.row(back_button('admin_payments'), home_button())
    return builder.as_markup()


def platega_management_kb(is_enabled: bool) -> InlineKeyboardMarkup:
    """
    Меню управления оплатой через Platega.

    Args:
        is_enabled: Включена ли Platega-оплата сейчас
    """
    builder = InlineKeyboardBuilder()
    toggle_text = 'Выключить 🔴' if is_enabled else 'Включить 🟢'
    builder.row(InlineKeyboardButton(text=toggle_text, callback_data='admin_platega_mgmt_toggle'))
    builder.row(InlineKeyboardButton(text='🆔 Изменить Merchant ID', callback_data='admin_platega_mgmt_edit_merchant'))
    builder.row(InlineKeyboardButton(text='🔐 Изменить Secret', callback_data='admin_platega_mgmt_edit_secret'))
    builder.row(back_button('admin_payments'), home_button())
    return builder.as_markup()


def cardlink_management_kb(is_enabled: bool) -> InlineKeyboardMarkup:
    """
    Меню управления оплатой через Cardlink.

    Args:
        is_enabled: Включена ли Cardlink-оплата сейчас
    """
    builder = InlineKeyboardBuilder()
    toggle_text = 'Выключить 🔴' if is_enabled else 'Включить 🟢'
    builder.row(InlineKeyboardButton(text=toggle_text, callback_data='admin_cardlink_mgmt_toggle'))
    builder.row(InlineKeyboardButton(text='🆔 Изменить Shop ID', callback_data='admin_cardlink_mgmt_edit_shop_id'))
    builder.row(InlineKeyboardButton(text='🔐 Изменить API-токен', callback_data='admin_cardlink_mgmt_edit_api_token'))
    builder.row(back_button('admin_payments'), home_button())
    return builder.as_markup()

def crypto_setup_kb(step: int) -> InlineKeyboardMarkup:
    """
    Клавиатура для шага настройки крипто-платежей.
    
    Args:
        step: Текущий шаг (1 = ссылка, 2 = ключ)
    """
    builder = InlineKeyboardBuilder()
    buttons = []
    if step > 1:
        buttons.append(InlineKeyboardButton(text='⬅️ Назад', callback_data='admin_crypto_setup_back'))
    buttons.append(InlineKeyboardButton(text='❌ Отмена', callback_data='admin_payments'))
    builder.row(*buttons)
    return builder.as_markup()

def crypto_setup_confirm_kb() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения настроек крипто."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='✅ Сохранить и включить', callback_data='admin_crypto_setup_save'))
    builder.row(InlineKeyboardButton(text='⬅️ Назад', callback_data='admin_crypto_setup_back'), InlineKeyboardButton(text='❌ Отмена', callback_data='admin_payments'))
    return builder.as_markup()

def cards_management_kb(is_enabled: bool) -> InlineKeyboardMarkup:
    """Клавиатура управления оплатой картами."""
    builder = InlineKeyboardBuilder()
    toggle_text = 'Выключить 🔴' if is_enabled else 'Включить 🟢'
    builder.row(InlineKeyboardButton(text=toggle_text, callback_data='admin_cards_mgmt_toggle'))
    builder.row(InlineKeyboardButton(text='🔗 Изменить Provider Token', callback_data='admin_cards_mgmt_edit_token'))
    builder.row(back_button('admin_payments'), home_button())
    return builder.as_markup()


def edit_crypto_kb(current_param: int, total_params: int) -> InlineKeyboardMarkup:
    """
    Клавиатура редактирования крипто-настроек с навигацией.
    
    Args:
        current_param: Индекс текущего параметра
        total_params: Общее количество параметров
    """
    builder = InlineKeyboardBuilder()
    nav_buttons = []
    if current_param > 0:
        nav_buttons.append(InlineKeyboardButton(text='⬅️ Пред.', callback_data='admin_crypto_edit_prev'))
    else:
        nav_buttons.append(InlineKeyboardButton(text='—', callback_data='noop'))
    if current_param < total_params - 1:
        nav_buttons.append(InlineKeyboardButton(text='➡️ След.', callback_data='admin_crypto_edit_next'))
    else:
        nav_buttons.append(InlineKeyboardButton(text='—', callback_data='noop'))
    builder.row(*nav_buttons)
    builder.row(InlineKeyboardButton(text='✅ Готово', callback_data='admin_crypto_edit_done'))
    return builder.as_markup()

def crypto_management_kb(is_enabled: bool) -> InlineKeyboardMarkup:
    """
    Меню управления крипто-платежами.
    
    Args:
        is_enabled: Включены ли крипто-платежи сейчас
    """
    builder = InlineKeyboardBuilder()
    status_text = '🟢 Выключить' if is_enabled else '⚪ Включить'
    builder.row(InlineKeyboardButton(text=status_text, callback_data='admin_crypto_mgmt_toggle'))
    builder.row(InlineKeyboardButton(text='🔗 Изменить ссылку на товар', callback_data='admin_crypto_mgmt_edit_url'))
    builder.row(InlineKeyboardButton(text='🔐 Изменить секретный ключ', callback_data='admin_crypto_mgmt_edit_secret'))
    builder.row(back_button('admin_payments'), home_button())
    return builder.as_markup()


def lava_management_kb(is_enabled: bool) -> InlineKeyboardMarkup:
    """Меню управления Lava."""
    builder = InlineKeyboardBuilder()
    toggle_text = 'Выключить 🔴' if is_enabled else 'Включить 🟢'
    builder.row(InlineKeyboardButton(text=toggle_text, callback_data='admin_lava_mgmt_toggle'))
    builder.row(InlineKeyboardButton(text='🆔 Изменить Shop ID', callback_data='admin_lava_mgmt_edit_shop_id'))
    builder.row(InlineKeyboardButton(text='🔑 Изменить API-токен', callback_data='admin_lava_mgmt_edit_api_key'))
    builder.row(back_button('admin_payments'), home_button())
    return builder.as_markup()


def freekassa_management_kb(is_enabled: bool) -> InlineKeyboardMarkup:
    """Меню управления Freekassa."""
    builder = InlineKeyboardBuilder()
    toggle_text = 'Выключить 🔴' if is_enabled else 'Включить 🟢'
    builder.row(InlineKeyboardButton(text=toggle_text, callback_data='admin_freekassa_mgmt_toggle'))
    builder.row(InlineKeyboardButton(text='🆔 Изменить Shop ID', callback_data='admin_freekassa_mgmt_edit_shop_id'))
    builder.row(InlineKeyboardButton(text='🔑 Изменить API-ключ', callback_data='admin_freekassa_mgmt_edit_api_key'))
    builder.row(InlineKeyboardButton(text='🔐 Изменить Секретное слово 1', callback_data='admin_freekassa_mgmt_edit_secret_1'))
    builder.row(InlineKeyboardButton(text='🔐 Изменить Секретное слово 2', callback_data='admin_freekassa_mgmt_edit_secret_2'))
    builder.row(back_button('admin_payments'), home_button())
    return builder.as_markup()


def rukassa_management_kb(is_enabled: bool) -> InlineKeyboardMarkup:
    """Меню управления Rukassa."""
    builder = InlineKeyboardBuilder()
    toggle_text = 'Выключить 🔴' if is_enabled else 'Включить 🟢'
    builder.row(InlineKeyboardButton(text=toggle_text, callback_data='admin_rukassa_mgmt_toggle'))
    builder.row(InlineKeyboardButton(text='🆔 Изменить Shop ID', callback_data='admin_rukassa_mgmt_edit_shop_id'))
    builder.row(InlineKeyboardButton(text='🔑 Изменить Токен', callback_data='admin_rukassa_mgmt_edit_token'))
    builder.row(back_button('admin_payments'), home_button())
    return builder.as_markup()


def payok_management_kb(is_enabled: bool) -> InlineKeyboardMarkup:
    """Меню управления Payok."""
    builder = InlineKeyboardBuilder()
    toggle_text = 'Выключить 🔴' if is_enabled else 'Включить 🟢'
    builder.row(InlineKeyboardButton(text=toggle_text, callback_data='admin_payok_mgmt_toggle'))
    builder.row(InlineKeyboardButton(text='🆔 Изменить Shop ID', callback_data='admin_payok_mgmt_edit_shop_id'))
    builder.row(InlineKeyboardButton(text='🔑 Изменить API-ключ', callback_data='admin_payok_mgmt_edit_api_key'))
    builder.row(InlineKeyboardButton(text='🔐 Изменить Секретный ключ', callback_data='admin_payok_mgmt_edit_secret_key'))
    builder.row(InlineKeyboardButton(text='🆔 Изменить API ID', callback_data='admin_payok_mgmt_edit_api_id'))
    builder.row(back_button('admin_payments'), home_button())
    return builder.as_markup()


def nowpayments_management_kb(is_enabled: bool) -> InlineKeyboardMarkup:
    """Меню управления NowPayments."""
    builder = InlineKeyboardBuilder()
    toggle_text = 'Выключить 🔴' if is_enabled else 'Включить 🟢'
    builder.row(InlineKeyboardButton(text=toggle_text, callback_data='admin_nowpayments_mgmt_toggle'))
    builder.row(InlineKeyboardButton(text='🔑 Изменить API-ключ', callback_data='admin_nowpayments_mgmt_edit_api_key'))
    builder.row(InlineKeyboardButton(text='🔐 Изменить IPN Secret', callback_data='admin_nowpayments_mgmt_edit_ipn_secret'))
    builder.row(back_button('admin_payments'), home_button())
    return builder.as_markup()


def robokassa_management_kb(is_enabled: bool) -> InlineKeyboardMarkup:
    """Меню управления Robokassa."""
    builder = InlineKeyboardBuilder()
    toggle_text = 'Выключить 🔴' if is_enabled else 'Включить 🟢'
    builder.row(InlineKeyboardButton(text=toggle_text, callback_data='admin_robokassa_mgmt_toggle'))
    builder.row(InlineKeyboardButton(text='🆔 Изменить Login', callback_data='admin_robokassa_mgmt_edit_login'))
    builder.row(InlineKeyboardButton(text='🔐 Изменить Пароль 1', callback_data='admin_robokassa_mgmt_edit_password_1'))
    builder.row(InlineKeyboardButton(text='🔐 Изменить Пароль 2', callback_data='admin_robokassa_mgmt_edit_password_2'))
    builder.row(back_button('admin_payments'), home_button())
    return builder.as_markup()
