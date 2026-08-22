import os
import requests
from datetime import datetime, timedelta
import json
import time
from zoneinfo import ZoneInfo

BERLIN_TZ = ZoneInfo("Europe/Berlin")

def now_berlin():
    return datetime.now(BERLIN_TZ)

# Environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8820415070:AAEbCXPeHbnxPdeENZCn7S8NaxCR4V3qCmM')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '714276411113')

# Special dates
FIRST_INCOMPLETE_WEEK_DATE = '2026-08-22'

# Hamburg School Holidays 2026-2027
SCHOOL_HOLIDAYS = [
    ('2026-05-11', '2026-05-15'),
    ('2026-05-26', '2026-05-30'),
    ('2026-07-09', '2026-08-25'),
    ('2026-10-19', '2026-10-30'),
    ('2026-12-21', '2027-01-01'),
    ('2027-03-01', '2027-03-12'),
    ('2027-05-07', '2027-05-15'),
    ('2027-07-01', '2027-08-11'),
]

# Hamburg Public Holidays 2026-2027
PUBLIC_HOLIDAYS = [
    '2026-01-01', '2026-04-03', '2026-04-06', '2026-05-01', '2026-05-14', '2026-05-25',
    '2026-10-03', '2026-10-31', '2026-12-25', '2026-12-26',
    '2027-01-01', '2027-04-02', '2027-04-05', '2027-05-01', '2027-05-13', '2027-05-24',
    '2027-10-03', '2027-10-31',
]

class BreakfastReminder:
    def __init__(self):
        self.recipes = {}
        self.inventory = {}
        self.week_plan = {}
        self.load_storage()
    
    def load_storage(self):
        """Load recipes and week plan from storage file"""
        storage_file = os.getenv('STORAGE_FILE', '/tmp/breakfast_storage.json')
        if os.path.exists(storage_file):
            try:
                with open(storage_file, 'r') as f:
                    data = json.load(f)
                    self.recipes = data.get('recipes', {})
                    self.inventory = data.get('inventory', {})
                    self.week_plan = data.get('weekplan', {})
            except:
                pass
    
    def is_school_day(self, date_str):
        """Check if date is a school day"""
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Not a weekday
        if date_obj.weekday() >= 5:
            return False
        
        # Is public holiday
        if date_str in PUBLIC_HOLIDAYS:
            return False
        
        # Is in school holidays
        for start, end in SCHOOL_HOLIDAYS:
            if start <= date_str <= end:
                return False
        
        return True
    
    def send_telegram_message(self, message):
        """Send message via Telegram bot"""
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        try:
            response = requests.post(url, json=payload)
            return response.status_code == 200
        except Exception as e:
            print(f"Error sending Telegram message: {e}")
            return False
    
    def send_weekly_plan_reminder(self):
        """Saturday: send weekly recipe picks + shopping list"""
        today = now_berlin().strftime('%Y-%m-%d')
        today_obj = now_berlin()
        
        if today_obj.weekday() != 5:  # Not Saturday
            return False
        
        week_recipes = self.week_plan.get('recipes', [])
        
        # Special handling for first incomplete week (Aug 22, 2026)
        if today == FIRST_INCOMPLETE_WEEK_DATE:
            recipes_to_show = week_recipes[2:5] if len(week_recipes) >= 5 else week_recipes[2:]
            message = "📋 <b>First Week Breakfast Plan (Wed-Fri)</b>\n"
            message += "<i>Only 3 days - school starts Wednesday!</i>\n\n"
        else:
            recipes_to_show = week_recipes
            message = "📋 <b>This Week's Breakfast Plan</b>\n\n"
        
        if not recipes_to_show:
            message += "No recipes selected yet. Please pick recipes in the app."
        else:
            for i, recipe_id in enumerate(recipes_to_show, 1):
                recipe = self.recipes.get(recipe_id, {})
                message += f"{i}. {recipe.get('name', 'Unknown')}\n"
            
            shopping_list = self.week_plan.get('shoppingList', {})
            if shopping_list:
                message += "\n🛒 <b>Shopping List</b>\n"
                
                mains = shopping_list.get('mains', [])
                if mains:
                    message += "\n<b>Mains:</b>\n"
                    for item in mains:
                        message += f"• {item}\n"
                
                extras = shopping_list.get('extras', [])
                if extras:
                    message += "\n<b>Extras (Fruit & Bits):</b>\n"
                    for item in extras:
                        message += f"• {item}\n"
        
        return self.send_telegram_message(message)
    
    def send_morning_reminder(self):
        """7am Mon-Fri: same-morning prep reminder"""
        today = now_berlin().strftime('%Y-%m-%d')
        today_obj = now_berlin()
        
        # Only Mon-Fri
        if today_obj.weekday() >= 5:
            return False
        
        # Skip if not a school day
        if not self.is_school_day(today):
            return False
        
        message = "☀️ <b>Good Morning!</b>\n\n"
        message += "Time to prepare today's breakfast. Check the app for today's recipe.\n\n"
        message += "Recipes needing same-morning prep: Standard & From-Frozen (reheat)"
        
        return self.send_telegram_message(message)
    
    def send_evening_reminder(self):
        """8pm Sun-Thu: overnight prep / defrost reminder"""
        today = now_berlin().strftime('%Y-%m-%d')
        today_obj = now_berlin()
        tomorrow_obj = today_obj + timedelta(days=1)
        tomorrow = tomorrow_obj.strftime('%Y-%m-%d')
        
        # Only Sun-Thu
        if today_obj.weekday() >= 4:
            return False
        
        # Skip if tomorrow is not a school day
        if not self.is_school_day(tomorrow):
            return False
        
        message = "🌙 <b>Evening Prep</b>\n\n"
        message += "Remember to prepare overnight items for tomorrow:\n"
        message += "• Overnight oats (refrigerate)\n"
        message += "• Frozen items (move to fridge to defrost)\n\n"
        message += "Check the app for tomorrow's recipe."
        
        return self.send_telegram_message(message)
    
    def send_weekend_reminder(self):
        """10am Sat & Sun: weekend batch-cook reminder"""
        today_obj = now_berlin()
        
        # Only Sat & Sun
        if today_obj.weekday() < 5:
            return False
        
        message = "👩‍🍳 <b>Weekend Batch Prep</b>\n\n"
        message += "Time to prepare batch items:\n"
        message += "• Cooked apples (for porridge)\n"
        message += "• Banana pancakes\n"
        message += "• Granola\n"
        message += "• Check Kindermüsli stock\n\n"
        message += "Refrigerate as needed for the week ahead."
        
        return self.send_telegram_message(message)
    
    def run_once(self):
        """Check time and send appropriate reminder — called every loop tick"""
        now = now_berlin()
        hour = now.hour
        minute = now.minute
        key = now.strftime('%Y-%m-%d-%H')  # one send per hour-slot max

        if key == self.last_sent_key:
            return  # already sent this hour's reminder

        sent = False

        # 7am morning reminder
        if hour == 7 and minute < 2:
            sent = self.send_morning_reminder()

        # 8pm evening reminder
        elif hour == 20 and minute < 2:
            sent = self.send_evening_reminder()

        # 9am Saturday weekly plan
        elif hour == 9 and minute < 2 and now.weekday() == 5:
            sent = self.send_weekly_plan_reminder()

        # 10am Sat & Sun weekend batch reminder
        elif hour == 10 and minute < 2 and now.weekday() >= 5:
            sent = self.send_weekend_reminder()

        if sent:
            self.last_sent_key = key

if __name__ == "__main__":
    print("Breakfast Box Automation starting — continuous loop, checking every 30s", flush=True)
    reminder = BreakfastReminder()
    reminder.last_sent_key = None
    while True:
        try:
            reminder.run_once()
        except Exception as e:
            print(f"Error in run_once: {e}", flush=True)
        time.sleep(30)
