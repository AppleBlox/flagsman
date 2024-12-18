from flask import Flask
from api.routes import api
from core.flag_service import FlagService
import asyncio
import os
import json
import logging
from datetime import datetime
import atexit

def setup_logging():

    os.makedirs('logs', exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f'logs/appleblox_{datetime.now().strftime("%Y%m%d")}.log'),
            logging.StreamHandler()
        ]
    )

def create_app():

    app = Flask(__name__)
    

    app.config['JSON_SORT_KEYS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024  
    

    app.register_blueprint(api)
    

    @app.errorhandler(404)
    def not_found(e):
        return {'error': 'Not found'}, 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return {'error': 'Method not allowed'}, 405

    @app.errorhandler(500)
    def server_error(e):
        logging.error(f"Server error: {str(e)}")
        return {'error': 'Internal server error'}, 500

    return app

def ensure_data_files():
    os.makedirs('data', exist_ok=True)
    
    default_files = {
        'whitelist.json': '[]',
        'risklist.json': '[]'
    }
    
    for filename, content in default_files.items():
        filepath = os.path.join('data', filename)
        if not os.path.exists(filepath):
            with open(filepath, 'w') as f:
                f.write(content)
            logging.info(f"Created default {filename}")

async def init_services():
    try:
        service = FlagService.instance()
        await service.update_cache()
        logging.info("Services initialized successfully")
    except Exception as e:
        logging.error(f"Service initialization failed: {e}")
        raise

def cleanup():

    logging.info("Shutting down FLAGSMAN API")

def main():

    setup_logging()
    logging.info("Starting FLAGSMAN API")
    
    try:

        ensure_data_files()
        

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        

        loop.run_until_complete(init_services())
        

        atexit.register(cleanup)
        

        app = create_app()
        app.run(
            host='0.0.0.0',
            port=8000,
            threaded=True,
            use_reloader=False 
        )
        
    except Exception as e:
        logging.error(f"Application startup failed: {e}")
        raise

if __name__ == '__main__':
    main()