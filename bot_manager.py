#!/usr/bin/env python3
"""
Bot Manager - Утилита для управления ботами
"""
import subprocess
import sys
import time
import signal
import os

class BotManager:
    """Менеджер для управления экземплярами бота"""
    
    @staticmethod
    def find_bot_processes():
        """Находит все процессы run_v2.py"""
        try:
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            processes = []
            
            for line in result.stdout.split('\n'):
                if 'run_v2.py' in line and 'grep' not in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        pid = parts[1]
                        processes.append(pid)
            
            return processes
        except Exception as e:
            print(f"Ошибка поиска процессов: {e}")
            return []
    
    @staticmethod
    def kill_all_bots():
        """Останавливает все экземпляры ботов"""
        processes = BotManager.find_bot_processes()
        
        if not processes:
            print("✅ Боты не найдены")
            return True
        
        print(f"🔍 Найдено {len(processes)} ботов: {', '.join(processes)}")
        
        for pid in processes:
            try:
                os.kill(int(pid), signal.SIGTERM)
                print(f"🛑 Остановлен бот PID {pid}")
            except ProcessLookupError:
                print(f"⚠️  Бот PID {pid} уже остановлен")
            except Exception as e:
                print(f"❌ Ошибка остановки PID {pid}: {e}")
        
        # Ждем и проверяем
        time.sleep(2)
        remaining = BotManager.find_bot_processes()
        
        if remaining:
            print(f"💀 Принудительная остановка {len(remaining)} ботов...")
            for pid in remaining:
                try:
                    os.kill(int(pid), signal.SIGKILL)
                    print(f"💀 KILL PID {pid}")
                except:
                    pass
        
        print("✅ Все боты остановлены")
        return True
    
    @staticmethod
    def status():
        """Показывает статус ботов"""
        processes = BotManager.find_bot_processes()
        
        if not processes:
            print("✅ Боты не запущены")
        else:
            print(f"🤖 Запущено ботов: {len(processes)}")
            for pid in processes:
                print(f"  - PID {pid}")
        
        return len(processes)
    
    @staticmethod
    def start_bot():
        """Запускает единственный экземпляр бота"""
        # Сначала убиваем все
        BotManager.kill_all_bots()
        
        print("🚀 Запуск нового бота...")
        try:
            # Запускаем в background
            process = subprocess.Popen(['python3', 'run_v2.py'], 
                                     stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE)
            
            # Даем время на запуск
            time.sleep(3)
            
            # Проверяем статус
            if process.poll() is None:
                print(f"✅ Бот запущен с PID {process.pid}")
                return process.pid
            else:
                stdout, stderr = process.communicate()
                print(f"❌ Бот завершился с кодом {process.returncode}")
                if stderr:
                    print(f"Ошибка: {stderr.decode()[:200]}")
                return None
                
        except Exception as e:
            print(f"❌ Ошибка запуска: {e}")
            return None

def main():
    """Главная функция"""
    if len(sys.argv) < 2:
        print("""
🤖 Bot Manager - Управление Telegram ботами

Команды:
  status     - показать статус ботов  
  kill       - остановить все боты
  start      - запустить единственный бот
  restart    - перезапустить бота
        """)
        return
    
    command = sys.argv[1]
    manager = BotManager()
    
    if command == 'status':
        manager.status()
    elif command == 'kill':
        manager.kill_all_bots()
    elif command == 'start':
        manager.start_bot()
    elif command == 'restart':
        manager.kill_all_bots()
        time.sleep(1)
        manager.start_bot()
    else:
        print(f"❌ Неизвестная команда: {command}")

if __name__ == "__main__":
    main()