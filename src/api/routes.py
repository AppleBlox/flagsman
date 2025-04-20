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
    
@api.route('/api/debug/flag-analysis')
@async_handler
async def debug_flag_analysis():
    try:
        fetcher = FlagFetcher()
        github_flags = await fetcher.fetch_flags_from_github()
        
        # Analyze the flags in github_flags
        prefixes = {}
        for flag in github_flags.keys():
            prefix = ""
            for p in ["DFFlag", "FFlag", "DFInt", "FInt", "DFString", "FString", "BFFlag"]:
                if flag.startswith(p):
                    prefix = p
                    break
            
            if prefix:
                if prefix not in prefixes:
                    prefixes[prefix] = 1
                else:
                    prefixes[prefix] += 1
            else:
                if "Unknown" not in prefixes:
                    prefixes["Unknown"] = 1
                else:
                    prefixes["Unknown"] += 1
        
        # Check if the target flag exists in github_flags
        target_flag = "DFIntTaskSchedulerTargetFps"
        has_target = target_flag in github_flags
        
        # Get a sample of flag names starting with "DFInt"
        dfint_flags = [f for f in github_flags.keys() if f.startswith("DFInt")][:10]
        
        return jsonify({
            'success': True,
            'github_raw_count': len(github_flags),
            'prefix_analysis': prefixes,
            'has_target_flag': has_target,
            'dfint_sample': dfint_flags,
            'cache_check': target_flag in fetcher._cache.get("ALL", {}).get("applicationSettings", {})
        })
    except Exception as e:
        logger.error(f"Error in flag analysis: {e}")
        return jsonify({'error': f'Error in analysis: {str(e)}'}), 500
    
@api.route('/api/debug/find-flag/<flag_name>')
@async_handler
async def debug_find_flag(flag_name: str):
    try:
        service = FlagService.instance()
        
        # Check all applications for this flag
        results = {}
        for app_id in FlagFetcher.VALID_CLIENTS:
            app_flags = await service.get_application_flags(app_id)
            flag_names = {f.name for f in app_flags}
            results[app_id] = flag_name in flag_names
        
        # Direct check in the FlagFetcher
        fetcher = FlagFetcher()
        github_flags = await fetcher.fetch_flags_from_github()
        in_github = flag_name in github_flags
        
        return jsonify({
            'success': True,
            'flag_name': flag_name,
            'in_applications': results,
            'in_github': in_github
        })
    except Exception as e:
        logger.error(f"Error finding flag {flag_name}: {e}")
        return jsonify({'error': f'Error finding flag: {str(e)}'}), 500