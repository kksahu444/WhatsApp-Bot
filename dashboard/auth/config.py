"""
Authentication Configuration
User credentials and authentication settings
"""

import yaml
from pathlib import Path

# Default authentication configuration
# In production, load from secure storage
AUTH_CONFIG = {
    'credentials': {
        'usernames': {
            'admin': {
                'name': 'Admin User',
                'password': '',  # Set hashed password here
                'email': 'admin@example.com',
                'role': 'admin',
            },
            'operator': {
                'name': 'Operator User',
                'password': '',  # Set hashed password here
                'email': 'operator@example.com',
                'role': 'operator',
            },
        }
    },
    'cookie': {
        'name': 'whatsapp_bot_auth',
        'key': '',  # Set from AUTH_SECRET_KEY env var
        'expiry_days': 30,
    },
    'preauthorized': {
        'emails': []
    }
}


def load_auth_config():
    """Load authentication configuration."""
    import os
    
    config = AUTH_CONFIG.copy()
    
    # Set cookie key from environment
    config['cookie']['key'] = os.getenv('AUTH_SECRET_KEY', 'default-secret-key')
    
    # Try to load from config file
    config_path = Path(__file__).parent.parent / 'auth_config.yaml'
    if config_path.exists():
        with open(config_path) as f:
            file_config = yaml.safe_load(f)
            if file_config:
                # Merge configurations
                if 'credentials' in file_config:
                    config['credentials'] = file_config['credentials']
                if 'preauthorized' in file_config:
                    config['preauthorized'] = file_config['preauthorized']
    
    return config


def get_user_role(username: str) -> str:
    """Get user role from config."""
    config = load_auth_config()
    user = config['credentials']['usernames'].get(username, {})
    return user.get('role', 'viewer')
