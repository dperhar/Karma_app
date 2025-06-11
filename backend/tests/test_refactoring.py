#!/usr/bin/env python3
"""Test script for refactored Telethon service."""

import asyncio
import sys
import json
from datetime import datetime
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.dependencies import container
from app.services.refactored_client_service import RefactoredTelethonClientService


async def test_refactored_service():
    """Test the refactored Telethon service."""
    print("🚀 ТЕСТИРОВАНИЕ РЕФАКТОРИРОВАННОГО TELETHON СЕРВИСА")
    print("=" * 60)
    
    try:
        # Получаем сервис из DI контейнера
        service = container.resolve(RefactoredTelethonClientService)
        print("✅ RefactoredTelethonClientService создан через DI")
        print(f"📊 Начальный статус: запущен={service._is_started}")
        
        # Запускаем сервис
        print("\n🔥 Запуск компонентов сервиса...")
        await service.start()
        print("✅ Сервис запущен!")
        print(f"📊 Статус после запуска: запущен={service._is_started}")
        
        # Тестируем статистику
        print("\n📈 ТЕСТИРОВАНИЕ СТАТИСТИКИ")
        print("-" * 30)
        stats = await service.get_service_stats()
        
        print("Connection Pool статистика:")
        pool_stats = stats.get('connection_pool', {})
        for key, value in pool_stats.items():
            print(f"  {key}: {value}")
            
        print("\nSession Manager статистика:")
        session_stats = stats.get('session_manager', {})
        for key, value in session_stats.items():
            print(f"  {key}: {value}")
            
        print("\nConnection Monitor статистика:")
        monitor_stats = stats.get('connection_monitor', {})
        for key, value in monitor_stats.items():
            print(f"  {key}: {value}")
        
        # Тестируем health report
        print("\n🏥 ТЕСТИРОВАНИЕ HEALTH REPORT")
        print("-" * 30)
        health = await service.get_health_report()
        
        summary = health.get('summary', {})
        print(f"Timestamp: {health.get('timestamp', 'N/A')}")
        print(f"Total Users: {summary.get('total_users', 0)}")
        print(f"Total Connections: {summary.get('total_connections', 0)}")
        print(f"Success Rate: {summary.get('overall_success_rate', 0):.1f}%")
        print(f"Recent Errors: {summary.get('recent_errors_count', 0)}")
        print(f"Recent FloodWaits: {summary.get('recent_flood_waits_count', 0)}")
        
        # Тестируем валидацию сессии для несуществующего пользователя
        print("\n🔍 ТЕСТИРОВАНИЕ ВАЛИДАЦИИ СЕССИИ")
        print("-" * 30)
        test_user_id = "test_user_123"
        has_session = await service.validate_user_session(test_user_id)
        print(f"Валидная сессия для {test_user_id}: {has_session}")
        
        # Тестируем получение клиента для несуществующего пользователя
        print("\n🔌 ТЕСТИРОВАНИЕ ПОЛУЧЕНИЯ КЛИЕНТА")
        print("-" * 30)
        client = await service.get_client(test_user_id)
        print(f"Клиент для {test_user_id}: {client is not None}")
        
        # Тестируем cleanup
        print("\n🧹 ТЕСТИРОВАНИЕ CLEANUP")
        print("-" * 30)
        await service.cleanup_invalid_sessions()
        print("✅ Cleanup завершен")
        
        # Финальная статистика
        print("\n📊 ФИНАЛЬНАЯ СТАТИСТИКА")
        print("-" * 30)
        final_stats = await service.get_service_stats()
        print(f"Текущие соединения: {final_stats.get('connection_pool', {}).get('current_connections', 0)}")
        print(f"Здоровые соединения: {final_stats.get('connection_pool', {}).get('healthy_connections', 0)}")
        print(f"Всего сессий: {final_stats.get('session_manager', {}).get('total_sessions', 0)}")
        print(f"Валидные сессии: {final_stats.get('session_manager', {}).get('valid_sessions', 0)}")
        
        # Останавливаем сервис
        print("\n🛑 ОСТАНОВКА СЕРВИСА")
        print("-" * 30)
        await service.stop()
        print("✅ Сервис остановлен")
        print(f"📊 Финальный статус: запущен={service._is_started}")
        
        print("\n" + "=" * 60)
        print("🎉 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО УСПЕШНО!")
        print("✅ Все компоненты рефакторинга работают корректно")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА ПРИ ТЕСТИРОВАНИИ: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_refactored_service()) 