from flask import Blueprint, jsonify, request
from core.flag_service import FlagService
from core.flag_fetcher import FlagFetcher
from functools import wraps
import asyncio
import logging

logger = logging.getLogger(__name__)
api = Blueprint('api', __name__)
flag_service = FlagService.instance()

def async_handler(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(f(*args, **kwargs))
        finally:
            loop.close()
    return wrapper

@api.route('/api/application/<app_id>')
@async_handler
async def get_application_flags(app_id: str):
    try:
        flags = await flag_service.get_application_flags(app_id)
        return jsonify({
            'success': True,
            'flags': [flag.to_dict() for flag in flags]
        })
    except ValueError as e:
        return jsonify({
            'error': str(e),
            'valid_applications': list(FlagFetcher.VALID_CLIENTS)
        }), 400
    except Exception as e:
        logger.error(f"Error getting flags for {app_id}: {e}")
        return jsonify({
            'error': 'Internal server error'
        }), 500

@api.route('/api/check', methods=['POST'])
@async_handler
async def check_flags():
    try:
        data = request.get_json()
        if not data or not isinstance(data, dict):
            return jsonify({'error': 'Invalid JSON payload'}), 400

        flags = data.get('flags', [])
        applications = data.get('applications', [])

        if not isinstance(flags, list) or not isinstance(applications, list):
            return jsonify({'error': 'flags and applications must be arrays'}), 400

        if not flags or not applications:
            return jsonify({'error': 'flags and applications arrays cannot be empty'}), 400

        result = await flag_service.check_flags(flags, applications)
        return jsonify({
            'success': True,
            'valid': result.valid,
            'invalid': result.invalid,
            'risk': result.risk
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error checking flags: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@api.route('/')
@async_handler
async def get_stats():
    try:
        stats = flag_service.stats
        return jsonify({
            'success': True,
            'uptime': stats.uptime,
            'last_fetch': stats.last_fetch.isoformat() if stats.last_fetch else None,
            'cache_size': stats.cache_size
        })
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500