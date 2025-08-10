#!/usr/bin/env python3
import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, '/app')

async def debug_session():
    from app.core.dependencies import container
    from app.repositories.telegram_connection_repository import TelegramConnectionRepository
    from app.core.security import get_encryption_service
    
    user_id = '68717fa198504e5aaa8abd61bd7f9533'
    conn_repo = container.resolve(TelegramConnectionRepository)
    encryption_service = get_encryption_service()
    
    print(f"🔍 Debugging session for user: {user_id}")
    
    # Get the connection
    connection = await conn_repo.get_by_user_id(user_id)
    if connection:
        print(f"✅ Found connection for user {user_id}")
        print(f"   - Active: {connection.is_active}")
        print(f"   - Validation status: {connection.validation_status}")
        print(f"   - Encrypted data length: {len(connection.session_string_encrypted) if connection.session_string_encrypted else 0}")
        
        # Try to decrypt
        try:
            decrypted = encryption_service.decrypt_session_string(connection.session_string_encrypted)
            print(f"✅ Decryption successful")
            print(f"   - Length: {len(decrypted)}")
            print(f"   - First 50 chars: {decrypted[:50]}...")
            print(f"   - Type: {type(decrypted)}")
            
            # Test if it's a valid Telethon session
            from telethon.sessions import StringSession
            try:
                session = StringSession(decrypted)
                print(f"✅ Valid Telethon session string")
            except Exception as e:
                print(f"❌ Invalid Telethon session string: {e}")
                
        except Exception as e:
            print(f"❌ Decryption failed: {e}")
    else:
        print(f"❌ No connection found for user {user_id}")
        
        # Check if there are any connections at all
        from app.models.telegram_connection import TelegramConnection
        from sqlalchemy.orm import sessionmaker
        from app.database import engine
        
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        try:
            all_connections = db.query(TelegramConnection).all()
            print(f"📊 Total connections in database: {len(all_connections)}")
            for conn in all_connections:
                print(f"   - User {conn.user_id}: active={conn.is_active}, status={conn.validation_status}")
        finally:
            db.close()

if __name__ == "__main__":
    asyncio.run(debug_session()) 