#!/usr/bin/env python3
"""
Setup script for BrayoForexBot
Installs dependencies and sets up the environment
"""

import subprocess
import sys
import os

def install_dependencies():
    """Install required Python packages"""
    print("📦 Installing dependencies...")
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        return False

def setup_environment():
    """Set up environment configuration"""
    print("⚙️ Setting up environment...")
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        if os.path.exists('.env.example'):
            # Copy example to .env
            with open('.env.example', 'r') as src, open('.env', 'w') as dst:
                dst.write(src.read())
            print("✅ Created .env file from template")
            print("⚠️ Please edit .env file with your API keys and settings")
        else:
            print("❌ .env.example file not found")
            return False
    else:
        print("✅ .env file already exists")
    
    return True

def create_directories():
    """Create necessary directories"""
    print("📁 Creating directories...")
    
    directories = ['logs', 'reports', 'data']
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✅ Created {directory} directory")
        else:
            print(f"✅ {directory} directory already exists")

def main():
    """Main setup function"""
    print("🚀 Setting up BrayoForexBot...")
    print("=" * 50)
    
    # Install dependencies
    if not install_dependencies():
        return False
    
    # Set up environment
    if not setup_environment():
        return False
    
    # Create directories
    create_directories()
    
    print("\n" + "=" * 50)
    print("🎉 Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Edit .env file with your API keys")
    print("2. Run: python cli.py test --notifications")
    print("3. Run: python cli.py backtest EUR/USD 2024-01-01 2024-12-31")
    print("4. Run: python cli.py run")
    print("\n📚 For more info, check README.md")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
