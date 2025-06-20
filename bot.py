from typing import Final
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from urllib.parse import quote_plus
from datetime import datetime
from zoneinfo import ZoneInfo
import logging
import aiohttp
import hashlib
import time
import os
import requests
import html # Import the html module


load_dotenv('bot.env')

# MongoDB configuration
username = os.getenv('DB_USERNAME')
password = os.getenv('DB_PASSWORD')
encoded_username = quote_plus(str(username))
encoded_password = quote_plus(str(password))

MONGO_URI = f"mongodb+srv://{encoded_username}:{encoded_password}@cluster0.d1k0aur.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = AsyncIOMotorClient(MONGO_URI)
db = client['smilebot']
users_collection = db['user']  # user data
order_collection = db['order']  # order data for mlbb

SMILE_ONE_BASE_URL_PH: Final = "https://www.smile.one/ph"
SMILE_ONE_BASE_URL_BR: Final = "https://www.smile.one/br"
TOKEN = os.getenv('BOTKEY')
UID = os.getenv('UID')
EMAIL = os.getenv('EMAIL')
KEY = os.getenv('KEY')
DEFAULT_PRODUCT_ID: Final = "213"
admins = [5671920054, 1836389511, 7135882496] # <-- သင့်ရဲ့ Admin ID များကို ဒီနေရာမှာ Integer အဖြစ် ထည့်သွင်းထားပါ။

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Packages for which balance will NOT be reverted on failure (as per user request)
SPECIAL_NON_REVERT_PACKAGES = ["wkp", "wkp2", "wkp3", "wkp4", "wkp5", "wkp10"]


############ Helper function to resolve user identifier ###############
async def resolve_user_identifier(identifier: str):
    """
    Resolves an identifier (Telegram ID or username) to a user_id string and a display name.
    If the identifier is a numeric ID, it directly returns it.
    If it's a username, it tries to find the corresponding user_id in the database.
    Returns (user_id_str, display_name) or (None, None) if username cannot be resolved.
    """
    # Remove any leading/trailing parentheses from the identifier
    identifier = identifier.strip('()')

    if identifier.isdigit():
        # It's a numeric ID, directly use it.
        # For numeric IDs, we can usually send messages even if user hasn't started bot,
        # but registering means they should interact for username capture.
        user = await users_collection.find_one({"user_id": identifier})
        if user:
            return user['user_id'], user.get('username', identifier) # Return username if available, else ID
        return identifier, identifier # If ID, but not in DB, return ID anyway for potential registration
    else:
        # It's a username (with or without '@')
        search_username = identifier.lstrip('@')
        user = await users_collection.find_one({"username": search_username})
        if user:
            # Found in database, return its actual user_id and username as display name
            return user['user_id'], identifier
        else:
            # Username not found in database. Cannot resolve to a user_id without prior interaction.
            # (Telegram API does not allow bot to get user_id from username without prior chat)
            return None, None


############ General message parts ###############

# Fetch and display user ID
async def getid_command(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id) # Ensure user_id is string
    
    # Check if user is registered by admin
    user_data = await users_collection.find_one({"user_id": user_id})
    if not user_data:
        await update.message.reply_text("You are not registered to use this bot. Please ask an admin to register you.", parse_mode='HTML')
        return

    username = update.message.from_user.username
    display_name = f"@{username}" if username else str(user_id)
    await update.message.reply_text(f"Your Telegram user is: <b>{html.escape(display_name)}</b> (ID: <code>{html.escape(str(user_id))}</code>)", parse_mode='HTML')


async def start_command(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)  # Telegram user ID
    username = update.message.from_user.username

    # Check if the user is registered in the database (by admin)
    user = await users_collection.find_one({"user_id": user_id})

    if not user:
        # If not registered by admin, inform user.
        not_registered_message = (
            "<b>WELCOME TO Minhtet Bot</b>\n\n"
            "You are not yet registered to use this bot's full features.\n"
            "Please ask an admin to register you. Your Telegram ID is: <code>{}</code>\n"
            "You can share this ID with your admin for registration."
        ).format(html.escape(user_id))
        
        await update.message.reply_text(
            not_registered_message,
            parse_mode="HTML"
        )
    else:
        # If registered, update their username in DB if it changed
        if user.get('username') != username:
            await users_collection.update_one({"user_id": user_id}, {"$set": {"username": username}})
            logger.info(f"Updated username for user {user_id} to {username}")

        balance_ph = user.get('balance_ph', 0)
        balance_br = user.get('balance_br', 0)
        existing_user_message = (
            "<b>HI! DEAR,</b>\n"
            "Your current balances:\n"
            f"🇵🇭 PH Balance : ${balance_ph}\n"
            f"🇧🇷 BR Balance : ${balance_br}\n\n"
            "<b>PLEASE PRESS /help FOR HOW TO USED</b>\n"
        )
        await update.message.reply_text(existing_user_message, parse_mode="HTML")


# handle_register_user callback is removed as self-registration is disabled


async def help_command(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)  # Get the user ID as a string
    
    # Check if user is registered by admin
    user_data = await users_collection.find_one({"user_id": user_id})
    if not user_data:
        await update.message.reply_text("You are not registered to use this bot. Please ask an admin to register you.", parse_mode='HTML')
        return

    username = update.message.from_user.username
    help_message = f"""
<b>HELLO</b> {html.escape(str(username))} 🤖

Please Contact admin ☺️
@minhtet4604

<b>COMMAND LIST</b>

/bal - <b>Bot Balance</b>

/his - <b>Orders History</b>

/role - <b>Check Username MLBB</b>

/getid - <b>Account ID</b>

/pricebr - <b>Brazil Price List</b>

/priceph - <b>Philippines Price List</b>

/use - <b>How To Use (or) How To Diamond Top Up</b>

Bot Creater by @sh1ntxant

    """
    try:
        # Log the message for debugging
        logger.info("Sending help message: %s", help_message)
        await update.message.reply_text(help_message, parse_mode='HTML')  # Use HTML
    except Exception as e:
        logger.error("Failed to send help message: %s", e)
        await update.message.reply_text("An error occurred while sending the help message.")


async def pricebr_command(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    
    # Check if user is registered by admin
    user_data = await users_collection.find_one({"user_id": user_id})
    if not user_data:
        await update.message.reply_text("You are not registered to use this bot. Please ask an admin to register you.", parse_mode='HTML')
        return

    # Define the merged price list
    price_list = """
<b>Pack List (FOR BR):</b>

<b>🇧🇷 Brazil:</b>

      DOUBLE DIAMOND PACK

    - svp: 39.00🪙
    - 55: 39.00🪙
    - 165: 116.90🪙
    - 275: 187.50🪙
    - 565: 385.00🪙
    
      NORMAL DIAMOND PACK
    
    - wkp: 76.00🪙
    - wkp2: 152.00🪙
    - wkp3: 228.00🪙
    - wkp4: 304.00🪙
    - wkp5: 380.00🪙
    - wkp10: 760.00🪙
    - twilight: 402.50🪙
    - 86: 61.50🪙
    - 172: 122.00🪙
    - 257: 177.50🪙
    - 343: 239.00🪙
    - 344: 244.00🪙
    - 429: 299.50🪙
    - 514: 355.00🪙
    - 600: 416.50🪙
    - 706: 480.00🪙
    - 792: 541.50🪙
    - 878: 602.00🪙
    - 963: 657.50🪙
    - 1049: 719.00🪙
    - 1135: 779.50🪙
    - 1220: 835.00🪙
    - 1412: 960.00🪙
    - 1584: 1082.00🪙
    - 1755: 1199.00🪙
    - 2195: 1453.00🪙
    - 2901: 1940.00🪙
    - 3688: 2424.00🪙
    - 4390: 2906.00🪙
    - 5532: 3660.00🪙
    - 9288: 6079.00🪙
    - 11483: 7532.00🪙"""
    await update.message.reply_text(price_list, parse_mode='HTML')
    
async def priceph_command(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    
    # Check if user is registered by admin
    user_data = await users_collection.find_one({"user_id": user_id})
    if not user_data:
        await update.message.reply_text("You are not registered to use this bot. Please ask an admin to register you.", parse_mode='HTML')
        return

    # Define the merged price list
    price_list = """
<b>Pack List (FOR PH):</b>

<b>🇵🇭 Philippines:</b>

    - 11: 10.00🪙
    - 22: 19.00 🪙
    - 56: 47.50🪙
    - 112: 95.00🪙
    - 223: 190.00🪙
    - 336: 285.00🪙
    - 570: 475.00🪙
    - 1163: 950.00🪙
    - 2398: 1900.00🪙
    - 6042: 4750.00🪙
    - wdp: 95.00🪙"""
    await update.message.reply_text(price_list, parse_mode='HTML')    
    
async def use_command(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)  # Get the user's ID
    
    # Check if user is registered by admin
    user_data = await users_collection.find_one({"user_id": user_id})
    if not user_data:
        await update.message.reply_text("You are not registered to use this bot. Please ask an admin to register you.", parse_mode='HTML')
        return
        
    # Example of functionality for /use command with country-specific instructions
    response_message = (
    "Welcome! Here's how you can use the bot:\n\n"
    "For Brazil 🇧🇷:\n"
    "<code>/mmb [id] [server id] [amount]</code>\n" # Added code tags and [ ] for clarity
    "E.g - <code>/mmb 12345678 2222 wkp</code>\n\n"
    
    "For Philippines 🇵🇭:\n"
    "<code>/mmp [id] [server id] [amount]</code>\n" # Added code tags and [ ] for clarity
    "E.g - <code>/mmp 12345678 2222 11</code>\n\n"
    
    "For Brazil /pricebr.\n"
    
    "For Philippines /priceph.\n"     
  
    "FAILED ORDER 🚫 If it occurs, please notify the Admin.\n" # Changed to English
  
    "For more details, contact @minhtet4604."
)
    await update.message.reply_text(response_message, parse_mode='HTML')

async def admin_command(update: Update, context: CallbackContext):
    username = update.message.from_user.username

    user_id = int(update.message.from_user.id) # Ensure user_id is int for comparison
    # Check if the user is an admin
    if user_id not in admins:
        await update.message.reply_text("❌Unauthorized Alert🚨")
        return

    help_message = f"""
<b>Hello Admin</b> {html.escape(str(username))}
<b>You can use below commands :</B>

1️⃣<b>Admin Mode</b>:
 /bal_admin - <b>Check balance</b>
 /user - <b>User List</b>
 /all_his - <b>All Order History</b>

2️⃣ <b>User Management:</b>
 /registeruser &lt;user_id_or_username&gt; - <b>Register a new user</b>
   (Example: <code>/registeruser @someuser</code> or <code>/registeruser 1234567890</code>)
 /removeuser &lt;user_id_or_username&gt; - <b>Remove an existing user</b>
   (Example: <code>/removeuser @someuser</code> or <code>/removeuser 1234567890</code>)

3️⃣ <b>Wallet Topup:</b>

Ask to user for telegram_id Press
/getid

Added
/add_bal &lt;user_id_or_username&gt; &lt;amount&gt; &lt;balance_type&gt;
(Example: <code>/add_bal @username 500 balance_ph</code>)

Deducted
/ded_bal &lt;user_id_or_username&gt; &lt;amount&gt; &lt;balance_type&gt;
(Example: <code>/ded_bal telegram_id 500 balance_br</code>)
    """

    try:
        # Log the message for debugging
        logger.info("Sending help message: %s", help_message)
        await update.message.reply_text(help_message, parse_mode='HTML')  # Use HTML parsing
    except Exception as e:
        logger.error("Failed to send help message: %s", e)
        await update.message.reply_text("An error occurred while sending the help message.")


# New Admin Command to Register Users
async def register_user_by_admin_command(update: Update, context: CallbackContext):
    admin_user_id = int(update.message.from_user.id) # Ensure user_id is int for comparison
    if admin_user_id not in admins:
        await update.message.reply_text("🚫 *Unauthorized*: You are not allowed to use this command.", parse_mode='Markdown')
        return

    if len(context.args) != 1:
        await update.message.reply_text("*Usage*: `/registeruser <user_id_or_username>`. Example: `/registeruser @someuser` or `/registeruser 1234567890`", parse_mode='Markdown')
        return

    identifier = context.args[0]
    # resolve_user_identifier will return (identifier, identifier) if it's a numeric ID not in DB yet,
    # or (None, None) if it's an unresolved username.
    target_user_id, display_name = await resolve_user_identifier(identifier)
    
    # If the identifier was a username and it couldn't be resolved from DB, then it's an issue.
    if target_user_id is None and not identifier.isdigit():
        await update.message.reply_text(f"❌ *Error*: Cannot register user <b>{html.escape(identifier)}</b>. If it's a username, the user must have interacted with the bot at least once (e.g., by sending /start) for their ID to be recorded. Please ask them to send /start first or provide their numeric Telegram ID.", parse_mode='HTML')
        return
    
    # If it's a numeric ID, display_name might just be the ID. Try to get their username from Telegram if possible.
    if target_user_id is not None and identifier.isdigit():
        try:
            chat_member = await context.bot.get_chat_member(chat_id=target_user_id, user_id=target_user_id)
            if chat_member.user.username:
                display_name = f"@{chat_member.user.username}"
            elif chat_member.user.full_name:
                display_name = chat_member.user.full_name
            else:
                display_name = str(target_user_id)
        except Exception as e:
            logger.warning(f"Could not get chat member info for ID {target_user_id}: {e}")
            display_name = str(target_user_id) # Fallback to ID


    # Check if user is already registered
    existing_user = await users_collection.find_one({"user_id": target_user_id})
    if existing_user:
        existing_username = existing_user.get('username')
        existing_display_name_from_db = f"@{existing_username}" if existing_username else target_user_id
        await update.message.reply_text(f"✅ User <b>{html.escape(existing_display_name_from_db)}</b> (ID: <code>{html.escape(target_user_id)}</code>) is already registered.", parse_mode='HTML')
        
        # Always update username if a new one is available or changed
        if display_name.startswith('@') and existing_username != display_name.lstrip('@'):
            await users_collection.update_one({"user_id": target_user_id}, {"$set": {"username": display_name.lstrip('@')}})
            logger.info(f"Updated username for existing user {target_user_id} to {display_name.lstrip('@')}")
        return

    # Register the user
    new_user_data = {
        "user_id": target_user_id,
        "username": display_name.lstrip('@') if display_name.startswith('@') else None, # Store username if it was from username or resolved display_name
        "balance_ph": 0,
        "balance_br": 0,
        "date_joined": int(time.time())
    }
    await users_collection.insert_one(new_user_data)

    admin_conf_msg = f"🎉 User <b>{html.escape(display_name)}</b> (ID: <code>{html.escape(target_user_id)}</code>) has been successfully registered."
    await update.message.reply_text(admin_conf_msg, parse_mode='HTML')

    # Attempt to send welcome message to the newly registered user
    user_welcome_msg = (
        f"🎉 Congratulations! You have been registered by an admin and can now use the bot.\n\n"
        f"Your current balances:\n"
        f"PH Balance : \$0\n" # Removed backslash, as $ is not special in HTML
        f"BR Balance : \$0\n\n" # Removed backslash, as $ is not special in HTML
        f"Please press /help for how to use the bot."
    )
    try:
        await context.bot.send_message(chat_id=target_user_id, text=user_welcome_msg, parse_mode='HTML')
        logger.info(f"Successfully sent welcome message to new user {target_user_id}")
    except Exception as e:
        logger.warning(f"Could not send welcome message to new user {target_user_id}: {e}. User might not have started the bot or blocked it.")
        await update.message.reply_text(f"⚠️ Warning: Could not send welcome message to user <b>{html.escape(display_name)}</b> (ID: <code>{html.escape(target_user_id)}</code>). They might not have started the bot or blocked it.", parse_mode='HTML')


# New Admin Command to Remove Users
async def remove_user_by_admin_command(update: Update, context: CallbackContext):
    admin_user_id = int(update.message.from_user.id) # Ensure user_id is int for comparison
    if admin_user_id not in admins:
        await update.message.reply_text("🚫 *Unauthorized*: You are not allowed to use this command.", parse_mode='Markdown')
        return

    if len(context.args) != 1:
        await update.message.reply_text("*Usage*: `/removeuser <user_id_or_username>`. Example: `/removeuser @someuser` or `/removeuser 1234567890`", parse_mode='Markdown')
        return

    identifier = context.args[0]
    target_user_id, display_name = await resolve_user_identifier(identifier)

    if target_user_id is None:
        await update.message.reply_text(f"❌ *User Not Found*: Cannot resolve user <b>{html.escape(identifier)}</b>. If it's a username, the user must have interacted with the bot at least once for the bot to record their ID.", parse_mode='HTML')
        return

    # Attempt to delete the user from the database
    delete_result = await users_collection.delete_one({"user_id": target_user_id})

    if delete_result.deleted_count > 0:
        admin_conf_msg = f"🗑️ User <b>{html.escape(display_name)}</b> (ID: <code>{html.escape(target_user_id)}</code>) has been successfully removed from the database."
        await update.message.reply_text(admin_conf_msg, parse_mode='HTML')

        # Attempt to send notification message to the removed user
        user_notification_msg = (
            f"🚫 You have been removed from the bot's registered users by an admin.\n\n"
            f"You will no longer be able to use the bot's features unless an admin re-registers you.\n"
            f"Please contact @minhtet4604 for more information."
        )
        try:
            await context.bot.send_message(chat_id=target_user_id, text=user_notification_msg, parse_mode='HTML')
            logger.info(f"Successfully sent removal notification to user {target_user_id}")
        except Exception as e:
            logger.warning(f"Could not send removal notification to user {target_user_id}: {e}. User might have blocked the bot or chat ID is invalid.")
            await update.message.reply_text(f"⚠️ Warning: Could not send removal notification to user <b>{html.escape(display_name)}</b> (ID: <code>{html.escape(target_user_id)}</code>). They might have blocked the bot or chat ID is invalid.", parse_mode='HTML')
    else:
        # User not found in DB
        await update.message.reply_text(f"❌ User <b>{html.escape(display_name)}</b> (ID: <code>{html.escape(target_user_id)}</code>) was not found in the database. No user was removed.", parse_mode='HTML')



async def get_balance(user_id: str):
    user = await users_collection.find_one({"user_id": user_id})  # Await the database query
    print(f"Fetching balance for user_id: {user_id}")  # Debugging statement
    if user:
        return {
            'balance_ph': user.get('balance_ph', 0),
            'balance_br': user.get('balance_br', 0),
        }
    return None

# Check balance command


async def balance_command(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)  # Convert user_id to string
    
    # Check if user is registered by admin
    user_data = await users_collection.find_one({"user_id": user_id})
    if not user_data:
        await update.message.reply_text("You are not registered to use this bot. Please ask an admin to register you.", parse_mode='HTML')
        return

    balances = await get_balance(user_id)  # Await the async get_balance function

    if balances:
        balance_ph = balances.get('balance_ph', 0)  # Fetch balance for PH
        balance_br = balances.get('balance_br', 0)  # Fetch balance for BR

        # Format the response with emojis and HTML styling
        response_message = (
            f"<b>MinHtet Bot BALANCE 💰:</b>\n\n"
            f"🇵🇭 <b>PH Balance</b>: <code>{balance_ph:.2f}</code> 🪙\n"
            f"🇧🇷 <b>BR Balance</b>: <code>{balance_br:.2f}</code> 🪙\n"
        )

        await update.message.reply_text(response_message, parse_mode='HTML')
    else:
        # This else is unlikely if the initial check passes, but good for safety
        await update.message.reply_text("Error: Could not retrieve your balance. Please try again later.", parse_mode='Markdown')


async def update_balance(user_id: str, amount: float, balance_type: str): # Changed amount to float
    """
    Atomically updates the balance of the specified user.
    If deducting, ensures sufficient balance.
    Returns the new balance, or None if the operation failed (e.g., insufficient balance).
    """
    # Using find_one_and_update for atomic operation
    query = {"user_id": user_id}
    if amount < 0: # If it's a deduction
        query[balance_type] = {"$gte": abs(amount)} # Ensure current balance is >= absolute amount
        
    result = await users_collection.find_one_and_update(
        query,
        {"$inc": {balance_type: amount}}, # Atomically increment/decrement
        return_document=True # Return the updated document
    )

    if result:
        logger.info(f"Balance update successful for user {user_id}, {balance_type}: new balance {result.get(balance_type)}")
        return result.get(balance_type)
    else:
        # If result is None, it means:
        # 1. User not found, OR
        # 2. For deduction, balance was insufficient (query condition failed).
        current_user = await users_collection.find_one({"user_id": user_id}) # Re-fetch to log current balance if possible
        if current_user and amount < 0 and current_user.get(balance_type, 0.0) < abs(amount):
            logger.warning(f"Balance update failed for user {user_id}: Insufficient balance for {balance_type} deduction. Current: {current_user.get(balance_type, 0.0)}, Attempted: {abs(amount)}")
            return None
        logger.error(f"Balance update failed for user {user_id} (unknown reason, possibly user not found).")
        return None


async def add_balance_command(update: Update, context: CallbackContext):
    """
    Command to add balance to a user's account by ID or username.
    """
    admin_user_id = int(update.message.from_user.id) # Ensure user_id is int for comparison
    if admin_user_id not in admins:
        await update.message.reply_text("🚫 *Unauthorized*: You are not allowed to use this command.", parse_mode='Markdown')
        return

    # Expecting three arguments: identifier (ID or username), amount, balance_type
    if len(context.args) != 3 or not context.args[1].isdigit() or context.args[2] not in ['balance_ph', 'balance_br']:
        await update.message.reply_text(
            "*Usage*: `/add_bal <user_id_or_username> <amount> <balance_type>` balance_type should be either balance_ph or balance_br. Example: `/add_bal @someuser 100 balance_ph`",
            parse_mode='Markdown'
        )
        return

    identifier = context.args[0].strip('()') # Strip parentheses
    amount = float(context.args[1]) # Changed to float
    balance_type = context.args[2]

    # Resolve target user ID and display name
    target_user_id, display_name = await resolve_user_identifier(identifier)

    if target_user_id is None:
        await update.message.reply_text(f"❌ *User Not Found*: Cannot resolve user <b>{html.escape(identifier)}</b>. If it's a username, the user must have started the bot at least once for the bot to record their ID.", parse_mode='HTML')
        return
    
    # Ensure the target user is registered in the database (by admin) before adding balance
    target_user_db_entry = await users_collection.find_one({"user_id": target_user_id})
    if not target_user_db_entry:
        await update.message.reply_text(f"❌ *User Not Registered*: User <b>{html.escape(display_name)}</b> (ID: <code>{html.escape(target_user_id)}</code>) is not registered by an admin. Please register them first using <code>/registeruser {html.escape(identifier)}</code>.", parse_mode='HTML')
        return


    # Add the balance to the target user
    try:
        new_balance = await update_balance(target_user_id, amount, balance_type)

        if new_balance is not None:
            # Message for Admin
            admin_success_message_text = (
                f"✅ <b>Success!</b> Added <code>{html.escape(str(amount))}</code> to <b>User</b> <code>{html.escape(display_name)}</code>'s ({html.escape(target_user_id)}) {html.escape(balance_type)}.\n\n"
                f"🇲🇲 New Balance: <code>{html.escape(str(new_balance))}</code> 🪙"
            )
            try:
                await update.message.reply_text(admin_success_message_text, parse_mode='HTML')
                logger.info(f"Successfully sent add_balance success message to admin for user {target_user_id}")
            except Exception as send_error:
                logger.error(f"Error sending add_balance success message to admin for user {target_user_id}: {send_error}")
                await update.message.reply_text("✅ Success! Balance updated (admin notification failed).", parse_mode=None)

            # Message for the Target User
            user_notification_message_text = (
                f"🎉 Your balance has been topped up!\n"
                f"Amount added: <code>{html.escape(str(amount))}</code>\n"
                f"Your new {html.escape(balance_type.replace('balance_ph', 'PH Balance').replace('balance_br', 'BR Balance'))}: <code>{html.escape(str(new_balance))}</code> 🪙\n\n"
                f"Please contact @minhtet4604 if you have any questions."
            )
            try:
                await context.bot.send_message(chat_id=target_user_id, text=user_notification_message_text, parse_mode='HTML')
                logger.info(f"Successfully sent balance top-up notification to user {target_user_id}")
            except Exception as user_send_error:
                logger.error(f"Error sending balance top-up notification to user {target_user_id}: {user_send_error}")
                # This error means the user might have blocked the bot or the chat ID is invalid.
                await update.message.reply_text(f"⚠️ Warning: Could not send notification to user <b>{html.escape(display_name)}</b> (ID: <code>{html.escape(target_user_id)}</code>). They might have blocked the bot or chat ID is invalid.", parse_mode='HTML')

        else:
             # This case should ideally not be reached if target_user exists and update_balance logic is correct
             await update.message.reply_text(f"❌ *Failed*: Unable to update balance for *User* <b>{html.escape(display_name)}</b>.", parse_mode='HTML')
    except Exception as general_error:
        # Catch other potential errors before sending the success message
        logger.error(f"Error during add_balance command for user {target_user_id}: {general_error}")
        await update.message.reply_text(f"An error occurred while adding balance for user <b>{html.escape(display_name)}</b>.", parse_mode='HTML')



async def deduct_balance_command(update: Update, context: CallbackContext):
    """
    Command to deduct balance from a user's account by ID or username.
    """
    admin_user_id = int(update.message.from_user.id) # Ensure user_id is int for comparison
    if admin_user_id not in admins:
        await update.message.reply_text("🚫 *Unauthorized*: You are not allowed to use this command.", parse_mode='Markdown')
        return

    # Expecting three arguments: identifier (ID or username), amount, balance_type
    if len(context.args) != 3 or not context.args[1].isdigit() or context.args[2] not in ['balance_ph', 'balance_br']:
        await update.message.reply_text(
            "*Usage*: `/ded_bal <user_id_or_username> <amount> <balance_type>` balance_type should be either balance_ph or balance_br. Example: `/ded_bal @someuser 50 balance_br`",
            parse_mode='Markdown'
        )
        return

    identifier = context.args[0].strip('()') # Strip parentheses
    amount = float(context.args[1]) # Changed to float
    balance_type = context.args[2]

    # Resolve target user ID and display name
    target_user_id, display_name = await resolve_user_identifier(identifier)

    if target_user_id is None:
        await update.message.reply_text(f"❌ *User Not Found*: Cannot resolve user <b>{html.escape(identifier)}</b>. If it's a username, the user must have started the bot at least once for the bot to record their ID.", parse_mode='HTML')
        return
    
    # Ensure the target user is registered in the database (by admin) before deducting balance
    target_user_db_entry = await users_collection.find_one({"user_id": target_user_id})
    if not target_user_db_entry:
        await update.message.reply_text(f"❌ *User Not Registered*: User <b>{html.escape(display_name)}</b> (ID: <code>{html.escape(target_user_id)}</code>) is not registered by an admin. Please register them first using <code>/registeruser {html.escape(identifier)}</code>.", parse_mode='HTML')
        return


    # Deduct the balance from the target user
    try:
        new_balance = await update_balance(target_user_id, -amount, balance_type)

        if new_balance is not None:
            # Message for Admin
            admin_success_message_text = (
                f"✅ <b>Success!</b> Deducted <code>{html.escape(str(amount))}</code> from <b>User</b> <code>{html.escape(display_name)}</code>'s ({html.escape(target_user_id)}) {html.escape(balance_type)}.\n\n"
                f"💵 New Balance: <code>{html.escape(str(new_balance))}</code> 🪙"
            )
            try:
                await update.message.reply_text(admin_success_message_text, parse_mode='HTML')
                logger.info(f"Successfully sent deduct_balance success message to admin for user {target_user_id}")
            except Exception as send_error:
                logger.error(f"Error sending deduct_balance success message to admin for user {target_user_id}: {send_error}")
                await update.message.reply_text("✅ Success! Balance updated (admin notification failed).", parse_mode=None)

            # Message for the Target User
            user_notification_message_text = (
                f"⚠️ Your balance has been deducted!\n"
                f"Amount deducted: <code>{html.escape(str(amount))}</code>\n"
                f"Your new {html.escape(balance_type.replace('balance_ph', 'PH Balance').replace('balance_br', 'BR Balance'))}: <code>{html.escape(str(new_balance))}</code> 🪙\n\n"
                f"Please contact @minhtet4604 if you have any questions."
            )
            try:
                await context.bot.send_message(chat_id=target_user_id, text=user_notification_message_text, parse_mode='HTML')
                logger.info(f"Successfully sent balance deduction notification to user {target_user_id}")
            except Exception as user_send_error:
                logger.error(f"Error sending balance deduction notification to user {target_user_id}: {user_send_error}")
                await update.message.reply_text(f"⚠️ Warning: Could not send notification to user <b>{html.escape(display_name)}</b> (ID: <code>{html.escape(target_user_id)}</code>). They might have blocked the bot or chat ID is invalid.", parse_mode='HTML')

        else:
             # This case should be for insufficient balance based on update_balance logic
            await update.message.reply_text(
                f"❌ *Failed*: Insufficient balance for *User* <b>{html.escape(display_name)}</b> or deduction failed.",
                parse_mode='HTML'
            )
    except Exception as general_error:
        logger.error(f"Error deducting balance: {general_error}")
        await update.message.reply_text(f"An error occurred while deducting balance for user <b>{html.escape(display_name)}</b>.", parse_mode='HTML')


def split_message(text, max_length=4096):
    """Splits the message into chunks that fit within the Telegram message limit."""
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]


async def get_users_command(update: Update, context: CallbackContext):
    user_id = int(update.message.from_user.id) # Ensure user_id is int for comparison
    # Check if the user is an admin
    if user_id not in admins:
        await update.message.reply_text("Unauthorized: You are not allowed to use this command.")
        return

    # Fetch all users from the database
    users_cursor = users_collection.find()  # Fetch all users
    users_list = await users_cursor.to_list(length=None)  # Convert cursor to list

    if not users_list:  # Check if there are no users
        await update.message.reply_text("No users found in the database.")
        return

    # Prepare the response message
    response_summary = "User Details: 📋\n\n"
    for user in users_list:
        db_user_id = user.get('user_id', 'N/A')
        db_username = user.get('username') # Get username from DB
        display_name = f"@{db_username}" if db_username else str(db_user_id) # Prefer username, else ID
        balance_ph = user.get('balance_ph', 0)
        balance_br = user.get('balance_br', 0)
        # Format date joined to 12-hour format
        date_joined_timestamp = user.get('date_joined', 0)
        date_joined_formatted = datetime.fromtimestamp(date_joined_timestamp).strftime('%Y-%m-%d %I:%M:%S %p') if date_joined_timestamp != 0 else 'N/A'


        # Enhance the output with clear formatting
        response_summary += (
            f"🆔 User: <b>{html.escape(display_name)}</b> (ID: <code>{html.escape(str(db_user_id))}</code>)\n" # Display username then ID
            f" PH BALANCE : ${balance_ph:.2f}\n"
            f" BR BALANCE : ${balance_br:.2f}\n"
            f"📅 DATE JOINED: {date_joined_formatted}\n" # Use 12-hour formatted date
            "---------------------------------\n"  # Separator for better readability
        )

    # Split message if it's too long
    messages = split_message(response_summary)

    # Send each chunk of the message
    for msg in messages:
        try:
            await update.message.reply_text(msg, parse_mode='HTML') # Use HTML parse mode
        except Exception as e:
            print(f"Error sending message: {e}")
            await update.message.reply_text("An error occurred while sending the message. Please try again later.")


async def get_user_orders(update: Update, context: CallbackContext):
    sender_user_id = str(update.message.from_user.id)  # Get the Telegram user's ID
    
    # Check if user is registered by admin
    user_data = await users_collection.find_one({"user_id": sender_user_id})
    if not user_data:
        await update.message.reply_text("You are not registered to use this bot. Please ask an admin to register you.", parse_mode='HTML')
        return

    sender_user_db = await users_collection.find_one({"user_id": sender_user_id})
    sender_display_name = f"@{sender_user_db['username']}" if sender_user_db and sender_user_db.get('username') else sender_user_id

    # Query both collections for orders made by this sender
    transactions_cursor = order_collection.find(
        {"sender_user_id": sender_user_id})

    # Convert the cursors to lists asynchronously
    transactions_list = await transactions_cursor.to_list(length=None)

    response_summary = f"==== Order History for <b>{html.escape(sender_display_name)}</b> ====\n\n"

    # Process orders from transactions_collection
    for order in transactions_list:
        db_sender_user_id = order.get('sender_user_id', 'N/A')
        player_id = order.get('player_id', 'N/A')
        zone_id = order.get('zone_id', 'N/A')
        pack = order.get('product_name', 'N/A')
        order_ids = order.get('order_ids', 'N/A')
        # Retrieve and format date to 12-hour format if available
        date_str = order.get('date', 'N/A')
        formatted_date = date_str
        if date_str != 'N/A':
            try:
                # Attempt to parse the stored date string. Adjust format string if necessary.
                # Assuming the date is stored in '%I:%M:%S %p %Y-%m-%d' format from bulk_command
                order_date_obj = datetime.strptime(date_str, '%I:%M:%S %p %Y-%m-%d')
                formatted_date = order_date_obj.strftime('%I:%M:%S %p %Y-%m-%d') # Re-format to ensure consistency
            except ValueError:
                # If parsing fails, maybe the stored date doesn't include time or is in a different format
                try:
                     date_only_obj = datetime.strptime(date_str.split(' ')[-1], '%Y-%m-%d') # Try to get date part only
                     formatted_date = date_only_obj.strftime('%Y-%m-%d') # Format date only
                except ValueError:
                     pass # Keep original string if parsing also fails


        total_cost = order.get('total_cost', 0.0)
        status = order.get('status', 'N/A')
        # Get remaining balance from order document if available
        remaining_balance = order.get('initial_balance', 'N/A') 

        if isinstance(order_ids, list):
            order_ids = ', '.join(order_ids)
        else:
            order_ids = str(order_ids)

        # Look up username for player_id if available in DB
        player_db_entry = await users_collection.find_one({"user_id": str(player_id)})
        player_display_name = f"@{player_db_entry['username']}" if player_db_entry and player_db_entry.get('username') else str(player_id)

        balance_display_line = ""
        if isinstance(remaining_balance, (int, float)):
            balance_display_line = f"Initial Balance: ${float(remaining_balance):.2f} 🪙\n"

        response_summary += (
            f"🆔 Telegram User: <b>{html.escape(player_display_name)}</b>\n" # Display user's username
            f"📍 Game ID: <code>{html.escape(str(player_id))}</code>\n" # Escape user ID
            f"🌍 Zone ID: {html.escape(str(zone_id))}\n" # Escape zone ID
            f"💎 Pack: {html.escape(str(pack))}\n" # Escape pack
            f"🆔 Order ID: <code>{html.escape(str(order_ids))}</code>\n" # Escape order IDs
            f"📅 Date: {formatted_date}\n" # Use formatted_date
            f"💵 Rate: ${float(total_cost):.2f}\n"
            + balance_display_line + # Add remaining balance line
            f"🔄 Status: {html.escape(str(status))}\n\n"
        )

    # Split the message if it's too long for a single reply
    messages = split_message(response_summary)
    for msg in messages:
        await update.message.reply_text(msg, parse_mode='HTML')


async def get_all_orders(update: Update, context: CallbackContext):
    user_id = int(update.message.from_user.id) # Ensure user_id is int for comparison
    # Check if the user is an admin
    if user_id not in admins:
        await update.message.reply_text("Unauthorized: You are not allowed to use this command.")
        return

    # Fetch all orders from the collection
    try:
        orders_cursor = order_collection.find({})  # Fetch all orders
        orders_list = await orders_cursor.to_list(length=None)  # Convert to a list

        if not orders_list:
            await update.message.reply_text("No orders found in the database.")
            return

        response_summary = "==== All Order Histories ====\n\n"

        # Process each order
        for order in orders_list:
            sender_user_id = order.get('sender_user_id', 'N/A')
            player_id = order.get('player_id', 'N/A')
            zone_id = order.get('zone_id', 'N/A')
            product_name = order.get('product_name', 'N/A')
            order_ids = order.get('order_ids', 'N/A')
             # Retrieve and format date to 12-hour format if available
            date_str = order.get('date', 'N/A')
            formatted_date = date_str
            if date_str != 'N/A':
                try:
                    # Attempt to parse the stored date string. Adjust format string if necessary.
                    # Assuming the date is stored in '%I:%M:%S %p %Y-%m-%d' format from bulk_command
                    order_date_obj = datetime.strptime(date_str, '%I:%M:%S %p %Y-%m-%d')
                    formatted_date = order_date_obj.strftime('%I:%M:%S %p %Y-%m-%d') # Re-format to ensure consistency
                except ValueError:
                    # If parsing fails, maybe the stored date doesn't include time or is in a different format
                    try:
                        date_only_obj = datetime.strptime(date_str.split(' ')[-1], '%Y-%m-%d') # Try to get date part only
                        formatted_date = date_only_obj.strftime('%Y-%m-%d') # Format date only
                    except ValueError:
                         pass # Keep original string if parsing also fails


            total_cost = order.get('total_cost', 0.0)
            status = order.get('status', 'N/A')
            # Get remaining balance from order document if available
            remaining_balance = order.get('initial_balance', 'N/A')


            if isinstance(order_ids, list):
                order_ids = ', '.join(order_ids)
            else:
                order_ids = str(order_ids)

            # Look up username for sender_user_id and player_id if available in DB
            sender_db_entry = await users_collection.find_one({"user_id": str(sender_user_id)})
            sender_display_name = f"@{sender_db_entry['username']}" if sender_db_entry and sender_db_entry.get('username') else str(sender_user_id)

            player_db_entry = await users_collection.find_one({"user_id": str(player_id)})
            player_display_name = f"@{player_db_entry['username']}" if player_db_entry and player_db_entry.get('username') else str(player_id)

            balance_display_line = ""
            if isinstance(remaining_balance, (int, float)):
                balance_display_line = f"Initial Balance: ${float(remaining_balance):.2f} 🪙\n"

            response_summary += (
                f"🆔 Sender: <b>{html.escape(sender_display_name)}</b> (ID: <code>{html.escape(str(sender_user_id))}</code>)\n"
                f"🎮 Player: <b>{html.escape(player_display_name)}</b> (ID: <code>{html.escape(str(player_id))}</code>)\n"
                f"🌍 Zone ID: {html.escape(str(zone_id))}\n"
                f"💎 Product: {html.escape(str(product_name))}\n"
                f"🆔 Order IDs: <code>{html.escape(str(order_ids))}</code>\n"
                f"📅 Date: {formatted_date}\n"
                f"💵 Total Cost: ${float(total_cost):.2f}\n"
                + balance_display_line + # Add remaining balance line
                f"🔄 Status: {html.escape(str(status))}\n\n"
            )

        # Split the message if it's too long for Telegram's limit
        messages = split_message(response_summary)
        for msg in messages:
            await update.message.reply_text(msg, parse_mode='HTML')

    except Exception as e:
        logging.error(f"Error retrieving orders: {e}")
        await update.message.reply_text("❌ Failed to retrieve order history. Please try again.")


############# Smile One Integration ###############

# Function to calculate sign


def calculate_sign(params):
    sorted_params = sorted(params.items())
    query_string = '&'.join([f"{k}={v}" for k, v in sorted_params])
    query_string += f"&{KEY}"
    hashed_string = hashlib.md5(hashlib.md5(
        query_string.encode()).hexdigest().encode()).hexdigest()
    return hashed_string


async def get_role_info(userid: str, zoneid: str, product_id: str = DEFAULT_PRODUCT_ID):
    endpoint = f"{SMILE_ONE_BASE_URL_PH}/smilecoin/api/getrole"  # Assuming PH is valid for role lookup
    current_time = int(time.time())
    params = {
        'uid': UID,
        'email': EMAIL,
        'userid': userid,
        'zoneid': zoneid,
        'product': 'mobilelegends',
        'productid': product_id,
        'time': current_time
    }
    params['sign'] = calculate_sign(params)

    async with aiohttp.ClientSession() as session:  # Use an async session
        try:
            async with session.post(endpoint, data=params, headers={'Content-Type': 'application/x-www-form-urlencoded'}) as response:
                response.raise_for_status()  # Raise an error for bad responses
                data = await response.json()  # Await the JSON response
                print(data)
                return data if data.get('status') == 200 else None
        except aiohttp.ClientError as e:
            logger.error(f"Error fetching role info: {e}")
            return None


async def role_command(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)  # Get the user ID as a string
    
    # Check if user is registered by admin
    user_data = await users_collection.find_one({"user_id": user_id})
    if not user_data:
        await update.message.reply_text("You are not registered to use this bot. Please ask an admin to register you.", parse_mode='HTML')
        return

    args = context.args
    if len(args) != 2:
        await update.message.reply_text('Contact to @minhtet4604 ')
        return
    userid = args[0].strip('()') # Strip parentheses
    zoneid = args[1].strip('()') # Strip parentheses
    role_info = await get_role_info(userid, zoneid)  # Await this call
    if role_info:
        username = role_info.get(
            'username', 'N/A')  # Check username for special characters
        reply_message = (
            f"<b>===  ===</b>\n"
            f"<b>Username:</b> {html.escape(str(username))}\n" # Escape username
            f"<b>         ID       :</b> <code>{html.escape(str(userid))}</code>\n" # Escape user ID
            f"<b>    Sever ID   :</b> {html.escape(str(zoneid))}" # Escape zone ID
        )
        await update.message.reply_text(reply_message, parse_mode='HTML')  # Use HTML for formatting
    else:
        await update.message.reply_text('Failed to fetch role info. Try again later.')


async def query_point_command(update: Update, context: CallbackContext):
    user_id = int(update.message.from_user.id) # Ensure user_id is int for comparison
    # Authorization check
    if user_id not in admins:
        await update.message.reply_text('Unauthorized access.')
        return

    async def get_query_points(endpoint: str, region: str):
        current_time = int(time.time())
        params = {
            'uid': UID,
            'email': EMAIL,
            'product': 'mobilelegends',
            'time': current_time
        }
        params['sign'] = calculate_sign(params)

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(endpoint, data=params) as response:
                    response.raise_for_status()
                    return await response.json()
            except aiohttp.ClientError as e:
                logger.error(f"Error fetching {region} points: {e}")
                return None

    # Define the endpoints
    endpoint_ph = f"{SMILE_ONE_BASE_URL_PH}/smilecoin/api/querypoints"
    endpoint_br = f"{SMILE_ONE_BASE_URL_BR}/smilecoin/api/querypoints"

    # Fetch Smile Points asynchronously
    response_ph = await get_query_points(endpoint_ph, "PH")
    response_br = await get_query_points(endpoint_br, "BR")

    # Extract points
    points_ph = response_ph.get('smile_points', 'Unavailable') if response_ph else 'Unavailable'
    points_br = response_br.get('smile_points', 'Unavailable') if response_br else 'Unavailable'

    # Format response using HTML parse mode
    response_message = (
        f"<b>ADMIN BALANCE</b>:\n\n"
        f"🇵🇭 <b>Smile One PH</b>: {html.escape(str(points_ph))}\n" # Escape points
        f"🇧🇷 <b>Smile One BR</b>: {html.escape(str(points_br))}\n" # Escape points
    )

    # Send response
    await update.message.reply_text(response_message, parse_mode='HTML')


product_info_ph = {
    "11": {"id": "212", "rate": 9.50},
    "22": {"id": "213", "rate": 19.00},
    "56": {"id": "214", "rate": 47.50},
    "112": {"id": "215", "rate": 95.00},
    "223": {"id": "216", "rate": 190.00},
    "336": {"id": "217", "rate": 285.00},
    "570": {"id": "218", "rate": 475.00},
    "1163": {"id": "219", "rate": 950.00},
    "2398": {"id": "220", "rate": 1900.00},
    "6042": {"id": "221", "rate": 4750.00},
    "wdp": {"id": "16641", "rate": 95.00},
}

product_info_br = {
    "svp": {"id": "22594", "rate": 39.00},
    "55": {"id": "22590", "rate": 39.00},
    "165": {"id": "22591", "rate": 116.90},
    "275": {"id": "22592", "rate": 187.50},
    "565": {"id": "22593", "rate": 385.00},
    "86": {"id": "13", "rate": 61.50},
    "172": {"id": "23", "rate": 122.00},
    "257": {"id": "25", "rate": 177.50},
    "706": {"id": "26", "rate": 480.00},
    "2195": {"id": "27", "rate": 1453.00},
    "3688": {"id": "28", "rate": 2424.00},
    "5532": {"id": "29", "rate": 3660.00},
    "9288": {"id": "30", "rate": 6079.00},
    "twilight": {"id": "33", "rate": 402.50},
    "wkp": {"id": "16642", "rate": 76.00},
    "343": {"id": ["13", "25"], "rate": 239.00},
    "344": {"id": ["23", "23"], "rate": 244.00},
    "429": {"id": ["23", "25"], "rate": 299.00},
    "514": {"id": ["25", "25"], "rate": 355.00},
    "600": {"id": ["25", "25", "13"], "rate": 416.00},
    "792": {"id": ["26", "13"], "rate": 541.00},
    "878": {"id": ["26", "23"], "rate": 602.00},
    "963": {"id": ["26", "25"], "rate": 657.00},
    "1049": {"id": ["26", "25", "13"], "rate": 719.00},
    "1135": {"id": ["26", "25", "23"], "rate": 779.00},
    "1220": {"id": ["26", "25", "25"], "rate": 835.00},
    "1412": {"id": ["26", "26"], "rate": 960.00},
    "1584": {"id": ["26", "26", "23"], "rate": 1082.00},
    "1755": {"id": ["26", "26", "25", "13"], "rate": 1199.00},
    "2901": {"id": ["27", "26"], "rate": 1940.00},
    "4390": {"id": ["27", "27"], "rate": 2906.00},
    "11483": {"id": ["30", "27"], "rate": 7532.00},
    "wkp2": {"id": ["16642", "16642"], "rate": 152.00},
    "wkp3": {"id": ["16642", "16642", "16642"], "rate": 228.00},
    "wkp4": {"id": ["16642", "16642", "16642", "16642"], "rate": 304.00},
    "wkp5": {"id": ["16642", "16642", "16642", "16642", "16642"], "rate": 380.00},
    "wkp10": {"id": ["16642", "16642", "16642", "16642", "16642", "16642", "16642", "16642", "16642", "16642"], "rate": 760.00},
}


async def create_order_and_log(userid: str, zoneid: str, product_id: str, base_url: str): # Added base_url parameter
    endpoint = f"{base_url}/smilecoin/api/createorder"
    current_time = int(time.time())

    params = {
        'uid': UID,
        'email': EMAIL,
        'userid': userid,
        'zoneid': zoneid,
        'product': 'mobilelegends',
        'productid': product_id,
        'time': current_time
    }

    params['sign'] = calculate_sign(params)

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(endpoint, data=params) as response:
                response.raise_for_status()
                data = await response.json()

                if data.get('status') == 200:
                    return {"order_id": data.get('order_id')}  # Return only the order ID if successful
                else:
                    error_message = data.get('message', 'Unknown error')  # Capture the specific failure reason
                    logger.error(f"Failed to create order via {base_url}: {error_message}")
                    return {"order_id": None, "reason": error_message}  # Return None with reason
        except aiohttp.ClientError as e:
            logger.error(f"Error creating order via {base_url}: {e}")
            return {"order_id": None, "reason": str(e)}  # Capture client error as reason if needed


async def bulk_command(update: Update, context: CallbackContext, region: str, product_info: dict, balance_type: str):
    user_id = str(update.message.from_user.id)  # Get the user ID as a string
    
    # Check if user is registered by admin
    user_data = await users_collection.find_one({"user_id": user_id})
    if not user_data:
        await update.message.reply_text("You are not registered to use this bot. Please ask an admin to register you.", parse_mode='HTML')
        return

    args = context.args

    command = 'mmb' if region == 'br' else 'mmp'

    # Security: Check for multiple commands in one input
    if len(update.message.text.split(f'/{command}')) > 2:
        await update.message.reply_text(f"Multiple /{command} commands detected in one input. Process aborted for security reasons.")
        return

    if len(args) < 3:  # Expecting at least one user ID, zone ID, and one product name
        await update.message.reply_text('Contact to @minhtet4604')
        return

    order_requests = []
    failed_orders = []
    sender_user_id = str(update.message.from_user.id)

    loading_message = await update.message.reply_text(
        "<b>Please Wait A Second</b> 🕐",
        parse_mode="HTML"
    )
    
    base_url_for_region = SMILE_ONE_BASE_URL_PH if region == 'ph' else SMILE_ONE_BASE_URL_BR

    # Iterate through the args to extract user ID, zone ID, and product names
    for i in range(0, len(args), 3):
        if i + 2 >= len(args):
            await update.message.reply_text('Invalid input. Make sure to provide user ID, zone ID, and product name for each order.')
            return

        user_id_raw = args[i]
        zone_id_raw = args[i+1]
        product_name = args[i+2].lower() # Ensure the product name is in lowercase

        # Strip parentheses from user_id and zone_id
        user_id_str = user_id_raw.strip('()')
        zone_id = zone_id_raw.strip('()')

        # Check if the product name is valid
        product = product_info.get(product_name)
        if not product:
            failed_orders.append({ # Append as dictionary for individual failed reports
                "user_id": user_id_str,
                "zone_id": zone_id,
                "product_name": product_name,
                "reason": "Invalid Product"
            })
            continue

        # Determine the rate based on user type
        product_rate = product["rate"]
        if product_rate is None:
            failed_orders.append({ # Append as dictionary for individual failed reports
                "user_id": user_id_str,
                "zone_id": zone_id,
                "product_name": product_name,
                "reason": "Product rate not available"
            })
            continue
        order_requests.append({
            "user_id": user_id_str,
            "zone_id": zone_id,
            "product_name": product_name,
            "product_rate": product_rate,
            "product_ids": product['id'] if isinstance(product['id'], list) else [product['id']]
        })

    if not order_requests:
        await loading_message.edit_text("No valid orders to process. Please Enter Valid Product Name", parse_mode='HTML')
        return

    # Check if the user has sufficient balance for ALL orders first
    current_balance_dict = await get_balance(sender_user_id) # Get the full balance dictionary
    if current_balance_dict is None:
        print(f"[ERROR] Sender wallet balance not found for User ID: {sender_user_id}")
        await loading_message.edit_text("Contact to @minhtet4604", parse_mode='HTML')
        return
    
    current_available_balance = current_balance_dict.get(balance_type, 0)

    # Calculate total cost of all valid orders
    total_cost_for_all_valid_orders = sum(order['product_rate'] for order in order_requests)

    # Check if the user's total balance is sufficient for all orders
    if current_available_balance < total_cost_for_all_valid_orders:
        print(f"[ERROR] Insufficient balance for User ID: {sender_user_id}. Required: {total_cost_for_all_valid_orders}, Available: {current_available_balance}")
        await loading_message.edit_text(
            f"Not Enough Balance for all orders.\nAvailable Balance: {current_available_balance}\nTotal Required: {total_cost_for_all_valid_orders}",
            parse_mode='HTML'
        )
        return

    # Process orders
    order_summary = []
    transaction_documents = []

    for order in order_requests:
        # Before processing each order, verify current balance again to prevent over-deduction
        # This is important if orders are processed one by one and balance is reduced.
        current_balance_for_deduction = (await get_balance(sender_user_id)).get(balance_type, 0.0)
        
        if current_balance_for_deduction < order['product_rate']:
            failed_orders.append({ # Append as dictionary for individual failed reports
                "user_id": order['user_id'],
                "zone_id": order['zone_id'],
                "product_name": order['product_name'],
                "reason": "Insufficient Balance during processing (after initial check)"
            })
            continue # Skip this order and move to the next

        # Store balance before deduction for this specific order
        initial_balance_for_this_order = current_balance_for_deduction

        # Attempt to deduct balance for the current order ATOMICALLY.
        # This will return None if balance is insufficient or user not found.
        new_balance_after_deduction = await update_balance(
            sender_user_id, -order['product_rate'], balance_type)

        if new_balance_after_deduction is None:
            # If deduction failed (e.g., insufficient balance or other DB issue)
            failed_orders.append({ # Append as dictionary for individual failed reports
                "user_id": order['user_id'],
                "zone_id": order['zone_id'],
                "product_name": order['product_name'],
                "reason": "Balance Deduction Failed (e.g., Insufficient Balance)"
            })
            continue # Skip this order and move to the next


        # Process the order with Smile One API
        order_ids = []
        order_failed_during_api_call = False
        for pid in order['product_ids']:
            # Pass the correct base_url for the region
            result = await create_order_and_log(order['user_id'], order['zone_id'], pid, base_url_for_region)
            order_id = result.get("order_id")
            if not order_id:
                # Order creation failed for one of the product IDs on Smile One
                failed_orders.append({ # Append as dictionary for individual failed reports
                    "user_id": order['user_id'],
                    "zone_id": order['zone_id'],
                    "product_name": order['product_name'],
                    "reason": html.escape(result.get('reason', 'Smile One Order creation failed'))
                })
                order_failed_during_api_call = True
                # Revert the balance deduction if any part of the order fails, UNLESS it's a SPECIAL_NON_REVERT_PACKAGE
                if order['product_name'] not in SPECIAL_NON_REVERT_PACKAGES:
                    reverted_balance = await update_balance(sender_user_id, order['product_rate'], balance_type)
                    if reverted_balance is not None:
                         logger.info(f"Reverted {order['product_rate']} to user {sender_user_id}. New balance: {reverted_balance}")
                    else:
                         logger.error(f"Failed to revert {order['product_rate']} to user {sender_user_id} after API failure.")
                else:
                    logger.info(f"Balance NOT reverted for {order['product_name']} for user {sender_user_id} due to SPECIAL_NON_REVERT_PACKAGES rule.")
                break # Stop processing product IDs for this order
            order_ids.append(order_id)

        if order_failed_during_api_call:
            continue # Move to the next order if API call failed for this one

        # If all product IDs for the order were processed successfully with Smile One
        role_info = await get_role_info(order['user_id'], order['zone_id'])
        username_from_role = html.escape(role_info.get('username', 'N/A')) if role_info else 'N/A'

        if role_info is None:
            # Role lookup failed, revert balance, UNLESS it's a SPECIAL_NON_REVERT_PACKAGE
            if order['product_name'] not in SPECIAL_NON_REVERT_PACKAGES:
                reverted_balance = await update_balance(sender_user_id, order['product_rate'], balance_type)  # Re-add balance on failed user lookup
                if reverted_balance is not None:
                    logger.info(f"Reverted {order['product_rate']} to user {sender_user_id}. New balance: {reverted_balance} (role lookup failed)")
                else:
                    logger.error(f"Failed to revert {order['product_rate']} to user {sender_user_id} after role lookup failure.")
            else:
                logger.info(f"Balance NOT reverted for {order['product_name']} for user {sender_user_id} due to SPECIAL_NON_REVERT_PACKAGES rule.")

            failed_orders.append({ # Append as dictionary for individual failed reports
                "user_id": order['user_id'],
                "zone_id": order['zone_id'],
                "product_name": order['product_name'],
                "reason": "User ID not exist (failed role lookup)"
            })
            continue

        # Get the balance after successful processing (this is the true remaining balance)
        final_remaining_balance_for_order = (await get_balance(sender_user_id)).get(balance_type, 0.0)

        order_summary.append({
            "order_ids": order_ids,
            "username": username_from_role,
            "user_id": order['user_id'],
            "zone_id": order['zone_id'],
            "product_name": order['product_name'],
            "total_cost": order['product_rate'],
            "remaining_balance": final_remaining_balance_for_order # Store actual remaining balance for this specific order
        })

        transaction_documents.append({
            "sender_user_id": sender_user_id,
            "user_id": order['user_id'],
            "zone_id": order['zone_id'],
            "username": username_from_role,
            "product_name": order['product_name'],
            "order_ids": order_ids,
            "date": datetime.now(ZoneInfo("Asia/Yangon")).strftime('%I:%M:%S %p %Y-%m-%d'),  # Store date with 12-hour format
            "total_cost": order['product_rate'],
            "status": "success",
            "initial_balance": final_remaining_balance_for_order # Store initial balance (or remaining) in transaction doc
        })

    # Insert all successful transactions to database
    if transaction_documents:
        try:
            await order_collection.insert_many(transaction_documents)
        except Exception as e:
             logger.error(f"Error inserting transactions: {e}")
             # This error should ideally not prevent sending reports, but needs logging
             pass

    # Send individual transaction reports for successful orders
    if order_summary:
        current_summary_time = datetime.now(ZoneInfo("Asia/Yangon")).strftime('%I:%M:%S %p %Y-%m-%d')
        for detail in order_summary:
            order_ids_str = ', '.join(detail["order_ids"])
            individual_report = (
                f"======{region.upper()} Transaction Report======\n"
                f"<b>Order Status    :  </b> Completed✅\n"
                f"<b>Order ID            :  </b> <code>{html.escape(str(order_ids_str))}</code>\n"
                f"<b>Game Name    :  </b> {html.escape(detail['username'])}\n"
                f"<b>Game ID           :  </b> <code>{html.escape(str(detail['user_id']))}</code>\n"
                f"<b>Game Server    :  </b> {html.escape(str(detail['zone_id']))}\n"
                f"<b>Time                  :  </b> {current_summary_time}\n"
                f"<b>Amount             :  </b> {html.escape(str(detail['product_name']))}💎\n"
                f"<b>Total Cost         :  </b> ${detail['total_cost']:.2f} 🪙\n"
                f"<b>Remaining Balance:  </b> ${detail['remaining_balance']:.2f} 🪙\n\n"
            )
            try:
                await update.message.reply_text(individual_report, parse_mode='HTML')
            except Exception as e:
                logger.error(f"Error sending individual report for order {order_ids_str}: {e}")
                # Log error but continue to send other reports

    # Send individual reports for failed orders (if any)
    if failed_orders:
        current_summary_time = datetime.now(ZoneInfo("Asia/Yangon")).strftime('%I:%M:%S %p %Y-%m-%d')
        for failed_order_detail in failed_orders: # failed_orders now contains dictionaries
            failed_report_text = (
                f"======{region.upper()} Transaction Report======\n"
                f"<b>Order Status    :  </b> Failed🚫\n"
                f"<b>Game ID           :  </b> {html.escape(failed_order_detail.get('user_id', 'N/A'))}\n"
                f"<b>Game Server    :  </b> {html.escape(failed_order_detail.get('zone_id', 'N/A'))}\n"
                f"<b>Items                :  </b> {html.escape(failed_order_detail.get('product_name', 'N/A'))}\n"
                f"<b>Reason            :  </b> {html.escape(failed_order_detail.get('reason', 'Unknown failure'))}\n"
                f"<b>Time                  :  </b> {current_summary_time}\n\n"
            )
            try:
                await update.message.reply_text(failed_report_text, parse_mode='HTML')
            except Exception as e:
                logger.error(f"Error sending individual failed report for {failed_order_detail.get('user_id', 'N/A')}: {e}")
            
    # Final message to user
    try:
        if order_summary or failed_orders:
            # If any reports (successful or failed) were sent, update loading message
            await loading_message.edit_text("✅ All orders processed. Check new messages for individual reports.", parse_mode='HTML')
        else:
            # If no orders were processed at all (e.g., initial command parsing failed)
            await loading_message.edit_text("No orders were processed. Please check your command.", parse_mode='HTML')
    except Exception as e:
        logger.error(f"Error updating final loading message: {e}")


async def bulk_command_ph(update: Update, context: CallbackContext):
    await bulk_command(update, context, 'ph', product_info_ph, 'balance_ph')


async def bulk_command_br(update: Update, context: CallbackContext):
    await bulk_command(update, context, 'br', product_info_br, 'balance_br')


if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('getid', getid_command))
    app.add_handler(CommandHandler('bal', balance_command))  # user balance
    app.add_handler(CommandHandler('bal_admin', query_point_command))  # admin balance
    app.add_handler(CommandHandler('admin', admin_command))
    app.add_handler(CommandHandler('pricebr', pricebr_command))
    app.add_handler(CommandHandler('priceph', priceph_command))
    app.add_handler(CommandHandler('use', use_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('role', role_command))  # user name check
    app.add_handler(CommandHandler('mmp', bulk_command_ph))
    app.add_handler(CommandHandler('mmb', bulk_command_br))
    app.add_handler(CommandHandler('add_bal', add_balance_command))  # add balance for user
    app.add_handler(CommandHandler('ded_bal', deduct_balance_command))  # remove balance from user
    app.add_handler(CommandHandler('user', get_users_command))  # admin command user list collect
    app.add_handler(CommandHandler('all_his', get_all_orders))
    app.add_handler(CommandHandler('his', get_user_orders))  # order history
    app.add_handler(CommandHandler('registeruser', register_user_by_admin_command)) # New admin command for registration
    app.add_handler(CommandHandler('removeuser', remove_user_by_admin_command)) # New admin command to remove user

    print("Bot is running...")
    app.run_polling(poll_interval=3)
