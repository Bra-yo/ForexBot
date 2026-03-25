"""
Telegram Webhook Handler for Interactive Trading Bot
Processes callback queries from inline keyboard buttons
"""

import json
import logging
from flask import Flask, request, abort
from advanced_telegram_assistant import AdvancedTelegramAssistant

logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize Telegram assistant
telegram_assistant = AdvancedTelegramAssistant()

@app.route('/webhook/telegram', methods=['POST'])
def telegram_webhook():
    """Handle incoming Telegram updates"""
    try:
        if request.method == 'POST':
            update = request.get_json()
            
            # Process callback queries
            if 'callback_query' in update:
                callback_query = update['callback_query']
                callback_data = callback_query.get('data', '')
                callback_query_id = callback_query.get('id', '')
                
                # Handle the callback
                success = telegram_assistant.handle_callback_query(callback_data, callback_query_id)
                
                if success:
                    logger.info(f"Successfully handled callback: {callback_data}")
                else:
                    logger.warning(f"Failed to handle callback: {callback_data}")
            
            return {'status': 'success'}, 200
    
    except Exception as e:
        logger.error(f"Error in webhook: {e}")
        return {'status': 'error', 'message': str(e)}, 500

@app.route('/webhook/telegram', methods=['GET'])
def get_webhook_info():
    """Get webhook status"""
    return {'status': 'running', 'webhook': 'telegram'}

@app.route('/')
def index():
    """Root endpoint"""
    return {'message': 'BrayoForexBot Telegram Webhook', 'status': 'active'}

if __name__ == '__main__':
    # Run webhook server
    app.run(host='0.0.0.0', port=8443, debug=True)
