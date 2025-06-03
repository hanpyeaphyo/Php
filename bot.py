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

/role - <b>Check Username MLBB</b>

/getid - <b>Account ID</b>

/price - <b>Price List</b>

/mmp - <b>Order PH</b>

/mmb - <b>Order BR</b>

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

<b>🇵🇭 Philippines:</b>
    11 - diamond 11
    22 - diamond 22
    56 - diamond 56
    112 - diamond 112
    223 - diamond 223
    336 - diamond 336
    570 - diamond 570
    1163 - diamond 1163
    2398 - diamond 2398
    6042 - diamond 6042
    wdp - diamond 95

<b>🇧🇷 Brazil:</b>
    - svp: $39.00
    - 55: $39.00
    - 165: $116.90
    - 275: $187.50
    - 565: $385.00
    
      NORMAL PACK
    
    - wkp: $76.00
    - wkp2: $152.00
    - wkp3: $228.00
    - wkp4: $304.00
    - wkp5: $380.00
    - wkp10: $760.00
    - twilight: $402.50
    - 86: $61.50
    - 172: $122.00
    - 257: $177.50
    - 343: $239.00
    - 344: $244.00
    - 429: $299.50
    - 514: $355.00
    - 600: $416.50
    - 706: $480.00
    - 792: $541.50
    - 878: $602.00
    - 963: $657.50
    - 1049: $719.00
    - 1135: $779.50
    - 1220: $835.00
    - 1412: $960.00
    - 1584: $1082.00
    - 1755: $1199.00
    - 2195: $1453.00
    - 2901: $1940.00
    - 3688: $2424.00
    - 4390: $2906.00
    - 5532: $3660.00
    - 9288: $6079.00
    - 11483: $7532.00"""
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
    admin_user_id = update.message.from_user.id  # Get the user ID of the admin issuing the command

    # Check if the user is an admin
    if admin_user_id not in admins:
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
    new_balance = await update_balance(target_user_id, amount, balance_type)

    if new_balance is not None:
        # Success message with formatting
        await update.message.reply_text(
            f"✅ *Success!* Added `{amount}` to *User ID* `{target_user_id}`'s {balance_type}.\n\n"
            f"🇲🇲 New Balance: `{new_balance}` 🪙",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(f"❌ *Failed*: Unable to update balance for *User ID* `{target_user_id}`.", parse_mode='Markdown')


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
    new_balance = await update_balance(target_user_id, -amount, balance_type)

    if new_balance is not None:
        # Success message with formatting
        await update.message.reply_text(
            f"✅ *Success!* Deducted `{amount}` from *User ID* `{target_user_id}`'s {balance_type}.\n\n"
            f"💵 New Balance: `{new_balance}` 🪙",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"❌ *Failed*: Insufficient balance or unable to deduct for *User ID* `{target_user_id}`.",
            parse_mode='Markdown'
        )


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
        date_joined = datetime.fromtimestamp(
            user.get('date_joined', 0)).strftime('%Y-%m-%d %H:%M:%S')

        # Enhance the output with clear formatting
        response_summary += (
            f"🆔 USER ID: {user_id}\n"
            f" PH BALANCE : ${balance_ph:.2f}\n"
            f" BR BALANCE : ${balance_br:.2f}\n"
            f"📅 DATE JOINED: {date_joined}\n"
            "---------------------------------\n"  # Separator for better readability
        )

    # Split message if it's too long
    messages = split_message(response_summary)

    # Send each chunk of the message
    for msg in messages:
        try:
            await update.message.reply_text(msg)  # Send the message without Markdown
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
        date = order.get('date', 'N/A')
        total_cost = order.get('total_cost', 0.0)
        status = order.get('status', 'N/A')

        if isinstance(order_ids, list):
            order_ids = ', '.join(order_ids)
        else:
            order_ids = str(order_ids)

        response_summary += (
            f"🆔 Telegram ID: {sender_user_id}\n"
            f"📍 Game ID: {user_id}\n"
            f"🌍 Zone ID: {zone_id}\n"
            f"💎 Pack: {pack}\n"
            f"🆔 Order ID: {order_ids}\n"
            f"📅 Date: {date}\n"
            f"💵 Rate: $ {float(total_cost):.2f}\n"
            f"🔄 Status: {status}\n\n"
        )

    # Split the message if it's too long for a single reply
    messages = split_message(response_summary)
    for msg in messages:
        await update.message.reply_text(msg, parse_mode='HTML')


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
            date = order.get('date', 'N/A')
            total_cost = order.get('total_cost', 0.0)
            status = order.get('status', 'N/A')

            if isinstance(order_ids, list):
                order_ids = ', '.join(order_ids)
            else:
                order_ids = str(order_ids)

            response_summary += (
                f"🆔 Sender Telegram ID: {sender_user_id}\n"
                f"🎮 Player ID: {player_id}\n"
                f"🌍 Zone ID: {zone_id}\n"
                f"💎 Product: {product_name}\n"
                f"🆔 Order IDs: {order_ids}\n"
                f"📅 Date: {date}\n"
                f"💵 Total Cost: $ {float(total_cost):.2f}\n"
                f"🔄 Status: {status}\n\n"
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
            f"<b>အသုံးပြုသူ:</b> {username}\n"
            f"<b>  အိုင်ဒီ        :</b> {userid}\n"
            f"<b>  ဆာဗာ        :</b> {zoneid}"
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

    # Format response
    response_message = (
        f"<b>ADMIN BALANCE</b>:\n\n"
        f"🇵🇭 <b>Smile One PH</b>: {points_ph}\n"
        f"🇧🇷 <b>Smile One BR</b>: {points_br}\n"
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

    command = 'mmb' if region == 'br' else 'mmp'

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
                f"<b>Game ID</b>: {user_id}\n"
                f"<b>Game Server</b>: {zone_id}\n"
                f"<b>Items</b>: {product_name}\n"
                f"<b>Results</b>: Invalid Product\n\n"
            )
            continue

        # Determine the rate based on user type
        product_rate = product["rate"]
        if product_rate is None:
            failed_orders.append(
                f"<b>Game ID</b>: {user_id}\n"
                f"<b>Game Server</b>: {zone_id}\n"
                f"<b>Items</b>: {product_name}\n"
                f"<b>Results</b>: Product rate not available\n\n"
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
    balance_to_readd = 0  # Track balance to re-add for failed orders

    for order in order_requests:
        current_balance = await get_balance(sender_user_id)
        if current_balance[balance_type] < order['product_rate']:
            print(f"[ERROR] Insufficient balance during processing for User ID: {sender_user_id}.")
            failed_orders.append(
                f"<b>Game ID:</b> {order['user_id']}\n"
                f"<b>Game Server:</b> {order['zone_id']}\n"
                f"<b>Items:</b> {order['product_name']}\n"
                f"<b>Results:</b> Insufficient Balance\n\n"
            )
            continue

        # Deduct balance for the current order
        new_balance = await update_balance(
            sender_user_id, -order['product_rate'], balance_type)
        if new_balance is None:
            failed_orders.append(
                f"<b>Game ID:</b> {order['user_id']}\n"
                f"<b>Game Server:</b> {order['zone_id']}\n"
                f"<b>Items:</b> {order['product_name']}\n"
                f"<b>Results:</b> Balance Deduction Failed\n\n"
            )
            continue

        # Process the order
        order_ids = []
        for pid in order['product_ids']:
            result = await create_order_and_log(region, order['user_id'], order['zone_id'], pid)
            order_id = result.get("order_id")
            if not order_id:
                # Revert the balance deduction if the order creation fails
                await update_balance(sender_user_id, order['product_rate'], balance_type)
                failed_orders.append(
                    f"<b>Game ID:</b> {order['user_id']}\n"
                    f"<b>Game Server:</b> {order['zone_id']}\n"
                    f"<b>Items:</b> {order['product_name']}\n"
                    f"<b>Results:</b> {result.get('reason', 'Order creation failed')}\n\n"
                )
                break
            order_ids.append(order_id)
        if not order_ids:
            continue

        role_info = await get_role_info(order['user_id'], order['zone_id'])
        if role_info is None:
            await update_balance(sender_user_id, order['product_rate'], balance_type)  # Re-add balance on failure
            failed_orders.append(
                f"<b>Game ID:</b> {order['user_id']}\n"
                f"<b>Game Server:</b> {order['zone_id']}\n"
                f"<b>Items:</b> {order['product_name']}\n"
                f"<b>Results:</b> User ID not exist\n\n"
            )
            continue

        username = role_info.get('username', 'N/A')
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
            "date": datetime.now().strftime('%Y-%m-%d'),
            "total_cost": order['product_rate'],
            "status": "success"
        })

    # Insert all successful transactions
    if transaction_documents:
        await order_collection.insert_many(transaction_documents)

    # Prepare response summary
    response_summary = f"======{region.upper()} Order Summary======\n"
    current_time = datetime.now(ZoneInfo("Asia/Yangon")).strftime('%Y-%m-%d %I:%M:%S %p')  # Myanmar time in 12-hour format with AM/PM
    for detail in order_summary:
        order_ids_str = ', '.join(detail["order_ids"])
        response_summary += (
            f"<b>Order Completed:</b> ✅\n"
            f"<b>Order ID:</b> {order_ids_str}\n"
            f"<b>Game Name:</b> {detail['username']}\n"
            f"<b>Game ID:</b> {detail['user_id']}\n"
            f"<b>Game Server:</b> {detail['zone_id']}\n"
            f"<b>Time:</b> {current_time}\n"
            f"<b>Amount:</b> {detail['product_name']}💎\n"
            f"<b>Total Cost:</b> ${detail['total_cost']:.2f} 🪙\n\n"
        )

    if failed_orders:
        response_summary += "\n<b>Failed Orders 🚫</b>:\n"
        response_summary += "\n".join(failed_orders)

    await loading_message.edit_text(response_summary, parse_mode='HTML')


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
    app.add_handler(CommandHandler('mmp', bulk_command_ph))
    app.add_handler(CommandHandler('mmb', bulk_command_br))
    app.add_handler(CommandHandler('add_bal', add_balance_command))  # add balance for user
    app.add_handler(CommandHandler('ded_bal', deduct_balance_command))  # remove balance from user
    app.add_handler(CommandHandler('user', get_users_command))  # admin command user list collect
    app.add_handler(CommandHandler('all_his', get_all_orders))
    app.add_handler(CommandHandler('his', get_user_orders))  # order history
    app.add_handler(CallbackQueryHandler(handle_register_user, pattern="register_user"))

    print("Bot is running...")
    app.run_polling(poll_interval=3)
