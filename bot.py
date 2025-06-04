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
admins = [5671920054, 1836389511, 7135882496]

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


############ General message parts ###############

# Fetch and display user ID
async def getid_command(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    await update.message.reply_text(f"Your Telegram user 🆔 is: {user_id}")


async def start_command(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)  # Telegram user ID
    username = update.message.from_user.username

    # Check if the user exists in the database
    user = await users_collection.find_one({"user_id": user_id})

    if not user:
        # Show the introduction message with a Register button
        not_registered_message = ("<b>WELCOME TO Minhtet Bot</b>\n"
                                  "<b>Register Now 👇</b>\n")
        # Add a Register button
        keyboard = [
            [InlineKeyboardButton("✅ Register", callback_data="register_user")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            not_registered_message,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    else:
        balance_ph = user.get('balance_ph', 0)
        balance_br = user.get('balance_br', 0)
        existing_user_message = (
            "<b>HI! DEAR,</b>\n"
            "Your current balances:\n"
            f"1️⃣ PH Balance : ${balance_ph}\n"
            f"2️⃣ BR Balance : ${balance_br}\n\n"
            "<b>PLEASE PRESS /help FOR HOW TO USED</b>\n"
        )
        await update.message.reply_text(existing_user_message, parse_mode="HTML")


async def handle_register_user(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()  # Acknowledge the callback query
    user_id = str(query.from_user.id)

    # Check if the user is already registered
    user = await users_collection.find_one({"user_id": user_id})
    if user:
        # User is already registered
        balance_ph = user.get('balance_ph', 0)
        balance_br = user.get('balance_br', 0)
        existing_user_message = (
            "Hi Dear, You are already registered!\n"
            "Your Current Balances:\n"
            f"1️⃣ PH Balance : ${balance_ph}\n"
            f"2️⃣ BR Balance : ${balance_br}\n\n"
            "<b>PLEASE PRESS /help FOR HOW TO USED</b>\n"
        )
        await query.edit_message_text(existing_user_message, parse_mode="HTML")
    else:
        # Register the user
        new_user = {
            "user_id": user_id,
            "balance_ph": 0,  # Initialize PH balance
            "balance_br": 0,  # Initialize BR balance
            "date_joined": int(time.time())
        }
        await users_collection.insert_one(new_user)

        # Send a successful registration message
        success_message = (
            "🎉 <b>Registration Successful!</b>\n"
            "You are now registered in our system. Welcome to our services!\n"
            "Your current balances:\n"
            "PH Balance : \$0\n"
            "BR Balance : \$0\n\n"
            "<b>PLEASE PRESS /help FOR HOW TO USED</b>\n"
        )
        await query.edit_message_text(success_message, parse_mode="HTML")


async def help_command(update: Update, context: CallbackContext):
    username = update.message.from_user.username
    user_id = str(update.message.from_user.id)  # Get the user ID as a string

    # Check if the user is registered in the database
    user = await users_collection.find_one({"user_id": user_id})

    if not user:
        # If the user is not found in the database
        await update.message.reply_text("ဆက်သွယ်ရန်😘😘@minhtet4604 ")
        return

    help_message = f"""
<b>HELLO</b> {username} 🤖

Please Contact admin ☺️
@minhtet4604

<b>COMMAND LIST</b>

/bal - <b>Bot Balance</b>

/his - <b>Orders History</b>

/role - <b>Check Username MAGIC CHESS GOGO</b>

/getid - <b>Account ID</b>

/price - <b>Price List</b>

/mgcp - <b>Order PH</b>

/mgcb - <b>Order BR</b>

    """
    try:
        # Log the message for debugging
        logger.info("Sending help message: %s", help_message)
        await update.message.reply_text(help_message, parse_mode='HTML')  # Use HTML
    except Exception as e:
        logger.error("Failed to send help message: %s", e)
        await update.message.reply_text("An error occurred while sending the help message.")


async def price_command(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)

    # Check if the user is registered in the database
    user = await users_collection.find_one({"user_id": user_id})

    if not user:
        await update.message.reply_text("ဆက်သွယ်ရန် 🥰🥰 @minhtet4604")
        return

    # Define the merged price list
    price_list = """
<b>Pack List (PH and BR):</b>

🇧🇷
Bonus Pack
55 = 40 🪙
165=120 🪙
275=200 🪙
565=400 🪙
wdp - 97.9 🪙

💎86  = 62.5 🪙
💎172 =125 🪙
💎257  =187 🪙
💎344  =250 🪙
💎516  =375 🪙
💎706 =500 🪙
💎1346 =937.5 🪙
💎1825 =1250 🪙
💎2195 =1500 🪙
💎3688=2500 🪙 
💎5532 =3750 🪙
💎9288=6250 🪙


🇵🇭

Bonus Pack
55=48.95 🪙
165=145.04 🪙
275=241.08 🪙
565=488.04 🪙
wdp= 98🪙

💎5=4.9 🪙
💎11=9.31 🪙
💎22=18.62 🪙
💎56= 46.55 🪙
💎112= 93.1 🪙
💎223= 186.2 🪙
💎339= 279.3 🪙
💎570= 465.5🪙
💎1163=931🪙
💎2398= 1862🪙
💎6042= 4655🪙"""
    await update.message.reply_text(price_list, parse_mode='HTML')


async def admin_command(update: Update, context: CallbackContext):
    username = update.message.from_user.username

    user_id = update.message.from_user.id
    # Check if the user is an admin
    if user_id not in admins:
        await update.message.reply_text("❌Unauthorized Alert🚨")
        return

    help_message = f"""
<b>Hello Admin</b> {username}
<b>You can use below commands :</B>

1️⃣<b>Admin Mode</b>:
 /bal_admin - <b>Check balance</b>
 /user - <b>User List</b>
 /all_his - <b>All Order History</b>

2️⃣ <b>Wallet Topup:</b>

Ask to user for telegram_id Press
/getid

Added
/add_bal 1836389511 500 balance_ph
/add_bal telegram_id amount balance_type

Deducted
/ded_bal 1836389511 500 balance_br
/ded_bal telegram_id amount balance_type
    """

    try:
        # Log the message for debugging
        logger.info("Sending help message: %s", help_message)
        await update.message.reply_text(help_message, parse_mode='HTML')  # Use HTML parsing
    except Exception as e:
        logger.error("Failed to send help message: %s", e)
        await update.message.reply_text("An error occurred while sending the help message.")


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

    user = await users_collection.find_one({"user_id": user_id})

    if not user:
        # If the user is not found in the database
        await update.message.reply_text("ဆက်သွယ်ရန် @minhtet4604 ")
        return

    balances = await get_balance(user_id)  # Await the async get_balance function

    if balances:
        balance_ph = balances.get('balance_ph', 0)  # Fetch balance for PH
        balance_br = balances.get('balance_br', 0)  # Fetch balance for BR

        # Format the response with emojis and Markdown styling
        response_message = (
            f"*MinHtet Bot BALANCE 💰:*\n\n"
            f"🇵🇭 *PH Balance*: `{balance_ph:.2f}` 🪙\n"
            f"🇧🇷 *BR Balance*: `{balance_br:.2f}` 🪙\n"
        )

        await update.message.reply_text(response_message, parse_mode='Markdown')
    else:
        await update.message.reply_text("ဆက်သွယ်ရန်@minhtet4604")


async def update_balance(user_id: str, amount: int, balance_type: str):
    """
    Updates the balance of the specified user.
    """
    user = await users_collection.find_one({"user_id": user_id})
    if user:
        current_balance = user.get(balance_type, 0)
        new_balance = current_balance + amount

        await users_collection.update_one({"user_id": user_id}, {"$set": {balance_type: new_balance}})
        return new_balance
    return None


async def add_balance_command(update: Update, context: CallbackContext):
    """
    Command to add balance to a user's account.
    """
    admin_user_id = str(update.message.from_user.id)  # Get the user ID of the admin issuing the command

    # Check if the user is an admin
    if int(admin_user_id) not in admins:
        await update.message.reply_text("🚫 *Unauthorized*: You are not allowed to use this command.", parse_mode='Markdown')
        return

    # Expecting three arguments: target_user_id, amount, balance_type
    if len(context.args) != 3 or not context.args[1].isdigit() or context.args[2] not in ['balance_ph', 'balance_br']:
        await update.message.reply_text(
            "*Usage*: `/add_bal <user_id> <amount> <balance_type>` balance_type should be either balance_ph or balance_br",
            parse_mode='Markdown'
        )
        return

    target_user_id = context.args[0]  # The user ID to add balance to
    amount = int(context.args[1])  # The amount to add
    balance_type = context.args[2]

    # Check if the target user exists in the database
    target_user = await users_collection.find_one({"user_id": target_user_id})
    if not target_user:
        await update.message.reply_text(f"❌ *User Not Found*: No user with ID `{target_user_id}` found.", parse_mode='Markdown')
        return

    # Add the balance to the target user
    try:
        new_balance = await update_balance(target_user_id, amount, balance_type)

        if new_balance is not None:
            # Success message with formatting using HTML parse mode
            success_message_text = (
                f"✅ <b>Success!</b> Added <code>{html.escape(str(amount))}</code> to <b>User ID</b> <code>{html.escape(str(target_user_id))}</code>'s {html.escape(balance_type)}.\n\n"
                f"🇲🇲 New Balance: <code>{html.escape(str(new_balance))}</code> 🪙"
            )
            try:
                await update.message.reply_text(success_message_text, parse_mode='HTML')
                logger.info(f"Successfully sent add_balance success message for user {target_user_id}")
            except Exception as send_error:
                logger.error(f"Error sending add_balance success message to user {target_user_id}: {send_error}")
                # Fallback to plain text message if HTML fails
                await update.message.reply_text("✅ Success! Balance updated.", parse_mode=None)
        else:
             # This case should ideally not be reached if target_user exists and update_balance logic is correct
             await update.message.reply_text(f"❌ *Failed*: Unable to update balance for *User ID* `{target_user_id}`.", parse_mode='Markdown')
    except Exception as general_error:
        # Catch other potential errors before sending the success message
        logger.error(f"Error during add_balance command for user {target_user_id}: {general_error}")
        await update.message.reply_text(f"An error occurred while adding balance for user ID `{target_user_id}`.", parse_mode='Markdown')



async def deduct_balance_command(update: Update, context: CallbackContext):
    """
    Command to deduct balance from a user's account.
    """
    user_id = str(update.message.from_user.id)  # Get the user ID of the person issuing the command

    # Check if the user is an admin
    if int(user_id) not in admins:
        await update.message.reply_text(
            "🚫 *Unauthorized*: You are not allowed to use this command.",
            parse_mode='Markdown'
        )
        return

    # Expecting three arguments: target_user_id, amount, balance_type
    if len(context.args) != 3 or not context.args[1].isdigit() or context.args[2] not in ['balance_ph', 'balance_br']:
        await update.message.reply_text(
            "*Usage*: `/ded_bal <user_id> <amount> <balance_type>` balance_type should be either balance_ph or balance_br",
            parse_mode='Markdown'
        )
        return

    target_user_id = context.args[0]  # The user ID to deduct balance from
    amount = int(context.args[1])  # The amount to deduct
    balance_type = context.args[2]

    # Check if the target user exists in the database
    target_user = await users_collection.find_one({"user_id": target_user_id})
    if not target_user:
        await update.message.reply_text(
            f"❌ *User Not Found*: No user with ID `{target_user_id}` found.",
            parse_mode='Markdown'
        )
        return

    # Deduct the balance from the target user
    try:
        new_balance = await update_balance(target_user_id, -amount, balance_type)

        if new_balance is not None:
            # Success message with formatting using HTML parse mode
            success_message_text = (
                f"✅ <b>Success!</b> Deducted <code>{html.escape(str(amount))}</code> from <b>User ID</b> <code>{html.escape(str(target_user_id))}</code>'s {html.escape(balance_type)}.\n\n"
                f"💵 New Balance: <code>{html.escape(str(new_balance))}</code> 🪙"
            )
            try:
                await update.message.reply_text(success_message_text, parse_mode='HTML')
                logger.info(f"Successfully sent deduct_balance success message for user {target_user_id}")
            except Exception as send_error:
                logger.error(f"Error sending deduct_balance success message to user {target_user_id}: {send_error}")
                 # Fallback to plain text message if HTML fails
                await update.message.reply_text("✅ Success! Balance updated.", parse_mode=None)
        else:
             # This case should be for insufficient balance based on update_balance logic
            await update.message.reply_text(
                f"❌ *Failed*: Insufficient balance for *User ID* `{target_user_id}` or deduction failed.",
                parse_mode='Markdown'
            )
    except Exception as general_error:
        logger.error(f"Error deducting balance: {general_error}")
        await update.message.reply_text(f"An error occurred while deducting balance for user ID `{target_user_id}`.", parse_mode='Markdown')


def split_message(text, max_length=4096):
    """Splits the message into chunks that fit within the Telegram message limit."""
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]


async def get_users_command(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id  # Get the user ID of the person issuing the command

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
        user_id = user.get('user_id', 'N/A')
        balance_ph = user.get('balance_ph', 0)
        balance_br = user.get('balance_br', 0)
        # Format date joined to 12-hour format
        date_joined_timestamp = user.get('date_joined', 0)
        date_joined_formatted = datetime.fromtimestamp(date_joined_timestamp).strftime('%Y-%m-%d %I:%M:%S %p') if date_joined_timestamp != 0 else 'N/A'


        # Enhance the output with clear formatting
        response_summary += (
            f"🆔 USER ID: {html.escape(str(user_id))}\n" # Escape user ID
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

    # Query both collections for orders made by this sender
    transactions_cursor = order_collection.find(
        {"sender_user_id": sender_user_id})

    # Convert the cursors to lists asynchronously
    transactions_list = await transactions_cursor.to_list(length=None)

    response_summary = "==== Order History ====\n\n"

    # Process orders from transactions_collection
    for order in transactions_list:
        sender_user_id = order.get('sender_user_id', 'N/A')
        user_id = order.get('player_id', 'N/A')
        zone_id = order.get('zone_id', 'N/A')
        pack = order.get('product_name', 'N/A')
        order_ids = order.get('order_ids', 'N/A')
        # Retrieve and format date to 12-hour format if available
        date_str = order.get('date', 'N/A')
        formatted_date = date_str
        if date_str != 'N/A':
            try:
                # Attempt to parse the stored date string. Adjust format string if necessary.
                # Assuming the date is stored in '%Y-%m-%d %I:%M:%S %p' format
                order_date_obj = datetime.strptime(date_str, '%Y-%m-%d %I:%M:%S %p')
                formatted_date = order_date_obj.strftime('%Y-%m-%d %I:%M:%S %p') # Re-format to ensure consistency
            except ValueError:
                # If parsing fails, maybe the stored date doesn't include time or is in a different format
                # In this case, keep the original string or format just the date part.
                try:
                     date_only_obj = datetime.strptime(date_str.split(' ')[0], '%Y-%m-%d')
                     formatted_date = date_only_obj.strftime('%Y-%m-%d') # Format date only
                except ValueError:
                     pass # Keep original string if date-only parsing also fails


        total_cost = order.get('total_cost', 0.0)
        status = order.get('status', 'N/A')

        if isinstance(order_ids, list):
            order_ids = ', '.join(order_ids)
        else:
            order_ids = str(order_ids)

        response_summary += (
            f"🆔 Telegram ID: {html.escape(str(sender_user_id))}\n" # Escape sender user ID
            f"📍 Game ID: {html.escape(str(user_id))}\n" # Escape user ID
            f"🌍 Zone ID: {html.escape(str(zone_id))}\n" # Escape zone ID
            f"💎 Pack: {html.escape(str(pack))}\n" # Escape pack
            f"🆔 Order ID: {html.escape(str(order_ids))}\n" # Escape order IDs
            f"📅 Date: {formatted_date}\n" # Use formatted_date
            f"💵 Rate: $ {float(total_cost):.2f}\n"
            f"🔄 Status: {html.escape(str(status))}\n\n" # Escape status
        )

    # Split the message if it's too long for a single reply
    messages = split_message(response_summary)
    for msg in messages:
        await update.message.reply_text(msg, parse_mode='HTML') # Use HTML parse mode


async def get_all_orders(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)  # Get the Telegram user's ID

    # Check if the user is an admin
    if int(user_id) not in admins:  # Convert to integer for proper comparison
        logging.info(f"Unauthorized access attempt by user ID: {user_id}")
        await update.message.reply_text("❌ Unauthorized: You are not allowed to use this command.")
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
                    # Assuming the date is stored in '%Y-%m-%d %I:%M:%S %p' format
                    order_date_obj = datetime.strptime(date_str, '%Y-%m-%d %I:%M:%S %p')
                    formatted_date = order_date_obj.strftime('%Y-%m-%d %I:%M:%S %p') # Re-format to ensure consistency
                except ValueError:
                    # If parsing fails, maybe the stored date doesn't include time or is in a different format
                    # In this case, keep the original string or format just the date part.
                    try:
                        date_only_obj = datetime.strptime(date_str.split(' ')[0], '%Y-%m-%d')
                        formatted_date = date_only_obj.strftime('%Y-%m-%d') # Format date only
                    except ValueError:
                         pass # Keep original string if date-only parsing also fails


            total_cost = order.get('total_cost', 0.0)
            status = order.get('status', 'N/A')

            if isinstance(order_ids, list):
                order_ids = ', '.join(order_ids)
            else:
                order_ids = str(order_ids)

            response_summary += (
                f"🆔 Sender Telegram ID: {html.escape(str(sender_user_id))}\n" # Escape sender user ID
                f"🎮 Player ID: {html.escape(str(player_id))}\n" # Escape player ID
                f"🌍 Zone ID: {html.escape(str(zone_id))}\n" # Escape zone ID
                f"💎 Product: {html.escape(str(product_name))}\n" # Escape product name
                f"🆔 Order IDs: {html.escape(str(order_ids))}\n" # Escape order IDs
                f"📅 Date: {formatted_date}\n" # Use formatted_date
                f"💵 Total Cost: $ {float(total_cost):.2f}\n"
                f"🔄 Status: {html.escape(str(status))}\n\n" # Escape status
            )

        # Split the message if it's too long for Telegram's limit
        messages = split_message(response_summary)
        for msg in messages:
            await update.message.reply_text(msg, parse_mode='HTML') # Use HTML parse mode

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

    # Check if the user is registered in the database
    user = await users_collection.find_one({"user_id": user_id})

    if not user:
        # If the user is not found in the database
        await update.message.reply_text("ဆက်သွယ်ရန် @minhtet4604")
        return

    args = context.args
    if len(args) != 2:
        await update.message.reply_text('ဆက်သွယ်ရန် @minhtet4604 ')
        return
    userid, zoneid = args
    role_info = await get_role_info(userid, zoneid)  # Await this call
    if role_info:
        username = role_info.get(
            'username', 'N/A')  # Check username for special characters
        reply_message = (
            f"<b>=== အချက်အလက် ===</b>\n"
            f"<b>အသုံးပြုသူ:</b> {html.escape(str(username))}\n" # Escape username
            f"<b>  အိုင်ဒီ        :</b> {html.escape(str(userid))}\n" # Escape user ID
            f"<b>  ဆာဗာ        :</b> {html.escape(str(zoneid))}" # Escape zone ID
        )
        await update.message.reply_text(reply_message, parse_mode='HTML')  # Use HTML for formatting
    else:
        await update.message.reply_text('Failed to fetch role info. Try again later.')


async def query_point_command(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

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
    "55": {"id": "23918", "rate": 48.95},
    "165": {"id": "23919", "rate": 145.04},
    "275": {"id": "23920", "rate": 241.08},
    "565": {"id": "23921", "rate": 488.04},
    "5": {"id": "23906", "rate": 4.90},
    "11": {"id": "23907", "rate": 9.31},
    "22": {"id": "23908", "rate": 18.62},
    "56": {"id": "23909", "rate": 46.55},
    "112": {"id": "23910", "rate": 93.10},
    "223": {"id": "23911", "rate": 186.20},
    "336": {"id": "23912", "rate": 279.30},
    "570": {"id": "23913", "rate": 465.50},
    "1163": {"id": "23914", "rate": 931.00},
    "2398": {"id": "23915", "rate": 1862.00},
    "6042": {"id": "23916", "rate": 4655.00},
    "wdp": {"id": "23922", "rate": 98.00},
    
}

product_info_br = {
    
    "55": {"id": "23837", "rate": 40.00},
    "165": {"id": "23838", "rate": 120.00},
    "275": {"id": "23839", "rate": 200.00},
    "565": {"id": "23840", "rate": 400.00},
    "86": {"id": "23825", "rate": 62.50},
    "172": {"id": "23826", "rate": 125.00},
    "257": {"id": "23827", "rate": 187.000},
    "344": {"id": "23828", "rate": 250.00},
    "516": {"id": "23829", "rate": 375.00},
    "706": {"id": "23830", "rate": 500.00},
    "1346": {"id": "23831", "rate": 937.50},
    "1825": {"id": "23832", "rate": 1250.00},
    "2195": {"id": "23833", "rate": 1500.00},
    "3688": {"id": "23834", "rate": 2500.00},
    "5532": {"id": "23835", "rate": 3750.00},
    "9288": {"id": "23836", "rate": 6250.00},
    "wdp": {"id": "23841", "rate": 97.90},
    }


async def create_order_and_log(region: str, userid: str, zoneid: str, product_id: str):
    endpoint = f"{SMILE_ONE_BASE_URL_PH if region == 'ph' else SMILE_ONE_BASE_URL_BR}/smilecoin/api/createorder"
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
                    logger.error(f"Failed to create {region.upper()} order: {error_message}")
                    return {"order_id": None, "reason": error_message}  # Return None with reason
        except aiohttp.ClientError as e:
            logger.error(f"Error creating {region.upper()} order: {e}")
            return {"order_id": None, "reason": str(e)}  # Capture client error as reason if needed


async def bulk_command(update: Update, context: CallbackContext, region: str, product_info: dict, balance_type: str):
    user_id = str(update.message.from_user.id)  # Get the user ID as a string

    # Check if the user is registered in the database
    user = await users_collection.find_one({"user_id": user_id})
    if not user:
        await update.message.reply_text("ဆက်သွယ်ရန် @minhtet4604")
        return

    args = context.args

    command = 'mgcb' if region == 'br' else 'mgcp'

    # Security: Check for multiple commands in one input
    if len(update.message.text.split(f'/{command}')) > 2:
        await update.message.reply_text(f"Multiple /{command} commands detected in one input. Process aborted for security reasons.")
        return

    if len(args) < 3:  # Expecting at least one user ID, zone ID, and one product name
        await update.message.reply_text('ဆက်သွယ်ရန် @minhtet4604')
        return

    order_requests = []
    failed_orders = []
    sender_user_id = str(update.message.from_user.id)

    loading_message = await update.message.reply_text(
        "<b>ခဏစောင့်ပေးပါ</b> 🕐",
        parse_mode="HTML"
    )

    # Iterate through the args to extract user ID, zone ID, and product names
    for i in range(0, len(args), 3):
        if i + 2 >= len(args):
            await update.message.reply_text('Invalid input. Make sure to provide user ID, zone ID, and product name for each order.')
            return

        user_id, zone_id, product_name = args[i:i+3]
        product_name = product_name.lower()  # Ensure the product name is in lowercase

        # Check if the product name is valid
        product = product_info.get(product_name)
        if not product:
            failed_orders.append(
                f"<b>Game ID</b>: {html.escape(user_id)}\n" # Escape user ID
                f"<b>Game Server</b>: {html.escape(zone_id)}\n" # Escape zone ID
                f"<b>Items</b>: {html.escape(product_name)}\n" # Escape product name
                f"<b>Results</b>: Invalid Product\n\n"
            )
            continue

        # Determine the rate based on user type
        product_rate = product["rate"]
        if product_rate is None:
            failed_orders.append(
                f"<b>Game ID</b>: {html.escape(user_id)}\n" # Escape user ID
                f"<b>Game Server</b>: {html.escape(zone_id)}\n" # Escape zone ID
                f"<b>Items</b>: {html.escape(product_name)}\n" # Escape product name
                f"<b>Results:</b> Product rate not available\n\n"
            )
            continue
        order_requests.append({
            "user_id": user_id,
            "zone_id": zone_id,
            "product_name": product_name,
            "product_rate": product_rate,
            "product_ids": product['id'] if isinstance(product['id'], list) else [product['id']]
        })

    if not order_requests:
        await loading_message.edit_text("No valid orders to process. Please Enter Valid Product Name")
        return

    # Check if the user has sufficient balance
    current_balance = await get_balance(sender_user_id)
    if current_balance is None:
        print(f"[ERROR] Sender wallet balance not found for User ID: {sender_user_id}")
        await loading_message.edit_text("ဆက်သွယ်ရန် @minhtet4604")
        return
    # Calculate total cost of all valid orders
    total_cost = sum(order['product_rate'] for order in order_requests)

    # Check if the user's balance is sufficient for the total cost
    if current_balance[balance_type] < total_cost:
        print(f"[ERROR] Insufficient balance for User ID: {sender_user_id}. Required: {total_cost}, Available: {current_balance[balance_type]}")
        await loading_message.edit_text(
            f"လက်ကျန်ငွေ မလုံလောက်ပါ.\nAvailable Balance: {current_balance[balance_type]}\nစုစုပေါင်း: {total_cost}"
        )
        return

    # Process orders
    order_summary = []
    transaction_documents = []

    for order in order_requests:
        # Attempt to deduct balance for the current order
        new_balance = await update_balance(
            sender_user_id, -order['product_rate'], balance_type)

        if new_balance is None:
            # If deduction fails (user not found or insufficient balance during processing)
            failed_orders.append(
                f"<b>Game ID:</b> {html.escape(order['user_id'])}\n" # Escape user ID
                f"<b>Game Server:</b> {html.escape(order['zone_id'])}\n" # Escape zone ID
                f"<b>Items:</b> {html.escape(order['product_name'])}\n" # Escape product name
                f"<b>Results:</b> Insufficient Balance or Deduction Failed\n\n"
            )
            continue # Skip this order and move to the next

        # Process the order
        order_ids = []
        order_failed_during_processing = False
        for pid in order['product_ids']:
            result = await create_order_and_log(region, order['user_id'], order['zone_id'], pid)
            order_id = result.get("order_id")
            if not order_id:
                # Order creation failed for one of the product IDs
                failed_orders.append(
                    f"<b>Game ID:</b> {html.escape(order['user_id'])}\n" # Escape user ID
                    f"<b>Game Server:</b> {html.escape(order['zone_id'])}\n" # Escape zone ID
                    f"<b>Items:</b> {html.escape(order['product_name'])}\n" # Escape product name
                    f"<b>Results:</b> {html.escape(result.get('reason', 'Order creation failed'))}\n\n" # Escape reason
                )
                order_failed_during_processing = True
                # Revert the balance deduction if any part of the order fails
                await update_balance(sender_user_id, order['product_rate'], balance_type)
                break # Stop processing product IDs for this order
            order_ids.append(order_id)

        if order_failed_during_processing:
            continue # Move to the next order if processing failed for this one

        # If all product IDs for the order were processed successfully
        if order_ids:
            role_info = await get_role_info(order['user_id'], order['zone_id'])
            # Escape username if available, before using it
            username = html.escape(role_info.get('username', 'N/A')) if role_info else 'N/A'

            if role_info is None:
                await update_balance(sender_user_id, order['product_rate'], balance_type)  # Re-add balance on failed user lookup
                failed_orders.append(
                    f"<b>Game ID:</b> {html.escape(order['user_id'])}\n" # Escape user ID
                    f"<b>Game Server:</b> {html.escape(order['zone_id'])}\n" # Escape zone ID
                    f"<b>Items:</b> {html.escape(order['product_name'])}\n" # Escape product name
                    f"<b>Results:</b> User ID not exist\n\n"
                )
                continue


            order_summary.append({
                "order_ids": order_ids,
                "username": username,
                "user_id": order['user_id'],
                "zone_id": order['zone_id'],
                "product_name": order['product_name'],
                "total_cost": order['product_rate'],
            })

            transaction_documents.append({
                "sender_user_id": sender_user_id,
                "user_id": order['user_id'],
                "zone_id": order['zone_id'],
                "username": username,
                "product_name": order['product_name'],
                "order_ids": order_ids,
                "date": datetime.now(ZoneInfo("Asia/Yangon")).strftime('%Y-%m-%d %I:%M:%S %p'), # Store date with 12-hour format
                "total_cost": order['product_rate'],
                "status": "success"
            })

    # Insert all successful transactions
    if transaction_documents:
        try:
            await order_collection.insert_many(transaction_documents)
        except Exception as e:
             logger.error(f"Error inserting transactions: {e}")
             # Handle potential database insert errors, perhaps log and inform admin
             pass


    # Prepare response summary
    response_summary = f"======{region.upper()} Order Summary======\n"
    # Get the current time for the summary message
    current_summary_time = datetime.now(ZoneInfo("Asia/Yangon")).strftime('%Y-%m-%d %I:%M:%S %p') # Myanmar time in 12-hour format with AM/PM

    for detail in order_summary:
        order_ids_str = ', '.join(detail["order_ids"])
        response_summary += (
            f"<b>Order Completed:</b> ✅\n"
            f"<b>Order ID:</b> {html.escape(str(order_ids_str))}\n" # Escape order IDs string
            f"<b>Game Name:</b> {html.escape(detail['username'])}\n" # Escape username
            f"<b>Game ID:</b> {html.escape(str(detail['user_id']))}\n" # Escape user ID
            f"<b>Game Server:</b> {html.escape(str(detail['zone_id']))}\n" # Escape zone ID
            f"<b>Time:</b> {current_summary_time}\n" # Use the summary time or the stored order time
            f"<b>Amount:</b> {html.escape(str(detail['product_name']))}💎\n" # Escape product name
            f"<b>Total Cost:</b> ${detail['total_cost']:.2f} 🪙\n\n"
        )

    if failed_orders:
        response_summary += "\n<b>Failed Orders 🚫</b>:\n"
        response_summary += "".join(failed_orders) # Failed orders are already formatted with HTML

    try:
        await loading_message.edit_text(response_summary, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Error sending bulk command summary message: {e}")
        # Fallback to plain text if HTML summary fails
        await loading_message.edit_text("Order processing finished. Check logs for details.", parse_mode=None)


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
    app.add_handler(CommandHandler('price', price_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('role', role_command))  # user name check
    app.add_handler(CommandHandler('mgcp', bulk_command_ph))
    app.add_handler(CommandHandler('mgcb', bulk_command_br))
    app.add_handler(CommandHandler('add_bal', add_balance_command))  # add balance for user
    app.add_handler(CommandHandler('ded_bal', deduct_balance_command))  # remove balance from user
    app.add_handler(CommandHandler('user', get_users_command))  # admin command user list collect
    app.add_handler(CommandHandler('all_his', get_all_orders))
    app.add_handler(CommandHandler('his', get_user_orders))  # order history
    app.add_handler(CallbackQueryHandler(handle_register_user, pattern="register_user"))

    print("Bot is running...")
    app.run_polling(poll_interval=3)
